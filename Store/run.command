#!/bin/bash
set -e
cd -- "$(dirname -- "$0")"
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
exec uv run run.py "$@"
