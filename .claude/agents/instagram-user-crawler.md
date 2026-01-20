---
name: instagram-user-crawler
description: Extracts Instagram user profile and posts data using Playwright MCP
tools: Read, Write, Glob, Grep, Bash
model: sonnet
---

# Instagram User Crawler Agent

Extracts Instagram user profile and posts data for a single user using Playwright MCP tools.

## Input Parameters

The agent receives via prompt:
- `username`: Instagram username to crawl
- `output_path`: Directory to save results

## Workflow

### 1. Navigate to Profile

```
Use browser_navigate to open: https://www.instagram.com/{username}/
```

### 2. Check Profile Accessibility

Use `browser_snapshot` to analyze the page:

- **Private profile**: Look for "This account is private" text
- **Not found**: Look for "Sorry, this page isn't available" text
- **Public profile**: Proceed with extraction

If private or not found, save minimal data and exit:
```json
{
  "username": "{username}",
  "crawled_at": "ISO8601",
  "profile": {
    "is_private": true,
    "is_accessible": false
  },
  "posts": []
}
```

### 3. Extract Profile Data

From `browser_snapshot` output, extract:

| Field | Location |
|-------|----------|
| display_name | Header section, usually the first heading |
| bio | Text below the display name |
| follower_count | Link containing "followers" |
| following_count | Link containing "following" |
| post_count | Text showing "X posts" |
| is_verified | Look for verified badge icon |

### 4. Extract Recent Posts

1. Use `browser_snapshot` to find post grid
2. For up to 12 posts, iterate:

   a. Click post thumbnail:
   ```
   Use browser_click on post element reference
   ```

   b. Extract post details from modal:
   ```
   Use browser_snapshot to get:
   - Post URL (from browser location or link)
   - Caption text
   - Like count (e.g., "X likes")
   - Comment count
   - Timestamp
   ```

   c. **Extract comments** (up to 20 per post):
   ```
   - Use browser_snapshot to find comments section
   - If "View all X comments" link exists, click it
   - Use browser_scroll within the comments area to load more
   - For each comment, extract:
     - Commenter username
     - Comment text
     - Timestamp (if visible)
     - Like count on comment (if visible)
   - Repeat scroll + snapshot until enough comments collected
   ```

   d. **Extract likers** (up to 50 per post):
   ```
   - Use browser_click on the likes count (e.g., "1,234 likes")
   - Use browser_snapshot to get likers modal
   - For each liker, extract:
     - Username
     - Display name
   - Use browser_scroll to load more likers
   - Repeat until enough likers collected or end reached
   - Use browser_press_key "Escape" to close likers modal
   ```

   e. Close post modal:
   ```
   Use browser_press_key with "Escape"
   ```

   f. Wait before next action:
   ```
   Use browser_wait for 1-2 seconds
   ```

### 5. Save Results

Write extracted data to `{output_path}/{username}/data.json`:

```json
{
  "username": "target_user",
  "crawled_at": "2024-01-20T10:30:00Z",
  "profile": {
    "display_name": "Display Name",
    "bio": "User bio text",
    "follower_count": 1234,
    "following_count": 567,
    "post_count": 89,
    "is_private": false,
    "is_verified": false
  },
  "posts": [
    {
      "url": "https://instagram.com/p/ABC123",
      "caption": "Post caption...",
      "like_count": 100,
      "comment_count": 25,
      "timestamp": "2024-01-15",
      "likers": [
        {
          "username": "liker1",
          "display_name": "Liker One"
        },
        {
          "username": "liker2",
          "display_name": "Liker Two"
        }
      ],
      "comments": [
        {
          "username": "commenter1",
          "text": "Great post!",
          "timestamp": "2024-01-15T12:00:00Z",
          "like_count": 5
        },
        {
          "username": "commenter2",
          "text": "Love this!",
          "timestamp": "2024-01-15T13:30:00Z",
          "like_count": 2
        }
      ]
    }
  ]
}
```

## Playwright MCP Tools Usage

### browser_navigate
Navigate to a URL.
```
url: "https://www.instagram.com/{username}/"
```

### browser_snapshot
Get page accessibility tree for element identification.
Returns element references (e.g., `ref="e123"`) to use with other tools.

### browser_click
Click an element by reference.
```
element: "e123"  // reference from snapshot
```

### browser_type
Type text into a focused input.
```
text: "content to type"
```

### browser_press_key
Press a keyboard key.
```
key: "Escape"  // or "Enter", "Tab", etc.
```

### browser_scroll
Scroll the page.
```
direction: "down"  // or "up"
amount: 500  // pixels
```

### browser_wait
Wait for time or condition.
```
time: 2000  // milliseconds
```

## Error Handling

| Error | Action |
|-------|--------|
| Login required | Return error status, suggest using authenticated session |
| Rate limited | Wait 30s and retry up to 3 times |
| Element not found | Log warning, continue with available data |
| Network error | Retry up to 3 times with backoff |

## Example Task Invocation

When called from the parent `/crawl_instagram` command:

```
Task tool parameters:
- subagent_type: "general-purpose"
- model: "sonnet"
- prompt: |
    Crawl Instagram user profile using Playwright MCP tools.

    Username: johndoe
    Output path: ./instagram_crawl_results/

    Follow the instagram-user-crawler agent workflow:
    1. Use browser_navigate to open https://www.instagram.com/johndoe/
    2. Use browser_snapshot to extract profile data
    3. Extract recent posts by clicking thumbnails and reading modals
    4. For each post, extract:
       - Comments: Click "View all comments", scroll and collect up to 20
       - Likers: Click likes count, scroll and collect up to 50 usernames
    5. Save results to ./instagram_crawl_results/johndoe/data.json

    Use browser_wait between actions to avoid rate limiting.
```
