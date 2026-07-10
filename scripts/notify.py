#!/usr/bin/env python3
"""
Sends Telegram notification with deployment results after GitHub Actions workflow completes.
"""

import os
import json
import urllib.request

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
JOB_STATUS = os.environ.get("JOB_STATUS", "unknown")
QUERY_INPUT = os.environ.get("QUERY_INPUT", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")


def send_message(chat_id: str, text: str) -> None:
    if not chat_id or not TELEGRAM_BOT_TOKEN:
        print("Telegram settings missing - skipping notification")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"Telegram notification sent: {resp.status}")
    except Exception as e:
        print(f"Telegram notification failed: {e}")


def main():
    if not CHAT_ID:
        print("Skipping notification because CHAT_ID is missing.")
        return
    
    # Generate GitHub Pages URL
    owner, repo = GITHUB_REPOSITORY.split("/") if "/" in GITHUB_REPOSITORY else ("", GITHUB_REPOSITORY)
    pages_url = f"https://{owner}.github.io/{repo}/" if owner else ""
    
    if JOB_STATUS == "success":
        message = (
            f"🎉 *Blog Deployment Complete!*\n\n"
            f"📝 Topic: `{QUERY_INPUT}`\n\n"
            f"✅ Writer & Editor agents review complete\n"
            f"✅ Korean + English posts generated successfully\n"
            f"✅ Deployed to GitHub Pages\n\n"
            f"🔗 View Blog: [{pages_url}]({pages_url})\n\n"
            f"_New posts will be visible in 1-2 minutes after the GitHub Pages build completes._"
        )
    else:
        message = (
            f"❌ *Blog Deployment Failed*\n\n"
            f"📝 Topic: `{QUERY_INPUT}`\n"
            f"⚠️ Status: `{JOB_STATUS}`\n\n"
            f"🔍 [View GitHub Actions Logs](https://github.com/{GITHUB_REPOSITORY}/actions)\n\n"
            f"Please verify your Secrets configuration if this issue persists."
        )
    
    send_message(CHAT_ID, message)


if __name__ == "__main__":
    main()
