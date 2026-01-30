"""
Orchestrator for LangGraph Agent Auto-Optimization
"""

import json
import yaml
import argparse
from pathlib import Path

from schemas import (
    OrchestratorState,
    ClaudeCodeResponse,
    TestCase,
    TestContext,
    TestResult,
    Turn,
)
from agent import create_agent, run_agent_turn


# =============================================================================
# Paths
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
STATE_FILE = BASE_DIR / "communication" / "state.json"
ANSWER_FILE = BASE_DIR / "communication" / "answer.json"
RESULTS_DIR = BASE_DIR / "results"


# =============================================================================
# Config Loading
# =============================================================================

def load_test_cases() -> list[TestCase]:
    with open(CONFIG_DIR / "test_cases.yaml") as f:
        data = yaml.safe_load(f)

    cases = []
    for tc in data["test_cases"]:
        cases.append(TestCase(
            id=tc["id"],
            query=tc["query"],
            context=TestContext(
                user_intent=tc["context"]["user_intent"],
                ground_truth=tc["context"]["ground_truth"],
            ),
            max_turns=tc.get("max_turns", 3),
        ))
    return cases


def get_test_case(test_id: str) -> TestCase:
    cases = load_test_cases()
    for tc in cases:
        if tc.id == test_id:
            return tc
    raise ValueError(f"Test case not found: {test_id}")


# =============================================================================
# State Management
# =============================================================================

def save_state(state: OrchestratorState):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"State saved to {STATE_FILE}")


def load_state() -> OrchestratorState:
    with open(STATE_FILE) as f:
        data = json.load(f)
    return OrchestratorState(**data)


def load_answer() -> ClaudeCodeResponse:
    with open(ANSWER_FILE) as f:
        data = json.load(f)
    return ClaudeCodeResponse(**data)


def save_result(result: TestResult):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"{result.test_id}.json"
    with open(result_file, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, ensure_ascii=False, default=str)
    print(f"Result saved to {result_file}")


# =============================================================================
# Core Logic
# =============================================================================

def start_test(test_id: str) -> OrchestratorState:
    tc = get_test_case(test_id)
    agent = create_agent()

    result = run_agent_turn(agent, thread_id=test_id, query=tc.query)

    if result["is_complete"]:
        status = "completed"
        current_question = None
    else:
        status = "waiting_answer"
        current_question = result.get("current_question")

    state = OrchestratorState(
        test_id=test_id,
        status=status,
        turn_count=1,
        max_turns=tc.max_turns,
        current_question=current_question,
        current_slots=result["slots"],
        context=tc.context,
        history=[Turn(role="user", content=tc.query)],
    )

    if current_question:
        state.history.append(Turn(role="agent", content=current_question))

    # 완료된 경우 결과 저장
    if status == "completed":
        test_result = TestResult(
            test_id=test_id,
            status="passed",
            turn_count=1,
            final_slots=result["slots"],
            history=state.history,
        )
        save_result(test_result)

    save_state(state)
    return state


def submit_answer() -> OrchestratorState:
    state = load_state()
    answer_response = load_answer()

    if answer_response.judgment != "valid":
        state.status = "failed"
        state.failure_reason = answer_response.judgment
        state.failure_details = answer_response.judgment_reason
        save_state(state)

        result = TestResult(
            test_id=state.test_id,
            status="failed",
            turn_count=state.turn_count,
            final_slots=state.current_slots,
            failure_reason=answer_response.judgment,
            failure_details=answer_response.judgment_reason,
            history=state.history,
        )
        save_result(result)
        return state

    agent = create_agent()

    tc = get_test_case(state.test_id)
    current_agent_state = {
        "query": tc.query,
        "slots": state.current_slots,
        "history": [{"role": h.role, "content": h.content} for h in state.history],
    }

    result = run_agent_turn(
        agent,
        thread_id=state.test_id,
        user_answer=answer_response.answer,
        current_state=current_agent_state,
    )

    state.history.append(Turn(role="user", content=answer_response.answer))
    state.turn_count += 1
    state.current_slots = result["slots"]

    if result["is_complete"]:
        state.status = "completed"
        state.current_question = None

        test_result = TestResult(
            test_id=state.test_id,
            status="passed",
            turn_count=state.turn_count,
            final_slots=state.current_slots,
            history=state.history,
        )
        save_result(test_result)
    else:
        if state.turn_count >= state.max_turns:
            state.status = "failed"
            state.failure_reason = "turn_exceeded"
            state.failure_details = f"Max turns ({state.max_turns}) exceeded"

            test_result = TestResult(
                test_id=state.test_id,
                status="failed",
                turn_count=state.turn_count,
                final_slots=state.current_slots,
                failure_reason="turn_exceeded",
                failure_details=state.failure_details,
                history=state.history,
            )
            save_result(test_result)
        else:
            state.status = "waiting_answer"
            state.current_question = result.get("current_question")
            if state.current_question:
                state.history.append(Turn(role="agent", content=state.current_question))

    save_state(state)
    return state


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="LangGraph Agent Orchestrator")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--test-id", required=True)

    subparsers.add_parser("answer")
    subparsers.add_parser("status")

    args = parser.parse_args()

    if args.command == "start":
        state = start_test(args.test_id)
        print(f"\nStatus: {state.status}")
        if state.current_question:
            print(f"Question: {state.current_question}")
        print(f"Slots: {state.current_slots}")

    elif args.command == "answer":
        state = submit_answer()
        print(f"\nStatus: {state.status}")
        if state.status == "waiting_answer":
            print(f"Question: {state.current_question}")
        elif state.status == "failed":
            print(f"Failure: {state.failure_reason}")
        print(f"Slots: {state.current_slots}")

    elif args.command == "status":
        try:
            state = load_state()
            print(json.dumps(state.model_dump(), indent=2, ensure_ascii=False))
        except FileNotFoundError:
            print("No active test.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
