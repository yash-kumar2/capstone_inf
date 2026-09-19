#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

check_cmd() { command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"; }

check_cmd docker
check_cmd bash

if [ ! -f .env ]; then
  fail ".env is missing; copy .env.example to .env first"
fi

if ! docker compose config >/dev/null 2>&1; then
  fail "docker compose configuration is invalid"
fi
pass "compose config is valid"

if ! bash -n scripts/check_dns.sh; then
  fail "check_dns.sh has a syntax error"
fi
if ! bash -n scripts/check_no_secrets.sh; then
  fail "check_no_secrets.sh has a syntax error"
fi
if ! bash -n scripts/check_persistence.sh; then
  fail "check_persistence.sh has a syntax error"
fi
if ! bash -n scripts/counts.sh; then
  fail "counts.sh has a syntax error"
fi
pass "shell validation scripts are syntactically valid"

if [ -d samples ] && [ "$(find samples -type f | wc -l)" -ge 10 ]; then
  pass "sample pack is present"
else
  fail "sample pack is incomplete"
fi

if [ -f docs/ARCHITECTURE.md ] && [ -f docs/DEMO.md ] && [ -f docs/VIVA.md ]; then
  pass "project documentation is present"
else
  fail "required documentation files are missing"
fi

if docker compose ps >/dev/null 2>&1; then
  if docker compose ps --status running | grep -q 'running'; then
    pass "docker services appear to be running"
  else
    echo "WARN: no running services detected; Docker checks require a live compose stack"
  fi
else
  echo "WARN: docker compose is not currently running; skipping runtime health checks"
fi

echo "Verification complete. Review the PASS/FAIL lines above and explain each one in the demo or viva notes."
