"""
Anobis API Test Suite
Tests all major endpoints with real, fake, and image documents.
"""
import os
import json
import sys
import io
import urllib.request
import urllib.error
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

BASE_URL = "http://localhost:8000"
DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "dataset")

PASS = 0
FAIL = 0


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def get(path):
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def upload_file(filepath):
    boundary = "AnobisBoundary12345"
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/investigate",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}


def create_fake_pdf(path):
    """Create a fake bank statement with intentional math errors."""
    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "BANK STATEMENT")
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, "Account: 1234567890")
    c.drawString(100, 700, "Period: 01/01/2024 - 31/01/2024")
    c.drawString(100, 670, "Opening Balance: 200,000.00")
    # Table with intentional math errors
    rows = [
        ("01/01/2024", "Debit", "5000.00", "195000.00"),
        ("05/01/2024", "Debit", "3000.00", "197600.00"),   # Wrong: should be 192000
        ("10/01/2024", "Credit", "10000.00", "202600.00"),  # Wrong
        ("15/01/2024", "Debit", "8000.00", "194600.00"),
        ("20/01/2024", "Debit", "5000.00", "189600.00"),
        ("25/01/2024", "Credit", "2000.00", "191600.00"),
        ("31/01/2024", "Debit", "3817.00", "187783.00"),
    ]
    y = 640
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Date")
    c.drawString(150, y, "Type")
    c.drawString(250, y, "Amount")
    c.drawString(380, y, "Balance")
    y -= 20
    c.setFont("Helvetica", 10)
    for row in rows:
        c.drawString(50, y, row[0])
        c.drawString(150, y, row[1])
        c.drawString(250, y, row[2])
        c.drawString(380, y, row[3])
        y -= 20
    c.drawString(100, y - 10, "Closing Balance: 100000.00")  # Wrong closing balance
    c.save()


# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Anobis API Test Suite")
print("=" * 60)

# ─── Test 1: Health Check ─────────────────────────────────────────────────────
print("\n[1] Health Check")
resp = get("/")
check(resp.get("status") == "online", "GET / returns status=online")
check("capabilities" in resp, "GET / has capabilities list")
check("pdf_metadata_forensics" in resp.get("capabilities", []), "PDF metadata forensics listed")
check("ai_summary_generation" in resp.get("capabilities", []), "AI summary generation listed")

# ─── Test 2: Detailed Health ──────────────────────────────────────────────────
print("\n[2] Detailed Health")
resp = get("/api/v1/health")
check(resp.get("status") in ("healthy", "degraded"), "GET /api/v1/health returns valid status")
check("forensic_layers" in resp, "Response has forensic_layers map")
layers = resp.get("forensic_layers", {})
check(layers.get("font_analysis"), "Font analysis layer enabled")
check(layers.get("digital_signature"), "Digital signature layer enabled")
check(layers.get("image_forensics"), "Image forensics layer enabled")

# ─── Test 3: Investigation CRUD ───────────────────────────────────────────────
print("\n[3] Investigation CRUD")
resp = get("/api/v1/investigations")
check(isinstance(resp, list), "GET /api/v1/investigations returns list")

# ─── Test 4: Real PDF ─────────────────────────────────────────────────────────
print("\n[4] Real PDF Analysis (HDFC Bank Statement)")
real_pdf = os.path.join(DATASET_DIR, "real", "461790262-335063360-Hdfc-Bank-Statement-pdf.pdf")
if os.path.exists(real_pdf):
    resp = upload_file(real_pdf)
    check("fraud_probability_score" in resp, "Response has fraud_probability_score")
    check("status" in resp, "Response has status field")
    check("anomalies" in resp, "Response has anomalies list")
    check("summary" in resp, "Response has AI summary")
    check(resp.get("fraud_probability_score", 100) <= 40, f"Real PDF has low fraud score (<= 40), got {resp.get('fraud_probability_score')}")
    check(resp.get("status") in ("TRUSTED", "LOW_RISK"), f"Real PDF is TRUSTED/LOW_RISK, got {resp.get('status')}")
    print(f"  Score: {resp.get('fraud_probability_score')}/100 | Status: {resp.get('status')} | Anomalies: {len(resp.get('anomalies', []))}")
    print(f"  Summary: {resp.get('summary', '')[:100]}...")
else:
    print(f"  [SKIP] File not found: {real_pdf}")

# ─── Test 5: Fake PDF ─────────────────────────────────────────────────────────
print("\n[5] Fake/Tampered PDF Analysis")
fake_path = os.path.join(os.path.dirname(__file__), "fake_test.pdf")
create_fake_pdf(fake_path)
resp = upload_file(fake_path)
check("fraud_probability_score" in resp, "Response has fraud_probability_score")
check(resp.get("fraud_probability_score", 0) >= 30, f"Fake PDF has elevated fraud score (>= 30), got {resp.get('fraud_probability_score')}")
check(len(resp.get("anomalies", [])) > 0, f"Fake PDF has anomalies detected, got {len(resp.get('anomalies', []))}")
print(f"  Score: {resp.get('fraud_probability_score')}/100 | Status: {resp.get('status')} | Anomalies: {len(resp.get('anomalies', []))}")
for a in resp.get("anomalies", [])[:3]:
    print(f"    [{a.get('severity', '?')}] {a.get('type', '?')}: {a.get('description', '')[:80]}")
if os.path.exists(fake_path):
    os.remove(fake_path)

# ─── Test 6: Image File ───────────────────────────────────────────────────────
print("\n[6] Image File Analysis")
img_path = os.path.join(DATASET_DIR, "real", "BankStatementChequing.png")
if os.path.exists(img_path):
    resp = upload_file(img_path)
    check("fraud_probability_score" in resp, "Response has fraud_probability_score")
    check("summary" in resp, "Response has AI summary")
    print(f"  Score: {resp.get('fraud_probability_score')}/100 | Status: {resp.get('status')} | Anomalies: {len(resp.get('anomalies', []))}")
    print(f"  Summary: {resp.get('summary', '')[:100]}...")
else:
    print(f"  [SKIP] Image not found: {img_path}")

# ─── Test 7: Unsupported File Type ────────────────────────────────────────────
print("\n[7] Rejection of Unsupported File Types")
boundary = "AnobisBoundary12345"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="malware.exe"\r\n'
    f"Content-Type: application/octet-stream\r\n\r\n"
).encode() + b"fake binary content" + f"\r\n--{boundary}--\r\n".encode()
req = urllib.request.Request(
    f"{BASE_URL}/api/v1/investigate",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
try:
    urllib.request.urlopen(req, timeout=10)
    check(False, "Server rejected .exe file (expected 400, got 200)")
except urllib.error.HTTPError as e:
    check(e.code == 400, f"Server correctly returns 400 for .exe file, got {e.code}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
