---
name: sns-environment
description: Pixelfed 로컬 SNS 환경 설정 및 관리. Docker Compose로 Pixelfed를 구동하고 시뮬레이션용 데이터를 시딩할 때 사용.
---

# SNS Environment Skill

## Overview

Pixelfed(Instagram 클론)를 Docker로 구동하여 에이전트 시뮬레이션의 격리된 무대를 제공합니다.

## Quick Start (5분)

### 1. Docker 컨테이너 시작

```bash
cd sns/pixelfed
docker-compose up -d
```

### 2. 상태 확인

```bash
docker ps | grep pixelfed
# Expected: pixelfed-app, pixelfed-mysql, pixelfed-redis
```

### 3. 접속 테스트

```
URL: https://localhost:8092
Default Password: password
```

## Data Seeding

### 시뮬레이션 데이터 초기화

```bash
# 1. DB 초기화
docker exec pixelfed-app php artisan migrate:fresh

# 2. 해커톤 시드 데이터 주입
cat seed_hackathon.php | docker exec -i pixelfed-app php artisan tinker
```

### 수동 계정 생성 (Fallback)

```bash
docker exec -it pixelfed-app php artisan user:create
# 또는 웹 UI에서 회원가입
```

## Default Accounts

| Username | Role | Password |
|----------|------|----------|
| `influencer1` | 인플루언서 | `password` |
| `agent1` | 시뮬레이션 에이전트 | `password` |
| `agent2` | 시뮬레이션 에이전트 | `password` |
| `agent3` | 시뮬레이션 에이전트 | `password` |

## Troubleshooting

### 404 에러
```bash
# APP_DOMAIN 확인
docker exec pixelfed-app cat .env | grep APP_DOMAIN
# 해결: APP_DOMAIN=localhost 확인 후
docker exec pixelfed-app php artisan route:clear
```

### 500 에러
```bash
# 로그 확인
docker exec pixelfed-app tail -50 storage/logs/laravel.log
```

### 환경 변경 적용
```bash
# restart는 불충분, force-recreate 필요
docker-compose up -d --force-recreate
```

### 컨테이너 완전 초기화
```bash
docker-compose down -v
docker-compose up -d
```

## Hackathon Mode 원칙

> **속도 우선**: 보안 경고 무시 가능
- 하드코딩된 비밀번호 `password` 허용
- `777` 권한 허용
- 표준 API 실패 시 직접 DB 주입 허용

## Key Files

```
sns/pixelfed/
├── .env                    # 환경변수 (수정 시 recreate 필요)
├── docker-compose.yml      # 인프라 정의 (포트: 8092)
├── artisan                 # Laravel CLI (컨테이너 내에서만 실행)
└── seed_hackathon.php      # 해커톤 시드 스크립트
```

## Integration Points

- **Agent가 접속할 URL**: `https://localhost:8092`
- **인증 방식**: 세션 기반 로그인
- **데이터 확인**: MySQL 직접 접근 또는 웹 UI
