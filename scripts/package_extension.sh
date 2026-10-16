#!/usr/bin/env bash
# Zip the browser extension for upload to the Chrome Web Store, Firefox Add-ons and Edge Add-ons.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
version="$(python3 -c "import json; print(json.load(open('$root/extension/manifest.json'))['version'])")"
out="$root/dist/world-charity-search-$version.zip"

mkdir -p "$root/dist"
rm -f "$out"
(cd "$root/extension" && zip -qr "$out" . -x '.*')
echo "$out"
