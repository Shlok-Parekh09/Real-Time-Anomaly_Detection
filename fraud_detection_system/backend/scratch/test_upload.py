import requests

def test_api():
    print("Testing backend API...")
    
    # 1. Create Investigation
    print("1. Creating investigation...")
    res = requests.post("http://localhost:7860/api/v1/investigations", json={
        "context": "Testing"
    })
    print(res.status_code, res.text)
    
    if res.status_code != 201:
        return
        
    inv_id = res.json()["id"]
    
    # 2. Upload Document
    print(f"2. Uploading document for {inv_id}...")
    with open("requirements.txt", "rb") as f:
        files = {"files": ("requirements.txt", f, "text/plain")}
        res = requests.post(f"http://localhost:7860/api/v1/investigations/{inv_id}/documents", files=files)
    print(res.status_code, res.text)

if __name__ == "__main__":
    test_api()
