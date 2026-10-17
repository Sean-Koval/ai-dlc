#!/bin/sh
set -eu
# Hosted agent environments set up this checkout like a local one; cloud sandbox
# rendering belongs to hangar (ADR 0001), so there is no cloud execution target.
# Re-run after checkout/cache restoration; successful setup steps are verified and resumed.
exec sh scripts/bootstrap.sh --source
