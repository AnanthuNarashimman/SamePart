#!/usr/bin/env bash
# Boot the API on a host.
#
# The database and the generated catalogues live under SAMEPART_DATA_ROOT, which on Railway is
# the mounted volume, so they survive deploys and restarts. On the first boot the volume is
# empty: seed and baseline run once (two or three minutes) and never again, because the file
# is there next time. Nothing here depends on the working directory except that it must be
# the repository root, which it is on every host that clones the repo.
set -euo pipefail

ROOT="${SAMEPART_DATA_ROOT:-/data}"
export PYTHONPATH="${PYTHONPATH:-backend}"
export SAMEPART_MODE="${SAMEPART_MODE:-live}"
export SAMEPART_DATA_DIR="$ROOT/generated"
export SAMEPART_DB_URL="sqlite:///$ROOT/samepart.db"

mkdir -p "$ROOT/generated"

if [ ! -s "$ROOT/samepart.db" ]; then
  echo "[start] no database at $ROOT/samepart.db — seeding (this happens once)"
  python -m samepart.cli seed
  python -m samepart.cli baseline
  echo "[start] seeded"
else
  echo "[start] database present, $(du -h "$ROOT/samepart.db" | cut -f1)"
fi

exec python -m uvicorn samepart.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
