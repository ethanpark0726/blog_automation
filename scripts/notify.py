#!/usr/bin/env python3
"""
GitHub Actions 완료 후 텔레그램으로 배포 결과 알림을 전송합니다.
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
        print("텔레그램 설정 없음 - 알림 건너뜀")
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
            print(f"텔레그램 알림 전송 완료: {resp.status}")
    except Exception as e:
        print(f"텔레그램 알림 실패: {e}")


def main():
    if not CHAT_ID:
        print("CHAT_ID가 없어 알림을 건너뜁니다.")
        return
    
    # GitHub Pages URL 생성
    owner, repo = GITHUB_REPOSITORY.split("/") if "/" in GITHUB_REPOSITORY else ("", GITHUB_REPOSITORY)
    pages_url = f"https://{owner}.github.io/{repo}/" if owner else ""
    
    if JOB_STATUS == "success":
        message = (
            f"🎉 *블로그 배포 완료!*\n\n"
            f"📝 주제: `{QUERY_INPUT}`\n\n"
            f"✅ Writer & Editor 에이전트 검수 완료\n"
            f"✅ 한국어 + 영어 포스트 2개 생성\n"
            f"✅ GitHub Pages 배포 완료\n\n"
            f"🔗 블로그 보기: [{pages_url}]({pages_url})\n\n"
            f"_새 포스트는 GitHub Pages 빌드 후 1-2분 내 반영됩니다._"
        )
    else:
        message = (
            f"❌ *블로그 배포 실패*\n\n"
            f"📝 주제: `{QUERY_INPUT}`\n"
            f"⚠️ 상태: `{JOB_STATUS}`\n\n"
            f"🔍 [GitHub Actions 로그 확인](https://github.com/{GITHUB_REPOSITORY}/actions)\n\n"
            f"문제가 반복되면 Secrets 설정을 확인해주세요."
        )
    
    send_message(CHAT_ID, message)


if __name__ == "__main__":
    main()
