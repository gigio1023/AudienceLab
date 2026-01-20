# Instagram User Crawler Agent

This agent extracts Instagram user activity data (posts, comments, likes) for a single user.

## Input Parameters

The agent receives:
- `username`: Instagram username to crawl
- `depth`: Current depth (0 = extract this user only, no followers)
- `session_name`: Browser session name for isolation

## Workflow

### 1. Initialize Browser Session

```bash
agent-browser --session $SESSION_NAME open "https://www.instagram.com/$USERNAME/" --headed
agent-browser --session $SESSION_NAME wait --load networkidle
```

### 2. Extract User Profile Data

Take a snapshot and extract basic profile info:
```bash
agent-browser --session $SESSION_NAME snapshot -i
```

Extract:
- Profile name
- Bio
- Follower count
- Following count
- Post count

### 3. Extract Recent Posts

Scroll through the user's posts and extract:
- Post URLs
- Post captions
- Like counts
- Comment counts
- Post dates

```bash
# Click on first post
agent-browser --session $SESSION_NAME snapshot -i
# Find and click post thumbnails
agent-browser --session $SESSION_NAME click @POST_REF
agent-browser --session $SESSION_NAME wait --load networkidle

# Extract post details
agent-browser --session $SESSION_NAME snapshot -i
agent-browser --session $SESSION_NAME get text @CAPTION_REF
agent-browser --session $SESSION_NAME get text @LIKES_REF
agent-browser --session $SESSION_NAME get text @COMMENTS_REF

# Navigate to next post or close modal
agent-browser --session $SESSION_NAME press Escape
```

### 4. Extract Comments (for each post)

When inside a post modal:
```bash
# Scroll to load more comments
agent-browser --session $SESSION_NAME scroll down 500
agent-browser --session $SESSION_NAME snapshot -i

# Extract comment data
# - Commenter username
# - Comment text
# - Comment timestamp
```

### 5. Extract Followers (if depth > 0)

If `depth > 0`, extract follower list for BFS traversal:

```bash
# Click on followers count
agent-browser --session $SESSION_NAME snapshot -i
agent-browser --session $SESSION_NAME click @FOLLOWERS_LINK_REF
agent-browser --session $SESSION_NAME wait --load networkidle

# Scroll and collect follower usernames
agent-browser --session $SESSION_NAME snapshot -i
# Repeat scrolling to load more followers
agent-browser --session $SESSION_NAME scroll down 500
```

### 6. Output Format

Return extracted data as JSON:

```json
{
  "username": "target_user",
  "profile": {
    "display_name": "Display Name",
    "bio": "User bio text",
    "follower_count": 1234,
    "following_count": 567,
    "post_count": 89
  },
  "posts": [
    {
      "url": "https://instagram.com/p/ABC123",
      "caption": "Post caption...",
      "like_count": 100,
      "comment_count": 25,
      "timestamp": "2024-01-15"
    }
  ],
  "comments": [
    {
      "post_url": "https://instagram.com/p/ABC123",
      "commenter": "other_user",
      "text": "Comment text",
      "timestamp": "2024-01-15"
    }
  ],
  "followers": ["follower1", "follower2", "..."]  // Only if depth > 0
}
```

### 7. Cleanup

```bash
agent-browser --session $SESSION_NAME close
```

## Error Handling

- If login is required, the agent should detect and report login requirement
- If rate limited, wait and retry with exponential backoff
- If profile is private, mark as private and skip extraction

## Session Isolation

Each agent instance uses a unique session name to allow parallel execution:
- Session naming convention: `ig_crawler_{username}_{timestamp}`
- Sessions are isolated and do not interfere with each other

## Usage Example

This agent is called by the main `/crawl_instagram` command:

```
# For depth 0 (extract single user only)
Extract Instagram data for user: johndoe
Depth: 0
Session: ig_crawler_johndoe_1705123456

# For depth 1 (extract user + get follower list for parent to process)
Extract Instagram data for user: seeduser
Depth: 1
Session: ig_crawler_seeduser_1705123456
```
