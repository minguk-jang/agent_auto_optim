"""
State schemas for LangGraph Agent Auto-Optimization System
"""

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


# =============================================================================
# Slot Schema
# =============================================================================

class Slots(BaseModel):
    """일정 생성에 필요한 슬롯"""
    title: str | None = None
    date: str | None = None
    time: str | None = None
    location: str | None = None


# =============================================================================
# LangGraph Agent State
# =============================================================================

class AgentState(BaseModel):
    """LangGraph Agent 내부 상태"""
    query: str
    slots: Slots = Field(default_factory=Slots)
    missing_required: list[str] = Field(default_factory=list)
    current_question: str | None = None
    is_complete: bool = False


# =============================================================================
# Communication: Orchestrator <-> Claude Code
# =============================================================================

class Turn(BaseModel):
    """대화 턴"""
    role: Literal["user", "agent"]
    content: str


class TestContext(BaseModel):
    """TC에서 가져온 컨텍스트 - Claude Code 판단용"""
    user_intent: str
    ground_truth: dict[str, str | None]


class OrchestratorState(BaseModel):
    """
    Orchestrator가 파일로 내보내는 상태
    Claude Code가 읽고 답변/판단함
    """
    test_id: str
    status: Literal["waiting_answer", "completed", "failed"]
    turn_count: int
    max_turns: int

    current_question: str | None
    current_slots: dict[str, str | None]

    context: TestContext
    history: list[Turn]

    failure_reason: str | None = None
    failure_details: str | None = None


class ClaudeCodeResponse(BaseModel):
    """Claude Code가 작성하는 응답"""
    answer: str | None = None
    judgment: Literal["valid", "redundant", "off_topic"]
    judgment_reason: str


# =============================================================================
# Test Case Schema
# =============================================================================

class TestCase(BaseModel):
    """테스트 케이스 정의"""
    id: str
    query: str
    context: TestContext
    max_turns: int = 3


class TestResult(BaseModel):
    """테스트 결과"""
    test_id: str
    status: Literal["passed", "failed"]
    turn_count: int
    final_slots: dict[str, str | None]

    failure_reason: str | None = None
    failure_details: str | None = None

    history: list[Turn] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Optimization
# =============================================================================

class OptimizationRun(BaseModel):
    """한 번의 최적화 실행 기록"""
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    results: list[TestResult]
    pass_rate: float
    avg_turns: float

    prompt_changes: dict[str, str] | None = None
