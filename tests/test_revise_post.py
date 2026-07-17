import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

fake_genai = types.ModuleType("google.genai")
fake_genai.Client = lambda **_kwargs: object()
fake_google = types.ModuleType("google")
fake_google.genai = fake_genai
sys.modules.setdefault("google", fake_google)
sys.modules.setdefault("google.genai", fake_genai)

from revise_post import (  # noqa: E402
    ReviewRequest,
    apply_revision,
    discover_ready_reviews,
    find_posts_by_post_id,
    parse_review_note,
)


def post(lang: str, post_id: str) -> str:
    title = "Korean Title" if lang == "ko" else "English Title"
    if lang == "ko":
        body = "## 소개\n\n" + ("기존 한국어 본문입니다. " * 90)
        body += "\n\n## 세부 내용\n\n" + ("추가 설명입니다. " * 90)
    else:
        body = "## Introduction\n\n" + ("Existing English body. " * 260)
        body += "\n\n## Details\n\n" + ("Additional explanation. " * 260)
    return f"""---
layout: post
title: "{title}"
lang: {lang}
post_id: "{post_id}"
topic_id: "topic"
tags:
  - test
---

{body}
"""


class FakeModel:
    def generate_content(self, _prompt, generation_config=None):
        del generation_config
        ko = "## 소개\n\n" + ("수정된 한국어 본문입니다. " * 90)
        ko += "\n\n## 세부 내용\n\n" + ("보강된 설명입니다. " * 90)
        en = "## Introduction\n\n" + ("Revised English body. " * 260)
        en += "\n\n## Details\n\n" + ("Expanded explanation. " * 260)
        return SimpleNamespace(
            text=json.dumps({"ko": ko, "en": en}, ensure_ascii=False),
            usage_metadata=SimpleNamespace(
                prompt_token_count=10,
                candidates_token_count=20,
                total_token_count=30,
            ),
        )


class RevisePostTests(unittest.TestCase):
    def test_parse_and_discover_ready_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pending = root / "_reviews" / "pending"
            pending.mkdir(parents=True)
            review_path = pending / "request.md"
            review_path.write_text(
                """---
target_post_id: "abc123"
scope: bilingual
status: ready
---

# Revision

- Add one paragraph.
""",
                encoding="utf-8",
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                review = parse_review_note(review_path)
                discovered = discover_ready_reviews()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(review.target_post_id, "abc123")
        self.assertEqual(review.instructions, ["Add one paragraph."])
        self.assertEqual(len(discovered), 1)

    def test_discover_ignores_example_review_notes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pending = root / "_reviews" / "pending"
            pending.mkdir(parents=True)
            (pending / "example-revision-request.md").write_text(
                """---
target_post_id: "example"
scope: bilingual
status: ready
---

# Revision

- This is documentation, not an executable request.
""",
                encoding="utf-8",
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                discovered = discover_ready_reviews()
            finally:
                os.chdir(original_cwd)

        self.assertEqual([], discovered)

    def test_apply_revision_updates_paired_posts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_id = "paired-123"
            (root / "_posts" / "ko").mkdir(parents=True)
            (root / "_posts" / "en").mkdir(parents=True)
            ko_path = root / "_posts" / "ko" / "post.md"
            en_path = root / "_posts" / "en" / "post.md"
            ko_path.write_text(post("ko", post_id), encoding="utf-8")
            en_path.write_text(post("en", post_id), encoding="utf-8")
            review = ReviewRequest(
                path=root / "_reviews" / "pending" / "request.md",
                target_post_id=post_id,
                instructions=["Add one paragraph."],
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                changed = apply_revision(review, FakeModel(), SimpleNamespace(
                    record_attempt=lambda _stage: None,
                    record_success=lambda _stage, _response: None,
                ))
                self.assertIn("_posts/ko/post.md", {Path(path).as_posix() for path in changed})
                self.assertIn("수정된 한국어", ko_path.read_text(encoding="utf-8"))
                self.assertIn("Revised English", en_path.read_text(encoding="utf-8"))
                self.assertTrue((root / "_knowledge" / "concepts" / "topic.md").exists())
            finally:
                os.chdir(original_cwd)

    def test_find_posts_accepts_unique_post_id_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_id = "adobe-architecture-0e0dace8"
            (root / "_posts" / "ko").mkdir(parents=True)
            (root / "_posts" / "en").mkdir(parents=True)
            (root / "_posts" / "ko" / "post.md").write_text(post("ko", post_id), encoding="utf-8")
            (root / "_posts" / "en" / "post.md").write_text(post("en", post_id), encoding="utf-8")

            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                matches = find_posts_by_post_id("0e0dace8")
            finally:
                os.chdir(original_cwd)

        self.assertEqual({"ko", "en"}, set(matches))


if __name__ == "__main__":
    unittest.main()
