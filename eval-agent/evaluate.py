import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Load env from agent directory
agent_env = Path("../agent/.env")
if agent_env.exists():
    load_dotenv(agent_env)

# Config
DATA_DIR = Path("../search-dashboard/public/simulation")
SEED_POSTS_PATH = Path("../sns-vibe/seeds/posts.json")
FEED_INDEX = DATA_DIR / "index.json"
MARKETING_TAGS = ("#ad", "#sponsored")
seed_ids = set()
marketing_post_ids = set()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
OPENAI_MAX_WORKERS = int(os.getenv("OPENAI_MAX_WORKERS", "16"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required to run the evaluator.")

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL if OPENAI_BASE_URL else None)

class JudgeResult(BaseModel):
    relevance_score: int = Field(description="1-5 score on relevance to context/reasoning")
    tone_score: int = Field(description="1-5 score on appropriate tone for the persona")
    consistency_score: int = Field(description="1-5 score on consistency between reasoning and action")
    explanation: str

def evaluate_comment(reasoning, comment):
    prompt = f"""
    Evaluate the following social media comment action performed by an AI agent.
    
    Agent Reasoning for Action: "{reasoning}"
    Actual Comment Posted: "{comment}"
    
    Assess the quality of this interaction:
    1. Relevance: Does the comment actually address the topic mentions in the reasoning?
    2. Tone: Is the comment style appropriate (supportive, casual, etc) as implied by the reasoning?
    3. Consistency: Does the actual comment match the intent described in the reasoning?
    
    Provide integer scores (1-5) for each and a brief explanation.
    """
    
    try:
        completion = client.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a social media engagement evaluator evaluating AI agent performance."},
                {"role": "user", "content": prompt},
            ],
            response_format=JudgeResult
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"LLM Call failed: {e}")
        return None

def load_feed_files():
    if FEED_INDEX.exists():
        with open(FEED_INDEX, "r") as file:
            index = json.load(file)
        return [DATA_DIR / name for name in index.get("files", [])]
    return list(DATA_DIR.glob("local-*.jsonl"))

def normalize_target_id(target):
    if not target:
        return None
    if target in seed_ids:
        return target
    if target.startswith("post-"):
        raw = target[len("post-"):]
        if raw.isdigit():
            return raw.zfill(3)
        return raw
    return target

def is_marketing_post(post_id):
    return post_id in marketing_post_ids

