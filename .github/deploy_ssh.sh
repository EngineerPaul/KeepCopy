#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DEPLOY_PATH:-}" ]]; then
  echo "DEPLOY_PATH is empty"
  exit 1
fi

cd "$DEPLOY_PATH"

if [[ ! -f keepcopy-ci-test.txt ]]; then
  echo "keepcopy-ci-test.txt not found in $DEPLOY_PATH"
  ls -la
  exit 1
fi

echo "Deploy OK: $DEPLOY_PATH"
ls -la
