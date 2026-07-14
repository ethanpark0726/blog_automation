import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import notify  # noqa: E402


class NotifyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
