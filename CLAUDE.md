# AGENTS.md

> **해커톤 AI 협업 가이드**
>
> 이 문서는 해커톤 기간 동안 팀원들이 AI 에이전트에게 프로젝트 협업과 코딩 작업을 맡길 때 사용하는 에이전트 인스트럭션 가이드입니다.

## 프로젝트 개요

로컬 우선 다중 에이전트 오케스트레이터로, 실제 Instagram 참여 데이터를 기준으로 인플루언서 캠페인을 시뮬레이션하고, 결과를 검색 + 시뮬레이션 대시보드에 표시합니다.

### 데모할 기능 (Product Story)
1. 회사가 원하는 결과를 자연어로 설명 (목표, 타겟, 지역, 톤, 예산).
2. 시스템이 적합한 인플루언서를 추천하고 적합성 이유를 설명.
3. 각 후보 인플루언서에 대해 로컬 SNS에서 팔로워 행동 시뮬레이션 실행.
4. 참여 기반 프록시 메트릭(좋아요/댓글/팔로우)으로 후보를 점수화하고 대표 페르소나 추적 표시.

이는 명시적으로 "폐루프" 시스템입니다: **데이터 → 페르소나 → 시뮬레이션 → 메트릭 → 순위 + 설명**.

## 이 가이드의 범위

- 이는 **루트 레벨, 프로젝트 전체 가이드**입니다.
- 컴포넌트 디렉토리 내에서 작업할 때는 해당 로컬 `AGENTS.md`를 읽고 따르십시오. 컴포넌트 가이드가 해당 범위에서 이 파일을 재정의합니다.

## 컴포넌트 및 역할

| 디렉토리 | 역할 | 기술 스택 |
|-----------|------|------------|
| `sns/` | 로컬 SNS 플랫폼 (시뮬레이션 스테이지) | Pixelfed, Docker, MySQL, Redis |
| `agent/` | 페르소나 기반 브라우저 에이전트 | Python, Playwright, OpenAI Computer Use API |
| `search-dashboard/` | 검색 + 시뮬레이션 UI | React, TypeScript, Vite |
| `insta-crawler/` | Instagram 크롤러 + 데이터셋 도구 | Python, Playwright, SQLite |
| `shared/` | 파일 기반 교환 (스키마, 시뮬레이션 결과) | JSON Schema |
| `context/` | 연구 노트 (참조 전용) | Markdown |

## 계약 경계 (데이터 흐름)

### Instagram 수집 (Source of Truth)
- `insta-crawler/`는 SQLite에 데이터를 저장합니다 (속도 제한으로 인해 최선의 노력).
- 다운스트림 컴포넌트는 최소 계약(아래 데이터 요구사항 참조)을 읽습니다.

### 시뮬레이션 출력 (에이전트 → 대시보드)
- `agent/`는 `shared/simulation/{simulationId}.json`에 `shared/simulation-schema.json`을 따르는 파일을 작성합니다.
- 대시보드는 공유 폴더를 폴링하여 시뮬레이션 출력을 읽습니다 (`shared/README.md` 참조).

## Instagram 데이터 요구사항

Instagram 데이터는 다음에 **필요합니다**:
- **매칭 기능**: 인플루언서 바이오 + 게시물 캡션/해시태그 적합성 증거.
- **교정 기준선**: 게시물별 좋아요/댓글 수가 시뮬레이션된 메트릭의 앵커.
- **평가**: 시뮬레이션된 참여도와 과거 참여도 비교.
- **페르소나 현실감 (Tier 2+)**: 댓글 + 댓글 작성자 프로필이 근거 있는 팔로워 페르소나 제공.

### 데이터 커버리지 티어

| 티어 | 내용 | 상태 |
|------|----------|--------|
| **Tier 1** (최소) | 인플루언서 프로필 + 게시물 + 게시물별 좋아요/댓글 수 | 교정된 데모 필수 |
| **Tier 2** (목표) | Tier 1 + 샘플 댓글 + 댓글 작성자 프로필 | 스트레치 목표 |
| **Tier 3** (좋음) | Tier 2 + 팔로워/팔로우 엣지 + 게시물 좋아요 사용자 | 선택사항 |

