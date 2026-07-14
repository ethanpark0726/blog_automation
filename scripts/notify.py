#!/usr/bin/env python3
"""Send quota-aware Telegram results after the generation workflow completes."""

import os
import json
import re
import urllib.request
from pathlib import Path

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
JOB_STATUS = os.environ.get("JOB_STATUS", "unknown")
QUERY_INPUT = os.environ.get("QUERY_INPUT", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
PIPELINE_RESULT_PATH = Path(os.environ.get("PIPELINE_RESULT_PATH", ".pipeline_result.json"))


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


def load_pipeline_result() -> dict:
    """Load the structured result written by the generation pipeline."""
    try:
        return json.loads(PIPELINE_RESULT_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Pipeline result not found: {PIPELINE_RESULT_PATH}")
    except (OSError, json.JSONDecodeError) as e:
        print(f"Pipeline result could not be read: {e}")
    return {}


def usage_summary(result: dict) -> str:
    usage = result.get("usage") or {}
    attempts = usage.get("api_attempts", 0)
    successful = usage.get("successful_calls", 0)
    prompt_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)
    if not any((attempts, successful, prompt_tokens, output_tokens, total_tokens)):
        return ""
    return (
        "\n\n📊 *Gemini 사용량 (이번 실행)*\n"
        f"• API 시도: `{attempts}`회 / 성공: `{successful}`회\n"
        f"• 입력 토큰: `{prompt_tokens:,}`\n"
        f"• 출력 토큰: `{output_tokens:,}`\n"
        f"• 총 토큰: `{total_tokens:,}`"
    )


def quota_failure_message(error: dict, logs_url: str) -> str:
    quota_type = error.get("quota_type") or "UNKNOWN"
    stage = error.get("stage") or "unknown"
    retry_after = error.get("retry_after_seconds")

    if quota_type == "RPD":
        title = "⛔ *Gemini 무료 일일 사용량 소진*"
        explanation = (
            "오늘 사용할 수 있는 일일 요청 한도를 모두 사용했습니다.\n"
            "이 오류는 재시도해도 해결되지 않아 즉시 중단했습니다.\n"
            "일일 quota는 태평양 시간 자정에 초기화됩니다."
        )
    elif quota_type == "RPM":
        title = "⏳ *Gemini 분당 요청 한도 초과*"
        explanation = "짧은 시간에 요청이 집중되어 자동 재시도 후에도 작업을 완료하지 못했습니다."
    elif quota_type == "TPM":
        title = "⏳ *Gemini 분당 토큰 한도 초과*"
        explanation = "최근 1분 동안 처리한 입력 토큰이 모델 한도를 초과했습니다."
    else:
        title = "⚠️ *Gemini API 사용 한도 초과*"
        explanation = "RPM, TPM 또는 RPD 중 어떤 한도인지 API 응답에서 확인할 수 없었습니다."

    retry_line = ""
    if retry_after is not None and quota_type != "RPD":
        retry_line = f"\n권장 대기 시간: `{float(retry_after):.0f}`초"

    return (
        f"{title}\n\n"
        f"📝 Topic: `{QUERY_INPUT}`\n"
        f"실패 단계: `{stage}`\n\n"
        f"{explanation}{retry_line}\n\n"
        f"🔍 [GitHub Actions 로그 확인]({logs_url})"
    )


def api_failure_message(error: dict, logs_url: str) -> str:
    category = error.get("category", "pipeline_error")
    stage = error.get("stage") or "unknown"
    status_code = error.get("status_code")
    detail = re.sub(r"\s+", " ", str(error.get("message") or "")).strip()
    detail = detail.replace("`", "'")[:350]

    titles = {
        "authentication_error": "🔐 *Gemini API 인증 또는 권한 오류*",
        "invalid_request": "🧩 *Gemini API 요청 형식 오류*",
        "service_unavailable": "🌐 *Gemini 서비스 일시 장애*",
        "timeout": "⌛ *Gemini API 응답 시간 초과*",
        "content_validation_error": "🧪 *생성된 콘텐츠 로컬 검증 실패*",
        "research_plan_error": "🧭 *영어 자료 조사 계획 생성 실패*",
        "source_coverage_error": "📚 *영어 참고자료 부족*",
        "unknown_api_error": "❌ *Gemini API 알 수 없는 오류*",
        "pipeline_error": "❌ *블로그 생성 파이프라인 오류*",
    }
    title = titles.get(category, titles["pipeline_error"])
    status_line = f"\nHTTP 상태: `{status_code}`" if status_code else ""
    detail_line = f"\n상세 사유: `{detail}`" if detail else ""
    return (
        f"{title}\n\n"
        f"📝 Topic: `{QUERY_INPUT}`\n"
        f"실패 단계: `{stage}`{status_line}{detail_line}\n\n"
        f"🔍 [GitHub Actions 로그 확인]({logs_url})"
    )


def main():
    if not CHAT_ID:
        print("Skipping notification because CHAT_ID is missing.")
        return
    
    # Generate GitHub Pages URL
    owner, repo = GITHUB_REPOSITORY.split("/") if "/" in GITHUB_REPOSITORY else ("", GITHUB_REPOSITORY)
    pages_url = f"https://{owner}.github.io/{repo}/" if owner else ""
    logs_url = f"https://github.com/{GITHUB_REPOSITORY}/actions"
    result = load_pipeline_result()
    usage = usage_summary(result)
    
    if JOB_STATUS == "success":
        message = (
            f"🎉 *Blog Generation Complete!*\n\n"
            f"📝 Topic: `{QUERY_INPUT}`\n\n"
            f"✅ English research coverage and fact-check complete\n"
            f"✅ Validated English article localized into Korean\n"
            f"✅ Saved to GitHub; Pages deployment has started\n\n"
            f"🔗 View Blog: [{pages_url}]({pages_url})\n\n"
            f"_New posts will be visible in 1-2 minutes after the GitHub Pages build completes._"
            f"{usage}"
        )
    else:
        error = result.get("error") or {}
        if error.get("category") == "quota_exhausted":
            message = quota_failure_message(error, logs_url) + usage
        elif error:
            message = api_failure_message(error, logs_url) + usage
        else:
            message = (
                f"❌ *Blog Automation Failed*\n\n"
                f"📝 Topic: `{QUERY_INPUT}`\n"
                f"⚠️ Status: `{JOB_STATUS}`\n\n"
                f"🔍 [GitHub Actions 로그 확인]({logs_url})"
                f"{usage}"
            )
    
    send_message(CHAT_ID, message)


if __name__ == "__main__":
    main()
