# Instagram Crawler Specification

본 문서는 실제 인스타그램 데이터를 수집하여 시뮬레이션의 기반 데이터(Ground Truth)를 구축하는 **Instagram Crawler**의 상세 설계 명세서이다.

## 1. System Overview

이 시스템은 특정 **Seed User(초기 인플루언서)**를 기점으로 팔로워/팔로잉 그래프를 탐색하며 프로필, 게시물, 댓글 데이터를 수집한다. 수집된 데이터는 **Simulation Persona Generation**과 **Evaluation Metrics(실제 반응 vs 시뮬레이션 반응 비교)**의 기준점으로 사용된다.

```mermaid
graph TD
    Seed[Seed Usernames] -->|Input| Scheduler[Crawl Scheduler]
    Scheduler -->|Task| Workers[Worker Pool]
    
    subgraph Worker
        Browser[Headless Browser (Playwright)] -->|Login/Cookie| Insta[Instagram.com]
        Insta -->|HTML/XHR| Parser[Data Parser]
        Parser -->|Raw JSON| Buffer[Local Buffer]
    end
    
    Buffer -->|Upsert| DB[(SQLite Database)]
    DB -->|Filters| Assets[Persona Templating]
```

---

## 2. Crawl Strategy

### 2.1 Graph Traversal (BFS)
크롤러는 **너비 우선 탐색(BFS)** 알고리즘을 사용하여 소셜 그래프를 확장한다.

1.  **Level 0 (Seeds)**: 사용자가 입력한 인플루언서 목록.
2.  **Level 1 (Direct Network)**: Seed 사용자의 최근 게시물 댓글 작성자, 태그된 사용자.
3.  **Level 2+ (Context)**: (선택적) Level 1 사용자의 프로필 정보.

### 2.2 Rate Limit Management
Instagram의 공격적인 Anti-Bot 정책을 우회하기 위한 전략적 접근이 필수적이다.

*   **Human Emulation**: 스크롤 속도 랜덤화, 불규칙한 대기 시간(Jitter) 적용.
*   **Session Persistence**: 로그인 쿠키를 파일로 저장하여 재사용 (`cookies.json`).
*   **Fail-Fast & Resume**: 차단 감지 시 즉시 중단하고, 마지막 성공 지점부터 재시작 가능한 체크포인트 시스템.

---

## 3. Data Schema (SQLite)

데이터는 관계형 데이터베이스(SQLite)에 저장되며, 분석 용이성을 위해 정규화된다.

### 3.1 `users`
| Field | Type | Description |
|-------|------|-------------|
| `username` | PK | 고유 사용자 ID |
| `full_name` | TEXT | 표시 이름 |
| `biography` | TEXT | 프로필 소개글 (페르소나 추출 핵심) |
| `followers_count` | INT | 영향력 척도 |
| `is_private` | BOOL | 비공개 계정 여부 |
| `raw_json` | JSON | 향후 분석을 위한 원본 데이터 백업 |

### 3.2 `posts`
| Field | Type | Description |
|-------|------|-------------|
| `shortcode` | PK | 게시물 고유 ID |
| `owner_username` | FK | 작성자 |
| `caption` | TEXT | 게시글 본문 |
| `hashtags` | JSON | 추출된 해시태그 목록 |
| `taken_at` | DATETIME | 게시 시각 |
| `like_count` | INT | 좋아요 수 (Engagement Metric) |
| `comment_count` | INT | 댓글 수 |

### 3.3 `comments` (Tier 2 Data)
| Field | Type | Description |
|-------|------|-------------|
| `id` | PK | 댓글 ID |
| `post_shortcode` | FK | 원본 게시물 |
| `owner_username` | FK | 댓글 작성자 |
| `text` | TEXT | 댓글 내용 (반응 분석용) |

---

## 4. Operational Workflow

### 4.1 CLI Interface (`scripts/crawl_instagram.py`)
운영자는 CLI를 통해 수집 작업을 제어한다.

```bash
# 기본 실행: Seed 유저 1명의 프로필 및 최근 게시물 수집
uv run scripts/crawl_instagram.py --seed "influencer_id" --depth 1

# 심화 실행: 댓글 작성자 프로필까지 수집 (Level 2)
uv run scripts/crawl_instagram.py --seed "influencer_id" --depth 2
```

### 4.2 Data Export
수집된 데이터는 시뮬레이터에서 사용하기 위해 JSON 템플릿으로 변환된다.
(`scripts/export_personas.py` - *Expected Implementation*)

---

## 5. Constraints & Ethics
*   **Rate Limits**: 시간당 요청 수 제한을 준수해야 함 (약 30~50 request/hour 안전 구간).
*   **Privacy**: 비공개 계정 데이터는 수집하지 않으며, PII(개인식별정보)는 연구 목적으로만 로컬에 저장한다.

---

## 6. Implementation Challenges & Know-how (Planning View)
실제 구현 흐름을 바탕으로, 크롤러를 "계획 단계"에서 어떻게 설계해야 안정적인 실행이 가능한지 정리한다.

1.  **로그인 우선순위 경로**: 쿠키 기반 로그인과 세션 파일 재사용 경로를 먼저 시도하고 실패 시 비밀번호 로그인으로 전환한다. 설계 문서에는 "쿠키 -> 세션 -> 패스워드" 순서와 실패 시 처리 규칙을 명시한다.
2.  **로그인 실패 허용 모드**: 로그인 실패 시에도 제한된 데이터 수집이 가능하다. 계획 단계에서 "로그인 실패 시 축소 모드"(댓글/좋아요 제외) 정책을 문서화한다.
3.  **Rate Limit 백오프**: 연속 요청 실패를 감지하면 점진적 대기 시간을 늘려야 한다. 설계 문서에 지수 백오프 기준(초기/최대 대기)과 복구 조건을 명시한다.
4.  **수집 캡 구조**: 사용자/포스트/댓글/좋아요/팔로워 각각에 대한 상한이 존재해야 한다. 계획 단계에서 "캡 설정값"을 CLI 옵션과 데이터 구조에 포함한다.
5.  **스키마 확장 대비**: 팔로워 테이블에서 user_edges로 확장되는 마이그레이션 경로가 필요하다. 설계 문서에 마이그레이션 버전 관리와 호환성 규칙을 포함한다.