### 최소 데이터 계약 (MVP)

```
Influencer: username, biography, followers (optional), is_private (optional), fetched_at
Post: shortcode/url, user_username, taken_at, caption, caption_hashtags, like_count, comment_count, fetched_at
Comment (Tier 2+): comment_id, shortcode, owner_username, created_at, text, fetched_at
```

### 누락 데이터 처리
- `insta-crawler/` 출력을 부분적으로 관찰 가능한 것으로 처리; 누락된 테이블/행은 예상됩니다.
- 댓글/엣지가 누락된 경우, 템플릿 + 인플루언서 콘텐츠 기능에서 팔로워 페르소나를 생성합니다.
- 폴백 데이터를 사용할 때 출력을 낮은 신뢰도로 표시합니다.

## 엔드 투 엔드 흐름

1. 인플루언서 시드 및 참여 신호에 대한 일회성 Instagram 크롤 실행.
2. 크롤링된 데이터에서 인플루언서 + 팔로워 페르소나/코호트 구축 (Tier 2 데이터가 누락된 경우에만 폴백 템플릿 허용).
3. 인플루언서 및 기존 게시물을 로컬 SNS(`sns/`)로 미러링.
4. 회사 쿼리의 경우, 후보 인플루언서를 선택하고 캠페인 시뮬레이션 구성.
5. 페르소나 기반 팔로워 에이전트(`agent/`)를 실행하여 Pixelfed에서 반응 시뮬레이션.
6. 로그 및 메트릭 집계, 과거 참여 데이터와 비교 (Tier 1+).
7. 대시보드(`search-dashboard/`)에서 검색, 시뮬레이션, 보고 흐름 표시.

---

## 컴포넌트별 가이드

### SNS (`sns/`)

Pixelfed(Laravel 기반 ActivityPub 사진 공유 플랫폼) 로컬 개발 환경입니다. Docker Compose로 애플리케이션, MySQL 데이터베이스, Redis 캐시, 백그라운드 워커를 조율합니다.

#### 해커톤 모드: 속도 우선

**우선순위**: 기능 가용성 > 보안 / 모범 사례
- **보안**: API 키, 하드코딩된 비밀번호(`password`), `777` 권한에 대한 경고 무시. 의도적인 것입니다.
- **데이터 무결성**: 표준 API가 실패할 경우 "더티" DB 주입이 허용됩니다.
- **목표**: AI 에이전트를 위한 즉시 재생 가능한 샌드박스 제공

#### 디렉토리 구조 및 핵심 파일

- **`pixelfed/`**: 메인 프로젝트 디렉토리
  - **`.env`**: 환경변수의 단일 진실의 원천. 중요: 이를 수정하면 컨테이너를 다시 생성해야 합니다 (`docker-compose up -d --force-recreate`).
  - **`docker-compose.yml`**: 인프라 정의. 현재 포트: **8092**
  - **`artisan`**: Laravel CLI 진입점 (호스트에서 직접 실행 금지; 컨테이너 내에서 실행)
  - **`seed_hackathon.php`** (계획): 빠른 데이터 채우기 스크립트

#### 운영 가이드라인

**실행 환경**
- 호스트 머신에서 `php` 또는 `composer` 명령을 직접 실행하지 마십시오.
- 애플리케이션 명령은 항상 `pixelfed-app` 컨테이너 내에서 실행하십시오.

```bash
docker exec pixelfed-app php artisan <command>
```

**시뮬레이션 데이터 관리**
에이전트용 스테이지 재설정 및 준비:
1. DB 삭제: `docker exec pixelfed-app php artisan migrate:fresh`
2. 데이터 시드: 해커톤 스크립트를 tinker로 파이프
   ```bash
   cat seed_hackathon.php | docker exec -i pixelfed-app php artisan tinker
   ```
   (에이전트, 인플루언서, 더미 게시물 생성)

