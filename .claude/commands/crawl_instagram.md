# Instagram BFS Crawler

Crawl Instagram user activity data using BFS traversal from a seed user.

## Arguments

- `$ARGUMENTS`: Seed username and options in format: `<seed_username> [--max-users <N>] [--output <path>] [--username <ig_username>] [--password <ig_password>]`

## Default Values

- `max_users`: 10 (maximum number of users to crawl including seed)
- `output`: `./instagram_crawl_results/` (output directory)
- `depth`: 1 (fixed - seed user + their followers)
- `username`: (optional) Instagram login username/email
- `password`: (optional) Instagram login password

## Workflow

### Step 1: Parse Arguments

Parse the input arguments:
- Extract seed username (required)
- Extract max users limit (default: 10)
- Extract output path (default: ./instagram_crawl_results/)
- Extract Instagram username (optional, for login)
- Extract Instagram password (optional, for login)

Example: `/crawl_instagram johndoe --max-users 5 --output ./data/ --username myuser@email.com --password mypassword`

### Step 2: Instagram Login (if credentials provided)

If `--username` and `--password` are provided, perform login before crawling:

```bash
# Open Instagram login page
agent-browser open "https://www.instagram.com/accounts/login/" --headed --session ig_crawler_seed_{timestamp}
agent-browser wait --load networkidle
agent-browser snapshot -i

# Fill in login credentials
agent-browser fill @USERNAME_INPUT "{username}"
agent-browser fill @PASSWORD_INPUT "{password}"
agent-browser wait 1000

# Click login button
agent-browser click @LOGIN_BUTTON
agent-browser wait --load networkidle
agent-browser wait 3000

# Check for login success - look for profile icon or home feed elements
agent-browser snapshot -i
# If login fails (still on login page), report error and exit
# If 2FA is required, report to user and wait for manual intervention

# Save authenticated state for reuse in parallel sessions
agent-browser state save ./instagram_auth_state.json --session ig_crawler_seed_{timestamp}
```

**Login Success Indicators:**
- Redirected away from /accounts/login/
- Profile icon visible in navigation
- Home feed or search elements present

**Login Failure Handling:**
- Wrong credentials: Report error, suggest checking credentials
- 2FA required: Inform user, wait for manual code entry
- Rate limited: Wait and retry with backoff
- Suspicious login: May need manual verification in browser

### Step 3: Initialize Output Directory

Create output directory structure:
```
{output}/
├── seed_user/
│   └── data.json
├── follower_1/
│   └── data.json
├── follower_2/
│   └── data.json
└── crawl_summary.json
```

### Step 4: Crawl Seed User (Depth 1)

Use the agent-browser skill to extract seed user data AND their follower list.

```bash
# Open Instagram profile
agent-browser open "https://www.instagram.com/{seed_username}/" --headed
agent-browser wait --load networkidle
agent-browser snapshot -i
```

Extract from seed user:
1. **Profile info**: name, bio, follower/following counts
2. **Posts**: Recent posts with captions, likes, comments
3. **Follower list**: Click followers link and scroll to collect usernames

Save seed user data to `{output}/{seed_username}/data.json`

### Step 5: Collect Follower Usernames

From the seed user's profile, extract follower usernames:

```bash
# Click followers count to open follower modal
agent-browser snapshot -i
# Find and click the followers link (usually shows "X followers")
agent-browser click @FOLLOWERS_REF
agent-browser wait --load networkidle

# Scroll and collect follower usernames up to (max_users - 1)
agent-browser snapshot -i
# Scroll to load more
agent-browser scroll down 500
agent-browser wait 1000
agent-browser snapshot -i
# Repeat until enough followers collected or end reached
```

Extract follower usernames until reaching `max_users - 1` (reserving 1 for seed).

### Step 6: Parallel Follower Extraction

For each follower, launch a parallel subagent using the Task tool:

```
IMPORTANT: Use the Task tool to spawn parallel agents for each follower.
Each subagent should:
1. Use a unique session name: ig_crawler_{username}_{timestamp}
2. Execute with depth=0 (extract only that user, no further followers)
3. Follow the instagram-user-crawler agent workflow
4. Save results to {output}/{follower_username}/data.json
```

**Parallel Execution Pattern:**

```
Task 1: Crawl follower_1 (depth=0, session=ig_crawler_follower1_xxx)
Task 2: Crawl follower_2 (depth=0, session=ig_crawler_follower2_xxx)
Task 3: Crawl follower_3 (depth=0, session=ig_crawler_follower3_xxx)
...
```

Each parallel task should:
1. Open a new browser session with unique session name
2. Load saved authentication state: `agent-browser state load ./instagram_auth_state.json --session {session_name}`
3. Navigate to the follower's Instagram profile
4. Extract profile, posts, and comments data
5. Save to individual JSON file
6. Close browser session

### Step 7: Aggregate Results

After all parallel crawls complete, create summary:

```json
// crawl_summary.json
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

## Example Usage

### Without authentication (public profiles only):
```
/crawl_instagram techguru --max-users 5 --output ./crawl_data/
```

### With authentication (recommended for full access):
```
/crawl_instagram techguru --max-users 5 --output ./crawl_data/ --username myemail@example.com --password mypassword123
```

This will:
1. Login to Instagram (if credentials provided)
2. Crawl `techguru`'s profile (seed user)
3. Get up to 4 of `techguru`'s followers
4. Crawl each follower's profile in parallel (using saved auth state)
5. Save all results to `./crawl_data/`

## Rate Limiting & Safety

- Add delays between requests (2-5 seconds)
- Use `agent-browser wait` commands liberally
- If rate limited, pause and retry
- Respect Instagram's terms of service

## Browser Sessions

- Seed user: `ig_crawler_seed_{timestamp}`
- Each follower: `ig_crawler_{follower_username}_{timestamp}`

Sessions are isolated, allowing true parallel execution.

## Error Handling

- Private profiles: Mark as "private" in summary, skip extraction
- Rate limits: Pause, wait, retry with backoff
- Login walls: Use `--username` and `--password` to authenticate
- Authentication failures: Report error with reason (wrong credentials, 2FA required, etc.)
- 2FA required: Pause and inform user, wait for manual code entry in headed browser
- Network errors: Retry up to 3 times

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
      "id": "string",
      "url": "string",
      "type": "image|video|carousel",
      "caption": "string",
      "like_count": "number",
      "comment_count": "number",
      "timestamp": "ISO8601"
    }
  ],
  "comments_made": [
    {
      "post_url": "string",
      "text": "string",
      "timestamp": "ISO8601"
    }
  ],
  "likes_given": [
    {
      "post_url": "string",
      "timestamp": "ISO8601"
    }
  ]
}
```
