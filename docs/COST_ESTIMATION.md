# 💰 Cost Analysis: Cognitive Swarm vs. Visual Swarm

> **전제 조건 (Assumptions)**
> *   **Model**: **GPT-4o** (Current Flagship) vs **GPT-5** (Hypothetical Next-Gen, estimated at 2x GPT-4o launch price).
> *   **Task**: 1개의 캠페인 게시물에 대해 **100명의 팔로워**가 반응을 시뮬레이션하는 시나리오.
> *   **Action**: 게시물 읽기 -> 심리적 추론(Thinking) -> 댓글/좋아요 결정.

## 1. Unit Pricing (OpenAI API Base)

| Model Tier | Type | Input ($/1M tokens) | Output ($/1M tokens) | Vision Cost (High Res) |
|---|---|---|---|---|
| **GPT-4o** | Current High-End | $2.50 | $10.00 | ~$0.0038 / image |
| **GPT-4o-mini** | Cost Efficient | $0.15 | $0.60 | ~$0.0038 / image |
| **GPT-5 (Est.)**| **Next-Gen Frontier** | **$10.00** (Est) | **$30.00** (Est) | **~$0.01** / image |

---

## 2. Comparative Analysis: 100 Agents Situation

우리의 전략(Headless Cognitive Swarm)이 왜 비용 효율적인지 비교합니다.

### Option A: FULL Visual Computer-Use Swarm (100 Agents)
*   **방식**: 100개의 에이전트가 모두 브라우저 스크린샷(Vision)을 찍으며 행동.
*   **Step per Agent**: 평균 10 Step (Login -> Feed Scroll -> Find Post -> Read -> Think -> Comment).
*   **Data Size**: Step당 스크린샷(1,000 tokens) + Context(2,000 tokens) = 3,000 tokens.
*   **Calculation (GPT-4o)**:
    *   Input: 3,000 tokens * 10 steps * 100 agents = 3,000,000 tokens -> **$7.50**
    *   Output: 200 tokens * 10 steps * 100 agents = 200,000 tokens -> **$2.00**
    *   Total: **$9.50 (per 1 Simulation Run)**
*   **Risk**: **GPT-5 적용 시 $40~$50 per run**. (1회 돌리는데 7만 원)

### Option B: Hybrid "Iceberg" Architecture (Our Strategy)
*   **구조**: 
    *   **99 Headless Agents**: Text-only (or 1-time Image) Reasoning.
    *   **1 Visual Agent**: Full Computer Use Showcase.

#### 1. Headless Cost (N=99)
이미지 1번 인지 후, 텍스트로만 사고(Internal Monologue) 진행.
*   **Step**: 1 Step (Read Post -> Think -> Output JSON).
*   **Data Size**: Persona + Post Description (1,000 tokens).
*   **Calculation (GPT-4o)**:
    *   Input: 1,000 tokens * 1 step * 99 agents = 99,000 tokens -> **$0.25**
    *   Output: 300 tokens * 1 step * 99 agents = 29,700 tokens -> **$0.30**
    *   Subtotal: **$0.55**

#### 2. Visual Hero Cost (N=1)
*   **Calculation (GPT-4o)**:
    *   Input: 3,000 tokens * 10 steps * 1 agent = 30,000 tokens -> **$0.075**
    *   Output: 200 tokens * 10 steps * 1 agent = 2,000 tokens -> **$0.02**
    *   Subtotal: **$0.095**

### 🏆 Total Cost (Option B)
*   **Total**: **$0.65 (per 1 Simulation Run)** with GPT-4o.
*   **GPT-5 Estimation**: **~$2.50 (per 1 Simulation Run)**.

---

## 3. Business Implication (ROI)

### 비용 절감 효과 (Cost Reduction)
*   **Option A ($9.50)** vs **Option B ($0.65)**
*   **절감률**: **93% Cost Reduction**.
*   이것은 단순한 비용 절감이 아니라, **서비스의 확장성(Scalability)**을 의미합니다.

### 쿼타(Quota) 및 속도 (Throughput)
*   **Rate Limit**: Visual Agent는 이미지를 전송하므로 Latency가 큽니다(3~5초). 100개를 병렬 처리하면 OpenAI TPM(Token Per Minute) 리밋에 걸립니다.
*   **Throughput**: Option B(Headless)는 텍스트 위주이므로 훨씬 빠르고, 1분 안에 100명의 시뮬레이션을 완료할 수 있습니다.

## 4. Conclusion for Hackathon
> "심사위원님, 저희는 무식하게 브라우저를 띄워서 API 비용을 태우는 길을 택하지 않았습니다.
> **인간의 행동(Movement)은 1명(Visual)으로 검증**하고, **인간의 판단(Decision)은 99명(Headless)으로 확장**하는 아키텍처를 설계했습니다.
> 이를 통해 **GPT-5급 초거대 모델**을 사용하더라도 **1회 시뮬레이션당 $2.5(3천원)** 수준의 경제성을 확보했습니다."

이 논리는 **"현실적인 비즈니스 모델(BM)"**로서의 설득력을 가집니다.
