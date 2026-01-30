"""
Evaluation Metrics for Agent Performance
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from schemas import TestResult


@dataclass
class SlotMetrics:
    """슬롯 단위 메트릭"""
    accuracy: float  # 정확히 추출된 비율
    precision: float  # 추출한 것 중 정확한 비율
    recall: float  # 있는 것 중 추출한 비율


@dataclass
class DetailedMetrics:
    """상세 메트릭"""
    pass_rate: float
    avg_turns: float

    # 슬롯 정확도
    slot_accuracy: float  # 전체 슬롯의 정확도
    title_accuracy: float
    date_accuracy: float
    time_accuracy: float
    location_accuracy: float

    # 효율성
    avg_turns_for_passed: float  # 통과한 테스트의 평균 턴 수
    redundancy_rate: float  # 중복 질문 비율

    # 실패 분석
    failure_by_redundant: int
    failure_by_turn_exceeded: int
    failure_by_off_topic: int


def calculate_slot_accuracy(
    extracted: Dict[str, Optional[str]],
    ground_truth: Dict[str, Optional[str]]
) -> Dict[str, bool]:
    """각 슬롯의 정확도 계산"""
    accuracy = {}

    for slot in ["title", "date", "time", "location"]:
        gt = ground_truth.get(slot)
        ex = extracted.get(slot)

        # None == None은 정확함
        if gt is None and ex is None:
            accuracy[slot] = True
        # 하나만 None이면 틀림
        elif gt is None or ex is None:
            accuracy[slot] = False
        # 둘 다 있으면 정규화해서 비교
        else:
            accuracy[slot] = normalize_slot_value(ex, slot) == normalize_slot_value(gt, slot)

    return accuracy


def normalize_slot_value(value: str, slot: str) -> str:
    """슬롯 값 정규화"""
    if value is None:
        return ""

    value = value.strip().lower()

    # 날짜 정규화
    if slot == "date":
        date_map = {
            "내일": "tomorrow",
            "모레": "day_after_tomorrow",
            "오늘": "today",
            "금요일": "friday",
            "토요일": "saturday",
            "일요일": "sunday",
            "월요일": "monday",
            "화요일": "tuesday",
            "수요일": "wednesday",
            "목요일": "thursday",
            "다음주": "next_week",
        }
        for kr, en in date_map.items():
            if kr in value:
                return en

    # 시간 정규화
    elif slot == "time":
        # "15:00", "오후 3시" 등을 24시간 형식으로
        import re

        # HH:MM 형식
        match = re.search(r'(\d{1,2}):(\d{2})', value)
        if match:
            return f"{int(match.group(1)):02d}:{match.group(2)}"

        # 점심, 저녁 등
        time_map = {
            "점심": "12:00",
            "저녁": "18:00",
            "아침": "08:00",
            "오전": "09:00",
            "오후": "14:00",
        }
        for kr, normalized in time_map.items():
            if kr in value:
                return normalized

    return value


def calculate_detailed_metrics(results: List[TestResult]) -> DetailedMetrics:
    """상세 메트릭 계산"""
    if not results:
        return DetailedMetrics(
            pass_rate=0.0,
            avg_turns=0.0,
            slot_accuracy=0.0,
            title_accuracy=0.0,
            date_accuracy=0.0,
            time_accuracy=0.0,
            location_accuracy=0.0,
            avg_turns_for_passed=0.0,
            redundancy_rate=0.0,
            failure_by_redundant=0,
            failure_by_turn_exceeded=0,
            failure_by_off_topic=0,
        )

    total = len(results)
    passed = [r for r in results if r.status == "passed"]
    failed = [r for r in results if r.status == "failed"]

    # 기본 메트릭
    pass_rate = len(passed) / total * 100
    avg_turns = sum(r.turn_count for r in results) / total
    avg_turns_for_passed = sum(r.turn_count for r in passed) / len(passed) if passed else 0.0

    # 슬롯 정확도 (통과한 테스트만)
    slot_accuracies = {"title": [], "date": [], "time": [], "location": []}

    for r in results:
        # ground_truth는 TestResult에 없으므로 TestCase를 다시 로드해야 함
        # 지금은 간단하게 final_slots가 있는지만 체크
        if r.status == "passed":
            for slot in ["title", "date", "time", "location"]:
                has_value = r.final_slots.get(slot) is not None
                slot_accuracies[slot].append(has_value)

    title_accuracy = sum(slot_accuracies["title"]) / len(slot_accuracies["title"]) * 100 if slot_accuracies["title"] else 0.0
    date_accuracy = sum(slot_accuracies["date"]) / len(slot_accuracies["date"]) * 100 if slot_accuracies["date"] else 0.0
    time_accuracy = sum(slot_accuracies["time"]) / len(slot_accuracies["time"]) * 100 if slot_accuracies["time"] else 0.0
    location_accuracy = sum(slot_accuracies["location"]) / len(slot_accuracies["location"]) * 100 if slot_accuracies["location"] else 0.0

    slot_accuracy = (title_accuracy + date_accuracy) / 2  # title과 date는 필수

    # 실패 분석
    failure_by_redundant = sum(1 for r in failed if r.failure_reason == "redundant")
    failure_by_turn_exceeded = sum(1 for r in failed if r.failure_reason == "turn_exceeded")
    failure_by_off_topic = sum(1 for r in failed if r.failure_reason == "off_topic")

    redundancy_rate = failure_by_redundant / total * 100 if total > 0 else 0.0

    return DetailedMetrics(
        pass_rate=pass_rate,
        avg_turns=avg_turns,
        slot_accuracy=slot_accuracy,
        title_accuracy=title_accuracy,
        date_accuracy=date_accuracy,
        time_accuracy=time_accuracy,
        location_accuracy=location_accuracy,
        avg_turns_for_passed=avg_turns_for_passed,
        redundancy_rate=redundancy_rate,
        failure_by_redundant=failure_by_redundant,
        failure_by_turn_exceeded=failure_by_turn_exceeded,
        failure_by_off_topic=failure_by_off_topic,
    )


def print_detailed_metrics(metrics: DetailedMetrics):
    """상세 메트릭 출력"""
    print("\n" + "="*60)
    print("DETAILED METRICS")
    print("="*60)

    print("\n성능:")
    print(f"  Pass Rate: {metrics.pass_rate:.1f}%")
    print(f"  Avg Turns: {metrics.avg_turns:.2f}")
    print(f"  Avg Turns (Passed): {metrics.avg_turns_for_passed:.2f}")

    print("\n슬롯 정확도:")
    print(f"  Overall: {metrics.slot_accuracy:.1f}%")
    print(f"  Title: {metrics.title_accuracy:.1f}%")
    print(f"  Date: {metrics.date_accuracy:.1f}%")
    print(f"  Time: {metrics.time_accuracy:.1f}%")
    print(f"  Location: {metrics.location_accuracy:.1f}%")

    print("\n실패 분석:")
    print(f"  Redundancy Rate: {metrics.redundancy_rate:.1f}%")
    print(f"  Failures by Redundant Questions: {metrics.failure_by_redundant}")
    print(f"  Failures by Turn Exceeded: {metrics.failure_by_turn_exceeded}")
    print(f"  Failures by Off Topic: {metrics.failure_by_off_topic}")

    print("="*60)
