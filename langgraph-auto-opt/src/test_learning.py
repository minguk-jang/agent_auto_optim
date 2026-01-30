"""
실제 학습 루프가 작동하는지 검증
"""

import sys
from pathlib import Path

# 1. 현재 테스트 결과 확인
print("="*60)
print("현재 상태 분석")
print("="*60)

from run_tests import run_all_tests, generate_report

results = run_all_tests()
report = generate_report(results)

print("\n" + "="*60)
print("학습 루프 검증")
print("="*60)

# 2. 실패가 있는가?
if report["failed"] == 0:
    print("❌ 문제: 실패하는 테스트가 없음")
    print("   → 최적화가 트리거되지 않음")
    print("   → 학습 루프가 실행되지 않음")
else:
    print(f"✓ 실패: {report['failed']}개")

# 3. 최적화가 실행될 조건인가?
target_pass_rate = 100.0
target_avg_turns = 2.0

print(f"\n목표:")
print(f"  Pass Rate: >= {target_pass_rate}%")
print(f"  Avg Turns: <= {target_avg_turns}")

print(f"\n현재:")
print(f"  Pass Rate: {report['pass_rate']:.1f}%")
print(f"  Avg Turns: {report['avg_turns']:.2f}")

if report["pass_rate"] >= target_pass_rate and report["avg_turns"] <= target_avg_turns:
    print("\n❌ 문제: 이미 목표 달성")
    print("   → auto_optimize()가 첫 iteration에서 종료됨")
    print("   → 학습이 일어나지 않음")
else:
    print("\n✓ 최적화 필요")

# 4. MockLLM이 프롬프트를 사용하는가?
print("\n" + "="*60)
print("MockLLM 프롬프트 사용 여부")
print("="*60)

from agent import MockLLM
import inspect

source = inspect.getsource(MockLLM._extract_slots)
if "prompt" in source.lower() and "system" not in source.lower():
    print("✓ MockLLM이 프롬프트를 사용함")
elif "re.search" in source or "pattern" in source:
    print("❌ 문제: MockLLM이 정규식 기반")
    print("   → 프롬프트 변경이 효과 없음")
    print("   → Mock 모드에서는 학습 불가능")

# 5. 결론
print("\n" + "="*60)
print("학습 루프 가능성 진단")
print("="*60)

issues = []

if report["failed"] == 0:
    issues.append("실패하는 테스트 없음")

if report["pass_rate"] >= target_pass_rate and report["avg_turns"] <= target_avg_turns:
    issues.append("이미 목표 달성")

if "re.search" in source:
    issues.append("MockLLM이 프롬프트 무시")

if issues:
    print("❌ 학습 루프 작동 불가:")
    for issue in issues:
        print(f"   - {issue}")
    print("\n해결 방안:")
    print("   1. 의도적으로 나쁜 프롬프트 생성")
    print("   2. 더 어려운 테스트 케이스 추가")
    print("   3. 실제 LLM 사용 (ANTHROPIC_API_KEY 필요)")
else:
    print("✓ 학습 루프 작동 가능")
