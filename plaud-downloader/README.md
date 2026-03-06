# Plaud Downloader

A simple Python script to download Plaud audio recordings with automatic format detection and conversion.

## Features

- **Automatic Format Detection**: Detects actual audio format (OPUS, MP3, WAV, FLAC) from file magic bytes
- **Format Conversion**: Convert OPUS to WAV (optimal for Whisper) or MP3
- **Redirect Handling**: Properly follows HTTP redirects (default behavior)
- **Whisper-Ready**: Convert to WAV at 16kHz mono for optimal Whisper transcription

## Approach

This script uses the **direct HTTP API approach** to interact with Plaud's web service. It:
- Authenticates using API token (from environment variable or command line)
- Fetches your list of recordings via Plaud's API
- Downloads each recording and auto-detects the actual format
- Optionally converts to WAV or MP3 as needed

## Prerequisites

- Python 3.7+
- `requests` library
- `ffmpeg` (for audio conversion) - install via `brew install ffmpeg` on macOS

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ffmpeg (required for conversion):**
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # Windows (using winget)
   winget install ffmpeg
   ```

3. **Set up the API token:**
   ```bash
   export PLAUD_API_TOKEN=your_token_here
   ```

   See [How to Get Your Token](#how-to-get-your-token) below for instructions.

## Usage

### Basic Download
```bash
export PLAUD_API_TOKEN=your_token_here
python download.py
```

### Download and Convert to WAV (optimal for Whisper)
```bash
python download.py --convert wav
```

### Download and Convert to MP3 (smaller file size)
```bash
python download.py --convert mp3
```

### List recordings only (without downloading)
```bash
python download.py --list-only
```

### Enable debug/verbose output
```bash
python download.py --debug
```

### Specify custom output directory
```bash
python download.py --output ./my_recordings --convert wav
```

## Format Detection & Conversion

### What Format Does Plaud Return?

Based on testing, Plaud API returns:
- **MP3** files (most common) - detected via ID3 tags and MPEG frame sync bytes
- **OPUS** files (in OGG container) - detected via OggS magic bytes

The script automatically detects the format from:
1. `Content-Type` HTTP header (if available)
2. File magic bytes (first 16 bytes)

### Why Convert to WAV?

WAV is recommended for Whisper transcription because:
- **No compression artifacts**: WAV is uncompressed PCM audio
- **Optimal sample rate**: 16kHz mono is ideal for Whisper
- **Better compatibility**: Works with all Whisper models

The conversion uses these optimal settings:
- **Format**: PCM 16-bit
- **Sample Rate**: 16kHz (optimal for Whisper)
- **Channels**: Mono

### Supported Conversions

| From | To WAV | To MP3 |
|------|--------|--------|
| OPUS/OGG | ✓ | ✓ |
| MP3 | ✓ | - |
| WAV | - | ✓ |
| FLAC | ✓ | ✓ |
| M4A | ✓ | ✓ |

## How to Get Your Token

1. **Log into Plaud** at https://plaud.ai in your browser
2. **Open Developer Tools** (press F12 or right-click → Inspect)
3. **Navigate to Application tab** (in DevTools)
4. **Click on "Local Storage"** in the left sidebar
5. **Select "plaud.ai"** domain
6. **Look for the auth token** - it could be named:
   - `access_token`
   - `auth_token`  
   - `token`
   - `auth`
7. **Copy the token value** (the text in the Value column)
8. **Set it as environment variable:**
   ```bash
   # macOS/Linux
   export PLAUD_API_TOKEN=your_copied_token_here
   
   # Windows (Command Prompt)
   set PLAUD_API_TOKEN=your_copied_token_here
   
   # Windows (PowerShell)
   $env:PLAUD_API_TOKEN="your_copied_token_here"
   ```

### Alternative: Using Session Storage
If you don't find the token in Local Storage, try:
1. Click on "Session Storage" in the DevTools sidebar
2. Select "plaud.ai" domain
3. Look for similar token keys

## Output

- Downloads are saved to `./downloads/` by default (or custom directory with `--output`)
- Files are named with correct extension: `{title}_{recording_id}.opus`, `{title}_{recording_id}.mp3`, etc.
- Already downloaded files are skipped automatically
- When using `--convert wav`, additional `.wav` files are created alongside original files

## Command-line Options

| Option | Description |
|--------|-------------|
| `--token` | Plaud API token (or use PLAUD_API_TOKEN env variable) |
| `--email` | Plaud account email (deprecated, use token) |
| `--password` | Plaud account password (deprecated, use token) |
| `--output`, `-o` | Output directory (default: "downloads") |
| `--list-only` | Only list recordings without downloading |
| `--debug` | Enable debug/verbose output (or use PLAUD_DEBUG=true env variable) |
| `--convert` | Convert to WAV (optimal for Whisper) or MP3 |

## Troubleshooting

- **No token found:** Make sure you're logged into Plaud in the browser before opening DevTools.
- **Login fails:** Ensure the token is correct and not expired. Try getting a fresh token.
- **No recordings found:** Check if you have any recordings in your Plaud account.
- **Download errors:** Some recordings may have expired or unavailable audio URLs.
- **ffmpeg not found:** Install ffmpeg (`brew install ffmpeg` on macOS)

### Debug Mode

For detailed troubleshooting, enable debug mode to see:
- API endpoints being called
- HTTP response status codes and headers
- Detected audio format
- Conversion progress

```bash
python download.py --debug
```

### Testing Format Detection

Run the included test script to verify format detection and conversion:
```bash
python test_format.py
```

### API Endpoints Used

This script uses the official Plaud API endpoints:
- **Authentication:** `POST https://api.plaud.ai/auth/access-token`
- **List Recordings:** `GET https://api.plaud.ai/file/simple/web?skip=0&limit=99999&is_trash=2&sort_by=start_time&is_desc=true`
- **Get Temp URL:** `GET https://api.plaud.ai/file/temp-url/{recording_id}`

Based on research from: https://github.com/JamesStuder/Plaud_API

## License

MIT
