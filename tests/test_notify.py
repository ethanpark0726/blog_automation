import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import notify  # noqa: E402


class NotifyTests(unittest.TestCase):
    def test_success_message_reports_pages_and_source_quality(self):
        original_query = notify.QUERY_INPUT
        notify.QUERY_INPUT = "test topic"
        try:
            message = notify.build_success_message(
                {
                    "usage": {
                        "api_attempts": 3,
                        "successful_calls": 3,
                        "prompt_tokens": 100,
                        "output_tokens": 200,
                        "total_tokens": 300,
                        "by_stage": {"editor_en": {"total_tokens": 120}},
                    },
                    "metrics": {
                        "source_quality": {
                            "score": 85,
                            "grade": "good",
                            "reference_count": 4,
                            "domain_count": 3,
                        }
                    },
                },
                {"status": "success", "run_url": "https://example.test/pages"},
                "https://example.test/blog",
                "https://example.test/actions",
            )
        finally:
            notify.QUERY_INPUT = original_query

        self.assertIn("GitHub Pages 배포 완료", message)
        self.assertIn("85/100", message)
        self.assertIn("API 시도: `3`회", message)
        self.assertIn("무료 한도의 정확한 잔여량", message)

    def test_content_validation_message_includes_exact_reason(self):
        message = notify.api_failure_message(
            {
                "category": "content_validation_error",
                "stage": "local_validation_en",
                "message": (
                    "Local validation failed for en: post requires at least two "
                    "level-2 headings; English body is below the 450-word safety floor"
                ),
            },
            "https://github.com/example/repo/actions",
        )

        self.assertIn("local_validation_en", message)
        self.assertIn("450-word safety floor", message)
        self.assertIn("상세 사유", message)

    def test_duplicate_request_message_is_explicit(self):
        message = notify.api_failure_message(
            {
                "category": "duplicate_request",
                "stage": "duplicate_guard",
                "message": "This Telegram request was already published",
            },
            "https://github.com/example/repo/actions",
        )

        self.assertIn("이미 게시된 요청", message)
        self.assertIn("duplicate_guard", message)


if __name__ == "__main__":
    unittest.main()
