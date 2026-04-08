from __future__ import annotations

from api import checkout_endpoint


def run() -> dict[str, str]:
    return checkout_endpoint("tok_demo", 100)


if __name__ == "__main__":
    print(run())
