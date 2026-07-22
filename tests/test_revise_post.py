import json
import contextlib
import io
import os
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

fake_genai = types.ModuleType("google.genai")
fake_genai.Client = lambda **_kwargs: object()
fake_google = types.ModuleType("google")
fake_google.genai = fake_genai
sys.modules.setdefault("google", fake_google)
sys.modules.setdefault("google.genai", fake_genai)

import revise_post  # noqa: E402
from revise_post import (  # noqa: E402
    ReviewRequest,
    apply_revision,
    complete_review,
    discover_ready_reviews,
    filter_reviews,
    find_posts_by_post_id,
    is_placeholder_post_id,
    parse_review_note,
    collect_review_research,
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


def immediate_gemini_call(model, prompt, stage, tracker, generation_config=None, **_kwargs):
    tracker.record_attempt(stage)
    response = model.generate_content(prompt, generation_config=generation_config)
    tracker.record_success(stage, response)
    return response.text.strip()


class IncompleteOperationModel:
    def __init__(self):
        self.calls = 0

    def generate_content(self, _prompt, generation_config=None):
        del generation_config
        self.calls += 1
        if self.calls == 1:
            payload = {
                "actions": [
                    {
                        "id": "R1",
                        "instruction": "Enrich the article.",
                        "kind": "enrich",
                        "languages": ["en", "ko"],
                        "requires_research": False,
                        "must_include": {"en": [], "ko": []},
                        "must_exclude": {"en": [], "ko": []},
                    }
                ],
                "search_queries_en": [],
            }
        else:
            payload = {"operations": [], "applied": ["R1"], "unresolved": []}
        return SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False),
            usage_metadata=SimpleNamespace(
                prompt_token_count=10,
                candidates_token_count=20,
                total_token_count=30,
            ),
        )


class SectionOperationModel:
    def __init__(self):
        self.calls = 0

    def generate_content(self, _prompt, generation_config=None):
        del generation_config
        self.calls += 1
        if self.calls == 1:
            payload = {
                "actions": [
                    {
                        "id": "R1",
                        "instruction": "Remove the child-directed introduction and dad wording.",
                        "kind": "delete",
                        "languages": ["en", "ko"],
                        "requires_research": False,
                        "must_include": {"en": [], "ko": []},
                        "must_exclude": {"en": ["Hey kids"], "ko": ["우리 친구들", "아빠"]},
                    },
                    {
                        "id": "R2",
                        "instruction": "Explain protosun formation.",
                        "kind": "enrich",
                        "languages": ["en", "ko"],
                        "requires_research": True,
                        "must_include": {"en": ["hydrogen fusion"], "ko": ["수소 핵융합"]},
                        "must_exclude": {"en": [], "ko": []},
                    },
                    {
                        "id": "R3",
                        "instruction": "Use a neutral declarative Korean style.",
                        "kind": "style",
                        "languages": ["ko"],
                        "requires_research": False,
                        "must_include": {"en": [], "ko": []},
                        "must_exclude": {"en": [], "ko": ["설명해요"]},
                    },
                ],
                "search_queries_en": ["protosun formation hydrogen fusion"],
            }
        elif self.calls == 2:
            payload = {
                "operations": [
                    {"action_id": "R1", "operation": "delete", "target": "preamble", "content": ""},
                    {
                        "action_ids": ["R2"],
                        "operation": "insert_after",
                        "target": "section_1",
                        "content": "## Protosun Formation\n\nHydrogen fusion begins after gravitational contraction.",
                    },
                ],
                "applied": ["R1", "R2"],
                "unresolved": [],
            }
        else:
            payload = {
                "operations": [
                    {"action_id": "R1", "operation": "delete", "target": "preamble", "content": ""},
                    {
                        "action_ids": ["R2"],
                        "operation": "insert_after",
                        "target": "section_1",
                        "content": "## 원시 태양 형성\n\n중력 수축 이후 중심 온도가 상승하면서 수소 핵융합이 시작된다.",
                    },
                    {
                        "action_ids": ["R3"],
                        "operation": "replace_text",
                        "target": "section_1",
                        "old_text": "기존 한국어 본문입니다.",
                        "content": "기존 한국어 본문이다.",
                    },
                    {
                        "action_ids": ["R3"],
                        "operation": "replace_text",
                        "target": "section_2",
                        "old_text": "추가 설명입니다.",
                        "content": "추가 설명이다.",
                    },
                ],
                "applied": ["R1", "R2", "R3"],
                "unresolved": [],
            }
        return SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False),
            usage_metadata=SimpleNamespace(
                prompt_token_count=10,
                candidates_token_count=20,
                total_token_count=30,
            ),
        )


