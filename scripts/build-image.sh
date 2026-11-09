#!/bin/sh
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
exec docker build --platform linux/amd64 -f docker/Dockerfile -t crusader-sdk:local .
