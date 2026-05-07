#!/usr/bin/env bash

BASE="$HOME/backups/bin"

# find newest timestamped backup folder
LATEST=$(ls "$BASE" | grep -E '^[0-9]{8}-[0-9]{6}$' | sort | tail -n 1)

TARGET="$BASE/$LATEST"

echo "[RUNNER] Using latest backup: $TARGET"

cd "$TARGET" || exit 1

export PYTHONPATH="$TARGET"

# stop any already running daemon (prevents "Already running")
pkill -f "quiz.daemon" 2>/dev/null

python3 -m quiz.daemon