**트러블슈팅**
- **404 에러**: `.env`의 `APP_DOMAIN` 불일치 또는 오래된 라우트 캐시로 인한 경우가 많음
  - 해결: `APP_DOMAIN=localhost` 확인 후 `php artisan route:clear` 실행
- **500 에러**: `storage/logs/laravel.log` 확인
- **환경 변경**: `.env` 변경에 `docker-compose restart`는 충분하지 않습니다. `docker-compose up -d --force-recreate` 사용

**빠른 참조**
- 앱 URL: `https://localhost:8092`
- 컨테이너 이름: `pixelfed-app`
- 기본 비밀번호: `password`
- 에이전트 계정: `agent1`, `agent2`...
- 인플루언서 계정: `influencer1`...

---

### Agent (`agent/`)

컴퓨터 사용 에이전트 시스템을 구축하여 현실적인 페르소나를 기반으로 100명 이상의 사용자가 로컬 SNS와 상호작용하도록 시뮬레이션합니다. 각 에이전트는 자율적으로 탐색, 게시, 좋아요, 댓글, 팔로우를 수행합니다.

#### 개발 스택

**언어**: Python + **`uv` CLI** 종속성 관리
- 모든 종속성 관리는 `uv` 명령만 사용합니다 (pip, poetry, venv 금지)
- 프로젝트 초기화: `uv init`
- 종속성 추가: `uv add playwright openai`
- 스크립트 실행: `uv run python script.py`
- 참고: https://docs.astral.sh/uv/

#### 브라우저 자동화 전략

**제약사항**: 100개 이상의 브라우저를 로컬에서 실행하면 상당한 리소스 오버헤드가 발생합니다. 효율성 최적화가 필요합니다.

**해결책**: 스마트 컨텍스트 주입과 헤드리스 브라우저 자동화 사용:
- Playwright for Python (`playwright`) - 헤드리스 모드 기본
- agent-browser: CLI 기반 스냅샷 옵션 (대화형 요소만, 컴팩트 모드)으로 에이전트 작업당 컨텍스트 오버헤드 최소화
- agent-browse: Playwright 대신 CDP(Chrome DevTools Protocol) 사용하여 더 가벼운 풋프린트

**컨텍스트 최적화**: 전통적인 브라우저 자동화와 달리 각 에이전트 작업에 필요한 최소 정보만 주입합니다.

#### 구현 단계

**1단계: 환경 설정**
- `uv init`으로 Python 프로젝트 초기화
- `uv add playwright openai`로 종속성 추가
- `uv run playwright install chromium`으로 Playwright 브라우저 설치
- 로컬 SNS 서버 통합 설정
- 헤드리스 브라우저 인프라 구성
- 에이전트 오케스트레이션 프레임워크 설정 (생성, 모니터링, 리소스 관리)

**2단계: 단일 에이전트 프로토타입**
- 페르소나 기반 에이전트 구현:
  - 인증
  - 페르소나 관련 상호작용으로 피드 탐색
  - 관심사 기반 콘텐츠 게시
  - 참여 작업 (좋아요, 댓글, 팔로우)
- 컨텍스트 최적화 전략 검증

**3단계: 다중 에이전트 시뮬레이션**
- 100개 이상의 동시 에이전트로 확장
- 리소스 풀링 및 브라우저 세션 관리 구현
- 현실적인 소셜 그래프 패턴 생성을 위한 에이전트 조정
- 시스템 리소스 사용량 모니터링 및 최적화

**4단계: 통합 및 검증**
- 페르소나 생성기와 연결하여 현실적인 에이전트 프로필
- 실제 사용자 행동 패턴과 시뮬레이션 출력 비교 검증
- 쇼케이스 및 평가 모듈용 시뮬레이션 데이터 내보내기

#### 핵심 설계 원칙

