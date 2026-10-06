#!/usr/bin/env bash
# Build one episode from a script file and publish it to the gh-pages branch.
# Usage: tools/daily.sh DATE "TITLE" "SUMMARY" SCRIPT.txt
# Run from the repo root (main branch checked out, push access configured).
set -euo pipefail
DATE="$1"; TITLE="$2"; SUMMARY="$3"; SCRIPT="$4"
BASE_URL="https://owenperkins111.github.io/cyber-brief"
REPO_ROOT="$(git rev-parse --show-toplevel)"
WORK="$(mktemp -d)"

pip install --break-system-packages -q kokoro-onnx soundfile >/dev/null 2>&1 || true

# 0. Privacy gate: refuse to publish if any denylisted term appears.
#    CB_DENY is a regex alternation supplied privately by the caller (never stored in this repo).
if [ -n "${CB_DENY:-}" ]; then
  if printf '%s\n%s\n' "$TITLE" "$SUMMARY" | cat - "$SCRIPT" | grep -n -i -w -E "$CB_DENY"; then
    echo "PRIVACY GATE: denylisted term found above; not publishing." >&2
    exit 3
  fi
else
  echo "PRIVACY GATE: CB_DENY not set; refusing to publish." >&2
  exit 3
fi

# 1. Archive the script on main
mkdir -p "$REPO_ROOT/scripts"
cp "$SCRIPT" "$REPO_ROOT/scripts/$DATE.txt"
git -C "$REPO_ROOT" add "scripts/$DATE.txt"
git -C "$REPO_ROOT" commit -qm "Script $DATE" || true
git -C "$REPO_ROOT" push -q origin HEAD:main

# 2. Audio
python3 "$REPO_ROOT/tools/tts.py" "$SCRIPT" "$WORK/$DATE.mp3"

# 3. Pull current site (if any), add episode, rebuild feed
SITE="$WORK/site"
if git -C "$REPO_ROOT" fetch -q origin gh-pages 2>/dev/null; then
  git -C "$REPO_ROOT" worktree add -q "$SITE" FETCH_HEAD --detach
else
  mkdir -p "$SITE"
fi
cp "$REPO_ROOT/tools/cover.png" "$SITE/cover.png"
python3 "$REPO_ROOT/tools/publish.py" "$SITE" "$WORK/$DATE.mp3" \
  --date "$DATE" --title "$TITLE" --summary "$SUMMARY" --base-url "$BASE_URL"

# 4. Publish gh-pages as a single orphan commit (keeps repo size flat)
PUB="$WORK/pub"; mkdir -p "$PUB"
(cd "$SITE" && tar --exclude=.git -cf - .) | (cd "$PUB" && tar -xf -)
cd "$PUB"
git init -q -b gh-pages
git config user.name "Cyber Brief"; git config user.email "cyber-brief@users.noreply.github.com"
git add -A
git commit -qm "Episode $DATE"
git push -qf "$(git -C "$REPO_ROOT" remote get-url origin)" gh-pages:gh-pages
git -C "$REPO_ROOT" worktree remove --force "$SITE" 2>/dev/null || true
echo "Published $BASE_URL/audio/$DATE.mp3"
