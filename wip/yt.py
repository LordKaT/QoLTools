#!/home/felicia/.venvs/bash/bin/python
import os
import re
import shutil
import subprocess
import sys
import torch
import unicodedata
import whisperx
from pathlib import Path
from pyannote.audio import Pipeline
from whisperx.diarize import DiarizationPipeline

# --- CONFIGURATION ---
YTDLP_PATH = Path.home() / "Projects" / "yt-dlp" / "yt-dlp"
ARCHIVE_DIR = Path.home() / "Documents" / "VideoArchives"
WHISPER_DIR = Path.home() / "Projects" / "whisper.cpp"
DOWNLOAD_DIR = Path.cwd()  # current dir
FFMPEG_FILTERS = (
    'atempo=2.0,highpass=f=150,lowpass=f=6000,'
    'acompressor=threshold=-18dB:ratio=2:attack=5:release=50,volume=1.2'
)
#WHISPER_CLI = Path(f"{WHISPER_DIR}/build/bin/whisper-cli")
#WHISPER_MODEL = Path(f"{WHISPER_DIR}/models/ggml-large-v3-turbo.bin")

WHISPER_MODEL = "large-v3"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"

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

def sanitize_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r'[^A-Za-z0-9._-]', '_', ascii_name)

def whisperx_transcribe(audio_path: Path, output_base: Path):
    print("🧠 Loading WhisperX model (CPU)...")

    # 1. Load ASR model
    model = whisperx.load_model(
        whisper_arch=WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE,
    )

    # 2. Load audio as waveform
    print("🎧 Loading audio...")
    audio = whisperx.load_audio(str(audio_path))

    # 3. Transcribe
    print("🎤 Transcribing with WhisperX...")
    result = model.transcribe(audio, batch_size=4)
    # result has keys: "segments", "language", ...

    # 4. Align timestamps
    print("📐 Aligning timestamps...")
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=WHISPER_DEVICE,
    )
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        WHISPER_DEVICE,
        return_char_alignments=False,
    )

    # 5. Speaker diarization via DiarizationPipeline
    print("🔎 Running speaker diarization (WhisperX + pyannote)...")

    hf_token = os.environ.get("HF_WHISPER_TOKEN")
    if hf_token is None:
        print("❌ ERROR: HF_WHISPER_TOKEN environment variable not set.")
        print("Run: export HF_WHISPER_TOKEN=your_huggingface_token")
        sys.exit(1)

    diarize_model = DiarizationPipeline(
        use_auth_token=hf_token,
        device=WHISPER_DEVICE,
    )

    diarize_segments = diarize_model(audio)
    # diarize_model(audio, min_speakers=..., max_speakers=...) if you want

    # 6. Combine diarization with ASR segments
    result = whisperx.assign_word_speakers(
        diarize_segments,
        result,
    )

    # 7. Write transcript with speaker labels
    lines = []
    for seg in result["segments"]:
        speaker = seg.get("speaker", "UNKNOWN")
        text = seg["text"].strip()
        lines.append(f"[{speaker}] {text}")

    transcript_path = output_base.with_suffix(".txt")
    transcript_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📝 Transcript saved: {transcript_path}")
    return transcript_path

def main(url):
    # --- Step 1: Download the video ---
    print("📥 Downloading video...")
    #run_cmd([str(YTDLP_PATH), "-f", "b", url])
    run_cmd([str(YTDLP_PATH), "-f", "b", "-o", "%(id)s.%(ext)s", url])

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

    # --- Step 6: Build transcript output path ---
    sanitized_base = sanitize_filename(archived_audio.stem)
    transcript_base = ARCHIVE_DIR / sanitized_base

    # --- Step 7: Run WhisperX instead of whisper.cpp ---
    transcript_file = whisperx_transcribe(archived_audio, transcript_base)

    print(f"✅ COMPLETE!\nAudio archived at: {archived_audio}\nTranscript: {transcript_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <YouTube_URL>")
        sys.exit(1)
    main(sys.argv[1])
