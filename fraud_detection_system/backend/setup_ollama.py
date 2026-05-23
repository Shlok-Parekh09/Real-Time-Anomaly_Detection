"""
Setup script for Ollama integration
Helps users install and configure Ollama with required models
"""

import subprocess
import sys
import time
import urllib.request
import json


OLLAMA_BASE_URL = "http://localhost:11434"
REQUIRED_MODELS = [
    "gemma4:31b-cloud",  # For fraud detection analysis
    "llama3",            # For descriptions
]


def check_ollama_installed():
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        request = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 200
    except:
        return False


def get_installed_models():
    """Get list of installed Ollama models."""
    try:
        request = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
    except:
        return []


def pull_model(model_name):
    """Pull a model from Ollama registry."""
    print(f"\n📥 Pulling model: {model_name}")
    print("This may take several minutes depending on model size...")
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=False,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Successfully pulled {model_name}")
            return True
        else:
            print(f"❌ Failed to pull {model_name}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout while pulling {model_name}")
        return False
    except Exception as e:
        print(f"❌ Error pulling {model_name}: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 Ollama Setup for Autonomous Fraud Detection")
    print("=" * 60)
    
    # Step 1: Check if Ollama is installed
    print("\n1️⃣  Checking Ollama installation...")
    if not check_ollama_installed():
        print("❌ Ollama is not installed!")
        print("\n📖 Installation instructions:")
        print("   • Linux/Mac: curl -fsSL https://ollama.com/install.sh | sh")
        print("   • Windows: Download from https://ollama.com/download")
        print("\nAfter installation, run this script again.")
        sys.exit(1)
    
    print("✅ Ollama is installed")
    
    # Step 2: Check if Ollama is running
    print("\n2️⃣  Checking Ollama service...")
    if not check_ollama_running():
        print("⚠️  Ollama service is not running!")
        print("\n🔧 Starting Ollama service...")
        print("   Run: ollama serve")
        print("\nOr Ollama will start automatically when you pull a model.")
        print("Waiting 5 seconds for service to start...")
        time.sleep(5)
        
        if not check_ollama_running():
            print("❌ Ollama service still not running")
            print("Please start Ollama manually: ollama serve")
            sys.exit(1)
    
    print("✅ Ollama service is running")
    
    # Step 3: Check installed models
    print("\n3️⃣  Checking installed models...")
    installed_models = get_installed_models()
    
    if installed_models:
        print(f"📦 Found {len(installed_models)} installed models:")
        for model in installed_models:
            print(f"   • {model}")
    else:
        print("📦 No models installed yet")
    
    # Step 4: Install required models
    print("\n4️⃣  Installing required models...")
    
    for model in REQUIRED_MODELS:
        # Check if model is already installed
        model_installed = any(m.startswith(model.split(':')[0]) for m in installed_models)
        
        if model_installed:
            print(f"✅ {model} is already installed")
        else:
            print(f"⚠️  {model} is not installed")
            response = input(f"   Install {model}? (y/n): ").strip().lower()
            
            if response == 'y':
                success = pull_model(model)
                if not success:
                    print(f"⚠️  Failed to install {model}")
                    print("   You can install it manually later: ollama pull " + model)
            else:
                print(f"⏭️  Skipping {model}")
    
    # Step 5: Verify setup
    print("\n5️⃣  Verifying setup...")
    installed_models = get_installed_models()
    
    all_installed = all(
        any(m.startswith(req.split(':')[0]) for m in installed_models)
        for req in REQUIRED_MODELS
    )
    
    if all_installed:
        print("\n" + "=" * 60)
        print("✅ Setup complete! All required models are installed.")
        print("=" * 60)
        print("\n🎉 Your fraud detection system is now fully autonomous!")
        print("\n📝 Models installed:")
        print(f"   • {REQUIRED_MODELS[0]} - Fraud detection analysis")
        print(f"   • {REQUIRED_MODELS[1]} - Description generation")
        print("\n🚀 You can now start the backend:")
        print("   cd fraud_detection_system/backend")
        print("   python main.py")
        print("\n💡 No API keys required - everything runs locally!")
    else:
        print("\n" + "=" * 60)
        print("⚠️  Setup incomplete - some models are missing")
        print("=" * 60)
        print("\n📝 Missing models:")
        for model in REQUIRED_MODELS:
            if not any(m.startswith(model.split(':')[0]) for m in installed_models):
                print(f"   • {model}")
        print("\n🔧 Install missing models manually:")
        for model in REQUIRED_MODELS:
            if not any(m.startswith(model.split(':')[0]) for m in installed_models):
                print(f"   ollama pull {model}")
        print("\n⚠️  The system will fall back to intelligent heuristics")
        print("   if Ollama models are not available.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        sys.exit(1)
