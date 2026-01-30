#!/bin/bash
set -e

echo "=================================="
echo "Learning Loop Validation"
echo "=================================="

export USE_MOCK=true

# Run validation non-interactively
echo "y" | python validate_learning.py

echo ""
echo "✓ Learning validation completed"
