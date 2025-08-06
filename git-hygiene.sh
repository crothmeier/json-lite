#!/usr/bin/env bash
set -euo pipefail

echo "🧹 Git Hygiene Check"
echo "===================="

# Check for symlinks
echo "Checking symlinks..."
for link in op1_large/json_worker/streaming_parser.py \
            op1_large/json_worker/gpu_guard.py \
            op2_lite/app/json_worker/streaming_parser.py \
            op2_lite/app/json_worker/gpu_guard.py; do
    if [ -L "$link" ]; then
        echo "✅ $link (symlink)"
    else
        echo "❌ $link (NOT a symlink)"
        exit 1
    fi
done

# Clean artifacts
echo "Cleaning artifacts..."
rm -rf .coverage coverage.xml htmlcov/ .benchmarks/ __pycache__/
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete

echo "✅ Clean complete"

# Run tests for ChatGPT extractor
echo ""
echo "Running ChatGPT extractor tests..."
if [ -f "tests/test_chatgpt_extractor.py" ]; then
    python -m pytest tests/test_chatgpt_extractor.py -v --no-header --tb=short || {
        echo "⚠️  ChatGPT extractor tests failed"
    }
else
    echo "⚠️  ChatGPT extractor tests not found"
fi

# Function to install pre-commit hooks
install_hooks() {
    echo ""
    echo "Installing pre-commit hooks..."
    
    # Create hooks directory if it doesn't exist
    mkdir -p .git/hooks
    
    # Install pre-commit hook
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook to verify symlinks and run basic checks

echo "🔍 Running pre-commit checks..."

# Check for broken symlinks
BROKEN_LINKS=0
for link in $(find . -type l -not -path "./.git/*" 2>/dev/null); do
    if [ ! -e "$link" ]; then
        echo "⚠️  Broken symlink: $link"
        BROKEN_LINKS=$((BROKEN_LINKS + 1))
    fi
done

if [ $BROKEN_LINKS -gt 0 ]; then
    echo "❌ Found $BROKEN_LINKS broken symlink(s). Please fix before committing."
    exit 1
fi

# Verify critical symlinks exist
for link in op1_large/json_worker/streaming_parser.py \
            op1_large/json_worker/gpu_guard.py \
            op2_lite/app/json_worker/streaming_parser.py \
            op2_lite/app/json_worker/gpu_guard.py; do
    if [ ! -L "$link" ]; then
        echo "❌ Missing required symlink: $link"
        exit 1
    fi
done

# Check for large files (>10MB)
LARGE_FILES=$(find . -type f -size +10M -not -path "./.git/*" -not -path "./venv/*" -not -path "./.venv/*" 2>/dev/null)
if [ ! -z "$LARGE_FILES" ]; then
    echo "⚠️  Large files detected (>10MB):"
    echo "$LARGE_FILES"
    echo "Consider using git-lfs for large files."
fi

# Check for secrets/keys (basic pattern matching)
if git diff --cached --name-only | xargs grep -E "(api[_-]?key|secret|token|password|passwd|pwd)" -i 2>/dev/null; then
    echo "⚠️  Potential secrets detected in staged files."
    echo "Please review and remove any sensitive information."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Pre-commit checks passed"
EOF
    
    chmod +x .git/hooks/pre-commit
    echo "✅ Pre-commit hooks installed"
    
    # Install pre-push hook for additional safety
    cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
# Pre-push hook to run tests before pushing

echo "🚀 Running pre-push checks..."

# Quick test run (if tests exist)
if [ -f "Makefile" ] && grep -q "test-fast" Makefile; then
    echo "Running quick tests..."
    make test-fast || {
        echo "❌ Tests failed. Please fix before pushing."
        exit 1
    }
fi

echo "✅ Pre-push checks passed"
EOF
    
    chmod +x .git/hooks/pre-push
    echo "✅ Pre-push hooks installed"
}

# Check if hooks should be installed
if [ "${1:-}" = "--install-hooks" ]; then
    install_hooks
elif [ ! -f ".git/hooks/pre-commit" ]; then
    echo ""
    echo "💡 Tip: Run './git-hygiene.sh --install-hooks' to install git hooks"
fi