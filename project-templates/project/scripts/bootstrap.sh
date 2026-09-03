#!/bin/sh
# Standalone entry: no preinstalled AI-DLC, Python, mise, Node, or Rust.
set -eu
AI_DLC_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
AI_DLC_TARGET=local
AI_DLC_MODE=release
AI_DLC_PLAN=false
while [ "$#" -gt 0 ]; do
    case "$1" in
        --source) AI_DLC_MODE=source; shift ;;
        --target) AI_DLC_TARGET=$2; shift 2 ;;
        --root) AI_DLC_ROOT=$2; shift 2 ;;
        --plan) AI_DLC_PLAN=true; shift ;;
        *) echo "Unknown bootstrap argument: $1" >&2; exit 2 ;;
    esac
done
AI_DLC_PLATFORM="$(uname -s)-$(uname -m)"
# Rosetta must not select Intel artifacts on an Apple silicon machine.
if [ "$(uname -s)" = Darwin ] && [ "$(sysctl -n hw.optional.arm64 2>/dev/null || true)" = 1 ]; then
    AI_DLC_PLATFORM=Darwin-arm64
fi
. "$AI_DLC_ROOT/bootstrap/versions.sh"
. "$AI_DLC_ROOT/bootstrap/download.sh"
AI_DLC_BOOTSTRAP_HOME=${AI_DLC_BOOTSTRAP_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/ai-dlc/bootstrap}
if [ "$AI_DLC_PLAN" = true ]; then
    printf 'platform=%s\nmode=%s\nuv=%s\npython=%s\nmise=%s\ntarget=%s\n' "$AI_DLC_PLATFORM" "$AI_DLC_MODE" "$AI_DLC_UV_URL" "$AI_DLC_PYTHON_VERSION" "$AI_DLC_MISE_URL" "$AI_DLC_TARGET"
    exit 0
fi
if [ "$AI_DLC_MODE" = release ]; then
    [ -f "$AI_DLC_ROOT/bootstrap/release.sh" ] || { echo 'Release wheel manifest is not available. For AI-DLC development use --source; publish a verified release before distributing project bootstrap.' >&2; exit 1; }
    . "$AI_DLC_ROOT/bootstrap/release.sh"
fi
command -v curl >/dev/null || { echo 'curl and CA certificates are required.' >&2; exit 1; }
mkdir -p "$AI_DLC_BOOTSTRAP_HOME/bin" "$AI_DLC_BOOTSTRAP_HOME/downloads"
AI_DLC_DOWNLOADS="$AI_DLC_BOOTSTRAP_HOME/downloads"
AI_DLC_UV_ARCHIVE="$AI_DLC_DOWNLOADS/uv-$AI_DLC_UV_VERSION-$AI_DLC_UV_TARGET.tar.gz"
if [ ! -f "$AI_DLC_UV_ARCHIVE" ] || [ "$(ai_dlc_hash "$AI_DLC_UV_ARCHIVE")" != "$AI_DLC_UV_SHA256" ]; then
    ai_dlc_download "$AI_DLC_UV_URL" "$AI_DLC_UV_SHA256" "$AI_DLC_UV_ARCHIVE"
