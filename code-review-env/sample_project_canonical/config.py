from __future__ import annotations


def get_config() -> dict[str, str]:
    # Hard root cause: required key auth_provider is missing.
    return {
        "api_base": "https://example.internal",
    }
