"""
LangGraph Agent for Schedule Creation Task
"""

import os
import re
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Mock 모드 체크
USE_MOCK = os.environ.get("USE_MOCK", "false").lower() == "true" or not os.environ.get("ANTHROPIC_API_KEY")

# Paths
BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"

if USE_MOCK:
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content

    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
else:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import SystemMessage, HumanMessage


# =============================================================================
# State Definition
# =============================================================================

class Slots(TypedDict, total=False):
    title: str | None
    date: str | None
    time: str | None
    location: str | None


class AgentState(TypedDict):
    query: str
    slots: Slots
    history: list[dict]
    current_question: str | None
    is_complete: bool
    user_answer: str | None


# =============================================================================
# Prompts - Load from files
# =============================================================================

def load_prompt(filename: str) -> str:
    """프롬프트 파일에서 내용을 로드"""
    prompt_file = PROMPTS_DIR / filename
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text(encoding='utf-8').strip()


def get_slot_extraction_prompt() -> str:
    """슬롯 추출 프롬프트 로드"""
    return load_prompt("slot_extraction.txt")


def get_question_generation_prompt() -> str:
    """질문 생성 프롬프트 로드"""
    return load_prompt("question_generation.txt")


# =============================================================================
# LLM Setup
# =============================================================================

def get_llm():
    if USE_MOCK:
        return MockLLM()
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=1024,
    )


class MockLLM:
    """테스트용 Mock LLM - 규칙 기반 슬롯 추출"""

    def invoke(self, messages):
        content = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        system_content = messages[0].content if hasattr(messages[0], 'content') else str(messages[0])

        if "JSON 형식으로만 응답" in system_content:
            return MockResponse(self._extract_slots(content))
        else:
            return MockResponse(self._generate_question(system_content))

    def _extract_slots(self, text: str) -> str:
        import json

        slots = {"title": None, "date": None, "time": None, "location": None}

        # 날짜 패턴
        date_patterns = [
            (r'내일', '내일'),
            (r'모레', '모레'),
            (r'오늘', '오늘'),
            (r'다음\s*주\s*(월|화|수|목|금|토|일)요일', lambda m: f'다음주 {m.group(1)}요일'),
            (r'다음\s*주', '다음주'),
            (r'(월|화|수|목|금|토|일)요일', lambda m: f'{m.group(1)}요일'),
        ]
        for pattern, result in date_patterns:
            match = re.search(pattern, text)
            if match:
                if callable(result):
                    slots["date"] = result(match)
                else:
                    slots["date"] = result
                break

        # 시간 패턴
        time_patterns = [
            (r'오전\s*(\d{1,2})\s*시', lambda m: f'{int(m.group(1)):02d}:00'),
            (r'오후\s*(\d{1,2})\s*시', lambda m: f'{int(m.group(1)) + 12 if int(m.group(1)) < 12 else int(m.group(1)):02d}:00'),
            (r'(\d{1,2})\s*시', lambda m: f'{int(m.group(1)) + 12 if int(m.group(1)) < 8 else int(m.group(1)):02d}:00'),
            (r'점심', '12:00'),
            (r'저녁', '18:00'),
            (r'오후', '14:00'),
        ]
        for pattern, result in time_patterns:
            match = re.search(pattern, text)
            if match:
                if callable(result):
                    slots["time"] = result(match)
                else:
                    slots["time"] = result
                break

        # 장소 패턴
        location_patterns = [
            r'(강남역\s*스타벅스)',
            r'(강남역)',
            r'(\w+역)',
            r'(\w+병원)',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                slots["location"] = match.group(1).strip()
                break

        # 제목 패턴
        title_patterns = [
            (r'팀\s*회의', '팀 회의'),
            (r'회의', '회의'),
            (r'미팅', '미팅'),
            (r'면접', '면접'),
            (r'치과', '치과'),
            (r'병원', '병원'),
            (r'저녁\s*약속', '저녁 약속'),
            (r'점심\s*약속', '점심 약속'),
            (r'약속', '약속'),
        ]
        for pattern, title in title_patterns:
            if re.search(pattern, text):
                slots["title"] = title
                break

        return json.dumps(slots, ensure_ascii=False)

    def _generate_question(self, system_content: str) -> str:
        """
        프롬프트 품질에 반응하는 질문 생성

        좋은 프롬프트 (명확한 규칙)가 있으면 중복 질문 안함
        나쁜 프롬프트 (규칙 없음)가 있으면 가끔 중복 질문 발생
        """
        filled = {}
        missing = []

        filled_match = re.search(r'현재 채워진 정보:\s*\n([^\n]+)', system_content)
        if filled_match:
            filled_str = filled_match.group(1).strip()
            if filled_str != "없음" and filled_str != "{}":
                pairs = re.findall(r"'(\w+)':\s*'([^']+)'", filled_str)
                filled = dict(pairs)

        missing_match = re.search(r'아직 필요한 정보:\s*\n([^\n]+)', system_content)
        if missing_match:
            missing_str = missing_match.group(1).strip()
            if missing_str != "없음":
                missing = re.findall(r"'(\w+)'", missing_str)

        # 프롬프트 품질 체크: 중복 방지 규칙이 있는가?
        has_redundancy_prevention = any([
            "절대 다시 묻지 마세요" in system_content,
            "이미 알고 있는 정보" in system_content,
            "already" in system_content.lower() and "don't" in system_content.lower(),
        ])

        questions = {
            "title": "어떤 일정인가요?",
            "date": "언제로 잡을까요?",
            "time": "몇 시에 하실 건가요?",
            "location": "장소는 어디인가요?",
        }

        # 나쁜 프롬프트: 이미 채워진 정보도 다시 물어볼 수 있음
        if not has_redundancy_prevention and filled:
            # 50% 확률로 이미 채워진 정보를 다시 물어봄 (나쁜 행동)
            import random
            if random.random() < 0.5 and filled:
                # 이미 채워진 슬롯 중 하나를 다시 물어봄
                redundant_slot = random.choice(list(filled.keys()))
                return questions.get(redundant_slot, "어떤 일정인가요?")

        # 정상적인 질문: 빠진 정보만 물어봄
        for slot in ["title", "date", "time", "location"]:
            if slot in missing or (slot not in filled and slot in ["title", "date"]):
                return questions.get(slot, "추가 정보를 알려주세요.")

        return "추가 정보를 알려주세요."


class MockResponse:
    def __init__(self, content: str):
        self.content = content


# =============================================================================
# Node Functions
# =============================================================================

def extract_slots(state: AgentState) -> AgentState:
    llm = get_llm()

    if state.get("user_answer"):
        new_input = state["user_answer"]
    else:
        new_input = state["query"]

    context = f"원본 요청: {state['query']}\n"
    if state.get("history"):
        context += "대화 히스토리:\n"
        for turn in state["history"]:
            context += f"- {turn['role']}: {turn['content']}\n"
    context += f"\n새 입력: {new_input}"

    messages = [
        SystemMessage(content=get_slot_extraction_prompt()),
        HumanMessage(content=context)
    ]

    response = llm.invoke(messages)

    import json
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        extracted = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        extracted = {}

    current_slots = state.get("slots", {})
    for key in ["title", "date", "time", "location"]:
        if extracted.get(key):
            current_slots[key] = extracted[key]

    history = state.get("history", []).copy()
    if state.get("user_answer"):
        history.append({"role": "user", "content": state["user_answer"]})

    return {
        **state,
        "slots": current_slots,
        "history": history,
        "user_answer": None,
    }


def check_completion(state: AgentState) -> AgentState:
    slots = state.get("slots", {})
    required = ["title", "date"]
    missing = [s for s in required if not slots.get(s)]
    is_complete = len(missing) == 0

    return {
        **state,
        "is_complete": is_complete,
    }


def generate_question(state: AgentState) -> AgentState:
    llm = get_llm()
    slots = state.get("slots", {})

    filled = {k: v for k, v in slots.items() if v}
    missing = [k for k in ["title", "date", "time", "location"] if not slots.get(k)]

    required_missing = [s for s in ["title", "date"] if s in missing]
    if required_missing:
        missing_to_ask = required_missing
    else:
        missing_to_ask = missing

    prompt = get_question_generation_prompt().format(
        filled_slots=filled if filled else "없음",
        missing_slots=missing_to_ask if missing_to_ask else "없음"
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="질문을 생성해주세요.")
    ]

    response = llm.invoke(messages)
    question = response.content.strip()

    history = state.get("history", []).copy()
    history.append({"role": "agent", "content": question})

    return {
        **state,
        "current_question": question,
        "history": history,
    }


