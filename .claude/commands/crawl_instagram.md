---
description: Crawl Instagram user activity data using BFS traversal from a seed user.
---

# Instagram BFS Crawler

Crawl Instagram user activity data using BFS traversal from a seed user.

## Arguments

- `$ARGUMENTS`: Seed username and options in format: `<seed_username> [--max-users <N>] [--output <path>] [--username <ig_username>] [--password <ig_password>]`

## Default Values

- `max_users`: 10 (maximum number of users to crawl including seed)
- `output`: `./instagram_crawl_results/` (output directory)
- `depth`: 1 (fixed - seed user + their followers)

## Workflow

### Step 1: Parse Arguments

Parse the input arguments:
- Extract seed username (required)
- Extract max users limit (default: 10)
- Extract output path (default: ./instagram_crawl_results/)
- Extract Instagram username (optional, for login)
- Extract Instagram password (optional, for login)

Example: `/crawl_instagram johndoe --max-users 5 --output ./data/ --username myuser@email.com --password mypassword`

### Step 2: Initialize Output Directory

Create output directory using Bash:
```bash
mkdir -p {output}/{seed_username}
```

### Step 3: Instagram Login (if credentials provided)

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

### Step 4: Crawl Seed User

Navigate to seed user's profile and extract data:

1. Navigate to profile:
   - Use `browser_navigate` to open `https://www.instagram.com/{seed_username}/`

2. Extract profile info:
   - Use `browser_snapshot` to get page content
   - Parse: display name, bio, follower count, following count, post count, verification status

3. Extract recent posts (up to 12):
   - Use `browser_snapshot` to find post thumbnails
   - For each post:
     - Use `browser_click` to open post modal
     - Use `browser_snapshot` to extract caption, like count, comment count
     - **Extract comments**: Scroll within modal to load comments, capture commenter usernames and text
     - **Extract likers**: Click on "likes" count to open likers modal, scroll to collect usernames
     - Use `browser_press_key` with "Escape" to close modal

4. Save seed user data to `{output}/{seed_username}/data.json`

### Step 5: Collect Follower Usernames

From the seed user's profile:

1. Open followers modal:
   - Use `browser_snapshot` to find followers link
   - Use `browser_click` on followers count

2. Scroll and collect usernames:
   - Use `browser_snapshot` to get visible followers
   - Use `browser_scroll` to load more followers
   - Repeat until `max_users - 1` followers collected

3. Close modal:
   - Use `browser_press_key` with "Escape"

### Step 6: Parallel Follower Crawling

For each collected follower, spawn a parallel Task agent:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- model: "sonnet"
- prompt: Include the following instructions for the agent:
  1. Username to crawl
  2. Output path for results
  3. Reference to instagram-user-crawler agent workflow
  4. Use Playwright MCP tools for all browser operations
```

**Parallel Task Pattern:**

Launch multiple Task tools in parallel (up to 3-5 concurrent):
```
Task 1: Crawl follower_1 using Playwright MCP
Task 2: Crawl follower_2 using Playwright MCP
Task 3: Crawl follower_3 using Playwright MCP
...
```

Each parallel task should:
1. Navigate to follower's Instagram profile using `browser_navigate`
2. Extract profile data using `browser_snapshot`
3. Extract posts data
4. Save to `{output}/{follower_username}/data.json`

### Step 7: Aggregate Results

After all crawls complete, create summary:

```json
// {output}/crawl_summary.json
{
  "seed_user": "johndoe",
  "crawl_timestamp": "2024-01-20T10:30:00Z",
  "total_users_crawled": 5,
  "max_users_limit": 10,
  "depth": 1,
  "users": [
    {
      "username": "johndoe",
      "role": "seed",
      "status": "success",
      "data_file": "./johndoe/data.json"
    },
    {
      "username": "follower1",
      "role": "follower",
      "status": "success",
      "data_file": "./follower1/data.json"
    }
  ],
  "errors": []
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

### Without authentication (public profiles only):
```
/crawl_instagram techguru --max-users 5 --output ./crawl_data/
```

### With authentication (recommended):
```
/crawl_instagram techguru --max-users 5 --output ./crawl_data/ --username myemail@example.com --password mypassword123
```

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

## Output Schema

Each user's `data.json`:

```json
{
  "username": "string",
  "crawled_at": "ISO8601 timestamp",
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
      "type": "image|video|carousel",
      "caption": "string",
      "like_count": "number",
      "comment_count": "number",
      "timestamp": "ISO8601",
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