1. **리소스 효율성**: 헤드리스 모드와 스마트 컨텍스트 관리로 에이전트당 메모리/CPU 최소화
2. **페르소나 충실도**: 에이전트 작업은 페르소나 특성을 일관되게 반영해야 함
3. **현실적인 타이밍**: 인간 같은 지연과 활동 패턴 도입 (봇 같은 동시성 회피)
4. **확장성**: 10개에서 1000개 이상의 에이전트로 확장 가능한 아키텍처
5. **관찰 가능성**: 분석 및 디버깅을 위한 에이전트 작업 로깅
6. **격리**: 각 에이전트는 독립적으로 작동; 실패가 연쇄되지 않음

#### 성공 기준

- 로컬 머신에서 100개 이상의 에이전트가 동시 실행
- SNS 데이터에서 다양하고 페르소나 기반 상호작용 패턴 관찰 가능
- 확장된 시뮬레이션 실행에 대한 시스템 리소스 사용량 지속 가능
- 생성된 소셜 그래프가 현실적인 속성(거듭제곱 분포, 클러스터링 등) 표시
- 에이전트 행동이 페르소나 정의와 일치

#### 통합 지점

- **입력**: 페르소나 생성기 모듈의 페르소나 정의
- **대상**: 로컬 SNS 서버 (인증, 탐색, 게시, 참여)
- **출력**: 평가 및 쇼케이스용 상호작용 로그 및 소셜 그래프 데이터
- **조정**: 페르소나 현실적인 콘텐츠 선호도를 알리기 위한 크롤러 데이터와 동기화

---

### Search Dashboard (`search-dashboard/`)

자연어/관심사 쿼리에서 관련 인플루언서를 찾고 가상 인플루언서 마케팅 시뮬레이션을 실행하여 캠페인 성과를 추정하는 검색 + 시뮬레이션 대시보드 프론트엔드를 구축합니다.

#### 기술 스택 (구현됨)

| 카테고리 | 기술 | 참고 |
|----------|------------|-------|
| 프레임워크 | React 18 + TypeScript | 유지보수를 위한 엄격한 타이핑 |
| 빌드 도구 | Vite 5 | 빠른 HMR, 최적화된 빌드 |
| 애니메이션 | motion (Framer Motion) | 선언적 애니메이션 |
| 스타일링 | 커스텀 CSS | CSS 변수, 프레임워크 없음 |
| 폰트 | Fraunces + Space Grotesk | Google Fonts |

#### 애니메이션 컴포넌트 (react-bits 기반)

```
src/components/animations/
├── CountUp.tsx         # 숫자 카운팅 애니메이션 (motion/react)
├── ShinyText.tsx       # 반짝이는 텍스트 효과 (CSS)
├── SpotlightCard.tsx   # 마우스 추적 스포트라이트 (CSS + JS)
├── AnimatedCard.tsx    # 호버 애니메이션 카드 (motion/react)
├── GlowingButton.tsx   # 글로우 효과 버튼 (CSS + motion)
├── AnimatedProgress.tsx # 애니메이션 프로그래스 바 (motion/react)
└── PulseIndicator.tsx  # 펄스 상태 표시 (motion/react)
```

#### 이 디렉토리의 범위

- 검색 경험 (자연어 + 태그)
- 인플루언서 발견 및 비교
- 시뮬레이션 구성 및 실행 UI
- 결과/보고 뷰
- 시스템 상태 및 데이터 신선도 패널

#### 핵심 기능 (MVP)

**검색 및 추천**
- 자연어 쿼리 입력 + 태그 칩
- 필터: 플랫폼, 카테고리, 지역, 팔로워 범위, 가격 범위
- 정렬: 관련성, 참여도, 도달범위, 예상 전환
- 빠른 작업(저장, 비교, 시뮬레이션)이 포함된 결과 목록

**인플루언서 상세**
- 프로필 요약, 핵심 메트릭, 최근 콘텐츠 하이라이트
- 오디언스 분석 (연령/성별/위치)
- 이전 캠페인 성과 (제공되는 경우)

