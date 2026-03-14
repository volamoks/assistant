import requests
import json
import os

LITELLM_URL = "http://localhost:18788/v1/chat/completions"
# Using an arbitrary key since the proxy is likely configured to accept any or is internal
API_KEY = "sk-litellm-openclaw-proxy" 

MODELS = [
    "claw-main",
    "claw-coder",
    "claw-architect",
    "claw-thinking",
    "claw-researcher",
    "claw-summarizer",
    "claw-free-fast",
    "claw-free-smart",
    "local-small",
    "local-medium"
]

def test_model(model_name):
    print(f"Testing model: {model_name}...", end=" ", flush=True)
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    try:
        response = requests.post(LITELLM_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            print("✅ OK")
            return True
        else:
            print(f"❌ FAIL ({response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    results = {}
    for model in MODELS:
        results[model] = test_model(model)
    
    print("\nSummary:")
    for model, status in results.items():
        print(f"{model}: {'✅' if status else '❌'}")
