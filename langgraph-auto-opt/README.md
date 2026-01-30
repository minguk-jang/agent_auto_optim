# LangGraph Agent Auto-Optimization System

> **Version 2.0** - Complete rewrite with functional prompt optimization

A self-improving system that automatically optimizes LangGraph Agent prompts based on test failures. Uses LLM-based meta-optimization to iteratively improve agent performance.

## 🎯 What This Does

1. **Runs Agent Tests** - Executes predefined test cases
2. **Analyzes Failures** - Detects patterns in failures
3. **Generates Improvements** - Uses Claude to suggest better prompts
4. **Applies Changes** - Updates prompt files automatically
5. **Iterates** - Repeats until target metrics achieved

## 🚀 Key Features

- ✅ **Dynamic Prompt Loading** - Prompts loaded from files, not hardcoded
- ✅ **LLM-Based Optimization** - Intelligent prompt improvements using Claude Sonnet 4
- ✅ **Comprehensive Metrics** - 11 different performance measurements
- ✅ **Automatic Backup** - Never lose working prompts
- ✅ **Mock Mode** - Fast development without API costs
- ✅ **End-to-End Testing** - Full workflow validation

## 📋 Prerequisites

\`\`\`bash
# Required
Python 3.10+

# For real optimization (optional for dev)
export ANTHROPIC_API_KEY=your-key-here
\`\`\`

## 🔧 Installation

\`\`\`bash
cd langgraph-auto-opt
pip install -r requirements.txt
\`\`\`

## 🏃 Quick Start

### Development Mode (No API Key Required)

\`\`\`bash
cd src
export USE_MOCK=true

# Run all tests
python run_tests.py --clean

# View results
python run_tests.py --report
\`\`\`

### Production Mode (Real Optimization)

\`\`\`bash
export ANTHROPIC_API_KEY=your-key
# Do NOT set USE_MOCK or set it to false

# Run tests
python run_tests.py --clean

# Analyze failures
python optimize.py analyze

# Get intelligent suggestions
python optimize.py suggest

# Apply specific improvement
python optimize.py apply --suggestion 1

# Full auto-optimization
python optimize.py auto --max-iter 5
\`\`\`

## 📊 Example Output

\`\`\`
============================================================
TEST REPORT
============================================================
Total: 8
Passed: 8
Failed: 0
Pass Rate: 100.0%
Avg Turns: 1.38

슬롯 정확도:
  Overall: 100.0%
  Title: 100.0%
  Date: 100.0%
  Time: 50.0%
  Location: 12.5%
============================================================
\`\`\`

## 📁 Project Structure

\`\`\`
langgraph-auto-opt/
├── src/
│   ├── agent.py              # LangGraph Agent (loads prompts dynamically)
│   ├── orchestrator.py       # Test execution manager
│   ├── run_tests.py          # Test runner with metrics
│   ├── optimize.py           # Optimization orchestrator
│   ├── prompt_optimizer.py   # LLM-based prompt improvement
│   ├── metrics.py            # Comprehensive evaluation metrics
│   └── schemas.py            # Pydantic data models
├── config/
│   └── test_cases.yaml       # 8 test cases (easy to hard)
├── prompts/
│   ├── slot_extraction.txt   # Agent prompt for slot extraction
│   └── question_generation.txt # Agent prompt for asking questions
├── CRITICAL_ISSUES.md        # Analysis of original implementation
├── IMPROVEMENTS.md           # Detailed improvement documentation
└── README.md                 # This file
\`\`\`

## 🧪 Test Cases

| ID | Description | Max Turns | Difficulty |
|----|-------------|-----------|------------|
| tc_001 | Complete information | 1 | Easy |
| tc_002 | Missing location | 2 | Easy |
| tc_003 | Ambiguous date | 3 | Medium |
| tc_004 | Only title | 4 | Medium |
| tc_005 | Slang/abbreviations | 3 | Hard |
| tc_006 | Ambiguous time | 2 | Edge Case |
| tc_007 | Partial info | 2 | Edge Case |
| tc_008 | Ambiguous expression | 2 | Hard |

## 📈 Key Improvements from v1.0

1. **Prompts now actually loaded from files** (was hardcoded)
2. **LLM-based intelligent optimization** (was simple string concatenation)
3. **11 detailed metrics** (was 2 basic metrics)
4. **Proper failure analysis** (was simple counting)
5. **Working optimization loop** (was non-functional)

See `CRITICAL_ISSUES.md` and `IMPROVEMENTS.md` for full details.

## ⚙️ Configuration

### Environment Variables

\`\`\`bash
# Use mock LLM (no API calls)
export USE_MOCK=true

# Use real Claude API
export ANTHROPIC_API_KEY=sk-ant-...
\`\`\`

### Prompt Configuration

Edit files in `prompts/` directory - changes take effect immediately!

## 📚 Documentation

- **CRITICAL_ISSUES.md** - Analysis of original implementation flaws
- **IMPROVEMENTS.md** - Detailed documentation of all improvements
- **This README** - Usage guide and quick reference

---

**Version:** 2.0 (2026-01-30)
**Status:** ✅ Functional - Core optimization loop working