**시뮬레이션**
- 입력: 목표/KPI, 예산, 기간, 타겟 페르소나, 메시지 톤
- 진행률 + 재시도와 함께 비동기 실행
- 결과: 도달범위, 참여도, CTR, 전환, ROAS + 불확실성 수준

**보고 및 비교**
- 3-5개 인플루언서 나란히 비교
- KPI 차트 및 요약 카드
- 내보내기: CSV 및 가벼운 PDF 요약

**시스템 상태**
- 데이터 신선도 표시기 (크롤러/시뮬레이터)
- 모델 버전 및 상태

#### 구현 고려사항

**애니메이션 모범 사례**

1. **motion/react로 복잡한 애니메이션 사용**
   ```tsx
   import { motion, AnimatePresence } from 'motion/react';

   <AnimatePresence mode="wait">
     <motion.div
       key={uniqueKey}
       initial={{ opacity: 0, y: 20 }}
       animate={{ opacity: 1, y: 0 }}
       exit={{ opacity: 0, y: -20 }}
     >
       ...
     </motion.div>
   </AnimatePresence>
   ```

2. **단순 호버 효과에는 CSS 사용**
   ```css
   .card {
     transition: transform 0.3s ease, box-shadow 0.3s ease;
   }
   .card:hover {
     transform: translateY(-2px);
     box-shadow: 0 12px 40px rgba(27, 31, 29, 0.15);
   }
   ```

3. **성능 최적화**
   - GPU 가속 힌트용 `will-change`는 드물게 사용
   - 애니메이션에는 `transform`과 `opacity` 선호 (GPU 가속)
   - 마운트/마운트 해제 애니메이션에 `AnimatePresence` 사용
   - 가능하면 레이아웃 속성(`width`, `height`) 애니메이션 회피

**상태 관리**

`App.tsx`의 중앙 상태와 프롭 드릴링. 향후 확장을 위해:
- 복잡한 상태에 Zustand 또는 Jotai 고려
- 시뮬레이션 상태는 디버깅을 위해 격리 유지

**컴포넌트 가이드라인**

1. `src/components/animations/`의 애니메이션 컴포넌트는 재사용 가능한 빌딩 블록
2. 패널 컴포넌트는 애니메이션과 비즈니스 로직을 구성
3. 파일 중심 유지: 파일당 하나의 컴포넌트, 최대 ~200줄
4. 접근성을 위해 시맨틱 HTML 사용

**스타일링 규칙**

```css
/* CSS 변수 이름 */
--accent-mint: #62f0d1;    /* 기본 성공 색상 */
--accent-amber: #f5c26b;   /* 경고/주의 색상 */
--accent-rose: #f08b75;    /* 오류 색상 */

/* 애니메이션 타이밍 */
transition: transform 0.2s ease, box-shadow 0.2s ease;

/* 일관된 그림자 */
box-shadow: 0 20px 50px rgba(27, 31, 29, 0.12);
```

#### 통합 지점 (가정된 API)

- `POST /api/search` -> `{ results, explanation }`
- `GET /api/influencers/:id` -> `{ influencer, history, audience }`
- `POST /api/simulations` -> `{ job_id }`
- `GET /api/simulations/:job_id` -> `{ status, progress, result? }`
- `GET /api/system/status` -> `{ crawler_last_sync, simulator_version, data_health }`

#### UX/비기능 요구사항

- 밀도 높은 데이터 화면을 위한 명확한 정보 계층
- 모든 비동기 패널에 로딩/빈/오류 상태
- 캐싱으로 첫 번째 검색 결과 ~3초 이내
- 핵심 뷰(검색/결과/보고)의 모바일 안전 레이아웃
- 시뮬레이션된 메트릭의 불확실성/신뢰도 표시
- 애니메이션은 데이터 이해를 방해하지 않도록 향상

#### 성공 기준

