"""
Test script for Local LLM backend
Tests forensics engine and LLM integration
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.forensics_engine import ForensicsEngine
from api.local_llm import get_llm


def test_forensics_engine():
    """Test the forensics engine"""
    print("\n" + "="*60)
    print("TEST 1: Forensics Engine")
    print("="*60)
    
    engine = ForensicsEngine()
    
    # Test with a sample PDF (create minimal PDF bytes)
    # This is a minimal valid PDF
    pdf_bytes = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""
    
    try:
        result = engine.analyze_pdf(pdf_bytes, "test.pdf")
        
        print(f"✓ File: {result['file_name']}")
        print(f"✓ Type: {result['file_type']}")
        print(f"✓ Anomalies: {result['anomaly_count']}")
        print(f"✓ Forensic Score: {result['forensic_score']}/100")
        
        if result['anomalies']:
            print(f"\nDetected Anomalies:")
            for i, anomaly in enumerate(result['anomalies'][:5], 1):
                print(f"  {i}. [{anomaly['severity']}] {anomaly['message']}")
        
        print("\n✓ Forensics Engine: PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Forensics Engine: FAILED")
        print(f"Error: {e}")
        return False


def test_llm_fallback():
    """Test LLM with fallback"""
    print("\n" + "="*60)
    print("TEST 2: LLM (Rule-based Fallback)")
    print("="*60)
    
    try:
        llm = get_llm()
        
        # Mock forensic data
        forensic_data = {
            "anomaly_count": 3,
            "forensic_score": 65.0,
            "anomalies": [
                {
                    "type": "metadata_missing",
                    "severity": "medium",
                    "message": "PDF has no metadata"
                },
                {
                    "type": "suspicious_creator",
                    "severity": "high",
                    "message": "Created with Photoshop"
                },
                {
                    "type": "invalid_date",
                    "severity": "high",
                    "message": "Invalid date: Feb 31"
                }
            ]
        }
        
        context = {
            "file_name": "test.pdf",
            "file_type": "pdf",
            "metadata": {"page_count": 1},
            "text_content": "Test document content",
            "full_text": "Test document content with some numbers $1000 and dates"
        }
        
        print(f"LLM Status: {'Initialized' if llm.initialized else 'Fallback Mode'}")
        print(f"Model: {llm.model_name}")
        
        result = llm.analyze_document(forensic_data, context)
        
        print(f"\n✓ Risk Score: {result['risk_score']}/100")
        print(f"✓ Trust Score: {result['trust_score']}/100")
        print(f"✓ Fraud Signals: {len(result['fraud_signals'])}")
        print(f"✓ Recommendation: {result['ai_explanation']['recommended_action']}")
        
        if result['fraud_signals']:
            print(f"\nGenerated Fraud Signals:")
            for i, signal in enumerate(result['fraud_signals'][:3], 1):
                print(f"  {i}. [{signal['severity']}] {signal['name']}")
                print(f"     {signal['summary']}")
        
        print("\n✓ LLM Analysis: PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ LLM Analysis: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test complete integration"""
    print("\n" + "="*60)
    print("TEST 3: Complete Integration")
    print("="*60)
    
    try:
        # Create minimal PDF
        pdf_bytes = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 20>>stream
BT /F1 12 Tf 100 700 Td (Bank Statement) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000217 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
287
%%EOF"""
        
        # Step 1: Forensics
        print("Running forensic analysis...")
        engine = ForensicsEngine()
        forensic_result = engine.analyze_pdf(pdf_bytes, "bank_statement.pdf")
        print(f"✓ Forensics: {forensic_result['anomaly_count']} anomalies, score={forensic_result['forensic_score']}")
        
        # Step 2: LLM Analysis
        print("Running LLM analysis...")
        llm = get_llm()
        context = {
            "file_name": "bank_statement.pdf",
            "file_type": "pdf",
            "metadata": forensic_result['metadata'],
            "text_content": forensic_result['text_content'],
            "full_text": forensic_result.get('full_text', '')
        }
        
        ai_result = llm.analyze_document(forensic_result, context)
        print(f"✓ LLM: risk={ai_result['risk_score']}, signals={len(ai_result['fraud_signals'])}")
        
        # Step 3: Verify results
        print("\nFinal Results:")
        print(f"  Risk Score: {ai_result['risk_score']}/100")
        print(f"  Trust Score: {ai_result['trust_score']}/100")
        print(f"  Recommendation: {ai_result['ai_explanation']['recommended_action']}")
        print(f"  Fraud Signals: {len(ai_result['fraud_signals'])}")
        
        # Verify structure
        assert 'risk_score' in ai_result
        assert 'trust_score' in ai_result
        assert 'fraud_signals' in ai_result
        assert 'ai_explanation' in ai_result
        assert len(ai_result['fraud_signals']) > 0
        
        print("\n✓ Integration Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Integration Test: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("LOCAL LLM BACKEND TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Forensics Engine", test_forensics_engine()))
    results.append(("LLM Analysis", test_llm_fallback()))
    results.append(("Integration", test_integration()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:.<40} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - Backend is ready!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Check errors above")
        return 1


if __name__ == "__main__":
    exit(main())
