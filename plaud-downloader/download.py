#!/usr/bin/env python3
"""
Plaud Downloader - Simple script to download Plaud audio recordings

Usage:
    python download.py --token your_api_token
    python download.py  # Uses PLAUD_API_TOKEN env variable
    python download.py --list-only  # Just list recordings without downloading
    python download.py --convert wav  # Convert to WAV format (better for Whisper)
    python download.py --convert mp3  # Convert to MP3 format
"""

import argparse
import os
import sys
import json
import requests
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# API Configuration
# Based on research from: https://github.com/JamesStuder/Plaud_API
PLAUD_API_BASE = os.environ.get("PLAUD_API_DOMAIN", "https://api.plaud.ai")
PLAUD_API_VERSION = "/v1"

# Correct API Endpoints (from official API.Plaud.NET library)
# Authentication: POST /auth/access-token
# List Recordings: GET /file/simple/web?skip=0&limit=99999&is_trash=2&sort_by=start_time&is_desc=true
# Get specific recordings: POST /file/list
# Get file tags: GET /filetag/
# Get temp URL for audio: GET /file/temp-url/{recording_id}

# Environment variable for API token
PLAUD_TOKEN_ENV = os.environ.get("PLAUD_TOKEN") or os.environ.get("PLAUD_API_TOKEN")

# Enable verbose/debug output
DEBUG = os.environ.get("PLAUD_DEBUG", "false").lower() == "true"

def debug_print(message):
    """Print debug messages if DEBUG mode is enabled"""
    if DEBUG:
        print(f"[DEBUG] {message}")

