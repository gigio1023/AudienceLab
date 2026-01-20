---
description: Crawl Instagram user activity data using BFS traversal from a seed user.
---

# Instagram BFS Crawler

Crawl Instagram user activity data using BFS traversal from a seed user. Supports incremental crawling to avoid re-crawling existing data.

## Arguments

- `$ARGUMENTS`: Seed username and options in format: `<seed_username> [--max-users <N>] [--output <path>] [--username <ig_username>] [--password <ig_password>] [--max-comments <N>] [--max-likers <N>] [--full]`

## Default Values

- `max_users`: 10 (maximum number of users to crawl including seed)
- `output`: `./instagram_crawl_results/` (output directory)
- `depth`: 1 (fixed - seed user + their followers)
- `mode`: incremental (default) - only crawl new data; use `--full` flag for full re-crawl
- `max_comments`: 0 (unlimited - extract ALL available comments per post)
- `max_likers`: 0 (unlimited - extract ALL available likers per post)

## Workflow

### Step 1: Parse Arguments

Parse the input arguments:
- Extract seed username (required)
- Extract max users limit (default: 10)
- Extract output path (default: ./instagram_crawl_results/)
- Extract Instagram username (optional, for login)
- Extract Instagram password (optional, for login)
- Extract max comments per post (default: 0 = unlimited)
- Extract max likers per post (default: 0 = unlimited)
- Check for `--full` flag (if present, do full crawl; otherwise incremental)

Example: `/crawl_instagram johndoe --max-users 5 --output ./data/ --username myuser@email.com --password mypassword --max-comments 50 --max-likers 100`

### Step 2: Check Existing Data (Incremental Mode)

**IMPORTANT: This step enables incremental crawling.**

Before crawling, check for existing data:

1. Check if `{output}/crawl_summary.json` exists
2. Check if `{output}/{seed_username}/data.json` exists
3. If exists, read and parse the existing data:
   ```javascript
   // Load existing data
   existingData = JSON.parse(read("{output}/{seed_username}/data.json"))
   existingPostUrls = new Set(existingData.posts.map(p => p.url))
   lastCrawlTime = existingData.crawled_at
   ```

4. Store existing data for later comparison:
   - `existingPosts`: Array of already crawled post URLs
   - `existingFollowers`: Array of already crawled follower usernames
   - `lastCrawlTime`: Timestamp of last crawl

5. If `--full` flag is provided, skip this step and do full crawl

**Display to user:**
```
Found existing data for {username}:
- Last crawled: {lastCrawlTime}
- Existing posts: {count}
- Mode: Incremental (will only crawl new posts)
```

### Step 3: Initialize Output Directory

Create output directory using Bash:
```bash
mkdir -p {output}/{seed_username}
```

### Step 4: Instagram Login (if credentials provided)

If `--username` and `--password` are provided, perform login using Playwright MCP:

1. Navigate to login page:
   - Use `browser_navigate` to open `https://www.instagram.com/accounts/login/`

2. Wait for page load and dismiss cookie consent if present:
   - Use `browser_snapshot` to get page state
   - If cookie dialog exists, use `browser_click` on close/accept button

3. Fill login form:
   - Use `browser_snapshot` to identify form elements
   - Use `browser_type` for username field (look for input with "phone", "username", or "email" placeholder)
   - Use `browser_type` for password field (look for input with "password" placeholder)

4. Submit login:
   - Use `browser_click` on the login button (로그인/Log in)
   - Use `browser_wait` for navigation to complete

5. Verify login success:
   - Use `browser_snapshot` to check for navigation elements (Home, Search, Explore)
   - If login fails or 2FA required, report to user

### Step 5: Crawl Seed User (Incremental)

Navigate to seed user's profile and extract data:

1. Navigate to profile:
   - Use `browser_navigate` to open `https://www.instagram.com/{seed_username}/`

2. Extract profile info (always update):
   - Use `browser_snapshot` to get page content
   - Parse: display name, bio, follower count, following count, post count, verification status
   - **Profile info is always updated** even in incremental mode

