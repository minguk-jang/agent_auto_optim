"""
Learning Loop Validation Script

의도적으로 나쁜 프롬프트로 시작하여
최적화가 실제로 개선을 만들어내는지 검증
"""

import shutil
import json
from pathlib import Path
from datetime import datetime

from run_tests import run_all_tests, generate_report
from optimize import analyze_failures, generate_suggestions, apply_suggestion
from metrics import calculate_detailed_metrics, print_detailed_metrics


BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
PROMPTS_BAD_DIR = BASE_DIR / "prompts_bad"
RESULTS_DIR = BASE_DIR / "results"
VALIDATION_LOG_DIR = BASE_DIR / "logs" / "validation"


def backup_prompts(backup_name: str):
    """현재 프롬프트 백업"""
    backup_dir = VALIDATION_LOG_DIR / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)

    for prompt_file in PROMPTS_DIR.glob("*.txt"):
        shutil.copy(prompt_file, backup_dir / prompt_file.name)

    print(f"✓ Backed up prompts to {backup_dir}")


def restore_prompts(backup_name: str):
    """프롬프트 복원"""
    backup_dir = VALIDATION_LOG_DIR / backup_name

    if not backup_dir.exists():
        print(f"❌ Backup not found: {backup_dir}")
        return False

    for prompt_file in backup_dir.glob("*.txt"):
        shutil.copy(prompt_file, PROMPTS_DIR / prompt_file.name)

    print(f"✓ Restored prompts from {backup_dir}")
    return True


def use_bad_prompts():
    """의도적으로 나쁜 프롬프트 사용"""
    if not PROMPTS_BAD_DIR.exists():
        print(f"❌ Bad prompts directory not found: {PROMPTS_BAD_DIR}")
        return False

    for bad_prompt in PROMPTS_BAD_DIR.glob("*.txt"):
        target = PROMPTS_DIR / bad_prompt.name
        shutil.copy(bad_prompt, target)
        print(f"✓ Copied bad prompt: {bad_prompt.name}")

    return True


