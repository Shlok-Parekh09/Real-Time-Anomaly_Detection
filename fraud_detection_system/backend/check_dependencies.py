"""
Quick dependency checker for highlighting feature
"""

print("=" * 70)
print("CHECKING HIGHLIGHTING DEPENDENCIES")
print("=" * 70)

dependencies = {
    "PyPDF2": "pip install PyPDF2",
    "fitz (PyMuPDF)": "pip install PyMuPDF",
    "cv2 (OpenCV)": "pip install opencv-python",
    "pytesseract": "pip install pytesseract",
    "PIL (Pillow)": "pip install Pillow",
    "numpy": "pip install numpy",
}

missing = []
installed = []

for name, install_cmd in dependencies.items():
    try:
        if "fitz" in name:
            import fitz
            installed.append(f"✓ {name} - version {fitz.version}")
        elif "PyPDF2" in name:
            import PyPDF2
            installed.append(f"✓ {name} - installed")
        elif "cv2" in name:
            import cv2
            installed.append(f"✓ {name} - version {cv2.__version__}")
        elif "pytesseract" in name:
            import pytesseract
            installed.append(f"✓ {name} - installed")
        elif "PIL" in name:
            from PIL import Image
            installed.append(f"✓ {name} - installed")
        elif "numpy" in name:
            import numpy
            installed.append(f"✓ {name} - version {numpy.__version__}")
    except ImportError:
        missing.append(f"✗ {name} - NOT INSTALLED")
        missing.append(f"  Install with: {install_cmd}")

print("\nINSTALLED:")
for item in installed:
    print(item)

if missing:
    print("\nMISSING:")
    for item in missing:
        print(item)
    print("\n" + "=" * 70)
    print("INSTALL ALL MISSING DEPENDENCIES:")
    print("=" * 70)
    print("pip install PyPDF2 PyMuPDF opencv-python pytesseract Pillow numpy")
else:
    print("\n" + "=" * 70)
    print("✓ ALL DEPENDENCIES INSTALLED!")
    print("=" * 70)
    print("\nYou can now use the highlighting feature.")
    print("Restart the backend if it's already running.")

print("\n" + "=" * 70)
print("QUICK TEST")
print("=" * 70)

try:
    import fitz
    print("✓ Can import fitz (PyMuPDF)")
    
    # Try to create a simple PDF
    doc = fitz.open()
    page = doc.new_page()
    print("✓ Can create PDF pages")
    
    # Try to add text
    page.insert_text((100, 100), "Test")
    print("✓ Can add text to PDF")
    
    # Try to search
    results = page.search_for("Test")
    print(f"✓ Can search text in PDF - found {len(results)} instances")
    
    doc.close()
    print("\n✓ PyMuPDF is working correctly!")
    
except Exception as e:
    print(f"\n✗ PyMuPDF test failed: {e}")

try:
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import DictionaryObject
    print("✓ Can import PyPDF2 components")
    print("\n✓ PyPDF2 is working correctly!")
except Exception as e:
    print(f"\n✗ PyPDF2 test failed: {e}")