- 종단 간 흐름: 검색 -> 선택 -> 시뮬레이션 -> 보고
- 현실적인 데이터 밀도와 명확한 비교가 있는 안정적인 UI
- 백엔드 엔드포인트가 확정되면 쉽게 확장 가능
- 해커톤 데모에서 "역동적이고 기능적인" 인상을 만드는 애니메이션

#### 새 애니메이션 컴포넌트 추가

react-bits에서 새 컴포넌트를 추가할 때:

1. 종속성 확인: motion/react로 충분한지 확인, 불필요한 경우 gsap 추가 회피
2. `/animations/`에서 생성: 애니메이션 로직과 비즈니스 로직 분리
3. index.ts에서 내보내기: 배럴 내보내기 업데이트
4. 필요한 경우 CSS 파일 추가: BEM과 유사한 이름 사용 (`.component-name__element--modifier`)
5. 호버 상태 테스트: macOS 트랙패드와 마우스가 모두 원활하게 작동해야 함

#### 알려진 제한사항

- 시뮬레이션은 모의 전용; 실제 에이전트 오케스트레이션 없음
- 단일 시뮬레이션 모드 (병렬 실행 없음)
- 영구 저장 없음; 새로고침하면 상태 손실
- 카드가 많은 저사양 기기에서 애니메이션 성능 저하 가능

#### 향후 개선 사항

- [ ] 백엔드 API 통합
- [ ] 다중 시뮬레이션 비교
- [ ] WebSocket을 통한 실시간 시뮬레이션 진행률
- [ ] 내보내기 기능 (CSV, PDF)
- [ ] 다크 모드 테마
- [ ] 접근성을 위한 감소된 동작 지원

---

### Instagram Crawler (`insta-crawler/`)

Instagram에서 인플루언서/팔로워 데이터를 수집하는 크롤러와 데이터셋 도구입니다.

#### 프로젝트 요구사항

- Python 종속성 관리에 `uv` 사용 (pip 또는 순진한 python 금지)

#### 문서화

- 각 CLI에 대한 최신 문서 작성

#### 검증

- 변경 사항이 대상 문제를 해결하는지 항상 확인합니다. 필요한 경우 테스트 코드 작성
- 검증이 완료될 때까지 계속 작업

---

## 시뮬레이션 세부사항

### 시뮬레이션되는 것
- 인플루언서는 기존 게시물을 가지며 로컬 SNS에 캠페인 콘텐츠를 게시합니다.
- 팔로워는 Instagram 데이터(Tier 2+) 또는 폴백 템플릿(Tier 1 전용)에서 파생된 페르소나로 표현됩니다.
- 각 페르소나는 현실적인 타이밍으로 탐색, 좋아요, 댓글, 팔로우를 수행하는 컴퓨터 사용 에이전트를 구동합니다.
- 에이전트는 행동을 일관되게 유지하기 위해 최근 작업 내역과 관련 컨텍스트(현재 페이지뿐만 아니라)를 받습니다.

### 프록시 메트릭으로서의 참여도
- 실제 결과(클릭/구매)는 범위 밖; 참여 신호(좋아요, 댓글, 팔로우)를 기본 평가 프록시로 사용합니다.
- 가정: 더 높은 참여도는 더 높은 마케팅 성과와 상관관계가 있습니다.

### 평가 논리 (티어 인식)
- Tier 1+: 시뮬레이션된 참여도를 과거 Instagram 참여도와 비교합니다.
- 규모로만 순위를 매기는 것을 피하기 위해 정규화된 메트릭(예: 게시물별 참여율)을 선호합니다.
- 커버리지(Tier 1 vs Tier 2/3)를 기반으로 항상 신뢰도 라벨을 부착합니다.

### 비용 및 확장
- 각 에이전트 작업에는 비용(모델 호출 + 컴퓨팅)이 있으며, 시뮬레이션에는 작업별 가격 책정 및 예산 캡이 포함되어야 합니다.
- 로컬에서 헤드리스 브라우징을 선호합니다; 서버리스 브라우저는 피합니다(로컬 전용 SNS 액세스 필요).
- 전체 규모 실행은 리소스 제한으로 인해 배칭/스케줄링이 필요할 수 있습니다.