def run_validation():
    """
    학습 루프 검증 실행

    Steps:
    1. 좋은 프롬프트 백업
    2. 나쁜 프롬프트로 교체
    3. 테스트 실행 (실패 예상)
    4. 최적화 실행
    5. 테스트 재실행 (개선 확인)
    6. Before/After 비교
    7. 원본 프롬프트 복원
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("="*80)
    print("LEARNING LOOP VALIDATION")
    print("="*80)
    print(f"Timestamp: {timestamp}\n")

    # Step 1: Backup good prompts
    print("\n[1/7] Backing up good prompts...")
    backup_prompts(f"good_{timestamp}")

    # Step 2: Use bad prompts
    print("\n[2/7] Switching to bad prompts...")
    if not use_bad_prompts():
        print("❌ Failed to use bad prompts")
        return

    # Step 3: Run tests (BEFORE optimization)
    print("\n[3/7] Running tests with BAD prompts...")
    print("-"*80)

    # Clear previous results
    if RESULTS_DIR.exists():
        shutil.rmtree(RESULTS_DIR)
    RESULTS_DIR.mkdir(parents=True)

    results_before = run_all_tests()
    report_before = generate_report(results_before)
    metrics_before = report_before.get("detailed_metrics")

    # Save results
    before_file = VALIDATION_LOG_DIR / f"before_{timestamp}.json"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    with open(before_file, "w") as f:
        json.dump({
            "pass_rate": report_before["pass_rate"],
            "avg_turns": report_before["avg_turns"],
            "failed": report_before["failed"],
            "results": [r.model_dump(mode="json") for r in results_before]
        }, f, indent=2, default=str)

    print(f"\n✓ Saved BEFORE results to {before_file}")

    # Step 4: Check if optimization is needed
    print("\n[4/7] Analyzing failures...")

    patterns = analyze_failures(results_before)

    if not patterns:
        print("❌ No failure patterns found!")
        print("   Bad prompts may not be bad enough to trigger failures.")
        print("   Or all tests still pass despite bad prompts.")
        restore_prompts(f"good_{timestamp}")
        return

    print(f"✓ Found {len(patterns)} failure pattern(s):")
    for p in patterns:
        print(f"  - {p.pattern_type}: {p.count} cases")

    # Step 5: Generate and apply improvements
    print("\n[5/7] Generating improvements...")

    suggestions = generate_suggestions(patterns)

    if not suggestions:
        print("❌ No suggestions generated!")
        restore_prompts(f"good_{timestamp}")
        return

    print(f"✓ Generated {len(suggestions)} suggestion(s)")

    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n  Suggestion {i}:")
        print(f"    File: {suggestion.target_file}")
        print(f"    Issue: {suggestion.issue_description}")
        apply_suggestion(suggestion)

    # Step 6: Run tests AFTER optimization
    print("\n[6/7] Running tests with IMPROVED prompts...")
    print("-"*80)

    # Clear previous results
    if RESULTS_DIR.exists():
        shutil.rmtree(RESULTS_DIR)
    RESULTS_DIR.mkdir(parents=True)

    results_after = run_all_tests()
    report_after = generate_report(results_after)
    metrics_after = report_after.get("detailed_metrics")

    # Save results
    after_file = VALIDATION_LOG_DIR / f"after_{timestamp}.json"
    with open(after_file, "w") as f:
        json.dump({
            "pass_rate": report_after["pass_rate"],
            "avg_turns": report_after["avg_turns"],
            "failed": report_after["failed"],
            "results": [r.model_dump(mode="json") for r in results_after]
        }, f, indent=2, default=str)

    print(f"\n✓ Saved AFTER results to {after_file}")

    # Step 7: Compare Before/After
    print("\n[7/7] Comparing BEFORE vs AFTER...")
    print("="*80)
    print("LEARNING VALIDATION RESULTS")
    print("="*80)

    print("\nBEFORE Optimization:")
    print(f"  Pass Rate: {report_before['pass_rate']:.1f}%")
    print(f"  Avg Turns: {report_before['avg_turns']:.2f}")
    print(f"  Failed: {report_before['failed']}/{report_before['total']}")
    if metrics_before:
        print(f"  Redundancy Rate: {metrics_before.redundancy_rate:.1f}%")

    print("\nAFTER Optimization:")
    print(f"  Pass Rate: {report_after['pass_rate']:.1f}%")
    print(f"  Avg Turns: {report_after['avg_turns']:.2f}")
    print(f"  Failed: {report_after['failed']}/{report_after['total']}")
    if metrics_after:
        print(f"  Redundancy Rate: {metrics_after.redundancy_rate:.1f}%")

    print("\nIMPROVEMENT:")
    pass_rate_delta = report_after['pass_rate'] - report_before['pass_rate']
    avg_turns_delta = report_after['avg_turns'] - report_before['avg_turns']
    failed_delta = report_after['failed'] - report_before['failed']

    print(f"  Pass Rate: {pass_rate_delta:+.1f}%")
    print(f"  Avg Turns: {avg_turns_delta:+.2f}")
    print(f"  Failed: {failed_delta:+d}")

    if metrics_before and metrics_after:
        redundancy_delta = metrics_after.redundancy_rate - metrics_before.redundancy_rate
        print(f"  Redundancy Rate: {redundancy_delta:+.1f}%")

    # Determine success
    print("\n" + "="*80)
    if pass_rate_delta > 0 or failed_delta < 0:
        print("✓ LEARNING VALIDATED: Optimization improved performance!")
        success = True
    elif pass_rate_delta == 0 and report_after['pass_rate'] == 100:
        print("⚠ LEARNING UNCLEAR: Already at 100%, no room for improvement")
        success = False
    else:
        print("❌ LEARNING FAILED: No improvement or performance decreased")
        success = False

    print("="*80)

    # Step 8: Restore good prompts
    print("\n[8/7] Restoring original prompts...")
    restore_prompts(f"good_{timestamp}")

    return success


if __name__ == "__main__":
    import sys

    print("""
╔═══════════════════════════════════════════════════════════════╗
║                LEARNING LOOP VALIDATION                       ║
╚═══════════════════════════════════════════════════════════════╝

This script validates that the optimization loop actually works:
1. Starts with intentionally BAD prompts
2. Runs tests (should fail)
3. Runs optimization
4. Runs tests again (should improve)
5. Compares before/after

NOTE: This requires BAD prompts in prompts_bad/ directory
""")

    confirm = input("Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        sys.exit(0)

    success = run_validation()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
