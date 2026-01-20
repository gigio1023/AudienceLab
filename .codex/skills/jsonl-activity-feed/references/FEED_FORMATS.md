# Feed Formats (JSONL + Index)

## 1) Agent JSONL

Each agent writes an append-only JSONL file:

```
search-dashboard/public/simulation/agent-01.jsonl
```

One line = one event. Example:

```json
{"id":"evt_0001","agent_id":"agent_01","action":"comment","timestamp":"2025-10-03T14:44:12Z","content":"Love the tone.","target":"post_001","metadata":{"platform":"pixelfed","screen":"feed"}}
```

### Recommended fields (loose)

- `id`: unique event id (string)
- `agent_id`: agent or persona id (string)
- `action`: action name (string, e.g. `comment`, `like`, `scroll`, `explore`)
- `timestamp`: ISO 8601
- `content`: optional text (comment, message)
- `target`: optional target id (post/user/etc.)
- `metadata`: optional object

The dashboard normalizes variations (`agentId`, `event`, `created_at`, etc.) via `src/lib/activityInterface.ts`.

## 2) Feed Index

`index.json` tells the dashboard which JSONL files are active.

```json
{
  "updated_at": "2025-10-03T00:00:00Z",
  "files": ["agent-01.jsonl", "agent-02.jsonl", "agent-03.jsonl"]
}
```

Location:

```
search-dashboard/public/simulation/index.json
```

If `index.json` is missing, the dashboard uses `VITE_AGENT_FEEDS`.

## 3) Operational Notes

- Append-only writes.
- Rotate by time or size to avoid large downloads.
- Use atomic writes (temp file + rename).
