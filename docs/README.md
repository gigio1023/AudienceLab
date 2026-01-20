# Project Definition: Persona-Driven Influencer Simulation

> **One-line Summary**: Real Instagram engagement 데이터를 Ground Truth로 사용하여, Private SNS 환경에서 Multi-Agent 시뮬레이션을 수행하고 인플루언서 캠페인 성과를 예측하는 Local-first Orchestrator System.

본 문서는 프로젝트의 목표, 핵심 가치, 시스템 범위 및 기술적 요구사항을 정의하는 최상위 명세서(Project Requirement Document)이다.

## 1. Product Story & Core Flow

우리가 만들고자 하는 데모 경험(User Journey)은 다음과 같다.

1.  **Input**: 사용자가 자연어로 캠페인 목표를 서술한다.
    > "20대 여성을 타겟으로 한 비건 스킨케어 런칭 캠페인. 톤앤매너는 고급스럽고 진지하게. 예산 $5,000."
2.  **Discovery**: 시스템이 적합한 인플루언서 후보를 제안하고 추천 사유를 설명한다.
3.  **Simulation & Validation**:
    *   선택된 인플루언서에 대해 Local SNS 환경에서 팔로워 행동 시뮬레이션을 수행한다.
    *   단순 메타데이터 매칭이 아닌, **"이 인플루언서의 팔로워들이 실제로 이 캠페인 메시지에 어떻게 반응할까?"**를 검증한다.
4.  **Output**: Engagement 기반의 Proxy Metrics(좋아요, 댓글, 팔로우)와 실제 페르소나의 반응 로그를 시각화하여 제공한다.

이 시스템은 **Data → Personas → Simulation → Metrics → Ranking**으로 이어지는 완전한 "Closed-loop" 구조를 지향한다.

## 2. The Problem We Solve

인플루언서 마케팅 시장은 거대하지만, 여전히 **"불확실성(Uncertainty)"**이라는 근본적인 문제에 직면해 있다. 마케터들은 다음과 같은 질문에 대해 데이터 기반의 답을 얻지 못한 채 직관에 의존하여 예산을 집행한다.

### 2.1 마케터의 고충 (Pain Points)
1.  **"팔로워 수가 진짜 영향력인가?" (Vanity Metrics)**
    *   단순한 팔로워 규모나 과거의 평균 좋아요 수치는 내 브랜드와의 적합성(Campaign Fit)을 보장하지 않는다.
    *   *예: 100만 팔로워를 가진 게임 유튜버에게 화장품 광고를 맡겼을 때의 반응을 예측할 수 없다.*

2.  **"실제 집행 전에는 알 수 없다" (Post-Campaign Only)**
    *   A/B 테스트가 불가능하다. 인플루언서에게 돈을 지급하고 포스팅이 올라가기 전까지는 성과를 검증할 방법이 없다.
    *   실패한 캠페인의 비용은 고스란히 매몰 비용(Sunk Cost)이 된다.

3.  **"결과의 이유를 모른다" (Black Box)**
    *   캠페인이 성공하거나 실패했을 때, "왜(Why)" 그런 결과가 나왔는지 정성적인 분석이 어렵다.
    *   단순히 "좋아요가 적다"는 결과만 알 뿐, "메시지가 너무 상업적이라 거부감을 느꼈는지", "타겟 연령대가 맞지 않았는지" 알 수 없다.

---

## 3. Technical Challenges

우리는 이 문제를 해결하기 위해 **"가상의 팔로워들을 통한 사전 시뮬레이션"**이라는 접근 방식을 택했다. 하지만 이를 실제로 구현하는 것은 기술적으로 매우 도전적인 과제이다.

### 3.1 Simulation Fidelity (현실성)
단순한 규칙 기반(Rule-based) 봇은 의미 있는 데이터를 만들어내지 못한다.
*   **Challenge**: 실제 인스타그램 데이터(Bio, 댓글 패턴 등)를 학습하여, 단순 긍정봇이 아닌 비판적 사고와 취향을 가진 **"Persona-Driven Agent"**를 구현해야 한다.

### 3.2 Execution Complexity (실행 복잡도)
*   **Challenge**: 텍스트 생성 모델(LLM)만으로는 부족하다. 실제 SNS UI 상에서 보고(Vision), 스크롤하고, 클릭하는 다수의 멀티 에이전트를 실시간으로 오케스트레이션해야 한다.

### 3.3 Calibration (보정)
*   **Challenge**: 시뮬레이션 결과가 "그럴싸한 소설"에 그치지 않으려면, 시뮬레이션 된 좋아요/댓글 수가 실제 과거 데이터(Historical Data)와 통계적으로 유사하도록 보정(Calibration)되어야 한다.

## 4. System Scope & Components

### 4.1 Component Architecture
*   **`insta-crawler/` (Data Ingestion)**:
    *   Instagram 데이터를 수집하여 "Ground Truth"를 확보한다.
    *   **Tier 1 (Min)**: 프로필, 포스트, 좋아요/댓글 수치.
    *   **Tier 2 (Target)**: 댓글 텍스트, 댓글 작성자 프로필 (페르소나 추출용).
*   **`sns/` (Simulation Environment)**:
    *   Dockerized **Pixelfed** (Laravel) 인스턴스.
    *   외부와 격리된 안전한 실험실(Sandbox) 역할을 수행한다.
