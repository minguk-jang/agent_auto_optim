"""
전체 테스트 실행 스크립트
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

from schemas import TestResult, OrchestratorState, ClaudeCodeResponse, Turn
from orchestrator import (
    load_test_cases,
    start_test,
    submit_answer,
    load_state,
    save_result,
    RESULTS_DIR,
    ANSWER_FILE,
)


# =============================================================================
# Claude Code 시뮬레이션
# =============================================================================

def simulate_claude_code_judgment(state: OrchestratorState) -> ClaudeCodeResponse:
    question = state.current_question or ""
    ground_truth = state.context.ground_truth
    current_slots = state.current_slots

    # 이미 있는 정보를 다시 묻는지 체크
    if any(kw in question for kw in ["어떤 일정", "무슨 일정", "제목"]):
        if current_slots.get("title"):
            return ClaudeCodeResponse(
                answer=None,
                judgment="redundant",
                judgment_reason=f"이미 '{current_slots['title']}'이라고 제목이 있는데 다시 물음"
            )

    if any(kw in question for kw in ["언제", "날짜", "며칠"]):
        if current_slots.get("date"):
            return ClaudeCodeResponse(
                answer=None,
                judgment="redundant",
                judgment_reason=f"이미 '{current_slots['date']}'라고 날짜가 있는데 다시 물음"
            )

    if any(kw in question for kw in ["몇 시", "시간"]):
        if current_slots.get("time"):
            return ClaudeCodeResponse(
                answer=None,
                judgment="redundant",
                judgment_reason=f"이미 '{current_slots['time']}'라고 시간이 있는데 다시 물음"
            )

    if any(kw in question for kw in ["어디", "장소", "위치"]):
        if current_slots.get("location"):
            return ClaudeCodeResponse(
                answer=None,
                judgment="redundant",
                judgment_reason=f"이미 '{current_slots['location']}'라고 장소가 있는데 다시 물음"
            )

    answer = generate_natural_answer(question, ground_truth, current_slots)

    return ClaudeCodeResponse(
        answer=answer,
        judgment="valid",
        judgment_reason="빠진 정보를 묻는 적절한 질문"
    )


def generate_natural_answer(question: str, ground_truth: dict, current_slots: dict) -> str:
    if any(kw in question for kw in ["언제", "날짜", "며칠"]):
        date = ground_truth.get("date")
        time = ground_truth.get("time")
        if date and time:
            return f"{date} {time}쯤"
        elif date:
            return date
        else:
            return "다음주쯤"

    if any(kw in question for kw in ["몇 시", "시간"]):
        time = ground_truth.get("time")
        if time:
            try:
                hour = int(time.split(":")[0])
                if hour >= 12:
                    return f"오후 {hour - 12 if hour > 12 else 12}시"
                else:
                    return f"오전 {hour}시"
            except:
                return time
        else:
            return "오후쯤"

    if any(kw in question for kw in ["어디", "장소", "위치"]):
        location = ground_truth.get("location")
        return location if location else "아직 안 정했어요"

    if any(kw in question for kw in ["어떤 일정", "무슨 일정", "제목"]):
        title = ground_truth.get("title")
        return title if title else "그냥 약속이요"

    return "네"


# =============================================================================
# 테스트 실행
# =============================================================================

def run_single_test(test_id: str, max_iterations: int = 10) -> TestResult:
    print(f"\n{'='*50}")
    print(f"Running: {test_id}")
    print(f"{'='*50}")

    state = start_test(test_id)
    print(f"Turn 1 - Slots: {state.current_slots}")

    iteration = 0
    while state.status == "waiting_answer" and iteration < max_iterations:
        iteration += 1

        print(f"  Question: {state.current_question}")

        response = simulate_claude_code_judgment(state)
        print(f"  Judgment: {response.judgment}")

        if response.judgment != "valid":
            print(f"  → Failed: {response.judgment_reason}")
            state.status = "failed"
            state.failure_reason = response.judgment
            state.failure_details = response.judgment_reason

            result = TestResult(
                test_id=test_id,
                status="failed",
                turn_count=state.turn_count,
                final_slots=state.current_slots,
                failure_reason=response.judgment,
                failure_details=response.judgment_reason,
                history=state.history,
            )
            save_result(result)
            return result

        print(f"  Answer: {response.answer}")

        with open(ANSWER_FILE, "w") as f:
            json.dump(response.model_dump(), f, ensure_ascii=False)

        state = submit_answer()
        print(f"Turn {state.turn_count} - Slots: {state.current_slots}")

    result_file = RESULTS_DIR / f"{test_id}.json"
    if result_file.exists():
        with open(result_file) as f:
            result_data = json.load(f)
        return TestResult(**result_data)

    result = TestResult(
        test_id=test_id,
        status="passed" if state.status == "completed" else "failed",
        turn_count=state.turn_count,
        final_slots=state.current_slots,
        failure_reason=state.failure_reason,
        failure_details=state.failure_details,
        history=state.history,
    )
    save_result(result)
    return result


def run_all_tests() -> list[TestResult]:
    cases = load_test_cases()
    results = []

    for tc in cases:
        result = run_single_test(tc.id)
        results.append(result)

    return results


# =============================================================================
# 리포트
# =============================================================================

def generate_report(results: list[TestResult] = None):
    if results is None:
        results = []
        for result_file in RESULTS_DIR.glob("tc_*.json"):
            with open(result_file) as f:
                results.append(TestResult(**json.load(f)))

    if not results:
        print("No results found.")
        return

    total = len(results)
    passed = sum(1 for r in results if r.status == "passed")
    failed = total - passed
    pass_rate = passed / total * 100 if total > 0 else 0
    avg_turns = sum(r.turn_count for r in results) / total if total > 0 else 0

    print("\n" + "="*60)
    print("TEST REPORT")
    print("="*60)
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print(f"Avg Turns: {avg_turns:.2f}")
    print("-"*60)

    for r in sorted(results, key=lambda x: x.test_id):
        status_icon = "✓" if r.status == "passed" else "✗"
        print(f"{status_icon} {r.test_id}: {r.status} (turns: {r.turn_count})")
        if r.failure_reason:
            print(f"    └ {r.failure_reason}: {r.failure_details}")

    print("="*60)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "avg_turns": avg_turns,
        "results": results,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-id", help="Run single test")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--clean", action="store_true")

    args = parser.parse_args()

    if args.clean:
        import shutil
        if RESULTS_DIR.exists():
            shutil.rmtree(RESULTS_DIR)
        RESULTS_DIR.mkdir(parents=True)
        print("Results cleaned.")

    if args.report:
        generate_report()
        return

    if args.test_id:
        result = run_single_test(args.test_id)
        generate_report([result])
    else:
        results = run_all_tests()
        generate_report(results)


if __name__ == "__main__":
    main()