fi
AI_DLC_EXTRACT=$(mktemp -d "$AI_DLC_DOWNLOADS/extract.XXXXXX")
trap 'rm -rf "$AI_DLC_EXTRACT"' EXIT HUP INT TERM
tar -xzf "$AI_DLC_UV_ARCHIVE" -C "$AI_DLC_EXTRACT"
cp "$AI_DLC_EXTRACT/uv-$AI_DLC_UV_TARGET/uv" "$AI_DLC_BOOTSTRAP_HOME/bin/uv"
cp "$AI_DLC_EXTRACT/uv-$AI_DLC_UV_TARGET/uvx" "$AI_DLC_BOOTSTRAP_HOME/bin/uvx"
export PATH="$AI_DLC_BOOTSTRAP_HOME/bin:$PATH"
export UV_PYTHON_INSTALL_DIR="$AI_DLC_BOOTSTRAP_HOME/python"
export UV_PYTHON_BIN_DIR="$AI_DLC_BOOTSTRAP_HOME/bin"
uv python install "$AI_DLC_PYTHON_VERSION" --managed-python
AI_DLC_ENGINE_PYTHON=$(uv python find --managed-python "$AI_DLC_PYTHON_VERSION")
if [ "$AI_DLC_MODE" = source ]; then
    # uv.lock belongs to this checkout; never execute an older installed release in self CI.
    AI_DLC_SOURCE_KEY=$(printf '%s' "$AI_DLC_ROOT" | cksum | cut -d ' ' -f 1)
    AI_DLC_SOURCE_ENV="$AI_DLC_BOOTSTRAP_HOME/source-$AI_DLC_SOURCE_KEY"
    UV_PROJECT_ENVIRONMENT="$AI_DLC_SOURCE_ENV" uv sync --project "$AI_DLC_ROOT" --locked --python "$AI_DLC_ENGINE_PYTHON"
    AI_DLC_CLI="$AI_DLC_SOURCE_ENV/bin/ai-dlc"
else
    ai_dlc_download "$AI_DLC_WHEEL_URL" "$AI_DLC_WHEEL_SHA256" "$AI_DLC_DOWNLOADS/$AI_DLC_WHEEL_NAME"
    ai_dlc_download "$AI_DLC_CONSTRAINTS_URL" "$AI_DLC_CONSTRAINTS_SHA256" "$AI_DLC_DOWNLOADS/constraints.txt"
    uv venv --python "$AI_DLC_ENGINE_PYTHON" "$AI_DLC_BOOTSTRAP_HOME/engine-$AI_DLC_ENGINE_VERSION"
    uv pip install --python "$AI_DLC_BOOTSTRAP_HOME/engine-$AI_DLC_ENGINE_VERSION/bin/python" --require-hashes -r "$AI_DLC_DOWNLOADS/constraints.txt"
    uv pip install --python "$AI_DLC_BOOTSTRAP_HOME/engine-$AI_DLC_ENGINE_VERSION/bin/python" --no-deps "$AI_DLC_DOWNLOADS/$AI_DLC_WHEEL_NAME"
    AI_DLC_CLI="$AI_DLC_BOOTSTRAP_HOME/engine-$AI_DLC_ENGINE_VERSION/bin/ai-dlc"
fi
AI_DLC_MISE_BINARY="$AI_DLC_DOWNLOADS/mise-$AI_DLC_MISE_VERSION-$AI_DLC_MISE_TARGET"
if [ ! -f "$AI_DLC_MISE_BINARY" ] || [ "$(ai_dlc_hash "$AI_DLC_MISE_BINARY")" != "$AI_DLC_MISE_SHA256" ]; then
    ai_dlc_download "$AI_DLC_MISE_URL" "$AI_DLC_MISE_SHA256" "$AI_DLC_MISE_BINARY"
fi
cp "$AI_DLC_MISE_BINARY" "$AI_DLC_BOOTSTRAP_HOME/bin/mise"
chmod +x "$AI_DLC_BOOTSTRAP_HOME/bin/mise"
ln -sf "$AI_DLC_CLI" "$AI_DLC_BOOTSTRAP_HOME/bin/ai-dlc"
ln -sf "$AI_DLC_CLI" "$AI_DLC_BOOTSTRAP_HOME/bin/ai-dlc-cli"
export PATH="$(dirname "$AI_DLC_CLI"):$PATH"
"$AI_DLC_CLI" project setup --root "$AI_DLC_ROOT" --target "$AI_DLC_TARGET"
if [ -n "${GITHUB_PATH:-}" ]; then
    printf '%s\n%s\n' "$(dirname "$AI_DLC_CLI")" "$AI_DLC_BOOTSTRAP_HOME/bin" >> "$GITHUB_PATH"
fi
printf '\nReady. Add these directories to your PATH for this environment:\n%s\n%s\n' "$(dirname "$AI_DLC_CLI")" "$AI_DLC_BOOTSTRAP_HOME/bin"