3. **Incremental Post Extraction:**
   - Use `browser_snapshot` to find post thumbnails
   - For each post visible on the grid:
     a. Extract the post URL from the link
     b. **Check if URL exists in `existingPostUrls`**
     c. **If post already exists, SKIP it** (don't click or extract details)
     d. **If post is NEW, extract ALL details:**
        - Use `browser_click` to open post modal
        - Use `browser_snapshot` to extract caption, like count, comment count, timestamp
        - **CRITICAL: Extract comments:**
          * Look for "View all X comments" or "댓글 X개 모두 보기" link and click if present
          * Use `browser_scroll` in comments area to load more
          * For each comment: extract username, text, timestamp, like_count
          * **Keep scrolling and extracting until:**
            - No more comments load (reached end), OR
            - Reached `max_comments` limit (if > 0)
          * If `max_comments` is 0 (unlimited), extract ALL available comments
        - **CRITICAL: Extract likers:**
          * Click on the likes count text (e.g., "1,234 likes", "좋아요 X개")
          * Use `browser_snapshot` to get likers modal
          * For each liker: extract username, display_name
          * Use `browser_scroll` to load more likers
          * **Keep scrolling and extracting until:**
            - No more likers load (reached end), OR
            - Reached `max_likers` limit (if > 0)
          * If `max_likers` is 0 (unlimited), extract ALL available likers
          * Press "Escape" to close likers modal
        - Use `browser_press_key` with "Escape" to close post modal
        - Use `browser_wait_for` with time: 2 seconds between posts
        - Add to `newPosts` array with ALL extracted data

4. **Merge existing and new data:**
   ```javascript
   // IMPORTANT: Each new post MUST have these fields:
   // - url, post_id, type, caption, like_count, comment_count
   // - timestamp, crawled_at
   // - comments: [{username, text, timestamp?, like_count?}]
   // - likers: [{username, display_name}]

   // Validate new posts have comments and likers arrays
   for (post of newPosts) {
     if (!post.comments) post.comments = []
     if (!post.likers) post.likers = []
     if (!post.like_count) post.like_count = 0
     if (!post.comment_count) post.comment_count = 0
   }

   // Merge posts: new posts first, then existing posts
   mergedPosts = [...newPosts, ...existingData.posts]

   // Update crawl timestamp
   userData.crawled_at = new Date().toISOString()
   userData.last_incremental_crawl = new Date().toISOString()
   userData.posts = mergedPosts
   ```

5. Save merged data to `{output}/{seed_username}/data.json`

**Display progress:**
```
Crawling {username}:
- Skipped {skipped_count} existing posts
- Found {new_count} new posts
- Total posts now: {total_count}
```

### Step 6: Collect Follower Usernames (Incremental)

From the seed user's profile:

1. Open followers modal:
   - Use `browser_snapshot` to find followers link
   - Use `browser_click` on followers count

2. Scroll and collect usernames:
   - Use `browser_snapshot` to get visible followers
   - **Filter out already crawled followers** from `existingFollowers`
   - Use `browser_scroll` to load more followers
   - Repeat until `max_users - 1` NEW followers collected (or no more available)

3. Close modal:
   - Use `browser_press_key` with "Escape"

**Logic for follower selection:**
```javascript
// Load existing crawled followers from crawl_summary.json
existingCrawledUsers = crawlSummary.users.map(u => u.username)

// Collect new followers only
newFollowersToProcess = []
for (follower of visibleFollowers) {
  if (!existingCrawledUsers.includes(follower.username)) {
    newFollowersToProcess.push(follower)
  }
  if (newFollowersToProcess.length >= maxUsers - 1 - existingCrawledUsers.length) {
    break
  }
}
```

### Step 7: Crawl Followers (Incremental)

For each follower to crawl:

1. **Check if follower data already exists:**
   ```javascript
   followerDataPath = "{output}/{follower_username}/data.json"
   if (fileExists(followerDataPath)) {
     existingFollowerData = JSON.parse(read(followerDataPath))
     // Apply same incremental logic as seed user
   }
   ```

2. Navigate to follower's Instagram profile using `browser_navigate`
3. Extract profile data (always update)
4. **Incremental post extraction** (same logic as Step 5)
5. Merge and save to `{output}/{follower_username}/data.json`

### Step 8: Aggregate Results (Merge with Existing Summary)

After all crawls complete, update the summary:

```json
// {output}/crawl_summary.json
{
  "seed_user": "johndoe",
  "first_crawl_timestamp": "2024-01-20T10:30:00Z",
  "last_crawl_timestamp": "2024-01-21T15:45:00Z",
  "crawl_history": [
    {
      "timestamp": "2024-01-20T10:30:00Z",
      "mode": "full",
      "users_crawled": 5,
      "new_posts_found": 47
    },
    {
      "timestamp": "2024-01-21T15:45:00Z",
      "mode": "incremental",
      "users_crawled": 5,
      "new_posts_found": 12
    }
  ],
  "total_users_crawled": 5,
  "max_users_limit": 10,
  "depth": 1,
  "users": [
    {
      "username": "johndoe",
      "role": "seed",
      "status": "success",
      "data_file": "./johndoe/data.json",
      "last_crawled": "2024-01-21T15:45:00Z",
      "total_posts_collected": 52
    },
    {
      "username": "follower1",
      "role": "follower",
      "status": "success",
      "data_file": "./follower1/data.json",
      "last_crawled": "2024-01-21T15:45:00Z",
      "total_posts_collected": 28
    }
  ],
  "errors": []
}
```

## Incremental Crawling Algorithm

```
FUNCTION incrementalCrawl(username, outputPath):
    existingData = loadExistingData(outputPath, username)
    existingPostUrls = extractPostUrls(existingData)

    navigateToProfile(username)
    profileInfo = extractProfileInfo()  // Always update

    newPosts = []
    visiblePosts = getVisiblePostsFromGrid()

    FOR EACH post IN visiblePosts:
        IF post.url NOT IN existingPostUrls:
            postDetails = openAndExtractPost(post)
            newPosts.append(postDetails)
            PRINT "New post found: {post.url}"
        ELSE:
            PRINT "Skipping existing post: {post.url}"

    // Merge: new posts at the beginning (most recent)
    mergedPosts = newPosts + existingData.posts

    // Remove duplicates (by URL)
    mergedPosts = deduplicateByUrl(mergedPosts)

    saveData(username, profileInfo, mergedPosts)

    RETURN {
        newPostsCount: newPosts.length,
        skippedCount: visiblePosts.length - newPosts.length,
        totalPosts: mergedPosts.length
    }
```

## Playwright MCP Tools Reference

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Navigate to URL |
| `browser_snapshot` | Get page accessibility tree (for finding elements) |
| `browser_click` | Click an element by reference |
| `browser_type` | Type text into an element |
| `browser_scroll` | Scroll page (up/down) |
| `browser_press_key` | Press keyboard key (Escape, Enter, etc.) |
| `browser_screenshot` | Take screenshot (for debugging) |
| `browser_wait` | Wait for time or element |

## Example Usage

### Incremental crawl (default - recommended for repeat crawls):
```
/crawl_instagram techguru --max-users 5 --output ./crawl_data/ --username myemail@example.com --password mypassword123
```
Output: "Found 3 new posts, skipped 9 existing posts"

### Full re-crawl (ignore existing data):
```
/crawl_instagram techguru --max-users 5 --output ./crawl_data/ --username myemail@example.com --password mypassword123 --full
```
Output: "Full crawl mode - re-crawling all posts"

## Rate Limiting & Safety

- Add 2-5 second delays between actions using `browser_wait`
- If rate limited, pause and retry with exponential backoff
- Respect Instagram's terms of service

## Error Handling

- **Private profiles**: Mark as "private" in summary, skip extraction
- **Rate limits**: Pause, wait, retry with backoff
- **Login walls**: Require `--username` and `--password` for authenticated access
- **2FA required**: Pause and inform user
- **Network errors**: Retry up to 3 times
- **Corrupted existing data**: Fall back to full crawl with warning

## Output Schema

Each user's `data.json`:

```json
{
  "username": "string",
  "crawled_at": "ISO8601 timestamp",
  "first_crawled_at": "ISO8601 timestamp",
  "last_incremental_crawl": "ISO8601 timestamp",
  "crawl_count": "number",
  "profile": {
    "display_name": "string",
    "bio": "string",
    "follower_count": "number",
    "following_count": "number",
    "post_count": "number",
    "is_private": "boolean",
    "is_verified": "boolean"
  },
  "posts": [
    {
      "url": "string",
      "post_id": "string (extracted from URL)",
      "type": "image|video|carousel",
      "caption": "string",
      "like_count": "number",
      "comment_count": "number",
      "timestamp": "ISO8601",
      "crawled_at": "ISO8601 (when this post was first crawled)",
      "likers": [
        {
          "username": "string",
          "display_name": "string"
        }
      ],
      "comments": [
        {
          "username": "string",
          "text": "string",
          "timestamp": "ISO8601",
          "like_count": "number"
        }
      ]
    }
  ]
}
```

## Post Identification

Posts are identified by their URL pattern:
- Reel: `https://www.instagram.com/{username}/reel/{post_id}/`
- Photo/Carousel: `https://www.instagram.com/{username}/p/{post_id}/`

The `post_id` is extracted from the URL and used as a unique identifier to detect duplicates across crawls.

---

## 최대 데이터 수집 가이드 (Maximum Data Collection Guide)

### 🎯 최대한 많은 post, comment, like 수집하기

#### 1. 기본 권장 실행 방법
```bash
# 로그인 필수 (더 많은 데이터 접근 가능)
/crawl_instagram <seed_username> --max-users 20 --output ./data/ --username <your_ig_email> --password <your_ig_password>
```

#### 2. 데이터 수집량 늘리는 옵션들

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--max-users` | 크롤링할 총 사용자 수 | 10 (20-50 권장, 너무 높으면 rate limit) |
| `--max-comments` | 포스트당 최대 댓글 수 | 0 (무제한 - 모든 댓글 추출) |
| `--max-likers` | 포스트당 최대 좋아요 누른 사람 수 | 0 (무제한 - 모든 likers 추출) |
| `--full` | 기존 데이터 무시하고 전체 재수집 | incremental이 기본 |

#### 3. 반복 실행 전략 (Incremental Crawling)

**가장 효과적인 방법: 주기적으로 incremental 크롤링 반복**

```bash
# 1차: 초기 전체 수집
/crawl_instagram creator123 --max-users 30 --output ./data/ --username my@email.com --password pass123

# 2차 (1-2일 후): 새 포스트만 추가 수집
/crawl_instagram creator123 --max-users 30 --output ./data/ --username my@email.com --password pass123

# 3차 (1-2일 후): 또 새 포스트 추가...
# 계속 반복하면 데이터가 누적됨
```

#### 4. 수집되는 데이터 항목

**각 포스트마다 반드시 수집:**
- ✅ `url`, `post_id`, `type` (reel/photo/carousel)
- ✅ `caption` (포스트 내용)
- ✅ `like_count`, `comment_count`
- ✅ `timestamp` (게시 시간)
- ✅ `comments[]` - 모든 댓글 (username, text, timestamp, like_count) - `--max-comments`로 제한 가능
- ✅ `likers[]` - 모든 좋아요 누른 사람 (username, display_name) - `--max-likers`로 제한 가능

#### 5. 주의사항

| 이슈 | 해결책 |
|------|--------|
| Rate limit (너무 빠른 요청) | 자동으로 2-5초 딜레이 적용됨 |
| 비공개 계정 | 로그인 + 팔로우 필요 |
| 2FA 인증 요청 | 수동으로 인증 후 재시도 |
| 로그인 세션 만료 | 브라우저를 닫고 다시 시작 |

#### 6. 대량 수집 예시

```bash
# 🚀 최대 수집: 모든 comments, likers 추출 (기본값)
/crawl_instagram popular_influencer --max-users 30 --output ./data/ --username your@email.com --password yourpassword --full

# ⚡ 빠른 수집: comments 50개, likers 100명으로 제한
/crawl_instagram popular_influencer --max-users 30 --output ./data/ --username your@email.com --password yourpassword --max-comments 50 --max-likers 100

# 📈 이후 매일 incremental (새 포스트만)
/crawl_instagram popular_influencer --max-users 30 --output ./data/ --username your@email.com --password yourpassword
```

#### 7. 결과 확인

```bash
# 수집된 전체 요약 보기
cat ./data/crawl_summary.json

# 특정 유저 데이터 확인
cat ./data/<username>/data.json
```

**Tip:** 한 번에 너무 많은 유저(50+)를 크롤링하면 Instagram에서 일시 차단될 수 있습니다. 20-30명씩 나눠서 수집하는 것을 권장합니다.