class PlaudDownloader:
    def __init__(self, email=None, password=None, token=None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.email = email
        self.password = password
        self.token = token
        self.user_id = None
        
        if DEBUG:
            print(f"[DEBUG] PlaudDownloader initialized")
            print(f"[DEBUG] API Base: {PLAUD_API_BASE}")
        
    def login(self):
        """Login to Plaud using email/password
        
        Uses the correct endpoint: POST /auth/access-token
        Based on: https://github.com/JamesStuder/Plaud_API
        """
        if not self.email or not self.password:
            print("Error: Email and password required for login")
            return False
            
        try:
            # CORRECT endpoint: /auth/access-token (NOT /auth/login)
            auth_url = f"{PLAUD_API_BASE}/auth/access-token"
            debug_print(f"Attempting authentication to: {auth_url}")
            
            response = self.session.post(
                auth_url,
                json={
                    "email": self.email,
                    "password": self.password
                },
                timeout=30
            )
            
            debug_print(f"Auth response status: {response.status_code}")
            debug_print(f"Auth response body: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                debug_print(f"Auth response JSON keys: {data.keys() if isinstance(data, dict) else 'not a dict'}")
                self.token = data.get("access_token") or data.get("token")
                if self.token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                    print(f"✓ Logged in successfully as {self.email}")
                    return True
                else:
                    debug_print(f"No access_token found in response: {data}")
                    
            print(f"Login failed: {response.status_code} - {response.text[:200]}")
            return False
            
        except Exception as e:
            print(f"Login error: {e}")
            debug_print(f"Login exception details: {str(e)}")
            return False
    
    def set_token(self):
        """Set token directly"""
        if not self.token:
            print("Error: API token required")
            return False
            
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
        print(f"✓ Using provided API token")
        return True
    
    def get_recordings(self):
        """Fetch list of recordings
        
        Uses the correct endpoint: GET /file/simple/web?skip=0&limit=99999&is_trash=2&sort_by=start_time&is_desc=true
        Based on: https://github.com/JamesStuder/Plaud_API
        """
        try:
            # CORRECT endpoint: /file/simple/web with query parameters
            # Note: is_trash=2 means get both trashed and non-trashed items
            endpoint = f"{PLAUD_API_BASE}/file/simple/web?skip=0&limit=99999&is_trash=2&sort_by=start_time&is_desc=true"
            debug_print(f"Fetching recordings from: {endpoint}")
            
            response = self.session.get(endpoint, timeout=30)
            
            debug_print(f"Recordings response status: {response.status_code}")
            debug_print(f"Recordings response body (first 500 chars): {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                debug_print(f"Recordings response type: {type(data)}")
                
                # Handle different response formats
                if isinstance(data, list):
                    debug_print(f"Found {len(data)} recordings (list format)")
                    return data
                elif isinstance(data, dict):
                    if "data" in data:
                        recordings = data["data"]
                        debug_print(f"Found {len(recordings)} recordings (dict.data format)")
                        return recordings
                    elif "fileList" in data:
                        recordings = data["fileList"]
                        debug_print(f"Found {len(recordings)} recordings (dict.fileList format)")
                        return recordings
                    elif "files" in data:
                        recordings = data["files"]
                        debug_print(f"Found {len(recordings)} recordings (dict.files format)")
                        return recordings
                    elif "data_file_list" in data:
                        recordings = data["data_file_list"]
                        debug_print(f"Found {len(recordings)} recordings (dict.data_file_list format)")
                        return recordings
                    elif "dataFileList" in data:
                        recordings = data["dataFileList"]
                        debug_print(f"Found {len(recordings)} recordings (dict.dataFileList format)")
                        return recordings
                    else:
                        debug_print(f"Unknown dict format, keys: {data.keys()}")
                        # Return the whole dict as a single item list
                        return [data]
            
            print(f"Error fetching recordings: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return []
            
        except Exception as e:
            print(f"Error fetching recordings: {e}")
            debug_print(f"Exception details: {str(e)}")
            import traceback
            debug_print(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _get_recordings_alt(self):
        """Alternative method to get recordings via web API"""
        # This method is deprecated - the main get_recordings() now uses the correct endpoint
        debug_print("Alternative method called (deprecated)")
        return []
    
    def detect_audio_format(self, filepath):
        """Detect audio format from file magic bytes
        
        Returns:
            str: Detected format ('opus', 'mp3', 'wav', 'flac', 'unknown')
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
                    debug_print(f"Detected format from magic bytes: {fmt}")
                    return fmt
            
            # Log the actual bytes for debugging
            debug_print(f"Unknown audio format, magic bytes: {magic[:8].hex()}")
            return 'unknown'
            
        except Exception as e:
            debug_print(f"Error detecting format: {e}")
            return 'unknown'
    
    def detect_format_from_content_type(self, response):
        """Detect format from Content-Type header
        
        Returns:
            str: Detected format or None if unknown
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
                debug_print(f"Detected format from Content-Type: {fmt} ({content_type})")
                return fmt
        
        return None

    def convert_audio(self, input_path, output_format='wav'):
        """Convert audio file to specified format using ffmpeg
        
        Args:
            input_path: Path to input audio file
            output_format: Target format ('wav', 'mp3')
            
        Returns:
            str: Path to converted file, or None if conversion failed
        """
        # Find ffmpeg
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            print("  ✗ ffmpeg not found - cannot convert audio")
            return None
        
        # Get input filename without extension
        input_dir = os.path.dirname(input_path)
        input_name = os.path.splitext(os.path.basename(input_path))[0]
        
        # Output path
        output_path = os.path.join(input_dir, f"{input_name}.{output_format}")
        
        # Skip if already converted
        if os.path.exists(output_path):
            debug_print(f"Converted file already exists: {output_path}")
            return output_path
        
        try:
            print(f"  Converting to {output_format.upper()}...")
            
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
                print(f"  ✗ Unsupported output format: {output_format}")
                return None
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                print(f"  ✗ Conversion failed: {result.stderr[:200]}")
                return None
            
            # Verify output file exists
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"  ✓ Converted to {output_format.upper()}: {size / 1024:.1f}KB")
                return output_path
            else:
                print(f"  ✗ Conversion failed: output file not created")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"  ✗ Conversion timeout (file may be too large)")
            return None
        except Exception as e:
            print(f"  ✗ Conversion error: {e}")
            return None

    def download_recording(self, recording, output_dir, convert_format=None):
        """Download a single recording
        
        The API returns recordings with temp URLs that need to be fetched separately.
        Based on the C# implementation, we need to:
        1. Get the recording ID
        2. Get a temp URL for the audio file using: GET /file/temp-url/{recording_id}
        3. Download from the temp URL
        
        Args:
            recording: Recording dict from API
            output_dir: Output directory
            convert_format: Optional format to convert to ('wav', 'mp3', or None)
        """
        # Extract recording info
        recording_id = recording.get("id")
        title = recording.get("title") or recording.get("name") or recording.get("filename") or f"recording_{recording_id}"
        
        debug_print(f"Processing recording: {recording_id}, title: {title}")
        
        # Handle different API response formats
        audio_url = (
            recording.get("audio_url") or
            recording.get("file_url") or
            recording.get("url") or
            recording.get("download_url") or
            recording.get("tempUrl") or
            recording.get("temp_url")
        )
        
        if not audio_url and recording_id:
            # Need to fetch the temp URL for the audio file
            debug_print(f"No audio URL found, fetching temp URL for recording: {recording_id}")
            try:
                temp_url_endpoint = f"{PLAUD_API_BASE}/file/temp-url/{recording_id}"
                debug_print(f"Fetching temp URL from: {temp_url_endpoint}")
                
                temp_response = self.session.get(temp_url_endpoint, timeout=30)
                debug_print(f"Temp URL response status: {temp_response.status_code}")
                
                if temp_response.status_code == 200:
                    temp_data = temp_response.json()
                    debug_print(f"Temp URL response: {temp_data}")
                    
                    # The response should contain tempUrl or url
                    # Try different field names for OPUS format
                    audio_url = (
                        temp_data.get("tempUrl") or
                        temp_data.get("url") or
                        temp_data.get("downloadUrl") or
                        temp_data.get("temp_url") or
                        temp_data.get("temp_url_opus") or
                        temp_data.get("data", {}).get("tempUrl") or
                        temp_data.get("data", {}).get("url")
                    )
                    
                    if audio_url:
                        debug_print(f"Got temp URL: {audio_url[:50]}...")
                    else:
                        print(f"  ⚠ No temp URL in response for: {title}")
                else:
                    print(f"  ⚠ Failed to get temp URL: {temp_response.status_code}")
            except Exception as e:
                print(f"  ⚠ Error fetching temp URL: {e}")
                debug_print(f"Temp URL exception: {str(e)}")
                
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
        
        # Start with .tmp extension, we'll rename after detecting format
        tmp_filename = f"{safe_title}_{recording_id}.tmp"
        tmp_filepath = os.path.join(output_dir, tmp_filename)
        
        # Skip if already downloaded (check for any known extension)
        for ext in ['.opus', '.ogg', '.mp3', '.wav', '.flac', '.m4a']:
            existing_file = os.path.join(output_dir, f"{safe_title}_{recording_id}{ext}")
            if os.path.exists(existing_file):
                print(f"  ✓ Already exists: {os.path.basename(existing_file)}")
                return True
        
        try:
            print(f"  Downloading: {title}")
            
            # Try direct URL first
            if audio_url and not audio_url.startswith("http"):
                audio_url = f"{PLAUD_API_BASE}{audio_url}"
            
            # Create a new session for downloading without the Authorization header
            # (S3 pre-signed URLs don't need it and adding it causes 400 errors)
            download_session = requests.Session()
            
            # Download the file with redirect handling (allow_redirects=True is default)
            response = download_session.get(audio_url, timeout=120, stream=True, allow_redirects=True)
            
            debug_print(f"Download response status: {response.status_code}")
            debug_print(f"Content-Type header: {response.headers.get('Content-Type')}")
            debug_print(f"Final URL (after redirects): {response.url}")
            
            if response.status_code != 200:
                print(f"  ✗ Failed to download: {response.status_code}")
                return False
            
            # Detect format from Content-Type header
            detected_format = self.detect_format_from_content_type(response)
            if detected_format:
                debug_print(f"Format detected from Content-Type: {detected_format}")
            
            # Save the file as .tmp first
            with open(tmp_filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Detect format from file magic bytes
            file_format = detected_format or self.detect_audio_format(tmp_filepath)
            
            # Determine file extension
            extension_map = {
                'opus': '.opus',
                'ogg': '.ogg',
                'mp3': '.mp3',
                'wav': '.wav',
                'flac': '.flac',
                'm4a': '.m4a',
            }
            extension = extension_map.get(file_format, '.audio')
            
            debug_print(f"Final detected format: {file_format}, extension: {extension}")
            
            # Rename to proper extension
            final_filename = f"{safe_title}_{recording_id}{extension}"
            final_filepath = os.path.join(output_dir, final_filename)
            
            # Remove old file if exists
            if os.path.exists(final_filepath):
                os.remove(final_filepath)
            
            os.rename(tmp_filepath, final_filepath)
            print(f"  ✓ Saved: {final_filename}")
            
            # Convert if requested
            if convert_format and file_format != convert_format:
                converted_path = self.convert_audio(final_filepath, convert_format)
                if converted_path:
                    # Update filepath to the converted file
                    final_filepath = converted_path
                    final_filename = os.path.basename(converted_path)
                    print(f"  ✓ Ready for transcription: {final_filename}")
                else:
                    print(f"  ⚠ Conversion failed, using original format")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            # Clean up temp file on error
            if os.path.exists(tmp_filepath):
                try:
                    os.remove(tmp_filepath)
                except:
                    pass
            return False
    
    def run(self, output_dir="downloads", list_only=False, convert_format=None):
        """Main execution
        
        Args:
            output_dir: Directory to save downloaded files
            list_only: If True, only list recordings without downloading
            convert_format: Optional format to convert to ('wav', 'mp3', or None)
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Authenticate
        if self.email and self.password:
            if not self.login():
                return False
        elif self.token:
            if not self.set_token():
                return False
        else:
            print("Error: Provide either --email/--password or --token")
            return False
        
        # Get recordings
        print("\nFetching recordings...")
        if DEBUG:
            print("[DEBUG] Debug mode enabled - showing detailed API responses")
            
        recordings = self.get_recordings()
        
        if not recordings:
            print("No recordings found")
            print("\nTroubleshooting tips:")
            print("1. Verify your API token is correct")
            print("2. Check if you have any recordings in your Plaud account")
            print("3. Try setting PLAUD_DEBUG=true for detailed output")
            return True
            
        print(f"Found {len(recordings)} recordings\n")
        
        # Debug: print first recording structure
        if DEBUG and recordings:
            import json
            print("[DEBUG] First recording structure:")
            print(json.dumps(recordings[0], indent=2, default=str)[:1000])
        
        # List recordings
        for i, rec in enumerate(recordings, 1):
            title = rec.get("title", rec.get("name", "Untitled"))
            created = rec.get("created_at", rec.get("created", ""))
            if created and isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created = created.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            print(f"{i}. {title} ({created})")
        
        if list_only:
            print("\n--list-only mode: skipping download")
            return True
        
        # Download recordings
        print(f"\nDownloading to: {output_dir}")
        if convert_format:
            print(f"Converting to: {convert_format.upper()}")
        success = 0
        for rec in recordings:
            if self.download_recording(rec, output_dir, convert_format):
                success += 1
                
        print(f"\n✓ Downloaded {success}/{len(recordings)} recordings")
        return True


def main():
    parser = argparse.ArgumentParser(description="Download Plaud recordings")
    parser.add_argument("--email", help="Plaud email (deprecated, use --token)")
    parser.add_argument("--password", help="Plaud password (deprecated, use --token)")
    parser.add_argument("--token", help="Plaud API token")
    parser.add_argument("--output", "-o", default="downloads", help="Output directory")
    parser.add_argument("--list-only", action="store_true", help="Only list recordings")
    parser.add_argument("--debug", action="store_true", help="Enable debug/verbose output")
    parser.add_argument(
        "--convert",
        choices=['wav', 'mp3'],
        help="Convert downloaded audio to specified format (wav=optimal for Whisper, mp3=smaller size)"
    )
    
    args = parser.parse_args()
    
    # Enable debug mode if requested
    global DEBUG
    if args.debug:
        DEBUG = True
        print("[DEBUG] Debug mode enabled via command line")
    
    # Get token from environment variable if not provided as argument
    token = args.token or os.environ.get("PLAUD_TOKEN") or os.environ.get("PLAUD_API_TOKEN", "")
    
    # Get email/password for backward compatibility
    email = args.email
    password = args.password
    
    # Check if we have valid credentials
    if not token and (email or password):
        print("Warning: Email/password is deprecated. Please use token instead.")
        print("Set PLAUD_API_TOKEN environment variable or use --token argument")
    elif not token:
        print(f"Error: No token provided. Set PLAUD_TOKEN or PLAUD_API_TOKEN environment variable or use --token")
        sys.exit(1)
    
    if DEBUG:
        print(f"[DEBUG] Token provided: {'Yes' if token else 'No'}")
        print(f"[DEBUG] Email provided: {'Yes' if email else 'No'}")
    
    downloader = PlaudDownloader(
        email=email,
        password=password,
        token=token
    )
    
    success = downloader.run(
        output_dir=args.output,
        list_only=args.list_only,
        convert_format=args.convert
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
