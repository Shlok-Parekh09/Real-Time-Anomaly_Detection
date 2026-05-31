"""
Quick test script to verify highlighting functionality
"""

import sys

# Test 1: Check if PyPDF2 is available
print("=" * 60)
print("TEST 1: Checking PyPDF2 availability")
print("=" * 60)
try:
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import DictionaryObject, NameObject, ArrayObject, FloatObject
    print("✓ PyPDF2 is installed and importable")
except ImportError as e:
    print(f"✗ PyPDF2 import failed: {e}")
    print("  Install with: pip install PyPDF2")
    sys.exit(1)

# Test 2: Check if PyMuPDF is available
print("\n" + "=" * 60)
print("TEST 2: Checking PyMuPDF availability")
print("=" * 60)
try:
    import fitz
    print(f"✓ PyMuPDF (fitz) is installed - version {fitz.version}")
except ImportError as e:
    print(f"✗ PyMuPDF import failed: {e}")
    print("  Install with: pip install PyMuPDF")
    sys.exit(1)

# Test 3: Check if OpenCV is available
print("\n" + "=" * 60)
print("TEST 3: Checking OpenCV availability")
print("=" * 60)
try:
    import cv2
    print(f"✓ OpenCV is installed - version {cv2.__version__}")
except ImportError as e:
    print(f"✗ OpenCV import failed: {e}")
    print("  Install with: pip install opencv-python")

# Test 4: Test PDF text extraction
print("\n" + "=" * 60)
print("TEST 4: Testing PDF text coordinate extraction")
print("=" * 60)
try:
    from text_coordinate_extractor import extract_pdf_text_coordinates
    
    # Create a simple test PDF
    test_text = "Test document with amount $1,234.56 and date 12/05/2017"
    print(f"Test text: {test_text}")
    
    # For now, just check if function exists
    print("✓ extract_pdf_text_coordinates function is available")
    print("  (Actual PDF test requires a real PDF file)")
    
except Exception as e:
    print(f"✗ PDF coordinate extraction test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test pattern extraction (DISABLED - extract_suspicious_text_patterns does not exist)
print("\n" + "=" * 60)
print("TEST 5: Testing suspicious pattern extraction (Disabled)")
print("=" * 60)
try:
    pass
    # from text_coordinate_extractor import extract_suspicious_text_patterns
    # 
    # test_text = """
    # Account Statement
    # Account No: 1234567890
    # Balance: $5,000.00
    # Date: 12/05/2017
    # Deposit: $1,234.56
    # Withdrawal: $500.00
    # """
    # 
    # patterns = extract_suspicious_text_patterns(test_text)
    # print(f"✓ Extracted {len(patterns)} suspicious patterns:")
    # for i, pattern in enumerate(patterns[:10], 1):
    #     print(f"  {i}. {pattern}")
    # 
    # if len(patterns) == 0:
    #     print("  ⚠ Warning: No patterns extracted - check pattern matching logic")
    
except Exception as e:
    print(f"✗ Pattern extraction test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Test PDF highlighter
print("\n" + "=" * 60)
print("TEST 6: Testing PDF highlighter")
print("=" * 60)
try:
    from pdf_highlighter import create_highlight_annotation, get_severity_color
    
    # Test color mapping
    colors = {
        "high": get_severity_color("high"),
        "medium": get_severity_color("medium"),
        "low": get_severity_color("low"),
    }
    
    print("✓ Severity color mapping:")
    for severity, color in colors.items():
        print(f"  {severity}: RGB{color}")
    
    # Test annotation creation
    annotation = create_highlight_annotation(100, 100, 200, 120, colors["high"], 800)
    print(f"✓ Created highlight annotation: {type(annotation)}")
    
except Exception as e:
    print(f"✗ PDF highlighter test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Test image highlighter
print("\n" + "=" * 60)
print("TEST 7: Testing image highlighter")
print("=" * 60)
try:
    from image_highlighter import get_severity_color_bgr
    
    # Test color mapping
    colors = {
        "high": get_severity_color_bgr("high"),
        "medium": get_severity_color_bgr("medium"),
        "low": get_severity_color_bgr("low"),
    }
    
    print("✓ Severity color mapping (BGR):")
    for severity, color in colors.items():
        print(f"  {severity}: BGR{color}")
    
except Exception as e:
    print(f"✗ Image highlighter test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("All basic tests completed!")
print("\nTo test with a real PDF:")
print("1. Place a PDF file in this directory as 'test.pdf'")
print("2. Run: python test_highlighting_real.py")
print("\nTo test the full API:")
print("1. Start the backend: uvicorn main:app --reload")
print("2. Upload a document through the frontend")
print("3. Check browser console for '[HIGHLIGHTING]' logs")
print("4. Check backend terminal for coordinate extraction logs")

