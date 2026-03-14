import requests
import json
import os

LITELLM_URL = "http://localhost:18788/v1/chat/completions"
# Using an arbitrary key since the proxy is likely configured to accept any or is internal
API_KEY = "sk-litellm-openclaw-proxy" 

MODELS = [
  "litellm/claw-main",
  "litellm/claw-coder",
  "litellm/claw-architect",
  "litellm/claw-thinking",
  "litellm/claw-researcher",
  "litellm/claw-summarizer",
  "litellm/claw-free-fast",
  "litellm/claw-free-smart",
  "litellm/kilo-deepseek-chat",
  "litellm/local-small"
]

def test_model(model_name):
    print(f"Testing {model_name}...", end=" ", flush=True)
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    import time
    start = time.time()
    try:
        response = requests.post(LITELLM_URL, json=payload, headers=headers, timeout=60)
        duration = time.time() - start
        if response.status_code == 200:
            print(f"✅ OK ({duration:.1f}s)")
            return True
        else:
            print(f"❌ FAIL ({response.status_code}) - {response.text[:200]}")
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
