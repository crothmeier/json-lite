#!/usr/bin/env bash
# Example workflow for a 2 GB JSON file.

set -eu
FILE=${1:-huge.json}
echo "Analyzing $FILE ..."
python manual_processor.py "$FILE" --chunk-size 4096
