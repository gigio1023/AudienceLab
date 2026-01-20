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

**IMPORTANT: Use a dedicated session name for login (e.g., `ig_login`) to isolate from other sessions.**

```bash
# Open Instagram login page with dedicated login session
agent-browser --session ig_login open "https://www.instagram.com/accounts/login/" --headed
agent-browser --session ig_login wait --load networkidle
agent-browser --session ig_login wait 3000

# Check for and dismiss cookie consent dialog if present
agent-browser --session ig_login snapshot -i
# Look for "닫기" (Close) button or similar cookie consent buttons and click if found
# Example: agent-browser --session ig_login click @CLOSE_BUTTON (if present)

# Get interactive elements and identify username/password fields
agent-browser --session ig_login snapshot -i
# Username field: textbox containing "전화번호" or "phone" or "username" or "email"
# Password field: textbox containing "비밀번호" or "password"

# IMPORTANT: Use 'type' instead of 'fill' for more reliable input
agent-browser --session ig_login type @USERNAME_INPUT "{username}"
agent-browser --session ig_login type @PASSWORD_INPUT "{password}"
agent-browser --session ig_login wait 500

# Re-snapshot to get updated element references (login button ref changes after typing)
agent-browser --session ig_login snapshot -i
# Find the login button (로그인) - it should now be enabled (no [disabled] tag)

# Click login button
agent-browser --session ig_login click @LOGIN_BUTTON
agent-browser --session ig_login wait --load networkidle
agent-browser --session ig_login wait 5000

# Verify login success by checking page content
agent-browser --session ig_login snapshot | head -20
# Success indicators: links containing "홈" (Home), "검색" (Search), "탐색" (Explore), "알림" (Notifications)
# If still on login page or see error message, report failure

# Save authenticated state for reuse in parallel sessions
agent-browser --session ig_login state save ./instagram_auth_state.json

# Close login session after saving state
agent-browser --session ig_login close
```

**Login Process Notes:**
- Always use `type` command instead of `fill` - it's more reliable for Instagram's input fields
- Element references change dynamically when typing (e.g., "show password" button appears)
- Re-run `snapshot -i` after filling fields to get correct login button reference
- The login button is disabled until both fields have content

**Login Success Indicators:**
- Page contains navigation elements: "홈" (Home), "릴스" (Reels), "검색" (Search)
- Links to /direct/inbox/, /explore/, /reels/ are present
- No login form elements visible

**Login Failure Handling:**
- Wrong credentials: Login form remains, may show error message
- 2FA required: Inform user, wait for manual code entry in headed browser
- Rate limited: Wait and retry with backoff
- Suspicious login: May need manual verification in browser
- Cookie consent: Dismiss by clicking "닫기" or close button before login

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

**IMPORTANT: Use a unique session name for the seed user (e.g., `ig_seed_{seed_username}`).**

```bash
# Load authenticated state into seed user session
agent-browser --session ig_seed_{seed_username} state load ./instagram_auth_state.json

# Open Instagram profile
agent-browser --session ig_seed_{seed_username} open "https://www.instagram.com/{seed_username}/" --headed
agent-browser --session ig_seed_{seed_username} wait --load networkidle
agent-browser --session ig_seed_{seed_username} snapshot -i
```

Extract from seed user:
1. **Profile info**: name, bio, follower/following counts
2. **Posts**: Recent posts with captions, likes, comments
3. **Follower list**: Click followers link and scroll to collect usernames

Save seed user data to `{output}/{seed_username}/data.json`

### Step 5: Collect Follower Usernames

From the seed user's profile, extract follower usernames:

```bash
# Click followers count to open follower modal (using seed session)
agent-browser --session ig_seed_{seed_username} snapshot -i
# Find and click the followers link (usually shows "X followers")
agent-browser --session ig_seed_{seed_username} click @FOLLOWERS_REF
agent-browser --session ig_seed_{seed_username} wait --load networkidle

# Scroll and collect follower usernames up to (max_users - 1)
agent-browser --session ig_seed_{seed_username} snapshot -i
# Scroll to load more
agent-browser --session ig_seed_{seed_username} scroll down 500
agent-browser --session ig_seed_{seed_username} wait 1000
agent-browser --session ig_seed_{seed_username} snapshot -i
# Repeat until enough followers collected or end reached

# Close seed session after collecting followers
agent-browser --session ig_seed_{seed_username} close
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
1. Create a new browser session with unique session name
2. Load saved authentication state: `agent-browser --session {session_name} state load ./instagram_auth_state.json`
3. Navigate to the follower's Instagram profile: `agent-browser --session {session_name} open "https://www.instagram.com/{follower_username}/" --headed`
4. Extract profile, posts, and comments data (all commands use `--session {session_name}`)
5. Save to individual JSON file
6. Close browser session: `agent-browser --session {session_name} close`

**CRITICAL: Each subagent MUST use `--session` flag with a unique session name for ALL agent-browser commands to ensure browser isolation.**

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

**CRITICAL: Each browser session MUST have a unique name and ALL commands for that session must include `--session {name}` flag.**

Session naming convention:
- Login session: `ig_login`
- Seed user: `ig_seed_{seed_username}`
- Each follower: `ig_crawler_{follower_username}_{timestamp}`

Example session usage:
```bash
# Session 1: Crawling follower_a
agent-browser --session ig_crawler_follower_a_12345 state load ./instagram_auth_state.json
agent-browser --session ig_crawler_follower_a_12345 open "https://www.instagram.com/follower_a/" --headed
agent-browser --session ig_crawler_follower_a_12345 snapshot -i
agent-browser --session ig_crawler_follower_a_12345 close

# Session 2 (parallel): Crawling follower_b
agent-browser --session ig_crawler_follower_b_12345 state load ./instagram_auth_state.json
agent-browser --session ig_crawler_follower_b_12345 open "https://www.instagram.com/follower_b/" --headed
agent-browser --session ig_crawler_follower_b_12345 snapshot -i
agent-browser --session ig_crawler_follower_b_12345 close
```

Sessions are isolated, allowing true parallel execution. Each session has its own browser instance.

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
