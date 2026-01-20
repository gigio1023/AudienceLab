---
name: sns-environment
description: Bring up and seed the local Pixelfed SNS via Docker Compose, validate access on https://localhost:8092, and handle reset/troubleshooting. Use when the SNS environment needs setup, reset, or validation.
---

# SNS Environment (Pixelfed)

## Quick start (recommended)

```bash
./scripts/setup_sns.sh
```

## Manual setup

```bash
cd sns/pixelfed

# Ensure env file exists
cp .env.docker.example .env

# Recreate containers to apply env
docker-compose up -d --force-recreate

# Seed hackathon data
cat ../seed_hackathon.php | docker exec -i pixelfed-app php artisan tinker
```

## Verify

```bash
curl -k https://localhost:8092
```

Default credentials: `agent1` / `password`.

## Troubleshooting

- **404 after env edits**: check `APP_DOMAIN=localhost`, then:
  ```bash
  docker exec pixelfed-app php artisan route:clear
  ```
- **Env change not applied**: use `docker-compose up -d --force-recreate`.
- **App errors**: inspect `storage/logs/laravel.log` in the container.
