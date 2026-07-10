#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
git config --local core.hooksPath .githooks
chmod +x .githooks/pre-push

echo "Configured local Git hooks:"
git config --local --get core.hooksPath
echo "Ready: pre-push will now run scripts/validate.sh"
