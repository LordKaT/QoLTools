#!/home/felicia/.venvs/bash/bin/python

import logging
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)
logging.disable(logging.CRITICAL)

import os
import re
import shutil
import subprocess
import sys
import torch
import unicodedata
import whisperx

from contextlib import contextmanager, nullcontext
from io import StringIO
from pathlib import Path

from pyannote.audio import Pipeline
from whisperx.diarize import DiarizationPipeline

# CONFIGURATION
YTDLP_PATH = Path.home() / "Projects" / "yt-dlp" / "yt-dlp.sh"
YTDLP_CONFIG = Path.home() / ".config" / "yt-dlp" / "yt-dlp.conf"
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

debug_flag = False

# The nuclear "shut everything up unless I want to see it" option
@contextmanager
def suppress_fds():
    # Save actual OS stdout/stderr file descriptors
    old_stdout_fd = os.dup(1)
    old_stderr_fd = os.dup(2)

    # Open os.devnull
    devnull = os.open(os.devnull, os.O_WRONLY)

    try:
        # Redirect both stdout and stderr at the *OS level*
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        yield
    finally:
        # Restore original file descriptors
        os.dup2(old_stdout_fd, 1)
        os.dup2(old_stderr_fd, 2)
        os.close(devnull)
        os.close(old_stdout_fd)
        os.close(old_stderr_fd)

@contextmanager
def suppress_output():
    # Suppress python warnings
    warnings.filterwarnings("ignore")

    # Redirect stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    try:
        yield
    finally:
        # Restore
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        warnings.resetwarnings()

@contextmanager
def ultra_silence():
    with suppress_output():      # Python-level prints
        with suppress_fds():     # OS-level prints
            # Silence logging
            logging.getLogger().setLevel(logging.CRITICAL)
            logging.disable(logging.CRITICAL)

            try:
                yield
            finally:
                logging.disable(logging.NOTSET)

def run_cmd(cmd, cwd=None, debug=False):
    ctx = ultra_silence if debug else nullcontext

    with ctx():
        print(f"[CMD] {' '.join(map(str, cmd))}")
        if debug:
            result = subprocess.run(cmd, cwd=cwd)
        else:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
        )
    
    if result.returncode != 0:
        print(f"❌ Command failed: {' '.join(map(str, cmd))}", file=sys.stderr)
        sys.exit(result.returncode)

def safe_remove(path: Path):
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

def whisperx_transcribe(audio_path: Path, output_base: Path, debug=False):
    ctx = ultra_silence if debug else nullcontext
    
    print("🧠 Loading WhisperX model (CPU)...")

    with ctx():
        # 1. Load ASR model
        model = whisperx.load_model(
            whisper_arch=WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
        )

    # 2. Load audio as waveform
    print("🎧 Loading audio...")
    with ctx():
        audio = whisperx.load_audio(str(audio_path))

    # 3. Transcribe
    print("🎤 Transcribing with WhisperX...")
    with ctx():
        result = model.transcribe(audio, batch_size=4)
        # result has keys: "segments", "language", ...

    # 4. Align timestamps
    print("📐 Aligning timestamps...")
    with ctx():
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
    
    with ctx():
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

def get_video_id(url):
    match = re.search(r"(?<=v=)[\w-]+|(?<=youtu\.be/)[\w-]+", url)
    return match.group(0) if match else None

def main(url):
    video_id = get_video_id(url)
    if not video_id:
        print("❌ Could not extract video ID")
        sys.exit(1)

    # Step 1: Download the video
    print("📥 Downloading video...")
    run_cmd([str(YTDLP_PATH), "--config-location", str(YTDLP_CONFIG), "-o", "%(id)s.%(ext)s", url], None, debug_flag)

    # Step 2: Find the most recent downloaded video
    candidates = sorted(
        DOWNLOAD_DIR.glob(f"{video_id}.*"),
        key=os.path.getmtime,
        reverse=True
    )

    if not candidates:
        print(f"❌ No downloaded files found matching ID: {video_id}")
        sys.exit(1)

    if download_only:
        print("✅ Download-only mode: skipping transcoding, archiving, transcript.")
        return

    input_file = candidates[0]

    # Step 3: Convert to sped-up WAV with filters
    output_file = input_file.with_suffix(".wav")
    print("🎧 Converting to WAV...")
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", str(input_file),
        "-filter:a", FFMPEG_FILTERS,
        "-loglevel", "quiet",
        "-nostats",
        "-vn",
        str(output_file)
    ]
    run_cmd(ffmpeg_cmd, None, debug_flag)

    # Step 4: Archive both files
    print("🗃 Archiving files...")
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived_video = ARCHIVE_DIR / input_file.name
    archived_audio = ARCHIVE_DIR / output_file.name
    shutil.copy2(input_file, archived_video)
    shutil.copy2(output_file, archived_audio)

    # Step 5: Clean up leftover files in home directory
    print("🧹 Cleaning up home directory...")
    home_dir = Path.home()
    for ext in (".mp4", ".mp3", ".wav"):
        for f in home_dir.glob(f"*{ext}"):
            safe_remove(f)

    # Step 6: Build transcript output path
    sanitized_base = sanitize_filename(archived_audio.stem)
    transcript_base = ARCHIVE_DIR / sanitized_base

    # Step 7: Run WhisperX instead of whisper.cpp
    transcript_file = whisperx_transcribe(archived_audio, transcript_base)

    print(f"✅ COMPLETE!\nAudio archived at: {archived_audio}\nTranscript: {transcript_file}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print("Usage: python yt.py [-d] <YouTube_URL>")
        sys.exit(1)
    
    download_only = False
    if args[0] == "-d":
        download_only = True
        args = args[1:]
    
    if len(args) != 1:
        print(f"Usage: {sys.argv[0]} <YouTube_URL>")
        sys.exit(1)

    main(args[0])
