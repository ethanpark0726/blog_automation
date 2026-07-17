import tempfile
import unittest
from pathlib import Path

import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from backfill_post_ids import backfill_post_ids, deterministic_post_id  # noqa: E402


def write_post(path: Path, *, lang: str, topic_id: str = "shared-topic", post_id: str = "") -> None:
    post_id_line = f'post_id: "{post_id}"\n' if post_id else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
layout: post
title: "{lang} title"
lang: {lang}
topic_id: "{topic_id}"
{post_id_line}---

## Body

Content.
""",
        encoding="utf-8",
    )


class BackfillPostIdsTests(unittest.TestCase):
    def test_backfills_same_post_id_for_bilingual_pair(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ko = root / "_posts" / "ko" / "post.md"
            en = root / "_posts" / "en" / "post.md"
            write_post(ko, lang="ko")
            write_post(en, lang="en")

            updated, skipped = backfill_post_ids(root / "_posts")

            expected = deterministic_post_id("shared-topic")
            self.assertEqual({ko, en}, set(updated))
            self.assertEqual([], skipped)
            self.assertIn(f'post_id: "{expected}"', ko.read_text(encoding="utf-8"))
            self.assertIn(f'post_id: "{expected}"', en.read_text(encoding="utf-8"))

    def test_reuses_existing_post_id_for_same_topic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ko = root / "_posts" / "ko" / "post.md"
            en = root / "_posts" / "en" / "post.md"
            write_post(ko, lang="ko", post_id="existing-123")
            write_post(en, lang="en")

            updated, skipped = backfill_post_ids(root / "_posts")

            self.assertEqual([en], updated)
            self.assertEqual([], skipped)
            self.assertIn('post_id: "existing-123"', ko.read_text(encoding="utf-8"))
            self.assertIn('post_id: "existing-123"', en.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
