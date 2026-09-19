#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T agent sh -lc 'getent hosts postgres qdrant redis mock-erp || python - <<"PY"
import socket
for host in ["postgres", "qdrant", "redis", "mock-erp"]:
    try:
        print(f"{host}: {socket.gethostbyname(host)}")
    except socket.gaierror as exc:
        raise SystemExit(f"{host}: {exc}")
PY
'
