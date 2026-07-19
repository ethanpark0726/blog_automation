#!/usr/bin/env python3
"""Send Telegram notifications for the Obsidian revision workflow."""

from __future__ import annotations

import os
import urllib.parse
import urllib.request


def changed_file_lines(raw: str, limit: int = 8) -> list[str]:
    files = [item.strip() for item in raw.split(",") if item.strip()]
    shown = files[:limit]
    lines = [f"- {path}" for path in shown]
    if len(files) > limit:
        lines.append(f"- ...and {len(files) - limit} more")
    return lines


def build_revision_message(status: str, changed_files: str, run_url: str, review_filter: str = "") -> str:
    normalized_status = (status or "").strip().lower()
    filter_label = f"\nFilter: {review_filter}" if review_filter else ""
    run_line = f"\n\nRun log: {run_url}" if run_url else ""

    if normalized_status == "success":
        lines = changed_file_lines(changed_files)
        if lines:
            return (
                "✅ Obsidian revision completed."
                f"{filter_label}\n\n"
                "Updated files:\n"
                + "\n".join(lines)
                + run_line
            )
        return (
            "ℹ️ Obsidian revision completed, but no ready review changes were found."
            f"{filter_label}"
            f"{run_line}"
        )

    return (
        "❌ Obsidian revision failed."
        f"{filter_label}"
        f"{run_line}\n\n"
        "Check the GitHub Actions log for the failed step."
    )


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = f"chat_id={chat_id}&text={urllib.parse.quote(text)}".encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("CHAT_ID", "")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN or CHAT_ID is missing; skipping revision notification.")
        return

    message = build_revision_message(
        status=os.environ.get("WORKFLOW_STATUS", ""),
        changed_files=os.environ.get("REVISION_CHANGED_FILES", ""),
        run_url=os.environ.get("GITHUB_RUN_URL", ""),
        review_filter=os.environ.get("REVIEW_FILTER", ""),
    )
    send_telegram_message(token, chat_id, message)


if __name__ == "__main__":
    main()
