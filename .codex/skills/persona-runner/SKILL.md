---
name: persona-runner
description: 멀티 페르소나 에이전트 실행 및 Stigmergy 협업 구현. 여러 페르소나가 순차적으로 실행되며 이전 에이전트의 행동이 다음에 영향을 주는 구조를 구현할 때 사용.
---

# Persona Runner Skill

## Overview

3~5개의 다양한 페르소나 에이전트를 순차 실행하고, **Stigmergy(환경 기반 협업)** 패턴을 구현합니다.

## Core Concept: Stigmergy

```
Agent A 댓글 작성
      │
      ▼
  [SNS 환경]  ◀─── 이전 댓글이 Context에 포함
      │
      ▼
Agent B가 A의 댓글 보고 반응
      │
      ▼
  [SNS 환경]
      │
      ▼
Agent C가 A+B 댓글 보고 최종 결정
```

## Implementation

### Main Runner Script

```python
# agent/persona_runner.py
import json
from datetime import datetime
from typing import List, Dict
import asyncio

# 페르소나 정의
PERSONAS = [
    {
        "id": "vegan_mom",
        "name": "비건맘",
        "age": "35-44",
        "interests": ["동물복지", "환경", "건강식품", "육아"],
        "tone": "긍정적, 지지적, 공감적",
        "values": ["동물권", "환경보호", "가족건강"],
        "reaction_tendency": "supportive"
    },
    {
        "id": "beauty_expert",
        "name": "뷰티덕후",
        "age": "25-34",
        "interests": ["화장품", "스킨케어", "성분분석", "리뷰"],
        "tone": "분석적, 질문형, 꼼꼼함",
        "values": ["제품 효능", "성분 안전성", "가성비"],
        "reaction_tendency": "questioning"
    },
    {
        "id": "cynical_mz",
        "name": "냉소적MZ",
        "age": "18-24",
        "interests": ["밈", "유머", "진정성", "트렌드"],
        "tone": "냉소적, 비판적, 위트있음",
        "values": ["진정성", "반광고", "자기표현"],
        "reaction_tendency": "skeptical"
    }
]


def build_system_prompt(persona: Dict, previous_comments: List[str]) -> str:
    """페르소나와 이전 댓글을 반영한 시스템 프롬프트 생성"""
    
    context = ""
    if previous_comments:
        context = f"""
## Previous Comments on This Post
{chr(10).join([f"- {c}" for c in previous_comments])}

Consider these existing comments when forming your reaction.
"""
    
    return f"""You are a social media user with the following persona:

## Profile
- Name: {persona['name']}
- Age Group: {persona['age']}
- Interests: {', '.join(persona['interests'])}
- Communication Tone: {persona['tone']}
- Core Values: {', '.join(persona['values'])}

{context}

## Task
Look at the social media post and provide your authentic reaction.
Your response should reflect your persona's values and communication style.

Respond in this JSON format:
{{
    "internal_thought": "Your internal thinking process (Chain of Thought)",
    "reaction": "positive" | "neutral" | "negative",
    "action": "like" | "comment" | "skip",
    "comment_text": "Your comment if action is 'comment', else null",
    "reasoning": "Brief explanation of your decision"
}}
"""


async def run_persona_simulation(
    post_description: str,
    personas: List[Dict] = PERSONAS
) -> Dict:
    """멀티 페르소나 시뮬레이션 실행"""
    
    from openai import OpenAI
    client = OpenAI()
    
    results = []
    previous_comments = []  # Stigmergy: 이전 댓글 축적
    
    for persona in personas:
        print(f"\n🎭 Running persona: {persona['name']}")
        
        # 시스템 프롬프트 생성 (이전 댓글 포함)
        system_prompt = build_system_prompt(persona, previous_comments)
        
        # VLM 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Post content: {post_description}"}
            ],
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        # 결과 파싱
        decision = json.loads(response.choices[0].message.content)
        decision["persona_id"] = persona["id"]
        decision["persona_name"] = persona["name"]
        
        results.append(decision)
        print(f"   → Reaction: {decision['reaction']}, Action: {decision['action']}")
        
        # Stigmergy: 댓글이 있으면 다음 에이전트 Context에 추가
        if decision.get("comment_text"):
            previous_comments.append(
                f"[{persona['name']}]: {decision['comment_text']}"
            )
    
    # 메트릭 계산
    metrics = calculate_metrics(results)
    
    # 결과 저장
    simulation_result = {
        "simulationId": f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "status": "completed",
        "createdAt": datetime.now().isoformat(),
        "config": {
            "post_description": post_description,
            "agent_count": len(personas)
        },
        "agents": results,
        "metrics": metrics,
        "stigmergy_trace": previous_comments
    }
    
    # JSON 파일로 저장
    output_path = f"../shared/simulation/{simulation_result['simulationId']}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(simulation_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Simulation complete: {output_path}")
    return simulation_result


def calculate_metrics(results: List[Dict]) -> Dict:
    """시뮬레이션 메트릭 계산"""
    
    total = len(results)
    reactions = {"positive": 0, "neutral": 0, "negative": 0}
    actions = {"like": 0, "comment": 0, "skip": 0}
    
    for r in results:
        reactions[r.get("reaction", "neutral")] += 1
        actions[r.get("action", "skip")] += 1
    
    return {
        "total_agents": total,
        "reactions": reactions,
        "actions": actions,
        "positive_rate": reactions["positive"] / total,
        "engagement_rate": (actions["like"] + actions["comment"]) / total,
        "sentiment_score": (reactions["positive"] - reactions["negative"]) / total
    }


# 실행 예시
if __name__ == "__main__":
    post = """
    [Skincare Brand Ad]
    "순수 비건 원료로 만든 프리미엄 스킨케어 라인 출시!
    동물실험 없이, 자연에서 온 성분만을 담았습니다.
    #비건뷰티 #크루얼티프리 #스킨케어"
    """
    
    asyncio.run(run_persona_simulation(post))
```

