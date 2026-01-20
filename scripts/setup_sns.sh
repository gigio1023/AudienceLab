#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIXELFED_DIR="$ROOT_DIR/sns/pixelfed"
SEED_FILE="$ROOT_DIR/sns/seed_hackathon.php"

if ! command -v docker-compose >/dev/null 2>&1; then
  echo "docker-compose not found. Please install Docker Compose." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Please install Python 3." >&2
  exit 1
fi

git -C "$ROOT_DIR" submodule update --init --recursive

if [[ ! -d "$PIXELFED_DIR" ]]; then
  echo "Pixelfed directory missing at $PIXELFED_DIR" >&2
  exit 1
fi

cd "$PIXELFED_DIR"

if [[ ! -f .env ]]; then
  cp .env.docker.example .env
fi

python3 - <<'PY'
import base64
import os
from pathlib import Path

env_path = Path(".env")
lines = env_path.read_text().splitlines()
data = {}
order = []
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key, val = line.split("=", 1)
        data[key] = val
        order.append(key)
    else:
        order.append(None)

def set_key(key, value):
    data[key] = value

set_key("APP_URL", "\"https://localhost:8092\"")
set_key("APP_DOMAIN", "\"localhost\"")
set_key("ADMIN_DOMAIN", "\"localhost\"")
set_key("SESSION_DOMAIN", "\"localhost\"")
set_key("DB_PASSWORD", "\"pixelfed\"")
set_key("DB_ROOT_PASSWORD", "\"pixelfed\"")

app_key = data.get("APP_KEY", "").strip("\"")
if not app_key:
    token = base64.b64encode(os.urandom(32)).decode()
    set_key("APP_KEY", f"base64:{token}")

out_lines = []
seen = set()
for item in lines:
    if "=" in item and not item.lstrip().startswith("#"):
        key = item.split("=", 1)[0]
        out_lines.append(f"{key}={data[key]}")
        seen.add(key)
    else:
        out_lines.append(item)

for key, value in data.items():
    if key not in seen:
        out_lines.append(f"{key}={value}")

env_path.write_text("\n".join(out_lines) + "\n")
PY

cat <<'CADDY' > Caddyfile
https://localhost {
  tls internal
  reverse_proxy pixelfed:8080
}
CADDY

cat <<'YAML' > docker-compose.override.yml
services:
  pixelfed:
    ports:
      - "8093:8080"

  caddy:
    image: caddy:2-alpine
    container_name: pixelfed-caddy
    restart: unless-stopped
    ports:
      - "8092:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./caddy-data:/data
      - ./caddy-config:/config
    depends_on:
      - pixelfed
    networks:
      - pixelfed-network
YAML

docker-compose up -d --force-recreate

if [[ ! -f "$SEED_FILE" ]]; then
  echo "seed_hackathon.php missing at $SEED_FILE" >&2
  exit 1
fi

cat "$SEED_FILE" | docker-compose exec -T pixelfed php artisan tinker

echo "SNS setup complete: http://localhost:8092"
