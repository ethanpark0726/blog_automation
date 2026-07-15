"""Shared Gemini API runtime utilities.

This module centralizes request accounting, retry decisions, error classification,
and the structured result consumed by the Telegram notification step.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


RESULT_PATH = Path(".pipeline_result.json")


def _read_value(source: Any, *names: str, default: int = 0) -> int:
    if source is None:
        return default
    for name in names:
        value = source.get(name) if isinstance(source, dict) else getattr(source, name, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return default


class UsageTracker:
    """Accumulates request attempts and token usage for one pipeline run."""

    def __init__(self) -> None:
        self.api_attempts = 0
        self.successful_calls = 0
        self.prompt_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.by_stage: dict[str, dict[str, int]] = {}

    def record_attempt(self, stage: str) -> None:
        self.api_attempts += 1
        stage_usage = self.by_stage.setdefault(stage, self._empty_stage())
        stage_usage["attempts"] += 1

    def record_success(self, stage: str, response: Any) -> None:
        metadata = getattr(response, "usage_metadata", None)
        prompt_tokens = _read_value(metadata, "prompt_token_count", "promptTokenCount")
        output_tokens = _read_value(
            metadata, "candidates_token_count", "candidatesTokenCount"
        )
        total_tokens = _read_value(metadata, "total_token_count", "totalTokenCount")
        if not total_tokens:
            total_tokens = prompt_tokens + output_tokens

        self.successful_calls += 1
        self.prompt_tokens += prompt_tokens
        self.output_tokens += output_tokens
        self.total_tokens += total_tokens

        stage_usage = self.by_stage.setdefault(stage, self._empty_stage())
        stage_usage["successful_calls"] += 1
        stage_usage["prompt_tokens"] += prompt_tokens
        stage_usage["output_tokens"] += output_tokens
        stage_usage["total_tokens"] += total_tokens

    def snapshot(self) -> dict[str, Any]:
        return {
            "api_attempts": self.api_attempts,
            "successful_calls": self.successful_calls,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "by_stage": self.by_stage,
        }

    @staticmethod
    def _empty_stage() -> dict[str, int]:
        return {
            "attempts": 0,
            "successful_calls": 0,
            "prompt_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }


@dataclass(frozen=True)
class GeminiErrorInfo:
    category: str
    status_code: int | None
    quota_type: str | None
    retryable: bool
    retry_after_seconds: float | None
    message: str

    def to_dict(self, stage: str, attempts: int) -> dict[str, Any]:
        return {
            "category": self.category,
            "status_code": self.status_code,
            "quota_type": self.quota_type,
            "retryable": self.retryable,
            "retry_after_seconds": self.retry_after_seconds,
            "stage": stage,
            "attempts": attempts,
            "message": self.message[:500],
        }


class GeminiRequestError(RuntimeError):
    """A Gemini failure that retains machine-readable diagnostic information."""

    def __init__(self, stage: str, attempts: int, info: GeminiErrorInfo) -> None:
        self.stage = stage
        self.attempts = attempts
        self.info = info
        super().__init__(self._summary())

    def _summary(self) -> str:
        if self.info.category == "quota_exhausted":
            quota = self.info.quota_type or "UNKNOWN"
            return f"Gemini quota exceeded ({quota}) during {self.stage}."
        status = f" HTTP {self.info.status_code}" if self.info.status_code else ""
        return f"Gemini API error{status} during {self.stage}: {self.info.category}."

    def to_dict(self) -> dict[str, Any]:
        return self.info.to_dict(self.stage, self.attempts)


def _exception_text(exc: Exception) -> str:
    values = [str(exc), repr(exc), exc.__class__.__name__]
    for attribute in ("errors", "details", "reason"):
        value = getattr(exc, attribute, None)
        if value:
            values.append(str(value))
    return " | ".join(values)


def _status_code(exc: Exception, text: str) -> int | None:
    candidates = [getattr(exc, "status_code", None), getattr(exc, "code", None)]
    response = getattr(exc, "response", None)
    if response is not None:
        candidates.append(getattr(response, "status_code", None))

    for value in candidates:
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
        if hasattr(value, "value"):
            value = value.value
        if isinstance(value, (tuple, list)) and value:
            value = value[0]
        try:
            code = int(value)
        except (TypeError, ValueError):
            continue
        if 100 <= code <= 599:
            return code

    lowered = text.lower()
    class_name = exc.__class__.__name__.lower()
    known_names = {
        "resourceexhausted": 429,
        "toomanyrequests": 429,
        "invalidargument": 400,
        "unauthenticated": 401,
        "permissiondenied": 403,
        "deadlineexceeded": 504,
        "internalservererror": 500,
        "serviceunavailable": 503,
    }
    for name, code in known_names.items():
        if name in class_name:
            return code
    for code in (400, 401, 403, 408, 429, 500, 502, 503, 504):
        if re.search(rf"(?:^|\D){code}(?:\D|$)", lowered):
            return code
    return None


def _quota_type(text: str) -> str | None:
    lowered = text.lower()
    compact = re.sub(r"[^a-z0-9]", "", lowered)

    rpd_patterns = (
        "requests per day",
        "request per day",
        "per_day",
        "daily request",
        "rpd",
    )
    if any(pattern in lowered for pattern in rpd_patterns) or any(
        pattern in compact
        for pattern in (
            "requestsperday",
            "generaterequestsperday",
            "generaterequestspermodelperday",
        )
    ):
        return "RPD"

    tpm_patterns = ("tokens per minute", "token per minute", "tokens_per_minute", "tpm")
    if any(pattern in lowered for pattern in tpm_patterns) or any(
        pattern in compact for pattern in ("tokensperminute", "inputtokenspermodelperminute")
    ):
        return "TPM"

    rpm_patterns = (
        "requests per minute",
        "request per minute",
        "requests_per_minute",
        "rpm",
    )
    if any(pattern in lowered for pattern in rpm_patterns) or any(
        pattern in compact for pattern in ("requestsperminute", "requestspermodelperminute")
    ):
        return "RPM"
    return None


def _retry_after_seconds(exc: Exception, text: str) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) if response is not None else None
    if headers:
        value = headers.get("retry-after") or headers.get("Retry-After")
        try:
            return float(value)
        except (TypeError, ValueError):
            pass

    for detail in getattr(exc, "details", []) or []:
        delay = getattr(detail, "retry_delay", None) or getattr(detail, "retryDelay", None)
        if delay is not None:
            seconds = getattr(delay, "seconds", 0)
            nanos = getattr(delay, "nanos", 0)
            if seconds or nanos:
                return float(seconds) + float(nanos) / 1_000_000_000

    patterns = (
        r"retry(?:\s+in|\s+after|delay)?[^0-9]{0,20}(\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?",
        r"retryDelay[^0-9]{0,10}(\d+(?:\.\d+)?)s",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def classify_gemini_error(exc: Exception) -> GeminiErrorInfo:
    text = _exception_text(exc)
    status = _status_code(exc, text)
    quota = _quota_type(text) if status == 429 else None
    retry_after = _retry_after_seconds(exc, text)

    if status == 429:
        category = "quota_exhausted"
        retryable = quota != "RPD"
    elif status in (401, 403):
        category = "authentication_error"
        retryable = False
    elif status == 400:
        category = "invalid_request"
        retryable = False
    elif status in (408, 504):
        category = "timeout"
        retryable = True
    elif status in (500, 502, 503):
        category = "service_unavailable"
        retryable = True
    else:
        category = "unknown_api_error"
        retryable = False

    return GeminiErrorInfo(
        category=category,
        status_code=status,
        quota_type=quota,
        retryable=retryable,
        retry_after_seconds=retry_after,
        message=text,
    )


def call_gemini(
    model: Any,
    prompt: str,
    stage: str,
    tracker: UsageTracker,
    retry: int = 3,
    generation_config: Any | None = None,
    initial_delay_seconds: float = 5,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> str:
    """Call Gemini with quota-aware retry handling and usage accounting."""

    if initial_delay_seconds > 0:
        sleep_fn(initial_delay_seconds)

    last_info: GeminiErrorInfo | None = None
    for attempt in range(1, retry + 1):
        tracker.record_attempt(stage)
        try:
            if generation_config is None:
                response = model.generate_content(prompt)
            else:
                response = model.generate_content(prompt, generation_config=generation_config)
            tracker.record_success(stage, response)
            return response.text.strip()
        except Exception as exc:
            last_info = classify_gemini_error(exc)
            quota = f", quota={last_info.quota_type}" if last_info.quota_type else ""
            print(
                f"[Gemini:{stage}] Attempt {attempt}/{retry} failed "
                f"(category={last_info.category}, status={last_info.status_code}{quota}): {exc}"
            )

            if not last_info.retryable or attempt == retry:
                raise GeminiRequestError(stage, attempt, last_info) from exc

            delay = last_info.retry_after_seconds or (5 * (2 ** (attempt - 1)))
            delay = min(60.0, max(1.0, delay))
            print(f"[Gemini:{stage}] Retrying in {delay:.1f} seconds...")
            sleep_fn(delay)

    raise GeminiRequestError(stage, retry, last_info or classify_gemini_error(RuntimeError()))


def reset_pipeline_result(path: Path = RESULT_PATH) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def write_pipeline_result(
    status: str,
    tracker: UsageTracker,
    *,
    error: Exception | None = None,
    created_files: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    path: Path = RESULT_PATH,
) -> None:
    error_payload: dict[str, Any] | None = None
    if isinstance(error, GeminiRequestError):
        error_payload = error.to_dict()
    elif error is not None:
        error_payload = {
            "category": getattr(error, "category", "pipeline_error"),
            "status_code": None,
            "quota_type": None,
            "retryable": False,
            "retry_after_seconds": None,
            "stage": getattr(error, "stage", None),
            "attempts": 0,
            "message": str(error)[:500],
        }

    payload = {
        "status": status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "usage": tracker.snapshot(),
        "metrics": metrics or {},
        "created_files": created_files or [],
        "error": error_payload,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
