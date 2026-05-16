import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from collections import defaultdict
import io
import tempfile
import os

def _looks_like_pdf(document_bytes: bytes) -> bool:
    return document_bytes.startswith(b"%PDF")

def perform_ela(image_bytes: bytes, quality: int = 90) -> tuple[bytes, float, list[str]]:
    """
    Performs Error Level Analysis (ELA) on an image to detect potential manipulations.
    
    Args:
        image_bytes: Raw image data.
        quality: JPEG compression quality for ELA comparison.
        
    Returns:
        tuple containing:
        - heatmap_bytes: The generated ELA heatmap image as PNG bytes.
        - risk_score: A calculated risk score (0-100) based on ELA anomalies.
        - anomalies: A list of string descriptions of specific anomalies found.
    """
    if _looks_like_pdf(image_bytes):
        return b"", 0.0, []

    temp_filename = None
    try:
        # Load original image
        original_img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # Save to a temporary file at specific quality to induce compression artifacts
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_filename = temp_file.name
            original_img.save(temp_filename, 'JPEG', quality=quality)
            
        # Load compressed image
        compressed_img = Image.open(temp_filename)
        
        # Calculate the absolute difference between original and compressed
        ela_img = ImageChops.difference(original_img, compressed_img)
        
        # Enhance the difference to make it visible
        extrema = ela_img.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
        
        scale = 255.0 / max_diff
        ela_img = ImageEnhance.Brightness(ela_img).enhance(scale)
        
        # Convert to OpenCV format to calculate heatmap and score
        ela_cv = np.array(ela_img)
        ela_cv = cv2.cvtColor(ela_cv, cv2.COLOR_RGB2BGR)
        
        # Apply a colormap for the heatmap (JET works well for highlighting hot spots)
        heatmap = cv2.applyColorMap(cv2.cvtColor(ela_cv, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_JET)
        
        # Convert heatmap back to bytes
        is_success, buffer = cv2.imencode(".png", heatmap)
        if not is_success:
            return b"", 0.0, ["Failed to encode ELA heatmap."]
        heatmap_bytes = io.BytesIO(buffer).getvalue()
        
        # Calculate a basic risk score based on the variance and max differences
        gray_ela = cv2.cvtColor(ela_cv, cv2.COLOR_BGR2GRAY)
        mean_diff = np.mean(gray_ela)
        std_diff = np.std(gray_ela)
        
        # A simple heuristic: high standard deviation indicates localized tampering (copy-paste)
        # where some regions have drastically different compression artifacts than the rest.
        risk_score = min(100.0, (std_diff / 50.0) * 100.0)
        
        anomalies = []
        if risk_score > 60:
            anomalies.append(f"Inconsistent compression levels detected (Score: {risk_score:.1f}). Possible localized manipulation.")
            
        if mean_diff > 40:
            anomalies.append(f"High overall pixel variance detected. Image may have been resaved multiple times.")

        return heatmap_bytes, risk_score, anomalies
        
    except Exception as e:
        print(f"Error during ELA: {e}")
        return b"", 0.0, [f"Failed to perform ELA: {str(e)}"]
    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)

def extract_metadata(image_bytes: bytes) -> tuple[dict, list[str]]:
    """
    Extracts basic EXIF metadata and checks for suspicious tags.
    """
    if _looks_like_pdf(image_bytes):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(image_bytes))
            metadata = {
                str(key).lstrip("/"): str(value)
                for key, value in (reader.metadata or {}).items()
                if value is not None
            }
            anomalies = []
            producer = " ".join(
                metadata.get(key, "") for key in ("Producer", "Creator", "ModDate")
            ).lower()
            suspicious_software = ['photoshop', 'illustrator', 'gimp', 'canva']
            if any(signature in producer for signature in suspicious_software):
                anomalies.append("Suspicious PDF metadata: editing software signature detected.")
            return metadata, anomalies
        except ImportError:
            return {}, []
        except Exception as e:
            return {}, [f"Failed to extract PDF metadata: {str(e)}"]

    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        
        metadata = {}
        anomalies = []
        
        if exif is not None:
            # Simple EXIF tag extraction (Tag 305 is Software)
            for tag_id, value in exif.items():
                # 305 = Software
                if tag_id == 305:
                    metadata['Software'] = str(value)
                    suspicious_software = ['photoshop', 'illustrator', 'gimp', 'canva']
                    if any(s in str(value).lower() for s in suspicious_software):
                        anomalies.append(f"Suspicious metadata: Editing software signature detected ({value})")
        
        return metadata, anomalies
    except Exception as e:
        return {}, [f"Failed to extract metadata: {str(e)}"]

def detect_copy_move(image_bytes: bytes) -> tuple[float, list[str]]:
    """
    Detects Copy-Move forgery by extracting ORB features and finding dense clusters 
    of identical keypoints that are spatially separated.
    """
    if _looks_like_pdf(image_bytes):
        return 0.0, []

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0, []
        
        # Initialize ORB
        orb = cv2.ORB_create(nfeatures=1000)
        
        # Find keypoints and descriptors
        keypoints, descriptors = orb.detectAndCompute(img, None)
        
        if descriptors is None or len(keypoints) < 10:
            return 0.0, []
            
        # Match descriptors against themselves, then keep only strong non-self matches.
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(descriptors, descriptors, k=4)
        
        displacement_clusters = defaultdict(list)
        spatial_threshold = 40.0  # minimum pixel distance between original and cloned area
        cluster_bin_size = 16.0
        
        for m_list in matches:
            non_self_matches = [match for match in m_list if match.queryIdx != match.trainIdx]
            if len(non_self_matches) < 2:
                continue

            best, second_best = non_self_matches[:2]
            if best.distance > 32 or best.distance > 0.75 * second_best.distance:
                continue

            pt1 = keypoints[best.queryIdx].pt
            pt2 = keypoints[best.trainIdx].pt
            dx = pt2[0] - pt1[0]
            dy = pt2[1] - pt1[1]
            dist = np.sqrt(dx**2 + dy**2)
            if dist <= spatial_threshold:
                continue

            cluster_key = (round(dx / cluster_bin_size), round(dy / cluster_bin_size))
            displacement_clusters[cluster_key].append((pt1, pt2))

        min_cluster_size = max(18, int(len(keypoints) * 0.04))
        clone_clusters = [
            cluster
            for cluster in displacement_clusters.values()
            if len(cluster) >= min_cluster_size
        ]
        num_clones = max((len(cluster) for cluster in clone_clusters), default=0)
        
        anomalies = []
        risk_score = 0.0
        
        if clone_clusters:
            risk_score = min(100.0, num_clones * 1.5)
            anomalies.append(
                f"Copy-Move forgery pattern detected: {num_clones} matched keypoints share a consistent displacement."
            )
            
        return risk_score, anomalies
    except Exception as e:
        print(f"Error in copy-move: {e}")
        return 0.0, [f"Copy-move check failed: {e}"]
