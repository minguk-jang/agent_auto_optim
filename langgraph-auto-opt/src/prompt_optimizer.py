"""
LLM-based Prompt Optimization
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List

# Mock 모드 체크
USE_MOCK = os.environ.get("USE_MOCK", "false").lower() == "true" or not os.environ.get("ANTHROPIC_API_KEY")

if not USE_MOCK:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import SystemMessage, HumanMessage


@dataclass
class PromptImprovement:
    """프롬프트 개선 제안"""
    target_file: str
    issue_description: str
    suggested_prompt: str
    reasoning: str


class PromptOptimizer:
    """LLM 기반 프롬프트 최적화기"""

    def __init__(self):
        if USE_MOCK:
            self.llm = None
        else:
            self.llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                temperature=0.3,
                max_tokens=2048,
            )

    def analyze_failures_and_suggest(
        self,
        current_prompt: str,
        failure_examples: List[dict],
        prompt_name: str
    ) -> PromptImprovement:
        """
        실패 사례를 분석하고 프롬프트 개선안 생성

        Args:
            current_prompt: 현재 프롬프트 내용
            failure_examples: 실패 사례 리스트
            prompt_name: 프롬프트 이름 (slot_extraction 또는 question_generation)

        Returns:
            PromptImprovement 객체
        """
        if USE_MOCK:
            return self._mock_suggestion(current_prompt, failure_examples, prompt_name)

        # 실패 사례 요약
        failure_summary = self._summarize_failures(failure_examples)

        # LLM에게 프롬프트 개선 요청
        system_prompt = """당신은 프롬프트 엔지니어링 전문가입니다.
주어진 프롬프트와 실패 사례를 분석하고, 더 나은 프롬프트를 제안하세요.

개선 원칙:
1. 명확성: 모호한 지시를 구체적으로
2. 제약 조건: 잘못된 행동을 명시적으로 금지
3. 예시: 좋은 예시와 나쁜 예시 추가
4. 단계별 지시: 복잡한 작업을 단계로 나누기
5. 출력 형식: 원하는 출력 형식을 명확하게

원본 프롬프트의 핵심 의도는 유지하면서, 실패 사례를 해결할 수 있도록 개선하세요."""

        user_message = f"""
# 프롬프트 이름
{prompt_name}

# 현재 프롬프트
```
{current_prompt}
```

# 실패 사례 분석
{failure_summary}

# 요청
위 실패 사례를 해결할 수 있도록 프롬프트를 개선해주세요.

다음 형식으로 응답하세요:

## 문제 분석
[현재 프롬프트의 문제점]

## 개선된 프롬프트
```
[새로운 프롬프트 전체 내용]
```

## 개선 이유
[왜 이렇게 수정했는지 설명]
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        response = self.llm.invoke(messages)
        content = response.content

        # 응답 파싱
        issue_desc = ""
        suggested_prompt = ""
        reasoning = ""

        if "## 문제 분석" in content:
            parts = content.split("## 문제 분석")[1]
            issue_desc = parts.split("## 개선된 프롬프트")[0].strip()

        if "## 개선된 프롬프트" in content:
            parts = content.split("## 개선된 프롬프트")[1]
            prompt_part = parts.split("## 개선 이유")[0].strip()

            # 코드 블록에서 추출
            if "```" in prompt_part:
                suggested_prompt = prompt_part.split("```")[1].strip()
                # 언어 지정자 제거
                if suggested_prompt.startswith("txt\n") or suggested_prompt.startswith("text\n"):
                    suggested_prompt = "\n".join(suggested_prompt.split("\n")[1:])
            else:
                suggested_prompt = prompt_part

        if "## 개선 이유" in content:
            reasoning = content.split("## 개선 이유")[1].strip()

        return PromptImprovement(
            target_file=f"{prompt_name}.txt",
            issue_description=issue_desc or "실패 사례 발견",
            suggested_prompt=suggested_prompt or current_prompt,
            reasoning=reasoning or "프롬프트 개선 제안",
        )

    def _summarize_failures(self, failure_examples: List[dict]) -> str:
        """실패 사례 요약"""
        if not failure_examples:
            return "실패 사례 없음"

        summary = []
        for i, example in enumerate(failure_examples[:5], 1):  # 최대 5개만
            summary.append(f"실패 사례 {i}:")
            summary.append(f"  - Test ID: {example.get('test_id', 'unknown')}")
            summary.append(f"  - 실패 이유: {example.get('details', 'unknown')}")
            if "slots_at_failure" in example:
                summary.append(f"  - 당시 슬롯: {example['slots_at_failure']}")

        return "\n".join(summary)

    def _mock_suggestion(
        self,
        current_prompt: str,
        failure_examples: List[dict],
        prompt_name: str
    ) -> PromptImprovement:
        """Mock 모드에서의 간단한 제안"""
        if "redundant" in str(failure_examples):
            addition = """

**중요: 중복 질문 방지**
- 현재 채워진 정보에 있는 내용은 절대 다시 묻지 마세요
- 사용자가 이미 제공한 정보를 재확인하지 마세요
- 비어있는 슬롯에 대해서만 질문하세요
"""
            return PromptImprovement(
                target_file=f"{prompt_name}.txt",
                issue_description="중복 질문 방지 규칙 필요",
                suggested_prompt=current_prompt + addition,
                reasoning="중복 질문을 방지하기 위한 명시적 규칙 추가",
            )

        return PromptImprovement(
            target_file=f"{prompt_name}.txt",
            issue_description="No specific issues found",
            suggested_prompt=current_prompt,
            reasoning="No changes needed",
        )


if __name__ == "__main__":
    # 테스트
    optimizer = PromptOptimizer()

    test_prompt = """당신은 일정 생성을 돕는 어시스턴트입니다.
사용자에게 부족한 정보를 자연스럽게 물어보세요."""

    test_failures = [
        {
            "test_id": "tc_001",
            "details": "이미 '회의'라고 제목이 있는데 다시 물음",
            "slots_at_failure": {"title": "회의", "date": "내일"},
        }
    ]

    result = optimizer.analyze_failures_and_suggest(
        test_prompt,
        test_failures,
        "question_generation"
    )

    print("Issue:", result.issue_description)
    print("\nSuggested Prompt:")
    print(result.suggested_prompt)
    print("\nReasoning:")
    print(result.reasoning)
