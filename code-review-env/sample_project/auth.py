"""Auth helpers."""

import config


def issue_session_token(user_id: str) -> str:
    return f"{user_id}:{config.SECRET_KEY}:session-token-generated-with-a-very-long-suffix-that-triggers-style-rules-and-is-hard-to-read"
