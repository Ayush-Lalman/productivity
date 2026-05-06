#!/bin/bash

# Only these files/folders get backed up
FILES_TO_BACKUP=(
    "$HOME/.local/bin/central-planner-daemon.sh"
    "$HOME/.local/bin/gosplan-gui.sh"
    "$HOME/.local/bin/gosplan-gui.py"
    "$HOME/.local/bin/time-monitor-daemon.py"
    "$HOME/.local/bin/reward-daemon.py"
    "$HOME/.local/bin/app-blocker-daemon.py"
    "$HOME/.local/bin/quiz"
    "$HOME/.local/bin/backup-daemons.sh"
)

BASE="$HOME/backups/bin"
GITHUB_REPO="$HOME/backups"

mkdir -p "$BASE"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEST="$BASE/$TIMESTAMP"
LATEST="$BASE/latest"

# Create new backup folder
mkdir -p "$DEST"

# Copy only the important files/folders
for item in "${FILES_TO_BACKUP[@]}"; do
    if [ -e "$item" ]; then
        cp -r "$item" "$DEST/"
    fi
done

# Update latest pointer
ln -sfn "$DEST" "$LATEST"

# Keep only last 10 snapshots locally
cd "$BASE" || exit
ls -1dt */ | tail -n +11 | xargs -r rm -rf

# Push to GitHub (only latest)
cd "$GITHUB_REPO" || exit

# Add only the latest backup and essential files
git add -f bin/latest 2>/dev/null
git add -f "$(readlink -f bin/latest)" 2>/dev/null
git add -f .gitignore 2>/dev/null

# Check if there are changes
if git diff --cached --quiet; then
    echo "No changes to commit"
else
    git commit -m "Backup: $TIMESTAMP"
    git push origin main
fi
