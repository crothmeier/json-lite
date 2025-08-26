#!/usr/bin/env bash
set -euo pipefail

echo "🐳 Safe Docker Build"
echo "==================="

# Ensure symlinks are correct
./git-hygiene.sh

# Build with proper context
docker build -f op1_large/Dockerfile -t json-lite-op1:local .
docker build -f op2_lite/Dockerfile -t json-lite-op2:local .

echo "✅ Docker images built successfully"