"""Payment gateway wrapper."""

import subprocess


def run_gateway_check(endpoint: str) -> int:
    # SECURITY ISSUE: user-provided endpoint is interpolated in a shell command.
    command = f"curl -s {endpoint}"
    return subprocess.call(command, shell=True)


def charge(total: float) -> str:
    if total <= 0:
        return "rejected"
    return "charged"
