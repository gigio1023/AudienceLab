# SNS Environment Specification (Pixelfed)

본 문서는 에이전트들이 활동할 가상의 소셜 미디어 공간인 **Local SNS Environment**의 상세 명세서이다. 현재 구현은 `sns/pixelfed` 기반의 Pixelfed 환경과 `sns/seed_hackathon.php` 시드 스크립트를 포함한다.

빠른 초기화를 위해 `scripts/setup_sns.sh`를 사용할 수 있다.

## 1. Environment Topology

전체 시스템은 Docker Compose에 의해 관리되는 컨테이너 네트워크로 구성된다.

```mermaid
graph TD
    Host[Simulation Runner] -->|HTTPS/8092| Nginx[Web Server / Load Balancer]
    Nginx -->|PHP-FPM| App[Pixelfed App (Laravel)]
    App -->|SQL| DB[(MySQL 8.0)]
    App -->|Cache/Queue| Redis[(Redis 7)]
    App --> Worker[Horizon Worker]
```

### 1.1 Infrastructure Components
*   **Application Server**: Laravel 기반의 Pixelfed 인스턴스. ActivityPub 프로토콜을 지원하지만, 본 시뮬레이션에서는 로컬 인스턴스 내부 상호작용에 집중한다.
*   **Database**: 사용자, 게시물, 활동 로그를 저장하는 영구 저장소 (MySQL).
*   **Queue Worker**: 비동기 작업(알림 발송, 이미지 처리 등)을 처리하여 응답 속도를 보장한다.

---

## 2. Configuration Specifications

### 2.1 Networking & Security
*   **Endpoint**: `https://localhost:8092`
    *   **Port 8092**: 표준 80/443 포트 충돌 방지 및 비특권 포트 사용.
    *   **HTTPS Required**: 최신 브라우저 정책 및 ActivityPub 호환성을 위해 Self-signed 인증서를 사용한 SSL/TLS 통신 필수.
*   **Domain**: `localhost` (로컬 DNS 해석)

### 2.2 Environment Variables (`.env`)
시뮬레이션 환경의 일관성을 위해 고정된 설정을 사용한다.

| Key | Value | Description |
|-----|-------|-------------|
| `APP_URL` | `https://localhost:8092` | 애플리케이션 진입점 |
| `APP_DOMAIN` | `localhost` | 페더레이션 도메인 식별자 |
| `DB_CONNECTION` | `mysql` | 데이터베이스 드라이버 |
| `BROADCAST_DRIVER` | `log` | 실시간 알림 단순화 (오버헤드 방지) |

---

## 3. Data Seeding Strategy

시뮬레이션 시작 시점의 "초기 상태(World State)"를 정의한다. 텅 빈 공간이 아닌, 이미 활발한 커뮤니티처럼 보이도록 데이터를 주입해야 한다.

### 3.1 Account Hierarchy
| Role | Count | Username Rule | Permissions | Note |
|------|-------|---------------|-------------|------|
| **Admin** | 1 | `admin` | Full Access | 시스템 모니터링 및 디버깅용 |
| **Influencer** | 3~5 | `influencer_{n}` | Standard | 시뮬레이션의 대상(Target) |
| **Agent** | 50+ | `agent_{user_id}` | Standard | 자율 에이전트용 계정 풀 |

### 3.2 Content Population (`seed_hackathon.php`)
*   **Influencer Posts**: 크롤링된 실제 데이터(Tier 1 Data)를 기반으로 인플루언서 계정이 게시물을 작성한 상태로 초기화한다.
*   **Contextual Comments**: 분위기 형성을 위해 배경(Background) 유저들의 더미 댓글을 생성한다.

## 4. Operational Protocols

### 4.1 Reset & Reboot
시뮬레이션 간 상태 간섭을 방지하기 위해 각 실행 전/후에 환경을 초기화할 수 있어야 한다.

```bash
# Soft Reset (데이터 유지, 캐시/세션 정리)
docker exec pixelfed-app php artisan cache:clear

# Hard Reset (데이터 완전 초기화 및 재시딩) - 약 30초 소요
cd sns/pixelfed
docker-compose down -v
docker-compose up -d
cat ../seed_hackathon.php | docker exec -i pixelfed-app php artisan tinker
```

### 4.2 Monitoring
*   **Logs**: `storage/logs/laravel.log`를 통해 애플리케이션 에러 모니터링.
*   **Telescope**: (Optional) Laravel Telescope를 활성화하여 쿼리 및 요청 상세 분석.

---

## 5. Known Limitations
1.  **Image Processing Speed**: Docker 환경에서 대용량 이미지 업로드 시 썸네일 생성에 지연이 발생할 수 있음. (Queue Worker 필수 가동)
2.  **Self-Signed Cert**: Headless Browser(Playwright) 사용 시 SSL 검증 무시(`ignore_https_errors=True`) 옵션이 필수적으로 요구됨.
3.  **Federation Disabled**: 외부 인스턴스와의 통신은 차단되어 있음 (Local-Only Simulation).

---

## 6. Implementation Challenges & Know-how (Planning View)
실제 구현 흐름을 바탕으로, 실행 전에 설계 단계에서 미리 정리해야 할 운영 포인트를 계획 관점으로 정리한다.

1.  **HTTPS 강제 경로**: 로컬에서도 HTTPS로 접근해야 로그인 루프가 줄어든다. 설계 문서에는 기본 진입 URL을 HTTPS로 고정하고, 초기 접속 시 브라우저 경고 처리 흐름을 포함한다.
2.  **환경 변수 우선순위**: 앱 URL/도메인 설정이 어긋나면 404 또는 인증 리다이렉트가 반복될 수 있다. 계획 단계에서 `.env` 값 고정(앱 URL/도메인/관리 도메인)과 변경 시 재기동 규칙을 명시한다.
3.  **초기 키 생성 순서**: 키/패스포트 키/인스턴스 사용자 생성은 첫 부팅에만 필요하지만 누락 시 인증 실패가 발생한다. 설계 문서에 "초기화 1회 실행 단계"를 명확히 분리한다.
4.  **시드 계정 정책**: 기본 계정(관리자/에이전트/인플루언서)은 반복 시뮬레이션에 필요하다. 계획 단계에서 시드 계정명과 기본 비밀번호를 고정하고, 리셋 후 재주입 루틴을 정의한다.
5.  **브라우저 캐시 이슈**: HSTS 캐시가 남으면 HTTPS 오류가 지속될 수 있다. 문서에 브라우저 캐시 초기화 안내를 포함해 반복 실험 실패를 줄인다.
