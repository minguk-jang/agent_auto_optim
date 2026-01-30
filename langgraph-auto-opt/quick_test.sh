#!/bin/bash

echo "======================================"
echo "Quick Learning Loop Test"
echo "======================================"

# Backup current prompts
mkdir -p prompts_backup_temp
cp prompts/*.txt prompts_backup_temp/

echo ""
echo "[1] Testing with BAD prompts..."
cp prompts_bad/*.txt prompts/

cd src
export USE_MOCK=true

# Run 3 times to account for randomness
python run_tests.py --clean 2>&1 | grep -E "(Pass Rate|Failed|Redundancy)" | head -20

echo ""
echo "[2] Restoring GOOD prompts..."
cd ..
cp prompts_backup_temp/*.txt prompts/
rm -rf prompts_backup_temp

echo ""
echo "✓ Test completed"