class KoreanOnlyOperationModel:
    def __init__(self):
        self.calls = 0

    def generate_content(self, _prompt, generation_config=None):
        del generation_config
        self.calls += 1
        if self.calls == 1:
            payload = {
                "actions": [
                    {
                        "id": "R1",
                        "instruction": "Use declarative Korean style.",
                        "kind": "style",
                        "languages": ["ko"],
                        "requires_research": False,
                        "must_include": {"en": [], "ko": ["본문이다"]},
                        "must_exclude": {"en": [], "ko": []},
                    }
                ],
                "search_queries_en": [],
            }
        else:
            payload = {
                "operations": [
                    {
                        "action_ids": ["R1"],
                        "operation": "replace_text",
                        "target": "section_1",
                        "old_text": "기존 한국어 본문입니다.",
                        "content": "수정된 한국어 본문이다.",
                    }
                ],
                "applied": ["R1"],
                "unresolved": [],
            }
        return SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False),
            usage_metadata=SimpleNamespace(
                prompt_token_count=10,
                candidates_token_count=20,
                total_token_count=30,
            ),
        )


class PromptAwarePreservationModel:
    def __init__(self):
        self.calls = 0

    def generate_content(self, prompt, generation_config=None):
        del generation_config
        self.calls += 1
        if self.calls == 1:
            payload = {
                "actions": [
                    {
                        "id": "R1",
                        "instruction": "Add formation context.",
                        "kind": "enrich",
                        "languages": ["en"],
                        "requires_research": False,
                        "must_include": {"en": ["New formation context"], "ko": []},
                        "must_exclude": {"en": [], "ko": []},
                    },
                    {
                        "id": "R2",
                        "instruction": "Use neutral wording.",
                        "kind": "style",
                        "languages": ["en"],
                        "requires_research": False,
                        "must_include": {"en": ["Neutral English body"], "ko": []},
                        "must_exclude": {"en": [], "ko": []},
                    },
                ],
                "search_queries_en": [],
            }
        elif "replace_text" in prompt:
            payload = {
                "operations": [
                    {
                        "action_ids": ["R1"],
                        "operation": "insert_after",
                        "target": "section_1",
                        "content": "## Formation Context\n\nNew formation context.",
                    },
                    {
                        "action_ids": ["R2"],
                        "operation": "replace_text",
                        "target": "section_1",
                        "old_text": "Existing English body.",
                        "content": "Neutral English body.",
                    },
                ],
                "applied": ["R1", "R2"],
                "unresolved": [],
            }
        else:
            payload = {
                "operations": [
                    {
                        "action_ids": ["R1", "R2"],
                        "operation": "replace",
                        "target": "section_1",
                        "content": "## Introduction\n\nNew formation context with Neutral English body.",
                    },
                    {
                        "action_ids": ["R1", "R2"],
                        "operation": "replace",
                        "target": "section_2",
                        "content": "## Details\n\nShort replacement.",
                    },
                ],
                "applied": ["R1", "R2"],
                "unresolved": [],
            }
        return SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False),
            usage_metadata=SimpleNamespace(
                prompt_token_count=10,
                candidates_token_count=20,
                total_token_count=30,
            ),
        )


class RevisePostTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(revise_post, "call_gemini", side_effect=immediate_gemini_call)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_apply_revision_applies_review_as_section_operations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_id = "solar-123"
            (root / "_posts" / "ko").mkdir(parents=True)
            (root / "_posts" / "en").mkdir(parents=True)
            ko_path = root / "_posts" / "ko" / "post.md"
            en_path = root / "_posts" / "en" / "post.md"
            ko_path.write_text(
                post("ko", post_id).replace(
                    "\n\n## 소개", "\n\n우리 친구들, 아빠가 설명해요.\n\n## 소개"
                ).replace("## ", "### "),
                encoding="utf-8",
            )
            en_path.write_text(
                post("en", post_id).replace(
                    "\n\n## Introduction", "\n\nHey kids, dad will explain.\n\n## Introduction"
                ).replace("## ", "### "),
                encoding="utf-8",
            )
            review = ReviewRequest(
                path=root / "_reviews" / "pending" / "request.md",
                target_post_id=post_id,
                instructions=[
                    "아이 대상 서문과 아빠 표현을 삭제한다.",
                    "원시 태양 형성 과정을 보강한다.",
                    "존댓말을 평서체로 변경한다.",
                ],
            )
            model = SectionOperationModel()
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                research = (
                    "Title: NASA Protosun Formation\nSummary\nLink: https://science.nasa.gov/protosun\n\n"
                    "Title: Stellar Formation Study\nSummary\nDOI Link: https://doi.org/10.1234/example"
                )
                with patch.object(
                    revise_post, "collect_review_research", return_value=research
                ) as research_mock:
                    apply_revision(
                        review,
                        model,
                        SimpleNamespace(
                            record_attempt=lambda _stage: None,
                            record_success=lambda _stage, _response: None,
                        ),
                    )
                self.assertEqual(
                    ["protosun formation hydrogen fusion"],
                    research_mock.call_args.args[3],
                )
                ko_text = ko_path.read_text(encoding="utf-8")
                en_text = en_path.read_text(encoding="utf-8")
            finally:
                os.chdir(original_cwd)

        self.assertEqual(3, model.calls)
        self.assertNotIn("우리 친구들", ko_text)
        self.assertNotIn("아빠", ko_text)
        self.assertIn("수소 핵융합", ko_text)
        self.assertIn("추가 설명이다", ko_text)
        self.assertNotIn("Hey kids", en_text)
        self.assertIn("hydrogen fusion", en_text.lower())
        self.assertIn("Additional explanation", en_text)
        self.assertIn("## References", en_text)
        self.assertIn("## 참고자료", ko_text)
        self.assertIn("https://science.nasa.gov/protosun", en_text)
        self.assertGreaterEqual(en_text.count("\n## "), 2)
        self.assertGreaterEqual(ko_text.count("\n## "), 2)

    def test_apply_revision_skips_language_without_actions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_id = "ko-only-123"
            (root / "_posts" / "ko").mkdir(parents=True)
            (root / "_posts" / "en").mkdir(parents=True)
            ko_path = root / "_posts" / "ko" / "post.md"
            en_path = root / "_posts" / "en" / "post.md"
            ko_path.write_text(post("ko", post_id), encoding="utf-8")
            en_path.write_text(post("en", post_id), encoding="utf-8")
            before_en = en_path.read_text(encoding="utf-8")
            review = ReviewRequest(
                path=root / "_reviews" / "pending" / "request.md",
                target_post_id=post_id,
                scope="ko",
                instructions=["한국어 문체만 평서체로 변경한다."],
            )
            model = KoreanOnlyOperationModel()
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                apply_revision(
                    review,
                    model,
                    SimpleNamespace(
                        record_attempt=lambda _stage: None,
                        record_success=lambda _stage, _response: None,
                    ),
                )
                after_en = en_path.read_text(encoding="utf-8")
                after_ko = ko_path.read_text(encoding="utf-8")
            finally:
                os.chdir(original_cwd)

        self.assertEqual(2, model.calls)
        self.assertEqual(before_en, after_en)
        self.assertIn("수정된 한국어 본문이다", after_ko)

    def test_style_and_enrichment_preserve_the_existing_article(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_id = "preserve-123"
            (root / "_posts" / "ko").mkdir(parents=True)
            (root / "_posts" / "en").mkdir(parents=True)
            ko_path = root / "_posts" / "ko" / "post.md"
            en_path = root / "_posts" / "en" / "post.md"
            ko_path.write_text(post("ko", post_id), encoding="utf-8")
            en_path.write_text(post("en", post_id), encoding="utf-8")
            review = ReviewRequest(
                path=root / "_reviews" / "pending" / "request.md",
                target_post_id=post_id,
                instructions=["설명을 보강한다.", "중립적인 문체로 바꾼다."],
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                apply_revision(
                    review,
                    PromptAwarePreservationModel(),
                    SimpleNamespace(
                        record_attempt=lambda _stage: None,
                        record_success=lambda _stage, _response: None,
                    ),
                )
                revised = en_path.read_text(encoding="utf-8")
            finally:
                os.chdir(original_cwd)

        self.assertIn("New formation context", revised)
        self.assertGreater(revised.count("Neutral English body."), 200)
        self.assertIn("Additional explanation.", revised)

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

    def test_discover_skips_placeholder_review_notes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pending = root / "_reviews" / "pending"
            pending.mkdir(parents=True)
            (pending / "solar-system-formation-d0fca2e0.md").write_text(
                """---
target_post_id: "replace-with-real-post-id"
scope: bilingual
status: ready
---

# Revision

- Add more details.
""",
                encoding="utf-8",
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                discovered = discover_ready_reviews()
            finally:
                os.chdir(original_cwd)

        self.assertTrue(is_placeholder_post_id("replace-with-real-post-id"))
        self.assertEqual([], discovered)

    def test_apply_revision_preserves_posts_when_operations_are_incomplete(self):
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
            review.path.parent.mkdir(parents=True)
            review.path.write_text("ready", encoding="utf-8")
            before_ko = ko_path.read_text(encoding="utf-8")
            before_en = en_path.read_text(encoding="utf-8")
            model = IncompleteOperationModel()
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.object(revise_post, "collect_review_research", return_value=""):
                    with self.assertRaisesRegex(ValueError, "Operations for en must cover"):
                        apply_revision(review, model, SimpleNamespace(
                            record_attempt=lambda _stage: None,
                            record_success=lambda _stage, _response: None,
                        ))
                self.assertEqual(2, model.calls)
                self.assertEqual(before_ko, ko_path.read_text(encoding="utf-8"))
                self.assertEqual(before_en, en_path.read_text(encoding="utf-8"))
                self.assertTrue(review.path.exists())
            finally:
                os.chdir(original_cwd)

    def test_apply_revision_validates_both_languages_before_writing_either(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_id = "atomic-123"
            (root / "_posts" / "ko").mkdir(parents=True)
            (root / "_posts" / "en").mkdir(parents=True)
            ko_path = root / "_posts" / "ko" / "post.md"
            en_path = root / "_posts" / "en" / "post.md"
            ko_path.write_text(
                post("ko", post_id).replace(
                    "\n\n## 소개", "\n\n우리 친구들, 아빠가 설명해요.\n\n## 소개"
                ),
                encoding="utf-8",
            )
            en_path.write_text(
                post("en", post_id).replace(
                    "\n\n## Introduction", "\n\nHey kids, dad will explain.\n\n## Introduction"
                ),
                encoding="utf-8",
            )
            before_ko = ko_path.read_text(encoding="utf-8")
            before_en = en_path.read_text(encoding="utf-8")
            review = ReviewRequest(
                path=root / "_reviews" / "pending" / "request.md",
                target_post_id=post_id,
                instructions=[
                    "아이 대상 서문과 아빠 표현을 삭제한다.",
                    "원시 태양 형성 과정을 보강한다.",
                    "존댓말을 평서체로 변경한다.",
                ],
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.object(revise_post, "collect_review_research", return_value=""):
                    with patch.object(
                        revise_post,
                        "validate_revised_body",
                        side_effect=[None, revise_post.ContentValidationError("ko", ["forced"])],
                    ):
                        with self.assertRaises(revise_post.ContentValidationError):
                            apply_revision(
                                review,
                                SectionOperationModel(),
                                SimpleNamespace(
                                    record_attempt=lambda _stage: None,
                                    record_success=lambda _stage, _response: None,
                                ),
                            )
                self.assertEqual(before_ko, ko_path.read_text(encoding="utf-8"))
                self.assertEqual(before_en, en_path.read_text(encoding="utf-8"))
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
                with contextlib.redirect_stdout(io.StringIO()):
                    matches = find_posts_by_post_id("0e0dace8")
            finally:
                os.chdir(original_cwd)

        self.assertEqual({"ko", "en"}, set(matches))

    def test_review_research_uses_english_title_for_korean_review_notes(self):
        front_matter = """---
layout: post
title: "Solar System Formation"
lang: en
post_id: "solar-system-formation-d0fca2e0"
---
"""
        review = ReviewRequest(
            path=Path("_reviews/pending/request.md"),
            target_post_id="solar-system-formation-d0fca2e0",
            instructions=["태양계 형성 과정을 보강한다."],
        )

        with patch.object(revise_post, "search_duckduckgo", return_value="Title: Solar System Formation\nSummary\nLink: https://example.com"):
            with patch.object(revise_post, "search_wikipedia", return_value="No Wikipedia pages found."):
                facts = collect_review_research(review, {"en": "## Introduction\n\nBody"}, {"en": front_matter})

        self.assertIn("Solar System Formation", facts)

    def test_filter_reviews_accepts_latest_and_partial_identifiers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_path = root / "old-review.md"
            new_path = root / "new-review.md"
            old_path.write_text("", encoding="utf-8")
            new_path.write_text("", encoding="utf-8")
            os.utime(old_path, (100, 100))
            os.utime(new_path, (200, 200))
            reviews = [
                ReviewRequest(path=old_path, target_post_id="turquoise-abc123"),
                ReviewRequest(path=new_path, target_post_id="adobe-architecture-0e0dace8"),
            ]

            self.assertEqual([new_path], [review.path for review in filter_reviews(reviews, "latest")])
            self.assertEqual([new_path], [review.path for review in filter_reviews(reviews, "0e0dace8")])
            self.assertEqual([old_path], [review.path for review in filter_reviews(reviews, "old")])
            self.assertEqual(reviews, filter_reviews(reviews, ""))

    def test_complete_review_deletes_processed_note(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pending = root / "_reviews" / "pending"
            pending.mkdir(parents=True)
            review_path = pending / "request.md"
            review_path.write_text(
                """---
target_post_id: "paired-123"
scope: bilingual
status: ready
---

# Revision

- Add concrete evidence.
""",
                encoding="utf-8",
            )
            review = ReviewRequest(
                path=review_path,
                target_post_id="paired-123",
                instructions=["Add concrete evidence."],
            )

            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                deleted_path = complete_review(review)
                deleted_full_path = root / deleted_path
                pending_exists = review_path.exists()
                completed_dir_exists = (root / "_reviews" / "completed").exists()
            finally:
                os.chdir(original_cwd)

        self.assertFalse(pending_exists)
        self.assertFalse(deleted_full_path.exists())
        self.assertFalse(completed_dir_exists)

    def test_main_keeps_ready_review_when_revision_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_path = root / "_reviews" / "pending" / "request.md"
            review_path.parent.mkdir(parents=True)
            review_path.write_text("ready", encoding="utf-8")
            review = ReviewRequest(
                path=Path("_reviews/pending/request.md"),
                target_post_id="paired-123",
                instructions=["Add concrete evidence."],
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "REVIEW_FILTER": ""}):
                    with patch.object(revise_post, "discover_ready_reviews", return_value=[review]):
                        with patch.object(revise_post, "apply_revision", side_effect=ValueError("invalid edit")):
                            with self.assertRaisesRegex(ValueError, "invalid edit"):
                                revise_post.main([])
                review_exists = review_path.exists()
            finally:
                os.chdir(original_cwd)

        self.assertTrue(review_exists)


if __name__ == "__main__":
    unittest.main()
