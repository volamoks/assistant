import requests
import json
import os

K_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6ImFjMDNkMDQyLWU1YTYtNGE5My05Yzc0LTZkYTYzZDQ2MTNjNiIsImFwaVRva2VuUGVwcGVyIjpudWxsLCJ2ZXJzaW9uIjozLCJpYXQiOjE3NzM0ODMzNTEsImV4cCI6MTkzMTE2MzM1MX0.pU6c_h5qOcaSUeLigeHahVG6vyBautBzkoGZQE26pzg"

def list_models():
    url = "https://api.kilo.ai/api/gateway/models"
    headers = {
        "Authorization": f"Bearer {K_API_KEY}"
    }
    print(f"Fetching models from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            models = [m['id'] for m in data.get('data', [])]
            print(f"Found {len(models)} models.")
            for m in sorted(models):
                if 'deepseek' in m.lower() or 'kimi' in m.lower() or 'moonshot' in m.lower():
                    print(f"  - {m}")
            
            with open('kilo_models.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("Full list saved to kilo_models.json")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    list_models()
