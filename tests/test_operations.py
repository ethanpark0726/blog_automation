import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from operations_summary import build_summary  # noqa: E402
from pages_status import wait_for_pages  # noqa: E402


class OperationsTests(unittest.TestCase):
    def test_wait_for_pages_returns_matching_success(self):
        requested_urls = []

        def fake_request(url, _token):
            requested_urls.append(url)
            return {
                "workflow_runs": [
                    {
                        "status": "completed",
                        "conclusion": "success",
                        "html_url": "https://github.test/run/1",
                    }
                ]
            }

        result = wait_for_pages(
            "owner/repo",
            "abc123",
            "token",
            request_json=fake_request,
            sleep_fn=lambda _seconds: None,
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("head_sha=abc123", requested_urls[0])

    def test_operations_summary_contains_stage_usage_and_quality(self):
        summary = build_summary(
            {
                "status": "success",
                "usage": {
                    "api_attempts": 3,
                    "successful_calls": 3,
                    "prompt_tokens": 100,
                    "output_tokens": 200,
                    "total_tokens": 300,
                    "by_stage": {
                        "editor_en": {
                            "attempts": 1,
                            "prompt_tokens": 40,
                            "output_tokens": 60,
                            "total_tokens": 100,
                        }
                    },
                },
                "metrics": {
                    "source_quality": {
                        "score": 82,
                        "grade": "good",
                        "reference_count": 3,
                        "domain_count": 2,
                    }
                },
            },
            {"status": "success"},
        )

        self.assertIn("Source quality: **82/100", summary)
        self.assertIn("`editor_en`", summary)
        self.assertIn("300 total", summary)


if __name__ == "__main__":
    unittest.main()
