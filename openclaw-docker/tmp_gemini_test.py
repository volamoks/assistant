import base64
import requests
import os
import json

# Use the environment variable from the container
api_key = os.environ.get('GEMINI_API_KEY')
audio_path = '/tmp/debug.opus'

# Read file
with open(audio_path, 'rb') as f:
    audio_data = base64.b64encode(f.read()).decode('utf-8')

print(f"Audio size: {len(audio_data)} chars")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

payload = {
    "contents": [{
        "parts": [
            {"text": "Transcribe this audio meeting. If it's encrypted or invalid, tell me what you see in the data."},
            {"inline_data": {"mime_type": "audio/ogg", "data": audio_data}}
        ]
    }]
}

response = requests.post(url, json=payload, timeout=300)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
