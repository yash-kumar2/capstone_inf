#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <image>" >&2
  exit 2
fi

image="$1"

if docker history --no-trunc "$image" 2>/dev/null | grep -Eiq 'AKIA[0-9A-Z]{16}|aws_secret|aws_access|POSTGRES_PASSWORD|password'; then
  echo "Possible secrets found in image history: $image" >&2
  docker history --no-trunc "$image" | grep -Eni 'AKIA[0-9A-Z]{16}|aws_secret|aws_access|POSTGRES_PASSWORD|password' || true
  exit 1
fi

if git grep -nE 'AKIA[0-9A-Z]{16}|aws_secret|aws_access|POSTGRES_PASSWORD|password' -- . ':!/.git' >/dev/null 2>&1; then
  echo "Possible secrets found in working tree." >&2
  git grep -nE 'AKIA[0-9A-Z]{16}|aws_secret|aws_access|POSTGRES_PASSWORD|password' -- . ':!/.git' || true
  exit 1
fi

echo "No obvious secrets found in $image or the working tree."
