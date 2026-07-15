#!/usr/bin/env python3
"""Wait for the Pages workflow that deploys a generated post commit."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


RESULT_PATH = Path(os.environ.get("PAGES_RESULT_PATH", ".pages_result.json"))


def _request_json(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "blog-automation-pages-monitor",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_pages(
    repository: str,
    commit_sha: str,
    token: str,
    *,
    timeout_seconds: int = 360,
    poll_seconds: int = 10,
    request_json: Callable[[str, str], dict] = _request_json,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    """Poll deploy.yml and return a non-throwing operational status payload."""
    query = urllib.parse.urlencode(
        {"event": "push", "head_sha": commit_sha, "per_page": 10}
    )
    url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        f"deploy.yml/runs?{query}"
    )
    deadline = time.monotonic() + timeout_seconds
    last_run: dict = {}

    while time.monotonic() < deadline:
        payload = request_json(url, token)
        runs = payload.get("workflow_runs") or []
        if runs:
            last_run = runs[0]
            if last_run.get("status") == "completed":
                conclusion = last_run.get("conclusion") or "unknown"
                return {
                    "status": "success" if conclusion == "success" else "failed",
                    "conclusion": conclusion,
                    "run_url": last_run.get("html_url", ""),
                    "commit_sha": commit_sha,
                }
        sleep_fn(poll_seconds)

    return {
        "status": "timeout",
        "conclusion": last_run.get("conclusion") or "timeout",
        "run_url": last_run.get("html_url", ""),
        "commit_sha": commit_sha,
    }


def main() -> None:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    commit_sha = os.environ.get("PAGES_COMMIT_SHA", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    result: dict
    try:
        if not all((repository, commit_sha, token)):
            raise ValueError("GITHUB_REPOSITORY, PAGES_COMMIT_SHA, and GITHUB_TOKEN are required")
        result = wait_for_pages(repository, commit_sha, token)
    except Exception as error:
        result = {
            "status": "monitor_error",
            "conclusion": "unknown",
            "run_url": "",
            "commit_sha": commit_sha,
            "message": str(error)[:300],
        }

    result["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Pages deployment status: {result['status']}")


if __name__ == "__main__":
    main()
