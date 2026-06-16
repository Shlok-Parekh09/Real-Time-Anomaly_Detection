import fitz  # PyMuPDF
from models.domain import AnomalyFeature

def validate_metadata(file_path: str) -> list[AnomalyFeature]:
    """
    Parses the PDF /Info dictionary to detect traces of consumer editing software 
    and validates timestamps.
    """
    anomalies = []
    
    try:
        # PyMuPDF opens the file locally without internet
        doc = fitz.open(file_path)
        metadata = doc.metadata
        
        producer = metadata.get("producer", "").lower()
        creator = metadata.get("creator", "").lower()
        
        # Blacklist of common consumer tools used to fake documents
        suspicious_tools = [
            "ilovepdf", "adobe acrobat", "smallpdf", 
            "canva", "corel", "pdf24", "sejda", "foxit"
        ]
        
        detected_tool = None
        for tool in suspicious_tools:
            if tool in producer or tool in creator:
                detected_tool = tool.title()
                break
                
        if detected_tool:
            anomalies.append(AnomalyFeature(
                type="Suspicious Software Trace",
                description=f"PDF metadata indicates modification via consumer editing software: {detected_tool}",
                risk_level="High"
            ))
            
        # Timestamp manipulation check
        creation_date = metadata.get("creationDate", "")
        mod_date = metadata.get("modDate", "")
        
        if creation_date and mod_date and creation_date != mod_date:
            anomalies.append(AnomalyFeature(
                type="Timestamp Mismatch",
                description="The modification date of this document is different from its creation date, indicating it was edited post-generation.",
                risk_level="Low"
            ))
            
        doc.close()
    except Exception as e:
        anomalies.append(AnomalyFeature(
            type="Forensic Parse Error",
            description=f"Could not inspect PDF internals: {str(e)}",
            risk_level="Medium"
        ))
        
    return anomalies
