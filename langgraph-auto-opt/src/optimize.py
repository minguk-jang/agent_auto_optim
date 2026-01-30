"""
프롬프트 자동 최적화
"""

import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from schemas import TestResult, OptimizationRun
from run_tests import run_all_tests, generate_report


# =============================================================================
# Paths
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"

SLOT_EXTRACTION_PROMPT = PROMPTS_DIR / "slot_extraction.txt"
QUESTION_GENERATION_PROMPT = PROMPTS_DIR / "question_generation.txt"


# =============================================================================
# 실패 패턴 분석
# =============================================================================

@dataclass
class FailurePattern:
    pattern_type: str
    count: int
    examples: list[dict]
    suggested_fix: str


def load_results() -> list[TestResult]:
    results = []
    for result_file in RESULTS_DIR.glob("tc_*.json"):
        with open(result_file) as f:
            data = json.load(f)
            results.append(TestResult(**data))
    return results


def analyze_failures(results: list[TestResult]) -> list[FailurePattern]:
    patterns = []

    failures_by_reason = {}
    for r in results:
        if r.status == "failed" and r.failure_reason:
            reason = r.failure_reason
            if reason not in failures_by_reason:
                failures_by_reason[reason] = []
            failures_by_reason[reason].append(r)

    for reason, failures in failures_by_reason.items():
        if reason == "redundant":
            patterns.append(FailurePattern(
                pattern_type="redundant_question",
                count=len(failures),
                examples=[{
                    "test_id": f.test_id,
                    "details": f.failure_details,
                    "slots_at_failure": f.final_slots,
                } for f in failures],
                suggested_fix="question_generation.txt에 중복 질문 방지 규칙 강화"
            ))

        elif reason == "turn_exceeded":
            patterns.append(FailurePattern(
                pattern_type="inefficient_questioning",
                count=len(failures),
                examples=[{
                    "test_id": f.test_id,
                    "turns": f.turn_count,
                    "final_slots": f.final_slots,
                } for f in failures],
                suggested_fix="question_generation.txt에 효율적인 질문 유도 추가"
            ))

    return patterns


# =============================================================================
# 수정 제안
# =============================================================================

@dataclass
class PromptSuggestion:
    id: int
    target_file: str
    change_type: str
    description: str
    original: str
    suggested: str


def generate_suggestions(patterns: list[FailurePattern]) -> list[PromptSuggestion]:
    suggestions = []
    suggestion_id = 1

    for pattern in patterns:
        if pattern.pattern_type == "redundant_question":
            current = QUESTION_GENERATION_PROMPT.read_text()

            addition = """
중요: 현재 채워진 정보에 있는 내용은 절대 다시 묻지 마세요!
"""

            if "절대 다시 묻지 마세요!" not in current:
                suggestions.append(PromptSuggestion(
                    id=suggestion_id,
                    target_file="question_generation.txt",
                    change_type="add",
                    description="중복 질문 방지 규칙 강화",
                    original="",
                    suggested=addition,
                ))
                suggestion_id += 1

    return suggestions


# =============================================================================
# 수정 적용
# =============================================================================

def backup_prompt(filepath: Path):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = LOGS_DIR / f"{filepath.stem}_{timestamp}.txt"
    shutil.copy(filepath, backup_path)
    print(f"Backup saved: {backup_path}")


def apply_suggestion(suggestion: PromptSuggestion):
    filepath = PROMPTS_DIR / suggestion.target_file
    backup_prompt(filepath)

    current = filepath.read_text()

    if suggestion.change_type == "add":
        new_content = current + "\n" + suggestion.suggested
    elif suggestion.change_type == "modify":
        new_content = current.replace(suggestion.original, suggestion.suggested)
    else:
        new_content = current

    filepath.write_text(new_content)
    print(f"Applied suggestion {suggestion.id} to {suggestion.target_file}")


# =============================================================================
# 자동 최적화 루프
# =============================================================================

def auto_optimize(
    max_iterations: int = 5,
    target_pass_rate: float = 100.0,
    target_avg_turns: float = 2.0,
):
    print("="*60)
    print("AUTO OPTIMIZATION")
    print("="*60)
    print(f"Target: pass_rate >= {target_pass_rate}%, avg_turns <= {target_avg_turns}")

    history = []

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration}/{max_iterations} ---\n")

        results = run_all_tests()
        report = generate_report(results)

        history.append({
            "iteration": iteration,
            "pass_rate": report["pass_rate"],
            "avg_turns": report["avg_turns"],
            "timestamp": datetime.now().isoformat(),
        })

        if report["pass_rate"] >= target_pass_rate and report["avg_turns"] <= target_avg_turns:
            print(f"\n✓ Target achieved at iteration {iteration}!")
            break

        patterns = analyze_failures(results)

        if not patterns:
            print("\nNo failure patterns found.")
            break

        suggestions = generate_suggestions(patterns)

        if not suggestions:
            print("\nNo suggestions available.")
            break

        for s in suggestions:
            apply_suggestion(s)

    print("\n" + "="*60)
    print("OPTIMIZATION HISTORY")
    print("="*60)
    for h in history:
        print(f"Iteration {h['iteration']}: pass_rate={h['pass_rate']:.1f}%, avg_turns={h['avg_turns']:.2f}")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump(history, f, indent=2)
    print(f"\nLog saved: {log_file}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("analyze")
    subparsers.add_parser("suggest")

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--suggestion", type=int, required=True)

    auto_parser = subparsers.add_parser("auto")
    auto_parser.add_argument("--max-iter", type=int, default=5)
    auto_parser.add_argument("--target-pass-rate", type=float, default=100.0)
    auto_parser.add_argument("--target-avg-turns", type=float, default=2.0)

    args = parser.parse_args()

    if args.command == "analyze":
        results = load_results()
        patterns = analyze_failures(results)

        print("="*60)
        print("FAILURE ANALYSIS")
        print("="*60)

        if not patterns:
            print("No failure patterns found.")
        else:
            for p in patterns:
                print(f"\n[{p.pattern_type}] ({p.count} cases)")
                print(f"  Suggested fix: {p.suggested_fix}")

    elif args.command == "suggest":
        results = load_results()
        patterns = analyze_failures(results)
        suggestions = generate_suggestions(patterns)

        print("="*60)
        print("SUGGESTIONS")
        print("="*60)

        if not suggestions:
            print("No suggestions.")
        else:
            for s in suggestions:
                print(f"\n[{s.id}] {s.description}")
                print(f"  Target: {s.target_file}")

    elif args.command == "apply":
        results = load_results()
        patterns = analyze_failures(results)
        suggestions = generate_suggestions(patterns)

        target = None
        for s in suggestions:
            if s.id == args.suggestion:
                target = s
                break

        if target:
            apply_suggestion(target)
        else:
            print(f"Suggestion {args.suggestion} not found.")

    elif args.command == "auto":
        auto_optimize(
            max_iterations=args.max_iter,
            target_pass_rate=args.target_pass_rate,
            target_avg_turns=args.target_avg_turns,
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
