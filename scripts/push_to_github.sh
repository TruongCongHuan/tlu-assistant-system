#!/usr/bin/env bash
# Push monorepo to GitHub (run once after creating account).
#
# Usage:
#   ./scripts/push_to_github.sh <github-username> [repo-name] [public|private]
#
# Example:
#   ./scripts/push_to_github.sh truongconghuan tlu-assistant-system public
#
set -euo pipefail

USER="${1:?GitHub username required}"
REPO="${2:-tlu-assistant-system}"
VIS="${3:-public}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if git remote get-url origin &>/dev/null; then
  echo "Remote 'origin' already set: $(git remote get-url origin)"
else
  git remote add origin "https://github.com/${USER}/${REPO}.git"
  echo "Added origin → https://github.com/${USER}/${REPO}.git"
fi

echo ""
echo "Create the repo on GitHub first (if not exists):"
echo "  https://github.com/new"
echo "  Name: ${REPO}"
echo "  Visibility: ${VIS}"
echo "  Do NOT add README / .gitignore (already in repo)"
echo ""
read -r -p "Press Enter after repo is created on GitHub..."

git branch -M main
git push -u origin main

echo ""
echo "Done. Repo URL: https://github.com/${USER}/${REPO}"
