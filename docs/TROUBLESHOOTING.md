# Incident Response Guide (Troubleshooting)

본 문서는 개발 및 시연 중 발생할 수 있는 주요 장애 상황(Incidents)에 대한 진단 절차 및 복구 가이드이다. 문제 발생 시 **Symptom(증상) -> Root Cause(원인) -> Resolution(해결)** 프로세스를 따른다.

## 1. Network & Connectivity Incidents

### Case 1.1: SNS Unreachable (`ERR_CONNECTION_REFUSED`)
*   **Symptom**: `https://localhost:8092` 접속 시 연결 거부됨.
*   **Root Cause**: Pixelfed Docker 컨테이너가 정상적으로 실행되지 않았거나, 포트 매핑이 충돌함.
*   **Diagnostic**:
    ```bash
    docker ps | grep pixelfed
    docker logs pixelfed-app --tail 20
    ```
*   **Resolution**:
    1.  컨테이너 상태 확인 (Exited 상태인지 확인).
    2.  `pixelfed-db` 또는 `pixelfed-redis`가 `Created` 상태면 다음을 실행:
        ```bash
        docker-compose up -d db redis
        ```
    3.  환경변수 변경사항 반영을 위한 강제 재생성:
        ```bash
        docker-compose up -d --force-recreate
        ```

### Case 1.2: SSL Certificate Errors (`NET::ERR_CERT_AUTHORITY_INVALID`)
*   **Symptom**: 브라우저 또는 Agent가 보안 경고와 함께 접속을 차단함.
*   **Root Cause**: 로컬 개발용 Self-Signed 인증서(mkcert)를 브라우저/OS가 신뢰하지 않음.
*   **Resolution**:
    *   **Browser**: "Advanced" -> "Proceed to localhost (unsafe)" 클릭.
    *   **Agent (Playwright)**: 코드 레벨에서 `ignore_https_errors=True` 옵션이 활성화되어 있으므로 별도 조치 불필요. 단, `curl` 테스트 시 `-k` (insecure) 옵션 사용 필수.

---

## 2. Runtime & Logic Incidents

### Case 2.1: Agent Login Loops
*   **Symptom**: 에이전트가 로그인 페이지에서 멈추거나 계속 새로고침함. Log에 `TimeoutError: waiting for selector` 발생.
*   **Root Cause**:
    1.  DB Seeding이 수행되지 않아 `agent` 계정이 존재하지 않음.
    2.  CSRF 토큰 만료 또는 세션 처리 오류.
*   **Resolution**:
    *   **Immediate Fix (DB Reset)**:
        ```bash
        cat sns/seed_hackathon.php | docker exec -i pixelfed-app php artisan tinker
        ```
    *   Login 성공 여부를 수동 브라우저로 교차 검증 (`agent1@local.dev` / `password`, 이메일 로그인).

### Case 2.2: LLM Hallucination / Rate Limits
*   **Symptom**: 에이전트가 엉뚱한 곳을 클릭하거나, API 오류 로그(`429 Too Many Requests`) 발생.
*   **Root Cause**:
    1.  OpenAI/OpenRouter API 쿼터 소진.
    2.  VLM이 복잡한 UI를 해석하지 못함.
*   **Resolution**:
    1.  **Fallback to Local LLM**: `.env`에서 `LLM_PROVIDER=ollama` 로 변경.
        ```bash
        brew install ollama && ollama run qwen3-vl:2b
        ```
    2.  **Prompt Engineering**: `agent/src/cua/client.py`의 시스템 프롬프트에서 `Coordinate Click` 대신 `Text Match Click`을 유도하도록 수정.

### Case 2.3: Persona Template Not Found
*   **Symptom**: `FileNotFoundError: No such file or directory: template_tech_enthusiast.json`
*   **Root Cause**: `agent/data/personas/templates/` 디렉토리가 비어있거나 경로 설정 오류.
*   **Resolution**:
    ```bash
    # 디렉토리 존재 확인
    ls -R agent/data/personas/
    # 템플릿 생성 스크립트 실행 (만약 존재한다면) 또는 수동 JSON 파일 복구.
    ```

---

## 3. Integration Incidents (Dashboard)

### Case 3.1: Simulation Progress Stuck at 0%
*   **Symptom**: "Running" 상태에서 프로그레스 바가 움직이지 않음.
*   **Root Cause**:
    1.  Bridge Server -> Runner 프로세스 스폰 실패.
    2.  Runner가 `shared/simulation/*.json` 파일에 쓰기 권한이 없거나 경로 불일치.
*   **Resolution**:
    1.  Agent Server 로그 확인 (`agent/server_stderr.log`).
    2.  파일 시스템 확인: `ls -l shared/simulation/` 으로 파일 생성 여부 및 갱신 시간 확인.
    3.  `verify_config.json`의 `headless` 옵션을 `false`로 변경하여 브라우저가 실제로 뜨는지 육안 확인 (로컬 디버깅 시).

---

> **Crisis Management**: 해결되지 않는 치명적 오류 발생 시, 모든 Docker 컨테이너를 삭제(`docker system prune`)하고 Quick Start의 1번 단계부터 다시 진행(Clean Install)하는 것을 권장한다.
