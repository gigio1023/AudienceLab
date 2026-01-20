
import json
import random
from datetime import datetime, timedelta

def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Load existing data
users = load_json('seeds/users.json')
posts = load_json('seeds/posts.json')
follows = load_json('seeds/follows.json')
likes = load_json('seeds/likes.json')
comments = load_json('seeds/comments.json')

# New influencer
influencer_username = "mens_style_hero"

# Identify agents
agents = [u['username'] for u in users if u['username'].startswith('agent')]

# 1. Generate Posts
new_posts = []
start_date = datetime.now() - timedelta(days=10)

captions = [
    "Summer vibes in the city. Linen suits are a must. #menswear #summerstyle",
    "Streetwear essentials: Hoodie + Cargo pants. simple but effective. #streetwear #ootd",
    "A gentleman's guide to accessories. Watch, ring, and confidence. #accessories #details",
    "Casual Friday. Denim on denim. #denim #casualstyle",
    "Sneaker rotation update. Which one is your favorite? #sneakers #kotd",
    "Suit up! Preparing for the gala tonight. #blacktie #formalwear",
    "Weekend getaway style. Comfortable yet sharp. #travelstyle #weekend",
    "Minimalist wardrobe: 5 pieces, 10 outfits. #minimalism #capsulewardrobe",
    "Layering tips for fall. Stay warm, look cool. #fallfashion #layering",
    "Gym fit vs Street fit. Balance is key. #gymwear #athleisure",
    "Vintage finding: 90s leather jacket. absolute gem. #vintage #thrift",
    "Morning coffee run. oversized tee and shorts. #chill #lifestyle",
    "Defining modern masculinity through style. #style #inspiration"
]

# Marketing posts (Indices 3 and 8, for example)
marketing_indices = [3, 8]

for i, caption in enumerate(captions):
    is_marketing = i in marketing_indices
    post_content = caption
    if is_marketing:
        post_content += " #ad #sponsored"
    
    post = {
        "id": f"mph_{i+1:03d}",
        "username": influencer_username,
        "content": post_content,
        "image_url": f"/samples/men_style_{i+1}.jpg",
        "createdAt": (start_date + timedelta(days=i*0.5)).isoformat()
    }
    new_posts.append(post)

# Append new posts if not already present (check by id)
existing_ids = {p['id'] for p in posts}
for p in new_posts:
    if p['id'] not in existing_ids:
        posts.append(p)

# 2. Generate Follows
# All agents follow the influencer
existing_follows = {(f['follower'], f['following']) for f in follows}
for agent in agents:
    if (agent, influencer_username) not in existing_follows:
        follows.append({
            "follower": agent,
            "following": influencer_username
        })

# 3. Generate Likes & Comments
comment_templates = [
    "fire fit! 🔥",
    "clean look man",
    "where did you get those shoes?",
    "always best style",
    "goals 💯",
    "looking sharp!",
    "details are crazy",
    "saving this for inspo",
    "sheesh 🥶",
    "classy as always",
    "need this outfit",
    "big mood",
    "🔥🔥🔥"
]

marketing_comment_templates = [
    "Just bought this!",
    "Is this available online?",
    "Great collab!",
    "Checking the link now",
    "Does it come in black?",
    "Need to cop ASAP",
    "Best ad I've seen",
    "Ordering mine today"
]

for post in new_posts:
    post_id = post['id']
    is_marketing = "#ad" in post['content']
    
    for agent in agents:
        # Engagement probability
        # Marketing posts might get slightly more engagement or specific comments
        like_prob = 0.8 if is_marketing else 0.6
        comment_prob = 0.5 if is_marketing else 0.3
        
        # Like
        if random.random() < like_prob:
            # Check if exists
            if not any(l.get('username') == agent and l.get('post_id') == post_id for l in likes): 
                # Note: likes.json uses 'username' and 'post_id', not 'user_id' based on previous view_file
                # Let me double check likes.json structure from previous steps.
                # Step 20 db.ts says: loadFile('likes.json') -> {username, post_id}
                # Step 8 likes.json size 6393.
                pass
            
            # Since checking existence in a large list is slow, we'll just append and assume unique logic or relying on DB unique constraint handling in seed.ts (INSERT OR IGNORE)
            # But seed.ts reads the file directly.
            # Let's just create the list of new likes and append.
            likes.append({
                "username": agent,
                "post_id": post_id
            })

        # Comment
        if random.random() < comment_prob:
            templates = marketing_comment_templates if is_marketing and random.random() < 0.7 else comment_templates
            content = random.choice(templates)
            comments.append({
                "username": agent,
                "post_id": post_id,
                "content": content,
                "createdAt": (datetime.fromisoformat(post['createdAt']) + timedelta(minutes=random.randint(5, 120))).isoformat()
            })

# Save all
save_json('seeds/posts.json', posts)
save_json('seeds/follows.json', follows)
save_json('seeds/likes.json', likes)
save_json('seeds/comments.json', comments)

print(f"Generated {len(new_posts)} posts for {influencer_username}")
print(f"Updated seeds with engagement data.")