## Persona Design Guidelines

### 다양성 확보하기

| 축 | 옵션 |
|---|------|
| **반응 성향** | 긍정 / 중립 / 부정 |
| **연령대** | Z세대 / 밀레니얼 / X세대 |
| **관심사** | 환경 / 가격 / 품질 / 트렌드 |
| **소통 스타일** | 지지적 / 분석적 / 비판적 |

### 예시: 5-Persona Set

```python
EXPANDED_PERSONAS = [
    {"id": "enthusiast", "tendency": "positive", "comment_prob": 0.8},
    {"id": "analyst", "tendency": "neutral", "comment_prob": 0.5},
    {"id": "skeptic", "tendency": "negative", "comment_prob": 0.6},
    {"id": "lurker", "tendency": "neutral", "comment_prob": 0.1},
    {"id": "influencer", "tendency": "positive", "comment_prob": 0.9},
]
```

## Stigmergy Demonstration

### 발표 시 어필 포인트

> "첫 번째 에이전트가 '동물실험 안 하는 거 맞죠?'라고 물으면,
> 두 번째 에이전트는 이 질문을 보고 '성분표도 공개해주세요'라고 추가 질문합니다.
> 세 번째 에이전트는 앞선 질문들을 보고 '광고인데 왜 이렇게 질문이 많지... 의심스럽네'라고 반응합니다.
> 
> 이것이 **Stigmergy**: 에이전트들이 직접 통신하지 않고 **환경(댓글)을 통해 서로 영향**을 주는 협업 패턴입니다."

## Output Example

```json
{
  "simulationId": "sim_20260120_143052",
  "status": "completed",
  "agents": [
    {
      "persona_name": "비건맘",
      "reaction": "positive",
      "action": "comment",
      "comment_text": "너무 좋아요! 동물실험 없는 제품 찾고 있었어요 💚",
      "internal_thought": "비건 가치관에 딱 맞는 제품이다..."
    },
    {
      "persona_name": "뷰티덕후",
      "reaction": "neutral", 
      "action": "comment",
      "comment_text": "성분표 전체 공개 가능한가요? 알러지 성분 체크하고 싶어요",
      "internal_thought": "비건이라고 다 좋은 건 아니지... 성분 확인 필요"
    },
    {
      "persona_name": "냉소적MZ",
      "reaction": "negative",
      "action": "skip",
      "comment_text": null,
      "internal_thought": "또 비건 마케팅... 그린워싱 아닌지 모르겠다"
    }
  ],
  "metrics": {
    "positive_rate": 0.33,
    "engagement_rate": 0.67,
    "sentiment_score": 0.0
  },
  "stigmergy_trace": [
    "[비건맘]: 너무 좋아요! 동물실험 없는 제품 찾고 있었어요 💚",
    "[뷰티덕후]: 성분표 전체 공개 가능한가요? 알러지 성분 체크하고 싶어요"
  ]
}
```

## Success Criteria

- [ ] 3개 이상 페르소나 순차 실행
- [ ] 이전 댓글이 다음 에이전트 Context에 포함됨 (Stigmergy)
- [ ] Chain-of-Thought 로깅 (internal_thought)
- [ ] `shared/simulation/` 에 결과 JSON 저장
- [ ] 긍정/중립/부정 비율 메트릭 계산
