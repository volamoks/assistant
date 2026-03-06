#!/usr/bin/env python3
"""Test script for format detection and conversion functionality"""

import os
import sys

# Add parent directory to path to import download module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the DEBUG variable for testing
import download
download.DEBUG = True

def test_detect_audio_format():
    """Test audio format detection from magic bytes"""
    print("=" * 50)
    print("Testing format detection...")
    print("=" * 50)
    
    # Create a downloader instance (no token needed for format detection)
    downloader = download.PlaudDownloader()
    
    # Test with existing MP3 file
    mp3_path = "downloads/01-08 Семинар Концепция A2A регуляторика ЦБ и инте_72262711c5c589c035981ce921b5f488.mp3"
    if os.path.exists(mp3_path):
        fmt = downloader.detect_audio_format(mp3_path)
        print(f"MP3 file detected as: {fmt}")
        assert fmt == 'mp3', f"Expected mp3, got {fmt}"
        print("  ✓ MP3 detection works")
    
    # Test with OPUS file we created
    opus_path = "test_opus.opus"
    if os.path.exists(opus_path):
        fmt = downloader.detect_audio_format(opus_path)
        print(f"OPUS file detected as: {fmt}")
        assert fmt == 'opus', f"Expected opus, got {fmt}"
        print("  ✓ OPUS detection works")
    
    print("✓ Format detection tests passed\n")

def test_convert_audio():
    """Test audio conversion from OPUS to WAV/MP3"""
    print("=" * 50)
    print("Testing audio conversion...")
    print("=" * 50)
    
    # Create a downloader instance
    downloader = download.PlaudDownloader()
    
    opus_path = "test_opus.opus"
    if not os.path.exists(opus_path):
        print("SKIP: OPUS test file not found")
        return
    
    # Test conversion to WAV
    print("\nConverting OPUS -> WAV...")
    wav_path = downloader.convert_audio(opus_path, 'wav')
    if wav_path:
        print(f"  ✓ Converted to: {wav_path}")
        # Verify the file
        assert os.path.exists(wav_path), "WAV file not created"
        print(f"  ✓ File exists: {os.path.getsize(wav_path)} bytes")
        
        # Verify it's actually WAV
        import subprocess
        result = subprocess.run(['file', wav_path], capture_output=True, text=True)
        print(f"  File type: {result.stdout.strip()}")
        assert 'WAVE' in result.stdout or 'RIFF' in result.stdout, "Not a valid WAV file"
        print("  ✓ WAV file is valid")
    else:
        print("  ✗ Conversion failed")
        return
    
    # Test conversion to MP3
    print("\nConverting OPUS -> MP3...")
    mp3_path = downloader.convert_audio(opus_path, 'mp3')
    if mp3_path:
        print(f"  ✓ Converted to: {mp3_path}")
        assert os.path.exists(mp3_path), "MP3 file not created"
        print(f"  ✓ File exists: {os.path.getsize(mp3_path)} bytes")
        
        # Verify it's actually MP3
        result = subprocess.run(['file', mp3_path], capture_output=True, text=True)
        print(f"  File type: {result.stdout.strip()}")
        assert 'MPEG' in result.stdout or 'MP3' in result.stdout, "Not a valid MP3 file"
        print("  ✓ MP3 file is valid")
    else:
        print("  ✗ Conversion failed")
        return
    
    print("\n✓ Audio conversion tests passed\n")

def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("Plaud Downloader - Format Detection & Conversion Tests")
    print("=" * 50 + "\n")
    
    try:
        test_detect_audio_format()
        test_convert_audio()
        
        print("=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup test files
        for f in ['test_opus.opus', 'test_opus.wav', 'test_opus.mp3']:
            if os.path.exists(f):
                os.remove(f)
                print(f"Cleaned up: {f}")

if __name__ == "__main__":
    main()
