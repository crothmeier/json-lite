#!/usr/bin/env bash
set -euo pipefail

echo "🧪 JSON-Lite Complete Test Suite"
echo "================================"

# Unit tests with coverage
echo "📊 Unit Tests with Coverage:"
pytest tests/test_*.py \
    --cov=shared --cov=op1_large --cov=op2_lite \
    --cov-report=term-missing:skip-covered \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=80 \
    --benchmark-disable \
    -m "not integration"

# Integration tests (separate coverage)
echo -e "\n🔄 Integration Tests:"
pytest tests/test_integration*.py \
    --cov=shared --cov=op1_large --cov=op2_lite \
    --cov-report=term-missing \
    --cov-fail-under=60 \
    --benchmark-disable \
    -m "integration or not integration"

# Benchmarks (no coverage)
echo -e "\n⚡ Benchmark Tests:"
pytest tests/ \
    --benchmark-only \
    --benchmark-autosave \
    -m "benchmark or not benchmark"

echo -e "\n📈 Final Coverage Report:"
coverage report

echo -e "\n✅ Test suite complete!"