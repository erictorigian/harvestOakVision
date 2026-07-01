#!/usr/bin/env bash
# Re-run the demo seed against a running stack (clears and reloads all demo data)
# Usage: ./scripts/reseed.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Reloading demo data..."
docker compose \
    -f docker-compose.yml \
    -f docker-compose.demo.yml \
    run --rm seed

echo "Done. Refresh the dashboard to see updated data."
