import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from notify_revision import build_revision_message, changed_file_lines  # noqa: E402


class NotifyRevisionTests(unittest.TestCase):
    def test_changed_file_lines_limits_long_lists(self):
        raw = ",".join(f"file-{index}.md" for index in range(10))
        lines = changed_file_lines(raw, limit=3)

        self.assertEqual(
            ["- file-0.md", "- file-1.md", "- file-2.md", "- ...and 7 more"],
            lines,
        )

    def test_build_success_message_with_changed_files(self):
        message = build_revision_message(
            status="success",
            changed_files="_posts/ko/post.md,_posts/en/post.md",
            run_url="https://github.com/example/actions/runs/1",
            review_filter="latest",
        )

        self.assertIn("✅ Obsidian revision completed.", message)
        self.assertIn("Filter: latest", message)
        self.assertIn("- _posts/ko/post.md", message)
        self.assertIn("Run log: https://github.com/example/actions/runs/1", message)

    def test_build_failure_message(self):
        message = build_revision_message(
            status="failure",
            changed_files="",
            run_url="https://github.com/example/actions/runs/2",
        )

        self.assertIn("❌ Obsidian revision failed.", message)
        self.assertIn("Check the GitHub Actions log", message)


if __name__ == "__main__":
    unittest.main()
