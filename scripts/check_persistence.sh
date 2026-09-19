#!/usr/bin/env bash
set -euo pipefail

echo '== before restart =='
./scripts/counts.sh

# Save a known-good state before restart.
docker compose down
sleep 2
docker compose up -d --build

echo '== after restart =='
./scripts/counts.sh

docker compose down -v
sleep 2
docker compose up -d --build

echo '== after volume reset =='
./scripts/counts.sh
