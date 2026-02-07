#!/bin/bash
# llama-runner.sh
# Usage: ./llama-runner.sh <model-path> [context-size] [port]

# Expand to user's home directory safely
HOME_DIR="$HOME"
MODEL_DIR="/srv/vmstore/models"

# Executable path (relative to home)
LLAMA_BIN="$HOME_DIR/Projects/llama.cpp/build/bin/llama-server"

# Positional arguments
MODEL_PATH="${1:-}"
CONTEXT_SIZE="${2:-32768}"
PORT="${3:-7777}"
THREADS="${4:-15}"

# Validation
if [ -z "$MODEL_PATH" ]; then
  echo "Usage: $0 <model-path> [context-size] [port]"
  exit 1
fi

# Run the command
"$LLAMA_BIN" \
  -m "$MODEL_DIR/$MODEL_PATH" \
  --ctx-size "$CONTEXT_SIZE" \
  --n-gpu-layers 10 \
  --no-kv-offload \
  --threads $THREADS \
  --port "$PORT" \
  --jinja