---

## 해커톤 제약 및 원칙

- **속도 우선**: 작동하는 데모가 모범 사례보다 중요합니다; 로컬 전용 배포.
- 필요한 경우 하드코딩된 자격 증명, 약한 비밀번호, 허용적 권한에 대한 경고를 무시합니다.
- 표준 흐름이 진행을 차단할 경우 실용적인 바로가기를 사용하지만, 변경은 포함되고 문서화되도록 유지합니다.
- Instagram 크롤링은 필요하지만 자동화된 파이프라인은 범위 밖입니다(수동/일회 실행 허용).
- 명시적인 계약 및 필요한 곳에 모의(mock)를 사용하여 컴포넌트를 느슨하게 결합합니다.

## 개발 가이드라인

- **서브모듈 확인 (중요)**: 작업을 시작하기 전에 git 서브모듈이 초기화되었는지 확인하십시오. `search-dashboard/react-bits` 또는 `search-dashboard/shadcn-ui`가 비어 있으면 `git submodule update --init --recursive`를 실행합니다.
- **서브모듈 일괄 업데이트**: 모든 서브모듈을 최신 상태로 맞추려면 `git submodule sync --recursive && git submodule update --init --recursive --remote`를 실행합니다.
- 컴포넌트별 기존 스택 및 도구를 따르십시오(README, package.json, pyproject, docker-compose 확인).
- 변경 사항을 작고 집중적으로 유지합니다; 필요한 경우가 아니면 컴포넌트 간 결합을 피합니다.
- 컴포넌트 간 명시적인 데이터 계약으로 타이핑된 인터페이스를 선호합니다.
- 백엔드 종속성을 사용할 수 없을 때 모의 또는 픽스처를 사용합니다.
- 종속성을 가볍게 유지합니다; 새 종속성은 노트 또는 PR에서 간단히 정당화합니다.
- Python 프로젝트: `uv` CLI를 사용하여 종속성을 관리합니다(pip, poetry, venv가 아님).

## 성공 기준 (해커톤)

- 로컬 SNS가 실행 중이고 접근 가능합니다.
- 에이전트가 인증하고 현실적인 작업을 수행할 수 있습니다.
- 대시보드가 `shared/simulation/*.json`을 사용하여 검색 → 시뮬레이션 → 보고 흐름을 종단 간으로 보여줍니다.
- 교정 모드: 최소 Tier 1 Instagram 데이터셋이 수집되고 로드됩니다(Tier 2+는 스트레치 목표).

## 알려진 간격 및 열린 질문

- 페르소나 빌더 품질 및 평가 파이프라인은 여전히 탐색 중입니다.
- 리소스 제한은 스케줄링 없이 진정한 100+ 동시 에이전트를 제한할 수 있습니다.
- 인플루언서 매칭(순위)은 아직 종단 간으로 구현되지 않았습니다; 대시보드는 현재 모의 데이터를 사용합니다.

## 참조 문서 (컴포넌트별)

- 루트 개요: `README.md`, `PLANS.md`, `PROJECT_DEFINITION.md`
- 공유 계약: `shared/README.md`, `shared/simulation-schema.json`
- 로컬 SNS 설정: `sns/README.md`, `sns/AGENTS.md`
- 에이전트 시뮬레이션: `agent/README.md`, `agent/AGENTS.md`
- 대시보드 UX: `search-dashboard/README.md`, `search-dashboard/AGENTS.md`
- Instagram 크롤러: `insta-crawler/README.md`, `insta-crawler/PLANS.md`, `insta-crawler/AGENTS.md`
- 이전 노트: `context/subject.md`, `context/simulation.md`, `context/eval.md`

## 참고 사항

- 코드에서 영어 식별자를 사용합니다; UI 텍스트는 현지화할 수 있습니다.
- 이 인스트럭션을 편집하는 경우 AGENTS.md, CLAUDE.md, GEMINI.md를 함께 업데이트합니다.
