#!/bin/sh
set -eu

photo_dir="${PHOTO_DIR:-/app/data/error_photos}"

mkdir -p "$photo_dir"
chown -R app:app "$photo_dir"

exec /usr/sbin/runuser -u app -- "$@"
