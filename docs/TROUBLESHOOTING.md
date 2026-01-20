# Incident Response Guide (Current Implementation)

본 문서는 **현재 구현된 구성요소**에서 발생하는 문제를 진단/복구하기 위한 가이드다.

## 1. Network & Connectivity

### Case 1.1: SNS Unreachable (`ERR_CONNECTION_REFUSED`)
- **Symptom**: `https://localhost:8092` 접속 불가
- **Root Cause**: Pixelfed 컨테이너 미기동 또는 포트 충돌
- **Resolution**:
  ```bash
  docker ps | rg pixelfed
  docker logs pixelfed-app --tail 20
  ./scripts/setup_sns.sh
  ```

### Case 1.2: SSL Certificate Errors
- **Symptom**: 브라우저가 인증서 경고 표시
- **Resolution**:
  - 브라우저에서 "Proceed" 허용
  - CLI에서 `curl -k https://localhost:8092`

---

## 2. Agent Runtime

### Case 2.1: Login 실패 / 루프
- **Symptom**: Hero가 로그인 후 피드 진입 실패
- **Root Cause**: 시드 미실행, 계정 없음, 자격 증명 불일치
- **Resolution**:
  ```bash
  cd sns/pixelfed
  cat ../seed_hackathon.php | docker-compose exec -T pixelfed php artisan tinker
  ```
  - `agent/.env`의 `SNS_EMAIL`, `SNS_PASSWORD` 확인
  - `--headed` 플래그로 브라우저를 띄워 수동 확인

### Case 2.2: OpenAI 오류 (401/429)
- **Symptom**: 액션 로그에 `openai_error` 표시
- **Resolution**:
  - `agent/.env`의 `OPENAI_API_KEY` 확인
  - 빠른 검증은 `--dry-run`으로 진행

### Case 2.3: Output 파일 누락
- **Symptom**: `shared/simulation/*.json` 또는 `actions.jsonl`이 생성되지 않음
- **Resolution**:
  - 실행 위치 확인 (`cd agent` 후 실행)
  - `agent/outputs/` 권한 확인
  - `uv run python cli.py smoke-test --verbose` 실행

---

## 3. Debug Tips

- **Hero 디버깅**: `--headed`로 UI 확인
- **Crowd만 검증**: `--no-hero --dry-run`
- **액션 로그 확인**:
  - `agent/outputs/{runId}/{agentId}/actions.jsonl`