# =============================================================================
# Routing
# =============================================================================

def should_continue(state: AgentState) -> str:
    if state.get("is_complete"):
        return "end"
    else:
        return "generate_question"


# =============================================================================
# Graph Construction
# =============================================================================

def create_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("extract_slots", extract_slots)
    workflow.add_node("check_completion", check_completion)
    workflow.add_node("generate_question", generate_question)

    workflow.add_edge(START, "extract_slots")
    workflow.add_edge("extract_slots", "check_completion")
    workflow.add_conditional_edges(
        "check_completion",
        should_continue,
        {
            "end": END,
            "generate_question": "generate_question",
        }
    )
    workflow.add_edge("generate_question", END)

    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


# =============================================================================
# Convenience Functions
# =============================================================================

def run_agent_turn(
    agent,
    thread_id: str,
    query: str | None = None,
    user_answer: str | None = None,
    current_state: dict | None = None,
) -> AgentState:
    config = {"configurable": {"thread_id": thread_id}}

    if query:
        initial_state = {
            "query": query,
            "slots": {},
            "history": [{"role": "user", "content": query}],
            "current_question": None,
            "is_complete": False,
            "user_answer": None,
        }
        result = agent.invoke(initial_state, config)
    else:
        if current_state is None:
            raise ValueError("current_state required for resume")

        updated_state = {
            "query": current_state.get("query", ""),
            "slots": current_state.get("slots", {}),
            "history": current_state.get("history", []),
            "current_question": current_state.get("current_question"),
            "is_complete": False,
            "user_answer": user_answer,
        }
        result = agent.invoke(updated_state, config)

    return result


if __name__ == "__main__":
    agent = create_agent()

    print("=== Test: 완전한 정보 ===")
    result = run_agent_turn(agent, "test1", query="내일 3시 강남에서 회의")
    print(f"Slots: {result['slots']}")
    print(f"Complete: {result['is_complete']}")
