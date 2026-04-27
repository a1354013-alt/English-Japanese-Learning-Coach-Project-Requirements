#!/bin/sh
set -eu

mkdir -p /data /data/chroma_db
chown -R appuser:appuser /data /app

exec su -s /bin/sh appuser -c "$*"
