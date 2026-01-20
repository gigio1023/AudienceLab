import os
import json
import glob
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
DATA_DIR = Path("../agent/outputs/multi_agent_test")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)

if not OPENAI_API_KEY and not OPENAI_BASE_URL:
    print("Warning: OPENAI_API_KEY not found. LLM Judge will fail.")

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

def main():
    actions = []
    # Search for actions.jsonl in subdirectories
    files = glob.glob(str(DATA_DIR / "**" / "actions.jsonl"), recursive=True)
    
    print(f"Found {len(files)} log files in {DATA_DIR}")
    
    for f in files:
        agent_id = Path(f).parent.name
        with open(f, 'r') as file:
            for line in file:
                try:
                    data = json.loads(line)
                    # Flatten relevant fields
                    decision = data.get("decision", {})
                    result = data.get("result", {})
                    
                    row = {
                        "agent_id": agent_id,
                        "timestamp": data.get("timestamp"),
                        "step": data.get("step"),
                        "action": decision.get("action"),
                        "success": result.get("success", False),
                        "target": decision.get("target"),
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
    
    # Action Distribution
    action_counts = df.groupby(['action', 'success']).size().unstack(fill_value=0)
    
    print("\n=== Quantitative Metrics ===")
    print(f"Total Agents: {total_agents}")
    print(f"Total Steps: {total_steps}")
    print(f"Total Engagements (Like/Comment/Follow): {engagement_count}")
    print(f"Engagement Rate: {engagement_rate:.2%}")
    print("\nAction Distribution:")
    print(action_counts)
    
    # 2. LLM Judge on Comments
    # We only evalaute successful comments that have text
    comments = df[
        (df['action'] == 'comment') & 
        (df['success'] == True) & 
        (df['comment_text'].notna()) & 
        (df['comment_text'] != "")
    ]
    
    judge_results = []
    if not comments.empty:
        print(f"\n=== LLM Judge Evaluation ({len(comments)} comments) ===")
        print("Running LLM evaluation (this may take a moment)...")
        
        for idx, row in comments.iterrows():
            res = evaluate_comment(row['reasoning'], row['comment_text'])
            if res:
                judge_results.append({
                    "agent_id": row['agent_id'],
                    "step": row['step'],
                    "comment": row['comment_text'],
                    "reasoning": row['reasoning'],
                    "relevance": res.relevance_score,
                    "tone": res.tone_score,
                    "consistency": res.consistency_score,
                    "explanation": res.explanation
                })
                print(f"[{row['agent_id']}]: R={res.relevance_score} T={res.tone_score} C={res.consistency_score}")
    else:
        print("\nNo successful comments found to evaluate.")

    # 3. Verdict & Grading System
    print("\n=== Performance Verdict (종합 평가) ===")
    
    # Engagement Grade
    if engagement_rate >= 0.5:
        eng_grade = "High (적극적)"
        eng_msg = "에이전트가 매우 적극적으로 상호작용하고 있습니다."
    elif engagement_rate >= 0.2:
        eng_grade = "Medium (보통)"
        eng_msg = "에이전트가 적절한 수준의 상호작용을 보입니다."
    else:
        eng_grade = "Low (소극적)"
        eng_msg = "에이전트의 상호작용 비율이 낮습니다. 개선이 필요할 수 있습니다."

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
    
    # 4. Save Reports
    
    # CSV Report of Judgments
    if judge_results:
        judged_df.to_csv("comment_quality_eval.csv", index=False)
        print("\n--- Average Quality Scores ---")
        print(avg_scores)
    else:
        avg_scores = None

    # Markdown Summary
    with open("evaluation_report.md", "w") as f:
        f.write("# AudienceLab Agent Evaluation Report\n\n")
        
        f.write("## 1. Executive Summary (종합 평가)\n")
        f.write("| Metric | Score | Grade | Verdict |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Engagement Rate** | {engagement_rate:.1%} | **{eng_grade}** | {eng_msg} |\n")
        if avg_scores is not None:
             f.write(f"| **Interaction Quality** | {avg_quality_score:.2f}/5.0 | **{quality_grade}** | {quality_msg} |\n")
        else:
             f.write(f"| **Interaction Quality** | N/A | N/A | 평가할 댓글이 없습니다. |\n")

        f.write("\n## 2. Quantitative Metrics (정량 지표)\n")
        f.write(f"- **Total Agents Active**: {total_agents}\n")
        f.write(f"- **Total recorded steps**: {total_steps}\n")
        f.write(f"- **Total Successful Engagements**: {engagement_count}\n")
        
        f.write("\n### Action Breakdown\n")
        f.write(action_counts.to_markdown())
        
        f.write("\n\n## 3. Qualitative Analysis (정성 평가 - LLM)\n")
        if avg_scores is not None:
            f.write("### Average Scores (1-5)\n")
            f.write(f"- **Relevance**: {avg_scores['relevance']:.2f}\n")
            f.write(f"- **Tone**: {avg_scores['tone']:.2f}\n")
            f.write(f"- **Consistency**: {avg_scores['consistency']:.2f}\n")
            
            f.write("\n### Detailed Comments Evaluation\n")
            f.write(judged_df[['agent_id', 'comment', 'relevance', 'tone', 'consistency', 'explanation']].to_markdown())
        else:
            f.write("No comments were available for qualitative evaluation.\n")

    print("\nReport saved to evaluation_report.md and comment_quality_eval.csv")

if __name__ == "__main__":
    main()
