#!/bin/bash

echo "======================================"
echo "Detailed Learning Loop Test"
echo "======================================"

# Backup
mkdir -p prompts_backup_temp
cp prompts/*.txt prompts_backup_temp/

echo ""
echo "=== BEFORE: Good Prompts ==="
cd src
export USE_MOCK=true
python run_tests.py --test-id tc_004 2>&1 | tail -30

echo ""
echo ""
echo "=== AFTER: Bad Prompts ==="
cd ..
cp prompts_bad/*.txt prompts/
cd src
python run_tests.py --test-id tc_004 2>&1 | tail -30

# Restore
cd ..
cp prompts_backup_temp/*.txt prompts/
rm -rf prompts_backup_temp

echo ""
echo "✓ Detailed test completed"
