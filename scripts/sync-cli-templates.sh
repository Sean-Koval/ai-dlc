#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${REPO_ROOT}/templates"
DEST="${REPO_ROOT}/crates/ai-dlc-cli/embedded-templates"

rsync -a --delete "${SRC}/" "${DEST}/"
