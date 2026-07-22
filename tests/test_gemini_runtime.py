import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from gemini_runtime import (  # noqa: E402
    GeminiRequestError,
    UsageTracker,
    call_gemini,
    classify_gemini_error,
    write_pipeline_result,
)
import notify  # noqa: E402


class FakeApiError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class FakeResponse:
    def __init__(self, text: str = "ok"):
        self.text = text
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=120,
            candidates_token_count=30,
            total_token_count=150,
        )
        self.candidates = [SimpleNamespace(finish_reason="STOP")]


class SequenceModel:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.generation_configs = []

    def generate_content(self, _prompt, **kwargs):
        self.generation_configs.append(kwargs.get("generation_config"))
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class GeminiRuntimeTests(unittest.TestCase):
    def test_classifies_daily_free_tier_quota(self):
        error = FakeApiError(
            "429 RESOURCE_EXHAUSTED: GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            429,
        )

        info = classify_gemini_error(error)

        self.assertEqual(info.category, "quota_exhausted")
        self.assertEqual(info.quota_type, "RPD")
        self.assertFalse(info.retryable)

    def test_classifies_rpm_and_retry_delay(self):
        error = FakeApiError(
            "429 RESOURCE_EXHAUSTED: requests per minute; retry in 12.5s",
            429,
        )

        info = classify_gemini_error(error)

        self.assertEqual(info.quota_type, "RPM")
        self.assertTrue(info.retryable)
        self.assertEqual(info.retry_after_seconds, 12.5)

    def test_daily_quota_stops_without_retry(self):
        model = SequenceModel(
            [FakeApiError("429 requests per day free tier quota", 429)]
        )
        tracker = UsageTracker()

        with self.assertRaises(GeminiRequestError) as raised:
            call_gemini(
                model,
                "prompt",
                "writer_ko",
                tracker,
                retry=3,
                initial_delay_seconds=0,
                sleep_fn=lambda _seconds: None,
            )

        self.assertEqual(model.calls, 1)
        self.assertEqual(tracker.snapshot()["api_attempts"], 1)
        self.assertEqual(raised.exception.info.quota_type, "RPD")

    def test_transient_rpm_retries_and_tracks_usage(self):
        model = SequenceModel(
            [
                FakeApiError("429 requests per minute; retry in 2s", 429),
                FakeResponse(" finished "),
            ]
        )
        tracker = UsageTracker()
        delays = []

        result = call_gemini(
            model,
            "prompt",
            "classifier",
            tracker,
            retry=3,
            initial_delay_seconds=0,
            sleep_fn=delays.append,
        )

        usage = tracker.snapshot()
        self.assertEqual(result, "finished")
        self.assertEqual(delays, [2.0])
        self.assertEqual(usage["api_attempts"], 2)
        self.assertEqual(usage["successful_calls"], 1)
        self.assertEqual(usage["prompt_tokens"], 120)
        self.assertEqual(usage["output_tokens"], 30)
        self.assertEqual(usage["total_tokens"], 150)

    def test_forwards_stage_generation_config(self):
        model = SequenceModel([FakeResponse()])
        tracker = UsageTracker()
        config = {"temperature": 0.2, "max_output_tokens": 8192}

        call_gemini(
            model,
            "prompt",
            "editor_ko",
            tracker,
            generation_config=config,
            initial_delay_seconds=0,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(model.generation_configs, [config])

    def test_success_log_includes_output_tokens_and_finish_reason(self):
        model = SequenceModel([FakeResponse()])
        tracker = UsageTracker()
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            call_gemini(
                model,
                "prompt",
                "revision_en",
                tracker,
                initial_delay_seconds=0,
                sleep_fn=lambda _seconds: None,
            )

        self.assertIn("output_tokens=30", output.getvalue())
        self.assertIn("finish_reason=STOP", output.getvalue())

    def test_writes_structured_failure_result(self):
        tracker = UsageTracker()
        tracker.record_attempt("writer_en")
        info = classify_gemini_error(
            FakeApiError("429 requests per day free tier quota", 429)
        )
        error = GeminiRequestError("writer_en", 1, info)

        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            write_pipeline_result("failed", tracker, error=error, path=result_path)
            payload = result_path.read_text(encoding="utf-8")

        self.assertIn('"quota_type": "RPD"', payload)
        self.assertIn('"stage": "writer_en"', payload)
        self.assertIn('"api_attempts": 1', payload)

    def test_daily_quota_telegram_message_is_explicit(self):
        original_query = notify.QUERY_INPUT
        notify.QUERY_INPUT = "test topic"
        try:
            message = notify.quota_failure_message(
                {
                    "quota_type": "RPD",
                    "stage": "writer_en",
                    "retry_after_seconds": None,
                },
                "https://github.com/example/repo/actions",
            )
        finally:
            notify.QUERY_INPUT = original_query

        self.assertIn("무료 일일 사용량 소진", message)
        self.assertIn("즉시 중단", message)
        self.assertIn("writer_en", message)


if __name__ == "__main__":
    unittest.main()
