#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

# --- CONFIGURATION ---
YTDLP_PATH = Path.home() / "Projects" / "yt-dlp" / "yt-dlp"
ARCHIVE_DIR = Path.home() / "Documents" / "VideoArchives"
WHISPER_DIR = Path.home() / "Projects" / "whisper.cpp"
DOWNLOAD_DIR = Path.cwd()  # current dir
FFMPEG_FILTERS = (
    'atempo=2.0,highpass=f=150,lowpass=f=6000,'
    'acompressor=threshold=-18dB:ratio=2:attack=5:release=50,volume=1.2'
)
WHISPER_CLI = Path(f"{WHISPER_DIR}/build/bin/whisper-cli")
WHISPER_MODEL = Path(f"{WHISPER_DIR}/models/ggml-large-v3-turbo.bin")

def run_cmd(cmd, cwd=None):
    print(f"[CMD] {' '.join(map(str, cmd))}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Command failed: {' '.join(map(str, cmd))}", file=sys.stderr)
        sys.exit(result.returncode)

def safe_remove(path: Path):
    """Safely delete a file if it exists."""
    try:
        if path.exists():
            path.unlink()
            print(f"🧹 Removed: {path}")
    except Exception as e:
        print(f"⚠️ Could not remove {path}: {e}")

def main(url):
    # --- Step 1: Download the video ---
    print("📥 Downloading video...")
    run_cmd([str(YTDLP_PATH), "-f", "b", url])

    # --- Step 2: Find the most recent downloaded video ---
    mp4_files = sorted(DOWNLOAD_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True)
    if not mp4_files:
        print("❌ No MP4 files found after download.")
        sys.exit(1)
    input_file = mp4_files[0]

    # --- Step 3: Convert to sped-up WAV with filters ---
    output_file = input_file.with_suffix(".wav")
    print("🎧 Converting to WAV...")
    ffmpeg_cmd = [
        "ffmpeg", "-i", str(input_file),
        "-filter:a", FFMPEG_FILTERS,
        "-vn", str(output_file)
    ]
    run_cmd(ffmpeg_cmd)

    # --- Step 4: Archive both files ---
    print("🗃 Archiving files...")
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived_video = ARCHIVE_DIR / input_file.name
    archived_audio = ARCHIVE_DIR / output_file.name
    shutil.copy2(input_file, archived_video)
    shutil.copy2(output_file, archived_audio)

    # --- Step 5: Clean up leftover files in home directory ---
    print("🧹 Cleaning up home directory...")
    home_dir = Path.home()
    for ext in (".mp4", ".mp3", ".wav"):
        for f in home_dir.glob(f"*{ext}"):
            safe_remove(f)

    def sanitize_filename(name: str) -> str:
        # Normalize unicode (remove accents, emoji, etc.)
        normalized = unicodedata.normalize("NFKD", name)
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        # Replace unsafe chars with underscores
        return re.sub(r'[^A-Za-z0-9._-]', '_', ascii_name)

    # --- Step 6: Prepare Whisper paths ---
    sanitized_base = sanitize_filename(archived_audio.stem)
    transcript_base = ARCHIVE_DIR / sanitized_base

    # --- Step 7: Run Whisper transcription ---
    print("🧠 Running Whisper transcription...")
    whisper_cmd = [
        str(WHISPER_CLI),
        "-m", str(WHISPER_MODEL),
        "-f", str(archived_audio),
        "-of", str(transcript_base),
        "-otxt",
        "-t", "6"
    ]
    run_cmd(whisper_cmd)
    transcript_file = transcript_base.with_suffix(".txt")
    print(f"✅ Done!\nArchived and transcribed:\n{archived_audio}\nTranscript: {transcript_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <YouTube_URL>")
        sys.exit(1)
    main(sys.argv[1])