*   **`agent/` (Simulation Engine)**:
    *   VLM(Vision-Language Model) 기반의 자율 브라우저 에이전트.
    *   Playwright를 사용하여 실제 사람처럼 보고(Vision), 판단하고(LLM), 행동(Action)한다.
*   **`search-dashboard/` (Control Plane)**:
    *   React 기반의 시뮬레이션 설정 및 결과 분석 UI.
    *   Mock Data와 실제 시뮬레이션 결과를 하이브리드로 처리한다.
*   **`shared/` (Interface Protocol)**:
    *   컴포넌트 간 데이터 교환을 위한 JSON Schema 및 파일 기반 IPC 규약.

### 4.2 Data Contract & Flow
1.  **Crawl**: 타겟 인플루언서의 데이터를 수집하여 SQLite에 저장 (Best-effort).
2.  **Persona Build**: 수집된 댓글/프로필 데이터에서 팔로워 페르소나(Interests, Tone)를 추출.
3.  **Mirroring**: Local SNS에 인플루언서 계정과 게시물을 복제(Seeding).
4.  **Simulation**: 수집된 페르소나를 에이전트에 주입하여 캠페인 포스트에 반응 유도.
5.  **Evaluation**: 시뮬레이션 된 반응(Metric)을 실제 과거 데이터(Baseline)와 비교 평가.

## 5. Requirement Specifications

### 5.1 Instagram Data as Ground Truth
Instagram 데이터는 단순한 참고용이 아닌 시스템의 필수 요소이다.
*   **Matching Features**: 캡션, 해시태그 등은 LLM이 Fit을 판단하는 핵심 근거가 된다.
*   **Calibration Anchor**: 시뮬레이션 된 좋아요/댓글 수가 실제 데이터와 얼마나 유사한지가 모델의 성능 지표가 된다.
*   **Fallback Strategy**: Tier 1 데이터 부재 시, 시뮬레이션은 "Uncalibrated Mode"로 동작하며 이는 명시적으로 라벨링된다.

### 5.2 Proxy Metrics for Success
실제 구매 전환(Conversion) 데이터는 확보가 불가능하므로, **Engagement(참여도)**를 대리 지표(Proxy Metric)로 사용한다.
*   가정: "높은 Engagement는 높은 마케팅 성과와 양의 상관관계를 가진다."
*   평가: 절대적 수치보다는 **Historical Engagement Rate** 대비 변화량을 중요하게 본다.

### 5.3 Hackathon Constraints
*   **Local-First**: 모든 컴포넌트는 로컬 머신(MacBook Pro 등) 내에서 실행 가능해야 한다.
*   **Speed over Security**: `777` 권한, 하드코딩된 비밀번호 등은 허용된다.
*   **Manual Pipeline**: 크롤링 등 일부 프로세스는 자동화되지 않아도 무방하다(Manual Trigger).

## 6. Directory Map

```
.
├── agent/              # [Core] Python-based Simulation Engine
├── docs/               # [Doc] Detailed Specifications & Guides
├── insta-crawler/      # [Data] Instagram Scraper
├── search-dashboard/   # [UI] React Web Application
├── shared/             # [Protocol] Shared Schemas
└── sns/                # [Env] Dockerized Pixelfed
```

---

---

## 7. Alignment with Hackathon Criteria

본 프로젝트는 해커톤 심사 기준을 충실히 반영하여 설계되었다.

### 7.1 B2B/Enterprise Value (시장성 & ROI)
*   **Pain Point**: "100만 원 집행 전까지는 결과를 모른다"는 마케터의 불안감 해소.
*   **Utility**: 실제 예산 집행 전 가상 시뮬레이션을 통한 **ROI 사전 검증** 및 리스크 매니지먼트.
*   **Target**: 광고 대행사(Agency) 및 인하우스 마케팅 팀.

### 7.2 Multi-Agent Architecture (기술적 깊이)
*   **Collaborative Interaction (Stigmergy)**: 에이전트들이 직접 통신하지 않고, SNS 게시물과 댓글을 매개로 서로의 행동에 영향을 주는 **환경 기반 협업** 구조.
    *   *Agent A가 댓글을 달면 -> Agent B가 이를 보고 '좋아요'를 누르거나 대댓글을 다는 Viral Loop 구현.*
*   **Orchestration**: 단일 제어기가 아닌 50+ 에이전트의 독립적 의사결정 프로세스 관리.

### 7.3 Completeness & Observability (완성도)
*   **Observability**: 대시보드를 통해 실시간 진행률, 에이전트별 로그, 스크린샷 캡처를 투명하게 시각화.
*   **Resiliency**: 개별 에이전트/브라우저 실패가 전체 시뮬레이션을 중단시키지 않는 **Fault-Tolerant** 설계.
*   **Optimization**: Headless Browser 리소스 관리 및 VLM 토큰 최적화 적용.

### 7.4 Safety & Ethics (가산점)
*   **Sandbox Isolation**: 실제 인스타그램이 아닌 **격리된 Local SNS(Pixelfed)**에서 수행되므로, 브랜드 이미지 손상이나 플랫폼 어뷰징 리스크가 0%.
*   **No PII Leakage**: 수집된 데이터는 로컬에서만 활용되며 외부로 유출되지 않음.
