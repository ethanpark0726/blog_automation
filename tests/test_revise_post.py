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
                        "operation": "replace_block",
                        "target": "section_1.block_1",
                        "content": "기존 한국어 본문이다. " * 90,
                    },
                    {
                        "action_ids": ["R3"],
                        "operation": "replace_block",
                        "target": "section_2.block_1",
                        "content": "추가 설명이다. " * 90,
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
                        "operation": "replace_block",
                        "target": "section_1.block_1",
                        "content": "수정된 한국어 본문이다. " * 100,
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


class SyncTranslationModel:
    def __init__(self):
        self.calls = 0

    def generate_content(self, prompt, generation_config=None):
        del generation_config
        self.calls += 1
        if "Korean source Markdown body" not in prompt:
            raise AssertionError("sync translation prompt must include the Korean source body")
        if "한국어에서 새로 보강한 문장" not in prompt:
            raise AssertionError("sync translation prompt must include the edited Korean content")
        body = (
            "## Synced Introduction\n\n"
            + ("The Korean source now adds a clearer explanation of heat stress and breathing load. " * 120)
            + "\n\n## Synced Details\n\n"
            + ("The English article now mirrors the Korean revision while preserving a natural blog style. " * 120)
        )
        return SimpleNamespace(
            text=json.dumps({"body": body}, ensure_ascii=False),
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
        elif "replace_block" in prompt:
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
                        "operation": "replace_block",
                        "target": "section_1.block_1",
                        "content": "Neutral English body. " * 260,
                    },
                ],
                "applied": ["R1", "R2"],
                "unresolved": [],
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
                        "old_text": "This sentence does not exist in the source.",
                        "content": "Neutral English body.",
                    },
                ],
                "applied": ["R1", "R2"],
                "unresolved": [],
            }
        else:
            raise AssertionError("Revision prompt is missing a supported safe edit operation")
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

    def test_replace_block_does_not_require_echoing_source_text(self):
        plan = {
            "actions": [
                {
                    "id": "R1",
                    "kind": "style",
                    "languages": ["en"],
                    "must_include": {"en": ["Neutral sentence."]},
                    "must_exclude": {"en": [], "ko": []},
                }
            ]
        }
        payload = {
            "operations": [
                {
                    "action_ids": ["R1"],
                    "operation": "replace_block",
                    "target": "section_1.block_1",
                    "content": "Neutral sentence.",
                }
            ],
            "applied": ["R1"],
            "unresolved": [],
        }

        revised = revise_post.apply_section_operations(
            "## Section\n\nFirst sentence.\nSecond sentence.", payload, plan, "en"
        )

        self.assertIn("Neutral sentence.", revised)

    def test_block_targets_remain_stable_after_earlier_block_deletion(self):
        plan = {
            "actions": [
                {"id": "R1", "kind": "delete", "languages": ["en"]},
                {"id": "R2", "kind": "style", "languages": ["en"]},
            ]
        }
        payload = {
            "operations": [
                {
                    "action_ids": ["R1"],
                    "operation": "delete",
                    "target": "section_1.block_1",
                    "content": "",
                },
                {
                    "action_ids": ["R2"],
                    "operation": "replace_block",
                    "target": "section_1.block_3",
                    "content": "Revised third paragraph.",
                },
            ],
            "applied": ["R1", "R2"],
            "unresolved": [],
        }
        original = (
            "## Section\n\n"
            "Delete this paragraph.\n\n"
            "Keep this paragraph.\n\n"
            "Original third paragraph.\n\n"
            "## Other\n\n"
            "Keep this section."
        )

        revised = revise_post.apply_section_operations(original, payload, plan, "en")

        self.assertNotIn("Delete this paragraph.", revised)
        self.assertIn("Keep this paragraph.", revised)
        self.assertIn("Revised third paragraph.", revised)
        self.assertNotIn("Original third paragraph.", revised)
        self.assertIn("Keep this section.", revised)

    def test_delete_action_can_remove_inline_content_with_replace_block(self):
        plan = {
            "actions": [
                {"id": "R1", "kind": "delete", "languages": ["en"]},
            ]
        }
        payload = {
            "operations": [
                {
                    "action_ids": ["R1"],
                    "operation": "replace_block",
                    "target": "section_1.block_1",
                    "content": "Heat stress raises cardiovascular load.",
                },
            ],
            "applied": ["R1"],
            "unresolved": [],
        }

        revised = revise_post.apply_section_operations(
            "## Section\n\nHeat stress raises cardiovascular load. 🥵", payload, plan, "en"
        )

        self.assertIn("Heat stress raises cardiovascular load.", revised)
        self.assertNotIn("🥵", revised)

    def test_replace_block_section_target_updates_heading_only(self):
        plan = {
            "actions": [
                {"id": "R1", "kind": "delete", "languages": ["en"]},
            ]
        }
        payload = {
            "operations": [
                {
                    "action_ids": ["R1"],
                    "operation": "replace_block",
                    "target": "section_1",
                    "content": "## The Core Concept",
                },
            ],
            "applied": ["R1"],
            "unresolved": [],
        }
        original = (
            "## The Core Concept 🥵\n\n"
            "Heat stress raises cardiovascular load.\n\n"
            "Hydration changes blood volume."
        )

        revised = revise_post.apply_section_operations(original, payload, plan, "en")

        self.assertIn("## The Core Concept", revised)
        self.assertNotIn("🥵", revised)
        self.assertIn("Heat stress raises cardiovascular load.", revised)
        self.assertIn("Hydration changes blood volume.", revised)

    def test_missing_delete_operation_is_applied_from_instruction(self):
        plan = {
            "actions": [
                {
                    "id": "R1",
                    "kind": "delete",
                    "languages": ["ko"],
                    "instruction": "첫 서문 삭제",
                },
                {"id": "R2", "kind": "style", "languages": ["ko"]},
                {"id": "R3", "kind": "delete", "languages": ["ko"], "instruction": "불필요한 이모지 삭제"},
                {"id": "R4", "kind": "enrich", "languages": ["ko"]},
                {
                    "id": "R5",
                    "kind": "delete",
                    "languages": ["ko"],
                    "instruction": "마지막 우리 친구들, 이야기로 만나요! 안녕!이라고 하는 마지막 결말 부분도 삭제",
                },
            ]
        }
        payload = {
            "operations": [
                {"action_ids": ["R1"], "operation": "delete", "target": "section_1.block_1", "content": ""},
                {
                    "action_ids": ["R2"],
                    "operation": "replace_block",
                    "target": "section_1.block_2",
                    "content": "더운 환경에서는 심혈관계와 호흡계 부담이 함께 증가한다.",
                },
                {
                    "action_ids": ["R3"],
                    "operation": "replace_block",
                    "target": "section_1.block_3",
                    "content": "운동 중 수분 손실은 혈액량을 줄이고 산소 전달 효율을 떨어뜨린다.",
                },
                {
                    "action_ids": ["R4"],
                    "operation": "insert_after",
                    "target": "section_1",
                    "content": "## 추가 설명\n\n열 스트레스는 피부 혈류와 활동근 혈류가 경쟁하게 만든다.",
                },
            ],
            "applied": ["R1", "R2", "R3", "R4", "R5"],
            "unresolved": [],
        }
        original = (
            "## 운동과 열 스트레스\n\n"
            "우리 친구들, 안녕하세요!\n\n"
            "더운 환경에서는 심장과 폐가 더 많이 일해요.\n\n"
            "땀이 많이 나면 산소 전달이 어려워져요. 🥵\n\n"
            "우리 친구들, 다음에도 더 재미있는 이야기로 만나요! 안녕!"
        )

        revised = revise_post.apply_section_operations(original, payload, plan, "ko")

        self.assertNotIn("안녕하세요", revised)
        self.assertIn("더운 환경에서는 심혈관계와 호흡계 부담이 함께 증가한다.", revised)
        self.assertIn("열 스트레스는 피부 혈류와 활동근 혈류가 경쟁하게 만든다.", revised)
        self.assertNotIn("🥵", revised)
        self.assertNotIn("우리 친구들", revised)
        self.assertNotIn("안녕", revised)

    def test_style_examples_are_not_required_literal_output(self):
        plan = {
            "actions": [
                {
                    "id": "R1",
                    "kind": "style",
                    "languages": ["ko"],
                    "must_include": {"en": [], "ko": ["시작되었다"]},
                    "must_exclude": {"en": [], "ko": ["태양계"]},
                }
            ]
        }
        payload = {
            "operations": [
                {
                    "action_ids": ["R1"],
                    "operation": "replace_block",
                    "target": "section_1.block_1",
                    "content": "태양계 형성은 중력 붕괴로 시작됐다.",
                }
            ],
            "applied": ["R1"],
            "unresolved": [],
        }

        revised = revise_post.apply_section_operations(
            "## 태양계 형성\n\n태양계 형성은 중력 붕괴로 시작되었어요.", payload, plan, "ko"
        )

        self.assertIn("시작됐다", revised)

    def test_model_generated_enrichment_phrase_is_not_a_literal_requirement(self):
        plan = {
            "actions": [
                {
                    "id": "R1",
                    "kind": "enrich",
                    "languages": ["en"],
                    "must_include": {"en": ["protostar formation"], "ko": []},
                    "must_exclude": {"en": [], "ko": []},
                }
            ]
        }
        payload = {
            "operations": [
                {
                    "action_ids": ["R1"],
                    "operation": "insert_after",
                    "target": "section_1",
                    "content": "## Protosun\n\nA protosun forms as the collapsing cloud heats up.",
                }
            ],
            "applied": ["R1"],
            "unresolved": [],
        }

        revised = revise_post.apply_section_operations(
            "## Solar Nebula\n\nGravity collapses the cloud.", payload, plan, "en"
        )

        self.assertIn("A protosun forms", revised)

    def test_revision_accepts_valid_article_after_requested_style_reduction(self):
        en_front_matter, original_en = revise_post.split_front_matter(post("en", "style-123"))
        ko_front_matter, original_ko = revise_post.split_front_matter(post("ko", "style-123"))
        revised_en = (
            "## Introduction\n\n"
            + ("Neutral technical explanation. " * 170)
            + "\n\n## Details\n\n"
            + ("Additional explanation. " * 80)
        )
        plan = {
            "actions": [
                {
                    "id": "R1",
                    "kind": "style",
                    "languages": ["en"],
                    "must_include": {"en": [], "ko": []},
                    "must_exclude": {"en": [], "ko": []},
                }
            ]
        }

        with patch.object(revise_post, "request_language_revision", return_value=revised_en):
            revised = revise_post.request_revision(
                object(),
                SimpleNamespace(),
                {"en": original_en, "ko": original_ko},
                {"en": en_front_matter, "ko": ko_front_matter},
                plan,
                "",
            )

        self.assertEqual(revised_en, revised["en"])

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

    def test_sync_translation_updates_target_language_from_source_post(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_id = "sync-123"
            (root / "_posts" / "ko").mkdir(parents=True)
            (root / "_posts" / "en").mkdir(parents=True)
            ko_path = root / "_posts" / "ko" / "post.md"
            en_path = root / "_posts" / "en" / "post.md"
            ko_path.write_text(
                post("ko", post_id) + "\n\n## 수동 보강\n\n한국어에서 새로 보강한 문장입니다.\n",
                encoding="utf-8",
            )
            en_path.write_text(post("en", post_id), encoding="utf-8")
            before_ko = ko_path.read_text(encoding="utf-8")
            review = ReviewRequest(
                path=root / "_reviews" / "pending" / "request.md",
                target_post_id=post_id,
                mode="sync_translation",
                source_lang="ko",
                target_lang="en",
                instructions=["한국어 포스트를 기준으로 영어 포스트를 동기화한다."],
            )
            model = SyncTranslationModel()
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                changed = apply_revision(
                    review,
                    model,
                    SimpleNamespace(
                        record_attempt=lambda _stage: None,
                        record_success=lambda _stage, _response: None,
                    ),
                )
                after_ko = ko_path.read_text(encoding="utf-8")
                after_en = en_path.read_text(encoding="utf-8")
            finally:
                os.chdir(original_cwd)

        self.assertEqual(1, model.calls)
        self.assertEqual(before_ko, after_ko)
        self.assertIn(str(Path("_posts") / "en" / "post.md"), changed)
        self.assertNotIn(str(Path("_posts") / "ko" / "post.md"), changed)
        self.assertIn("Synced Introduction", after_en)
        self.assertIn("mirrors the Korean revision", after_en)

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
mode: sync_translation
source_lang: ko
target_lang: en
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
        self.assertEqual(review.mode, "sync_translation")
        self.assertEqual(review.source_lang, "ko")
        self.assertEqual(review.target_lang, "en")
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
