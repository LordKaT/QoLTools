#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path

HOME_DIR = Path.home()
MODEL_DIR = Path("/srv/vmstore/models")
LLAMA_BIN = HOME_DIR / "Projects/llama.cpp/build/bin/llama-server"

parser = argparse.ArgumentParser(description="Run llama-server with named arguments")
parser.add_argument("--model", "-m", required=True, help="Model path (relative to MODEL_DIR)")
parser.add_argument("--ctx", "-c", type=int, default=32768, help="Context size")
parser.add_argument("--port", "-p", type=int, default=7777, help="Port number")
parser.add_argument("--threads", "-t", type=int, default=15, help="Number of CPU threads")
parser.add_argument("--gpu", "-g", type=int, default=0, help="Number of layers to offload to GPU")

args = parser.parse_args()

cmd = [
    str(LLAMA_BIN),
    "-m", str(MODEL_DIR / args.model),
    "--ctx-size", str(args.ctx),
    "--n-gpu-layers", str(args.gpu),
    "--no-kv-offload",
    "--threads", str(args.threads),
    "--port", str(args.port),
    "--jinja"
]

print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)
