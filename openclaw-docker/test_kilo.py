import requests
import os

K_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6ImFjMDNkMDQyLWU1YTYtNGE5My05Yzc0LTZkYTYzZDQ2MTNjNiIsImFwaVRva2VuUGVwcGVyIjpudWxsLCJ2ZXJzaW9uIjozLCJpYXQiOjE3NzM0ODMzNTEsImV4cCI6MTkzMTE2MzM1MX0.pU6c_h5qOcaSUeLigeHahVG6vyBautBzkoGZQE26pzg"

models = [
    "deepseek/deepseek-chat",
    "deepseek/deepseek-reasoner",
    "moonshotai/kimi-k2.5:free",
    "minimax/minimax-m2.5:free"
]

def ping_kilo(model):
    print(f"Pinging KiloCode model: {model}...", end=" ", flush=True)
    url = "https://api.kilo.ai/api/gateway/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {K_API_KEY}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ OK")
        else:
            print(f"❌ FAIL ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")

if __name__ == "__main__":
    for m in models:
        ping_kilo(m)
