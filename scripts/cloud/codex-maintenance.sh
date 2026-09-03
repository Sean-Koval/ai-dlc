#!/bin/sh
set -eu
# Re-run after checkout/cache restoration; successful setup steps are verified and resumed.
exec sh scripts/bootstrap.sh --source --target codex-cloud
