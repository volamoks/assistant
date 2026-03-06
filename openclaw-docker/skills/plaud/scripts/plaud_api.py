import os
import shutil
import subprocess
import requests

PLAUD_TOKEN = os.getenv("PLAUD_TOKEN")
PLAUD_API_DOMAIN = os.getenv("PLAUD_API_DOMAIN", "https://api-euc1.plaud.ai")

HEADERS = {
    "Authorization": f"Bearer {PLAUD_TOKEN}",
    "Content-Type": "application/json"
}

# ── Format Detection & Conversion ──────────────────────────────────────────

def detect_format_from_content_type(response):
    """
    Detect audio format from Content-Type header.
    Returns: 'opus', 'mp3', 'wav', 'flac', 'm4a', or None if unknown.
    """
    content_type = response.headers.get('Content-Type', '').lower()
    format_map = {
        'audio/ogg': 'opus',
        'audio/opus': 'opus',
        'audio/mp4': 'm4a',
        'audio/mpeg': 'mp3',
        'audio/x-mpeg': 'mp3',
        'audio/wav': 'wav',
        'audio/x-wav': 'wav',
        'audio/flac': 'flac',
    }
    for ct, fmt in format_map.items():
        if ct in content_type:
            return fmt
    return None

def detect_audio_format(filepath):
    """
    Detect audio format from file magic bytes.
    Returns: 'opus', 'mp3', 'wav', 'flac', or 'unknown'
    """
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(16)

        audio_signatures = {
            b'OggS': 'opus',      # OGG/Opus
            b'ID3': 'mp3',        # MP3 with ID3 tags
            b'\xff\xfb': 'mp3',   # MP3 frame sync
            b'\xff\xf3': 'mp3',   # MP3 frame sync
            b'\xff\xf2': 'mp3',   # MP3 frame sync
            b'RIFF': 'wav',       # WAV (RIFF header)
            b'fLaC': 'flac',      # FLAC
        }

        for sig, fmt in audio_signatures.items():
            if magic.startswith(sig):
                return fmt

        return 'unknown'

    except Exception:
        return 'unknown'

def convert_audio(input_path, output_format='wav'):
    """
    Convert audio file to specified format using ffmpeg.
    Args:
        input_path: Path to input audio file
        output_format: Target format ('wav' or 'mp3')
    Returns:
        Path to converted file, or None if conversion failed
    """
    # Find ffmpeg
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        print("  -> Warning: ffmpeg not found - cannot convert audio")
        return None

    # Get input filename without extension
    input_dir = os.path.dirname(input_path)
    input_name = os.path.splitext(os.path.basename(input_path))[0]

    # Output path
    output_path = os.path.join(input_dir, f"{input_name}.{output_format}")

    # Skip if already converted
    if os.path.exists(output_path):
        return output_path

    try:
        print(f"  -> Converting to {output_format.upper()}...")

        if output_format == 'wav':
            # Convert to WAV (PCM 16-bit, 16kHz mono - optimal for Whisper)
            cmd = [
                ffmpeg_path, '-y',  # -y to overwrite
                '-i', input_path,
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',          # 16kHz sample rate (optimal for Whisper)
                '-ac', '1',              # Mono channel
                output_path
            ]
        elif output_format == 'mp3':
            # Convert to MP3 (128kbit - good quality/size ratio)
            cmd = [
                ffmpeg_path, '-y',
                '-i', input_path,
                '-acodec', 'libmp3lame',
                '-ab', '128k',
                output_path
            ]
        else:
            print(f"  -> Warning: Unsupported output format: {output_format}")
            return None

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            print(f"  -> Warning: Conversion failed: {result.stderr[:200]}")
            return None

        # Verify output file exists
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"  -> Converted to {output_format.upper()}: {size / 1024:.1f}KB")
            return output_path
        else:
            print(f"  -> Warning: Conversion failed - output file not created")
            return None

    except subprocess.TimeoutExpired:
        print(f"  -> Warning: Conversion timeout (file may be too large)")
        return None
    except Exception as e:
        print(f"  -> Warning: Conversion error: {e}")
        return None

