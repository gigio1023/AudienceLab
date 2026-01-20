from __future__ import annotations

SNS_URL_DEFAULT = "http://localhost:18383"
DEFAULT_PASSWORD = "password"

AGENT_EMAILS = [f"agent{idx}@local.dev" for idx in range(1, 11)]
INFLUENCER_EMAILS = [f"influencer{idx}@local.dev" for idx in range(1, 4)]
ADMIN_EMAIL = "admin@local.dev"


def get_agent_email(index: int) -> str:
    if index <= 1:
        return AGENT_EMAILS[0]
    if index > len(AGENT_EMAILS):
        return AGENT_EMAILS[-1]
    return AGENT_EMAILS[index - 1]
