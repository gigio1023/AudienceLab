---
name: demo-preparation
description: 해커톤 데모 준비 및 발표 자료 작성. 데모 시나리오, 스크립트, README 템플릿, 발표 Q&A 대비에 사용.
---

# Demo Preparation Skill

## Overview

해커톤 데모 영상 녹화, README 작성, 발표 자료 준비를 지원합니다.

## Demo Scenario (5분 시나리오)

### Scene 1: Problem Statement (30초)
```
"마케터들은 인플루언서에게 100만 원을 지불하기 전까지 
캠페인 성과를 알 수 없습니다.

저희는 이 문제를 해결합니다."
```

### Scene 2: Input (30초)
```
[대시보드 화면]
마케터가 캠페인 목표를 입력:
"20대 여성 타겟, 비건 스킨케어 런칭, 예산 500만원"
```

### Scene 3: Simulation (2분)
```
[시뮬레이션 실행]
3개의 다양한 페르소나가 순차적으로 반응:

1️⃣ 비건맘: "동물실험 없는 거 맞죠? 너무 좋아요!" → 좋아요 + 댓글
2️⃣ 뷰티덕후: "성분표 보여주세요~" → 분석적 질문
3️⃣ 냉소적MZ: "광고티 심한데... 패스" → 스킵

[Stigmergy 시각화]
"이전 댓글이 다음 에이전트의 반응에 영향을 미칩니다"
```

### Scene 4: Results (1분)
```
[대시보드 메트릭]
- 긍정 반응: 33%
- 중립 반응: 33%
- 부정 반응: 33%
- 예상 참여율: 67%

[인사이트]
"이 인플루언서의 팔로워 중 1/3이 부정적 반응 예상.
MZ 세대 타겟이라면 다른 인플루언서를 고려하세요."
```

### Scene 5: Closing (30초)
```
"저희는 OpenAI의 Multi-Agent 패턴을 적용하여
Brain(인지)과 Body(행동)를 분리한 하이브리드 아키텍처를 구현했습니다.

93% 비용 절감, 실제 B2B 사업화 가능한 구조입니다.
감사합니다."
```

## README Template

```markdown
# 🎯 Persona-Driven Influencer Simulation

> Real Instagram 데이터를 Ground Truth로 사용하여 Multi-Agent 시뮬레이션으로 
> 인플루언서 캠페인 성과를 예측하는 시스템

## 🎬 Demo

[![Demo Video](https://img.shields.io/badge/Demo-YouTube-red)](링크)

**Live Demo**: [링크] (해커톤 기간 한정)

## 🏗️ Multi-Agent Architecture

```
┌─────────────────────────────────────────────────┐
│              ORCHESTRATOR                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ HERO AGENT  │  │ CROWD AGENTS│  │EVALUATOR│ │
│  │ (Browser)   │  │ (Headless)  │  │(Metrics)│ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
│                       │                        │
│                  Stigmergy                     │
│                       ▼                        │
│              [Local SNS Environment]           │
└─────────────────────────────────────────────────┘
```

### 적용된 OpenAI Multi-Agent 패턴

| 패턴 | 설명 |
|------|------|
| **Orchestrator-Subagent** | Runner가 다수의 Persona Agent 조율 |
| **Agent Specialization** | Hero(Action) vs Crowd(Reasoning) 분리 |
| **Stigmergy** | SNS 환경 통한 간접 협업 |
| **Agentic Loop** | Perceive → Reason → Act 사이클 |
| **Guardrails** | Sandbox 격리, 예산 제어 |

## 🚀 Quick Start

### 1. 환경 설정

\`\`\`bash
# Local SNS 구동
cd sns/pixelfed && docker-compose up -d

# Agent 환경
cd agent && uv sync

# Dashboard
cd search-dashboard && npm install && npm run dev
\`\`\`

### 2. 시뮬레이션 실행

\`\`\`bash
cd agent
uv run python persona_runner.py
\`\`\`

### 3. 결과 확인

대시보드 접속: `http://localhost:5173`

## 📊 Results

| 메트릭 | 값 |
|--------|-----|
| 에이전트 수 | 3개 (확장 가능: 100+) |
| 시뮬레이션 비용 | ~$0.65/회 (93% 절감) |
| 실행 시간 | ~30초 |

## 🔧 Tech Stack

- **Agent**: Python, Playwright, OpenAI GPT-4o Vision
- **Frontend**: React 18, TypeScript, Vite
- **Environment**: Pixelfed (Docker), MySQL, Redis

## 👥 Team

- [Team Member 1]
- [Team Member 2]

## 📝 License

MIT
```

## Q&A 방어 논리

### Q1: "왜 브라우저 100개 안 띄웠나요?"

```
A: "저희는 '기술력 과시'가 아닌 '비즈니스 가치'에 집중했습니다.

Brain(인지)과 Body(행동)를 분리한 하이브리드 아키텍처로:
- 99개 Headless Agent: 마케팅 성과 예측 (API only, $0.55)
- 1개 Visual Agent: 기술력 증명 (Full Browser, $0.10)

이로써 93% 비용 절감을 달성했고,
이것은 실제 B2B 사업화가 가능한 구조입니다."
```

### Q2: "Stigmergy가 뭐예요?"

```
A: "Stigmergy는 개미가 페로몬으로 소통하는 것과 같은 패턴입니다.

저희 에이전트들은 직접 통신하지 않습니다.
Agent A가 댓글을 달면 → Agent B가 그 댓글을 보고 반응합니다.

즉, '환경(SNS)'을 매개로 간접 협업하는 구조입니다.
OpenAI에서 제시하는 Multi-Agent 패턴 중 하나입니다."
```

### Q3: "이게 실제로 맞아요? 예측이 정확해요?"

```
A: "저희는 Ground Truth Seeding을 사용합니다.

실제 인스타그램 댓글 데이터를 Few-Shot으로 학습시켜
해당 인플루언서 팔로워들의 Tone & Manner를 모방합니다.

현재는 해커톤 MVP이지만, 충분한 데이터가 있으면
통계적으로 유의미한 예측이 가능합니다."
```

### Q4: "OpenAI API 어떻게 사용했나요?"

```
A: "GPT-4o Vision을 사용합니다.

각 에이전트는:
1. SNS 화면 스크린샷을 Vision으로 분석
2. 페르소나 프롬프트와 함께 의사결정
3. Chain-of-Thought로 추론 과정 로깅
4. JSON 형태로 구조화된 응답 반환

핵심은 '단순 API 호출'이 아닌
'페르소나 기반 인지 시뮬레이션'입니다."
```

## Recording Checklist

- [ ] 화면 녹화 소프트웨어 준비 (OBS, QuickTime)
- [ ] 해상도 설정 (1920x1080 권장)
- [ ] 마이크 테스트
- [ ] 시나리오 1회 리허설
- [ ] Pixelfed 상태 확인
- [ ] API 키 유효성 확인
- [ ] 5분 타이머 세팅
- [ ] 최종 녹화 (2회 이상 시도)

## Submission Checklist

- [ ] README.md 완성
- [ ] Demo 영상 링크 추가
- [ ] 코드 정리 (불필요한 파일 제거)
- [ ] 환경 변수 제거 (.env.example만 남기기)
- [ ] 팀 정보 추가
- [ ] 제출 폼 작성
