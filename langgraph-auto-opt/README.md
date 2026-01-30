# LangGraph Agent Auto-Optimization System

LangGraph Agent의 HITL(Human-in-the-Loop)을 자동화하고, 테스트 결과를 바탕으로 프롬프트를 자동 최적화하는 시스템입니다.

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

### 전체 테스트 실행

```bash
cd src
USE_MOCK=true python run_tests.py --clean
```

### 단일 테스트

```bash
USE_MOCK=true python run_tests.py --test-id tc_001
```

### 실패 분석

```bash
USE_MOCK=true python optimize.py analyze
```

### 자동 최적화

```bash
USE_MOCK=true python optimize.py auto
```

## 디렉토리 구조

```
langgraph-auto-opt/
├── src/
│   ├── agent.py          # LangGraph Agent
│   ├── orchestrator.py   # 테스트 실행기
│   ├── run_tests.py      # 전체 테스트 + 시뮬레이션
│   ├── optimize.py       # 프롬프트 자동 최적화
│   └── schemas.py        # 데이터 스키마
├── config/
│   └── test_cases.yaml   # 테스트 케이스
├── prompts/
│   ├── slot_extraction.txt
│   └── question_generation.txt
├── communication/        # 상태 파일
├── results/              # 테스트 결과
└── logs/                 # 최적화 로그
```

## 테스트 케이스

|ID    |설명         |예상 턴|
|------|-----------|----|
|tc_001|정보 완전함     |1   |
|tc_002|location 빠짐|1-2 |
|tc_003|모호한 날짜     |1-3 |
|tc_004|제목만 있음     |2-4 |
|tc_005|비문/줄임말     |2-3 |

## 실제 LLM 사용

`ANTHROPIC_API_KEY` 환경변수를 설정하면 실제 Claude API를 사용합니다:

```bash
export ANTHROPIC_API_KEY=your-key
python run_tests.py
```
