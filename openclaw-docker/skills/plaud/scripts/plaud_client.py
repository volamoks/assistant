#!/usr/bin/env python3
"""
Plaud API Client — fetch recordings, transcripts, and AI summaries.

Usage:
    python3 plaud_client.py list [--json]
    python3 plaud_client.py details <file_id> [--json]
    python3 plaud_client.py download <file_id> [-o output.mp3]

Environment variables (or .env in same directory):
    PLAUD_TOKEN        — JWT token (with or without 'bearer ' prefix)
    PLAUD_API_DOMAIN   — API domain (auto-discovered if not set)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests

# ── Load .env from same dir ──────────────────────────────────────────────────
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# ── Domain candidates (tried in order) ───────────────────────────────────────
_DOMAIN_CANDIDATES = [
    "https://api.plaud.ai",
    "https://api-euc1.plaud.ai",
    "https://api-use1.plaud.ai",
    "https://api-usw2.plaud.ai",
]


class PlaudClient:
    """Minimal Plaud API client with auto-domain-discovery."""

    def __init__(self, token: str = None, domain: str = None):
        raw = token or os.environ.get("PLAUD_TOKEN", "")
        # Normalise: always send lowercase 'bearer <jwt>'
        if raw.lower().startswith("bearer "):
            self._token = raw
        else:
            self._token = f"bearer {raw}"

        self._domain = domain or os.environ.get("PLAUD_API_DOMAIN", "")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": self._token,
            "Content-Type": "application/json",
        })

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _get(self, path: str, domain: str = None, **kwargs) -> requests.Response:
        base = domain or self._domain or _DOMAIN_CANDIDATES[0]
        url = f"{base.rstrip('/')}/{path.lstrip('/')}"
        return self._session.get(url, timeout=30, **kwargs)

    def _discover_domain(self) -> str:
        """Find which domain serves list API for this token."""
        if self._domain:
            return self._domain
        for d in _DOMAIN_CANDIDATES:
            try:
                r = self._session.get(
                    f"{d}/file/simple/web", timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("data_file_list") is not None or data.get("code") == 0:
                        self._domain = d
                        return d
            except Exception:
                continue
        raise RuntimeError("Could not auto-discover Plaud API domain. Set PLAUD_API_DOMAIN.")

    def _discover_detail_domain(self, file_id: str) -> str:
        """
        Find which regional domain holds the detail for a specific file.
        Plaud returns code=-302 with {"data":{"domains":{"api":"<correct domain>"}}}
        when you hit the wrong region.
        """
        for d in _DOMAIN_CANDIDATES:
            try:
                r = self._session.get(
                    f"{d}/file/detail/{file_id}", timeout=10
                )
                if r.status_code != 200:
                    continue
                body = r.json()
                code = body.get("code", body.get("status"))
                if code == -302:
                    # Server told us the right domain
                    hint = (body.get("data") or {}).get("domains", {}).get("api")
                    if hint:
                        return hint
                    continue
                if body.get("data") is not None and code not in (-1, -302):
                    return d
            except Exception:
                continue
        return self._discover_domain()  # fallback to list domain

    # ── Public API ───────────────────────────────────────────────────────────

    def list_files(self, include_trash: bool = False) -> list:
        """List all files. Returns list of file dicts."""
        domain = self._discover_domain()
        r = self._get("file/simple/web", domain=domain)
        r.raise_for_status()
        data = r.json()
        files = data.get("data_file_list", [])
        if not include_trash:
            files = [f for f in files if not f.get("is_trash")]
        return files

    def get_file_details(self, file_id: str) -> dict:
        """Get full file detail including trans_result and ai_content."""
        domain = self._discover_detail_domain(file_id)
        r = self._get(f"file/detail/{file_id}", domain=domain)
        r.raise_for_status()
        body = r.json()
        code = body.get("code", body.get("status"))
        if code == -302:
            # One more hop with the hinted domain
            hint = (body.get("data") or {}).get("domains", {}).get("api")
            if hint:
                r = self._get(f"file/detail/{file_id}", domain=hint)
                r.raise_for_status()
                body = r.json()
        return body

    def get_transcript(self, file_id: str) -> str | None:
        """
        Extract plain-text transcript from file detail.
        Returns concatenated segment texts, or None if not available.
        """
        body = self.get_file_details(file_id)
        data = body.get("data") or {}
        tr = data.get("trans_result") or {}
        segments = tr.get("segments", []) if isinstance(tr, dict) else []
        if not segments:
            return None
        return " ".join(s.get("text", "") for s in segments if s.get("text"))

    def get_ai_summary(self, file_id: str) -> dict | None:
        """Return the ai_content dict from file detail, or None."""
        body = self.get_file_details(file_id)
        data = body.get("data") or {}
        return data.get("ai_content") or None

    # ── Format Detection & Conversion ─────────────────────────────────────

    def detect_format_from_content_type(self, response: requests.Response) -> str | None:
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

    def detect_audio_format(self, filepath: str) -> str:
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

    def convert_audio(self, input_path: str, output_format: str = 'wav') -> str | None:
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
            print("  Warning: ffmpeg not found - cannot convert audio")
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
                print(f"  Warning: Unsupported output format: {output_format}")
                return None

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                print(f"  Warning: Conversion failed: {result.stderr[:200]}")
                return None

            # Verify output file exists
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"  Converted to {output_format.upper()}: {size / 1024:.1f}KB")
                return output_path
            else:
                print(f"  Warning: Conversion failed - output file not created")
                return None

        except subprocess.TimeoutExpired:
            print(f"  Warning: Conversion timeout (file may be too large)")
            return None
        except Exception as e:
            print(f"  Warning: Conversion error: {e}")
            return None

    def download_audio(self, file_id: str, output_path: str = None, convert_format: str = None) -> str:
        """
        Download audio file. Returns path to saved file.
        
        Args:
            file_id: Plaud file ID
            output_path: Optional output path. If not provided, uses file_name.mp3
            convert_format: Optional format to convert to ('wav' or 'mp3'). 
                           If provided, will convert the downloaded audio to this format.
                           
        Note: Plaud sends binary audio with Content-Type: application/json — handled.
        Supports OPUS format detection and conversion.
        """
        domain = self._discover_detail_domain(file_id)

        if output_path is None:
            details = self.get_file_details(file_id)
            name = (details.get("data") or {}).get("file_name", file_id)
            name = "".join(c for c in name if c.isalnum() or c in " -_").strip()
            output_path = f"{name}.mp3"

        r = self._get(f"file/download/{file_id}", domain=domain, stream=True)
        r.raise_for_status()

        # Detect format from Content-Type header
        content_type_format = self.detect_format_from_content_type(r)

        # Peek first bytes to distinguish real JSON error vs binary audio
        peek = b""
        chunks_buf = []
        for chunk in r.iter_content(8192):
            if chunk:
                chunks_buf.append(chunk)
                peek += chunk
                if len(peek) >= 64:
                    break

        peek_text = peek[:4].decode("utf-8", errors="ignore").strip()
        if peek_text and peek_text[0] in ("{", "["):
            # It's a real JSON error response
            raw = peek + b"".join(r.iter_content(8192))
            try:
                err = json.loads(raw)
                raise RuntimeError(f"Download error: {err.get('msg', raw[:100])}")
            except json.JSONDecodeError:
                raise RuntimeError(f"Unexpected response: {raw[:100]}")

        # Determine file extension based on detected format
        extension_map = {
            'opus': '.opus',
            'mp3': '.mp3',
            'wav': '.wav',
            'flac': '.flac',
            'm4a': '.m4a',
        }
        detected_format = content_type_format
        if not detected_format:
            # Save to temp path first, then detect from magic bytes
            tmp_path = output_path + ".tmp"
            with open(tmp_path, "wb") as f:
                for c in chunks_buf:
                    f.write(c)
                for c in r.iter_content(8192):
                    if c:
                        f.write(c)
            detected_format = self.detect_audio_format(tmp_path)
            
            # Rename to proper extension
            extension = extension_map.get(detected_format, '.audio')
            final_path = output_path.rsplit('.', 1)[0] + extension if '.' in output_path else output_path + extension
            if tmp_path != final_path:
                import shutil as sh
                sh.move(tmp_path, final_path)
            output_path = final_path
        else:
            # Use Content-Type based extension
            extension = extension_map.get(detected_format, '.audio')
            base_path = output_path.rsplit('.', 1)[0] if '.' in output_path else output_path
            output_path = base_path + extension
            
            with open(output_path, "wb") as f:
                for c in chunks_buf:
                    f.write(c)
                for c in r.iter_content(8192):
                    if c:
                        f.write(c)

        # Report detected format
        print(f"  Downloaded: {os.path.basename(output_path)} (format: {detected_format or 'unknown'})")

        # Convert if requested
        if convert_format and detected_format != convert_format:
            converted_path = self.convert_audio(output_path, convert_format)
            if converted_path:
                print(f"  Converted to {convert_format.upper()}: {os.path.basename(converted_path)}")
                return converted_path
            else:
                print(f"  Warning: Conversion failed, returning original format")

        return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def _fmt_duration(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s" if m else f"{s}s"


def main():
    p = argparse.ArgumentParser(description="Plaud API Client")
    p.add_argument("--token", "-t", default=os.environ.get("PLAUD_TOKEN"))
    p.add_argument("--domain", "-d", default=os.environ.get("PLAUD_API_DOMAIN", ""))
    sub = p.add_subparsers(dest="cmd")

    lp = sub.add_parser("list")
    lp.add_argument("--json", "-j", action="store_true")
    lp.add_argument("--include-trash", action="store_true")

    dp = sub.add_parser("details")
    dp.add_argument("file_id")
    dp.add_argument("--json", "-j", action="store_true")

    dl = sub.add_parser("download")
    dl.add_argument("file_id")
    dl.add_argument("--output", "-o", default=None)
    dl.add_argument("--convert", "-c", choices=['wav', 'mp3'], default=None,
                    help="Convert downloaded audio to specified format (wav=optimal for Whisper)")

    sub.add_parser("tags")

    args = p.parse_args()

    if not args.token:
        print("Error: PLAUD_TOKEN not set. Use --token or set env var.", file=sys.stderr)
        sys.exit(1)

    client = PlaudClient(token=args.token, domain=args.domain)

    try:
        if args.cmd == "list":
            files = client.list_files(include_trash=getattr(args, "include_trash", False))
            if getattr(args, "json", False):
                print(json.dumps(files, indent=2, ensure_ascii=False))
            else:
                print(f"Found {len(files)} files:\n")
                for f in files:
                    dur = _fmt_duration(f.get("duration", 0))
                    trans = "✓" if f.get("is_trans") else " "
                    summ  = "✓" if f.get("is_summary") else " "
                    print(f"  {f['id']}  {dur:>10}  T:{trans} S:{summ}  {f['filename']}")

        elif args.cmd == "details":
            body = client.get_file_details(args.file_id)
            if getattr(args, "json", False):
                print(json.dumps(body, indent=2, ensure_ascii=False))
            else:
                data = body.get("data") or {}
                tr = data.get("trans_result") or {}
                segs = tr.get("segments", []) if isinstance(tr, dict) else []
                ai = data.get("ai_content")
                print(f"File:     {data.get('file_name')}")
                print(f"Duration: {_fmt_duration(data.get('duration', 0))}")
                print(f"Transcript segments: {len(segs)}")
                print(f"AI summary: {'yes' if ai else 'no'}")
                if segs:
                    print("\n--- Transcript preview ---")
                    for s in segs[:3]:
                        print(f"  [{s.get('start',0)//1000}s] {s.get('text','')[:100]}")

        elif args.cmd == "download":
            out = client.download_audio(args.file_id, args.output, convert_format=args.convert)
            print(f"Saved: {out}")

        elif args.cmd == "tags":
            domain = client._discover_domain()
            r = client._get("filetag/", domain=domain)
            r.raise_for_status()
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))

        else:
            p.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
