#!/bin/sh
set -eu
AI_DLC_SESSION_BIN=${AI_DLC_BOOTSTRAP_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/ai-dlc/bootstrap}/bin
export PATH="$PWD/.venv/bin:$AI_DLC_SESSION_BIN:$PATH"
ai-dlc context --brief
