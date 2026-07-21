#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="$(cd "$(dirname "$0")" && pwd)"
PAGE="file://${RUN_DIR}/concepts/prototype.html"
OUT="${RUN_DIR}/round-concepts/evidence"
CHROME="${CHROME:-/Users/esetseitkamal/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell}"

mkdir -p "$OUT"

for concept in a b c; do
  for screen in route photo guided; do
    for size in 375x844 1280x900; do
      width="${size%x*}"
      height="${size#*x}"
      "$CHROME" \
        --headless \
        --disable-gpu \
        --hide-scrollbars \
        --allow-file-access-from-files \
        --window-size="${width},${height}" \
        --screenshot="${OUT}/${concept}-${screen}-${size}.png" \
        "${PAGE}?concept=${concept}&screen=${screen}" >/dev/null 2>&1
    done
  done
done

for size in 375x844 1280x900; do
  width="${size%x*}"
  height="${size#*x}"
  "$CHROME" \
    --headless \
    --disable-gpu \
    --hide-scrollbars \
    --allow-file-access-from-files \
    --window-size="${width},${height}" \
    --screenshot="${OUT}/c-recovery-${size}.png" \
    "${PAGE}?concept=c&screen=recovery" >/dev/null 2>&1
done

printf 'Rendered %s screenshots into %s\n' "$(find "$OUT" -name '*.png' | wc -l | tr -d ' ')" "$OUT"
