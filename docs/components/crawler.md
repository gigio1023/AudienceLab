# Instagram Crawler (Current Status)

본 저장소에는 **Instagram 크롤러가 포함되어 있지 않다**. 현재 구현은 로컬 SNS(SNS-Vibe) 시드 데이터를 JSON으로 주입하는 방식에 집중한다.

## 1. Current Data Ingestion

- 시드 데이터: `sns-vibe/seeds.json`
- 실행 방법:
  ```bash
  npx tsx src/lib/server/seed.ts
  ```

## 2. Data Contract (Reference)

현재 시뮬레이션은 아래 최소 필드가 존재한다고 가정한다.

```
Influencer: username, biography, followers (optional), is_private (optional), fetched_at
Post: shortcode/url, user_username, taken_at, caption, caption_hashtags, like_count, comment_count, fetched_at
Comment (Tier 2+): comment_id, shortcode, owner_username, created_at, text, fetched_at
```

> 크롤러 구현은 별도 작업으로 분리되어 있으며, 이 저장소에는 포함되어 있지 않다.