def fetch_files_list():
    resp = requests.get(f"{PLAUD_API_DOMAIN}/file/simple/web", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    code = data.get("code") if data.get("code") is not None else data.get("status")
    if code != 0 and code != 200 and not data.get("data_file_list"):
        print(f"Error fetching files (Status {code}): {data.get('msg')}")
        if code == -302:
            print(f"Region mismatch! Suggested domain: {data.get('data', {}).get('domains', {}).get('api')}")
        return []
    return data.get("data_file_list", [])

def fetch_file_detail(file_id):
    resp = requests.get(f"{PLAUD_API_DOMAIN}/file/detail/{file_id}", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    code = data.get("code") if data.get("code") is not None else data.get("status")
    if code != 0 and code != 200 and not data.get("data"):
        return None
    return data.get("data")

def check_file_status(file_id):
    """Check if file audio is available for download (not encrypted/on-device only)."""
    try:
        resp = requests.get(f"{PLAUD_API_DOMAIN}/file/detail/{file_id}", headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        code = data.get("code") if data.get("code") is not None else data.get("status")
        if code != 0 and code != 200:
            return None
        file_data = data.get("data", {})
        return {
            "wait_pull": file_data.get("wait_pull", 0),
            "duration": file_data.get("duration", 0),
            "file_name": file_data.get("file_name", "Unknown"),
        }
    except Exception as e:
        print(f"  -> Warning: Could not check file status: {e}")
        return None

def download_audio(file_id, output_path, convert_format=None):
    """
    Download audio file from Plaud API.
    
    Args:
        file_id: Plaud file ID
        output_path: Path to save the file
        convert_format: Optional format to convert to ('wav' or 'mp3').
                       If provided, will convert the downloaded audio to this format.
                       
    NOTE: Plaud API sometimes returns Content-Type: application/json even for binary audio.
    We peek at the first bytes to distinguish real JSON from binary audio data.
    Supports OPUS format detection and conversion.
    """
    try:
        resp = requests.get(f"{PLAUD_API_DOMAIN}/file/download/{file_id}", headers=HEADERS, stream=True, timeout=60)
        resp.raise_for_status()

        # Buffer a small peek to detect if response is JSON or binary audio
        peek = b""
        chunks_buffer = []
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                chunks_buffer.append(chunk)
                peek += chunk
                if len(peek) >= 64:
                    break

        if not peek:
            print(f"Download API Error: Empty response received")
            return False

        # Determine if the response is real JSON (starts with '{' or '[')
        # vs binary audio content (Plaud sends audio with wrong Content-Type)
        peek_text = peek[:4].decode('utf-8', errors='ignore').strip()
        is_real_json = peek_text and peek_text[0] in ('{', '[')

        if is_real_json:
            # Reassemble and parse JSON to look for redirect URL
            raw = peek
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    raw += chunk
            try:
                data = raw.decode('utf-8')
                import json as _json
                parsed = _json.loads(data)
                code = parsed.get("code") if parsed.get("code") is not None else parsed.get("status")
                download_url = parsed.get("data", {}).get("download_url") if isinstance(parsed.get("data"), dict) else None
                if download_url:
                    print(f"  -> Got download URL from API")
                    dl_resp = requests.get(download_url, stream=True, timeout=120)
                    dl_resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        downloaded = 0
                        for chunk in dl_resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                    if downloaded == 0:
                        print(f"Download API Error: Empty file from redirect URL")
                        return False
                    print(f"  -> Downloaded {downloaded / 1024:.1f}KB")
                    return True
                else:
                    msg = parsed.get('msg', 'No download_url in response')
                    print(f"Download API Error: {msg} (code={code})")
                    return False
            except Exception as e:
                print(f"Download API Error: Failed to parse JSON response: {e}")
                return False
        else:
            # Binary audio — write buffered chunks then stream the rest
            print(f"  -> Binary audio detected, streaming to disk...")
            with open(output_path, "wb") as f:
                downloaded = 0
                for chunk in chunks_buffer:
                    f.write(chunk)
                    downloaded += len(chunk)
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            if downloaded == 0:
                print(f"Download API Error: Empty file received")
                return False

            print(f"  -> Downloaded {downloaded / 1024:.1f}KB")

        # Verify file was written
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print(f"Download API Error: File not created or empty after write")
            return False

        # Log detected audio format (informational only — don't reject unknown formats)
        with open(output_path, 'rb') as f:
            magic = f.read(16)

        audio_signatures = {
            b'OggS': 'opus',
            b'ID3': 'mp3',
            b'\xff\xfb': 'mp3',
            b'\xff\xf3': 'mp3',
            b'RIFF': 'wav',
            b'fLaC': 'flac',
        }
        detected_format = None
        for sig, fmt in audio_signatures.items():
            if magic.startswith(sig):
                detected_format = fmt
                print(f"  -> Detected format: {fmt}")
                break
        else:
            print(f"  -> Audio format: unknown/proprietary (first bytes: {magic[:8].hex()})")

        # Convert if requested
        if convert_format and detected_format and detected_format != convert_format:
            converted_path = convert_audio(output_path, convert_format)
            if converted_path:
                print(f"  -> Converted to {convert_format.upper()}: {os.path.basename(converted_path)}")
                return converted_path
            else:
                print(f"  -> Warning: Conversion failed, returning original format")

        return output_path if convert_format else True

    except requests.exceptions.Timeout:
        print(f"Download API Error: Timeout after 60s")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Download API Error: {e}")
        return False
    except Exception as e:
        print(f"Download API Error: Unexpected error - {e}")
        return False
