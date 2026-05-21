#!/usr/bin/env python3
"""
Test script to verify Word document X-ray recovery functionality.
This script tests the _word_recovered_version function with a sample Word document.
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fraud_detection_system', 'backend'))

from forensics import recover_previous_version, detect_file_type


def test_word_xray():
    """Test Word document X-ray recovery."""
    print("=" * 60)
    print("Word Document X-ray Recovery Test")
    print("=" * 60)
    
    # Test with a sample file path (you'll need to provide an actual .docx file)
    test_file = "test.docx"
    
    if not os.path.exists(test_file):
        print(f"\n❌ Test file '{test_file}' not found.")
        print("\nTo test Word X-ray recovery:")
        print("1. Create a Word document with tracked changes")
        print("2. Save it as 'test.docx' in the project root")
        print("3. Run this script again")
        return
    
    print(f"\n📄 Testing file: {test_file}")
    
    # Read the file
    with open(test_file, 'rb') as f:
        file_bytes = f.read()
    
    # Detect file type
    file_type = detect_file_type(test_file, "", file_bytes)
    print(f"✓ Detected file type: {file_type}")
    
    # Recover previous version
    print("\n🔍 Running X-ray recovery...")
    result = recover_previous_version(file_bytes, test_file, "")
    
    # Display results
    print("\n" + "=" * 60)
    print("X-ray Recovery Results")
    print("=" * 60)
    print(f"\n✓ Available: {result['available']}")
    print(f"✓ Title: {result['title']}")
    print(f"✓ Method: {result['method']}")
    print(f"✓ Confidence: {result['confidence'] * 100:.1f}%")
    print(f"\n📝 Summary:\n{result['summary']}")
    
    if result['changes']:
        print(f"\n🔄 Changes Found: {len(result['changes'])}")
        for i, change in enumerate(result['changes'][:5], 1):
            print(f"\n  Change #{i}:")
            print(f"    Field: {change['field']}")
            print(f"    Type: {change['type']}")
            print(f"    Previous: {change['previous_value'][:80]}...")
            print(f"    Current: {change['current_value'][:80]}...")
    
    if result['sections']:
        print(f"\n📋 Sections Found: {len(result['sections'])}")
        for section in result['sections']:
            print(f"\n  {section['title']}:")
            for item in section['items'][:3]:
                print(f"    - {item[:80]}...")
    
    if result['preview_text']:
        print(f"\n📄 Preview Text (first 200 chars):")
        print(f"  {result['preview_text'][:200]}...")
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)


def test_backend_imports():
    """Test that all backend imports work correctly."""
    print("\n🔧 Testing backend imports...")
    
    try:
        from forensics import (
            detect_file_type,
            extract_metadata,
            extract_document_text,
            recover_previous_version,
            analyze_forensic_signals,
        )
        print("✓ All forensics functions imported successfully")
        
        # Check if python-docx is available
        try:
            from docx import Document
            print("✓ python-docx library is available")
        except ImportError:
            print("❌ python-docx library not found")
            print("   Install with: pip install python-docx")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 Starting Word X-ray Recovery Tests\n")
    
    # Test imports first
    if not test_backend_imports():
        print("\n❌ Backend imports failed. Please check your installation.")
        sys.exit(1)
    
    # Test Word X-ray recovery
    test_word_xray()
    
    print("\n✨ All tests completed!\n")
