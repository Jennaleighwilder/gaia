#!/bin/bash
# Deploy GAIA public status page to GitHub Pages.
# Usage: ./scripts/deploy_github_pages.sh
# Ensure git remote is set: git remote add origin https://github.com/jennaleighwilder/jennaleighwilder.github.io.git

set -e
cd "$(dirname "$0")/.."

# Ensure we have the status page
STATUS_HTML="docs/gaia_public_status.html"
if [ ! -f "$STATUS_HTML" ]; then
  echo "Missing $STATUS_HTML"
  exit 1
fi

# For username.github.io repo: root index.html is the site
# For project repo: use docs/ or gh-pages branch
# This script supports both - copies to index.html for root deploy
cp "$STATUS_HTML" docs/index.html 2>/dev/null || mkdir -p docs && cp "$STATUS_HTML" docs/index.html

git add docs/index.html docs/gaia_public_status.html 2>/dev/null || true
git status

echo ""
echo "To deploy to GitHub Pages:"
echo "  1. git add -A && git commit -m 'Add GAIA public status'"
echo "  2. git branch -M main && git remote add origin https://github.com/jennaleighwilder/jennaleighwilder.github.io.git  # if new"
echo "  3. git push -u origin main"
echo ""
echo "If using project repo with gh-pages:"
echo "  git checkout -b gh-pages && git add docs/ && git commit -m 'GAIA status' && git push origin gh-pages"
echo "  Then enable Pages in repo Settings > Pages > Source: gh-pages / docs"
