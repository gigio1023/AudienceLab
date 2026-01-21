# SNS-Vibe

Lightweight, agent-friendly social media simulation platform built for fast iteration during the hackathon.

## Why This Exists

- Simple login flow for automated agents
- Predictable DOM IDs for Playwright selectors
- Local SQLite storage with deterministic seed data

## Quick Start (Local Dev)

```bash
npm install
bash scripts/reset-db.sh
npm run dev -- --port 8383
```

Set `SNS_URL=http://localhost:8383` in `agent/.env`.

## Docker (Optional)

```bash
docker-compose up --build -d
```

Default mapping: `http://localhost:8383`

## Data and Seeding

- SQLite database file: `sns.db`
- Seed files: `seeds/*.json`
- Manual seed run:
  ```bash
  npx tsx src/lib/server/seed.ts
  ```

## DOM Conventions for Automation

The UI includes stable IDs for agent automation:

- Like button: `#like-button-{postId}`
- Comment input: `#comment-input-{postId}`
- Comment submit: `#comment-button-{postId}`

If you change the UI, keep these selectors or update the agent code in `agent/local_agent.py`.

## Project Structure (High Level)

```
sns-vibe/
├── src/
│   ├── lib/server/   # SQLite + seeding
│   └── routes/       # Login + feed UI
├── seeds/            # Seed JSON files
├── scripts/          # Reset/seed helpers
└── sns.db            # Local database (generated)
```

## Related Docs

- Agent simulator: `../agent/README.md`
- Project overview: `../README.md`