def main():
    if not SEED_POSTS_PATH.exists():
        print(f"Missing seed posts file: {SEED_POSTS_PATH}")
        return

    with open(SEED_POSTS_PATH, "r") as file:
        seed_posts = json.load(file)

    global seed_ids, marketing_post_ids
    seed_ids = {post["id"] for post in seed_posts}
    marketing_post_ids = {
        post["id"]
        for post in seed_posts
        if any(tag in post.get("content", "").lower() for tag in MARKETING_TAGS)
    }

    actions = []
    files = load_feed_files()

    print(f"Found {len(files)} log files in {DATA_DIR}")

    for f in files:
        agent_id = f.stem
        with open(f, "r") as file:
            for line in file:
                try:
                    data = json.loads(line)
                    # Flatten relevant fields
                    decision = data.get("decision", {})
                    result = data.get("result", {})
                    
                    target = decision.get("target")
                    normalized_target = normalize_target_id(target)

                    row = {
                        "agent_id": data.get("agentId", agent_id),
                        "timestamp": data.get("timestamp"),
                        "step": data.get("step"),
                        "action": decision.get("action"),
                        "success": result.get("success", False),
                        "target": target,
                        "normalized_target": normalized_target,
                        "is_marketing_post": is_marketing_post(normalized_target),
                        "comment_text": result.get("comment") or decision.get("comment_text"), # Use result comment if available, else decision
                        "reasoning": decision.get("reasoning")
                    }
                    actions.append(row)
                except Exception as e:
                    print(f"Skipping bad line in {f}: {e}")
                    continue
                    
    df = pd.DataFrame(actions)
    if df.empty:
        print("No actions found.")
        return

    # 1. Quantitative Stats
    total_steps = len(df)
    total_agents = df['agent_id'].nunique()
    
    # Successful engagements (Like, Comment, Follow)
    engagements = df[
        (df['success'] == True) & 
        (df['action'].isin(['like', 'comment', 'follow']))
    ]
    
    engagement_count = len(engagements)
    # Engagement Rate: Successful Interactions / Total Steps
    engagement_rate = engagement_count / total_steps if total_steps > 0 else 0

    marketing_engagements = engagements[
        (engagements['is_marketing_post'] == True) &
        (engagements['action'].isin(['like', 'comment']))
    ]
    marketing_engagement_count = len(marketing_engagements)
    marketing_engagement_rate = (
        marketing_engagement_count / total_steps if total_steps > 0 else 0
    )
    
    # Action Distribution
    action_counts = df.groupby(['action', 'success']).size().unstack(fill_value=0)
    
    print("\n=== Quantitative Metrics ===")
    print(f"Total Agents: {total_agents}")
    print(f"Total Steps: {total_steps}")
    print(f"Total Engagements (Like/Comment/Follow): {engagement_count}")
    print(f"Engagement Rate: {engagement_rate:.2%}")
    print(f"Marketing Engagements (Like/Comment): {marketing_engagement_count}")
    print(f"Marketing Engagement Rate: {marketing_engagement_rate:.2%}")
    print("\nAction Distribution:")
    print(action_counts)

    # 2. LLM Judge on Comments
    # We only evaluate successful comments that have text on marketing posts
    comments = df[
        (df['action'] == 'comment') & 
        (df['success'] == True) & 
        (df['is_marketing_post'] == True) &
        (df['comment_text'].notna()) & 
        (df['comment_text'] != "")
    ]
    
    judge_results = []
    if not comments.empty:
        print(f"\n=== LLM Judge Evaluation ({len(comments)} comments) ===")
        print("Running LLM evaluation (this may take a moment)...")
        
        comment_rows = list(comments.to_dict(orient="records"))
        worker_count = max(1, min(OPENAI_MAX_WORKERS, len(comment_rows)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    evaluate_comment,
                    row["reasoning"],
                    row["comment_text"],
                ): row
                for row in comment_rows
            }
            for future in as_completed(futures):
                row = futures[future]
                res = future.result()
                if res:
                    judge_results.append({
                        "agent_id": row["agent_id"],
                        "step": row["step"],
                        "comment": row["comment_text"],
                        "reasoning": row["reasoning"],
                        "relevance": res.relevance_score,
                        "tone": res.tone_score,
                        "consistency": res.consistency_score,
                        "explanation": res.explanation
                    })
                    print(f"[{row['agent_id']}]: R={res.relevance_score} T={res.tone_score} C={res.consistency_score}")
    else:
        print("\nNo successful marketing comments found to evaluate.")

    # 3. Verdict & Grading System
    print("\n=== Performance Verdict (종합 평가) ===")
    
    # Engagement Grade
    if marketing_engagement_rate >= 0.5:
        eng_grade = "High (적극적)"
        eng_msg = "마케팅 포스트에 대해 매우 적극적으로 상호작용하고 있습니다."
    elif marketing_engagement_rate >= 0.2:
        eng_grade = "Medium (보통)"
        eng_msg = "마케팅 포스트에 대해 적절한 수준의 상호작용을 보입니다."
    else:
        eng_grade = "Low (소극적)"
        eng_msg = "마케팅 포스트에 대한 상호작용 비율이 낮습니다. 개선이 필요할 수 있습니다."

    print(f"Engagement Level: {eng_grade}")
    print(f"Comment: {eng_msg}")

    # Quality Grade
    quality_grade = "N/A"
    quality_msg = "평가된 댓글이 없습니다."
    
    avg_quality_score = 0
    if judge_results:
        judged_df = pd.DataFrame(judge_results)
        avg_scores = judged_df[['relevance', 'tone', 'consistency']].mean()
        avg_quality_score = avg_scores.mean() # Total Average
        
        if avg_quality_score >= 4.5:
            quality_grade = "Excellent (최우수)"
            quality_msg = "에이전트가 페르소나에 완벽히 부합하며 맥락에 맞는 고품질 댓글을 작성합니다."
        elif avg_quality_score >= 4.0:
            quality_grade = "Good (우수)"
            quality_msg = "대체로 좋은 품질의 상호작용을 보이나, 일부 개선의 여지가 있을 수 있습니다."
        elif avg_quality_score >= 3.0:
            quality_grade = "Fair (보통)"
            quality_msg = "무난한 수준이지만, 페르소나의 매력을 더 살리거나 맥락을 더 깊게 파악할 필요가 있습니다."
        else:
            quality_grade = "Poor (미흡)"
            quality_msg = "상호작용의 품질이 낮습니다. 프롬프트나 로직 개선이 시급합니다."
            
        print(f"Quality Score: {avg_quality_score:.2f} / 5.0")
        print(f"Quality Grade: {quality_grade}")
        print(f"Comment: {quality_msg}")
    
    if judge_results:
        print("\n--- Average Quality Scores ---")
        print(avg_scores)
    else:
        avg_scores = None

if __name__ == "__main__":
    main()
