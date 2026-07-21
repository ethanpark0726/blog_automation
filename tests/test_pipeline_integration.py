import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def load_pipeline_module():
    fake_genai = types.ModuleType("google.genai")

    class FakeClient:
        def __init__(self, **_kwargs):
            self.models = SimpleNamespace(generate_content=lambda **_kwargs: object())

    fake_genai.Client = FakeClient
    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai

    spec = importlib.util.spec_from_file_location(
        "multi_agent_integration_test",
        SCRIPTS_DIR / "multi_agent.py",
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "QUERY_INPUT": "How was our Solar System formed?"},
    ), patch.dict(
        sys.modules,
        {"google": fake_google, "google.genai": fake_genai},
    ):
        spec.loader.exec_module(module)
    return module


def article(lang: str) -> str:
    if lang == "ko":
        body = "## 소개\n\n" + ("태양계 형성 과정에 대한 검증된 설명입니다. " * 100)
        body += "\n\n## 자세한 과정\n\n" + ("근거를 바탕으로 단계별 과정을 설명합니다. " * 100)
        metadata = {
            "title": "태양계 형성 과정",
            "description": "태양계가 형성된 과정을 설명합니다.",
            "tags": ["태양계", "과학"],
            "search_query_en": "formation of the Solar System",
        }
    else:
        body = "## Introduction\n\n" + ("This is a source-grounded explanation of solar system formation. " * 650)
        body += "\n\n## Detailed Process\n\n" + (
            "The article explains each stage carefully using the collected evidence. " * 650
        )
        metadata = {
            "title": "How the Solar System Formed",
            "description": "A source-grounded explanation of Solar System formation.",
            "tags": ["Solar System", "Science"],
        }
    return body + "\n\n```json_meta\n" + json.dumps(metadata, ensure_ascii=False) + "\n```"


class PipelineIntegrationTests(unittest.TestCase):
    def test_gemini_adapter_maps_generation_config_to_genai_config(self):
        pipeline = load_pipeline_module()
        calls = []
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(text="ok")
            )
        )
        adapter = pipeline.GeminiModelAdapter(client, "gemini-test")

        response = adapter.generate_content(
            "hello",
            generation_config={"temperature": 0.2, "max_output_tokens": 10},
        )

        self.assertEqual(response.text, "ok")
        self.assertEqual(calls[0]["model"], "gemini-test")
        self.assertEqual(calls[0]["contents"], "hello")
        self.assertEqual(calls[0]["config"]["temperature"], 0.2)

    def test_full_offline_pipeline_uses_three_successful_calls(self):
        pipeline = load_pipeline_module()
        stages = []

        def fake_call(_prompt, stage, retry=3):
            del retry
            stages.append(stage)
            if stage == "research_writer_en":
                response = SimpleNamespace(
                    usage_metadata=SimpleNamespace(
                        prompt_token_count=100,
                        candidates_token_count=200,
                        total_token_count=300,
                    )
                )
                pipeline.usage_tracker.record_attempt(stage)
                pipeline.usage_tracker.record_success(stage, response)
                research = json.dumps(
                    {
                        "canonical_topic_en": "Formation of the Solar System",
                        "search_queries_en": [
                            "formation of the Solar System",
                            "solar nebula theory",
                        ],
                        "intent_summary_en": "Explain how the Solar System formed.",
                    }
                )
                return article("en") + "\n\n```json_research\n" + research + "\n```"
            lang = "ko" if stage.endswith("_ko") else "en"
            response = SimpleNamespace(
                usage_metadata=SimpleNamespace(
                    prompt_token_count=100,
                    candidates_token_count=200,
                    total_token_count=300,
                )
            )
            pipeline.usage_tracker.record_attempt(stage)
            pipeline.usage_tracker.record_success(stage, response)
            return article(lang)

        pipeline.call_gemini = fake_call
        pipeline.send_telegram = lambda *_args, **_kwargs: None
        pipeline.search_duckduckgo = lambda _query: "[Overview] Solar system overview"
        search_queries = []

        def fake_wikipedia(query):
            search_queries.append(query)
            return (
                "[Wikipedia] Title: Formation and evolution of the Solar System\n"
                "Snippet: " + ("Source-grounded formation summary. " * 25) + "\n"
                "Link: https://en.wikipedia.org/wiki/Formation_and_evolution_of_the_Solar_System"
            )

        pipeline.search_wikipedia = fake_wikipedia
        pipeline.search_google_books = lambda _query: (
            "[Book] Title: The Origin of the Solar System\n"
            "Author(s): Example Author\n"
            "Link: https://books.google.com/books?id=solar-system"
        )
        pipeline.search_crossref = lambda _query: (
            "[Scholarly Publication] Title: Solar System Formation Evidence\n"
            "Author(s): Example Researcher\n"
            "Abstract: Independent scholarly evidence.\n"
            "DOI Link: https://doi.org/10.1234/solar-system"
        )

        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            os.chdir(temp_path)
            try:
                with patch.dict(
                    os.environ,
                    {"GITHUB_ENV": str(temp_path / "github_env"), "GITHUB_ACTIONS": "true"},
                ), patch("builtins.print"):
                    pipeline.main()

                result = json.loads(
                    (temp_path / ".pipeline_result.json").read_text(encoding="utf-8")
                )
                ko_files = list((temp_path / "_posts" / "ko").glob("*.md"))
                en_files = list((temp_path / "_posts" / "en").glob("*.md"))
                knowledge_files = list((temp_path / "_knowledge" / "concepts").glob("*.md"))
                ko_content = ko_files[0].read_text(encoding="utf-8")
            finally:
                os.chdir(original_cwd)

        self.assertEqual(
            stages,
            ["research_writer_en", "editor_en", "localizer_ko"],
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["usage"]["successful_calls"], 3)
        self.assertEqual(result["usage"]["api_attempts"], 3)
        self.assertGreaterEqual(
            result["metrics"]["source_quality"]["score"],
            90,
        )
        self.assertEqual(len(ko_files), 1)
        self.assertEqual(len(en_files), 1)
        self.assertGreaterEqual(len(knowledge_files), 1)
        self.assertIn("request_fingerprint:", ko_content)
        self.assertIn(
            "formation of the solar system",
            [query.casefold() for query in search_queries],
        )

    def test_source_gate_blocks_long_form_calls_when_references_are_missing(self):
        pipeline = load_pipeline_module()
        pipeline.search_duckduckgo = lambda _query: "No search results"
        pipeline.search_wikipedia = lambda _query: "No Wikipedia pages found."
        pipeline.search_google_books = lambda _query: "No books found."
        pipeline.search_crossref = lambda _query: "No publications found."

        with self.assertRaises(pipeline.SourceCoverageError):
            pipeline.ScholarlySearchAgent().run(
                {"mode": "trivia"},
                {
                    "canonical_topic_en": "Unknown niche topic",
                    "search_queries_en": ["unknown niche topic"],
                },
            )

    def test_checkpoint_restores_completed_stage_data(self):
        pipeline = load_pipeline_module()
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                checkpoint = pipeline.PipelineCheckpoint("abc123")
                checkpoint.save("english_research", facts="verified facts")
                restored = pipeline.PipelineCheckpoint("abc123")
            finally:
                os.chdir(original_cwd)

        self.assertTrue(restored.has("english_research"))
        self.assertEqual(restored.get("facts"), "verified facts")

    def test_duplicate_guard_blocks_existing_fingerprint(self):
        pipeline = load_pipeline_module()
        fingerprint = pipeline.request_fingerprint("same question")
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            post_dir = temp_path / "_posts" / "en"
            post_dir.mkdir(parents=True)
            (post_dir / "existing.md").write_text(
                f'---\nrequest_fingerprint: "{fingerprint}"\n---\n',
                encoding="utf-8",
            )
            os.chdir(temp_path)
            try:
                with self.assertRaises(pipeline.DuplicateRequestError):
                    pipeline.ensure_request_is_new(fingerprint)
            finally:
                os.chdir(original_cwd)

    def test_full_checkpoint_resume_uses_no_additional_model_calls(self):
        pipeline = load_pipeline_module()
        pipeline.send_telegram = lambda *_args, **_kwargs: None
        pipeline.call_gemini = lambda *_args, **_kwargs: self.fail(
            "checkpoint resume should not call Gemini"
        )
        fingerprint = pipeline.request_fingerprint(pipeline.QUERY_INPUT)
        plan = {
            "canonical_topic_en": "Formation of the Solar System",
            "search_queries_en": ["solar system formation"],
            "intent_summary_en": "Explain formation.",
        }

        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            os.chdir(temp_path)
            try:
                checkpoint = pipeline.PipelineCheckpoint(fingerprint)
                checkpoint.save(
                    "research_writer",
                    research_plan=plan,
                    english_draft=article("en"),
                )
                checkpoint.save("english_research", facts="restored verified facts")
                checkpoint.save(
                    "english_editor",
                    reviewed_english=article("en"),
                    final_english=article("en"),
                )
                checkpoint.save("korean_localizer", final_korean=article("ko"))

                with patch.dict(
                    os.environ,
                    {"GITHUB_ENV": str(temp_path / "github_env"), "GITHUB_ACTIONS": "true"},
                ), patch("builtins.print"):
                    pipeline.main()

                result = json.loads(
                    (temp_path / ".pipeline_result.json").read_text(encoding="utf-8")
                )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["usage"]["successful_calls"], 0)

    def test_korean_localizer_recovers_missing_metadata_block(self):
        pipeline = load_pipeline_module()
        body = "## Intro\n\n" + ("Localized Korean article body. " * 80)
        body += "\n\n## Details\n\n" + ("More localized Korean article body. " * 80)
        facts = """
[Wikipedia] Title: MCP
Snippet: Example source.
Link: https://en.wikipedia.org/wiki/MCP
"""

        pipeline.call_gemini = lambda *_args, **_kwargs: body
        localized = pipeline.KoreanLocalizerAgent().run(
            reviewed_english=article("en"),
            original_query="MCP란 무엇인가?",
            classification={
                "mode": "trivia",
                "topic_ko": "MCP란 무엇인가?",
                "keywords": ["MCP", "운영체제"],
            },
            facts=facts,
        )

        self.assertIn("```json_meta", localized)
        self.assertIn('"title": "MCP란 무엇인가?"', localized)
        self.assertIn("https://en.wikipedia.org/wiki/MCP", localized)

    def test_research_writer_recovers_missing_draft_metadata_block(self):
        pipeline = load_pipeline_module()
        raw = """## Introduction

This draft explains hands-on detection in driver assistance systems.

## Sensor Comparison

Capacitive sensing and torque sensing measure different signals.

```json_research
{
  "canonical_topic_en": "Capacitive vs torque steering-wheel hands-on detection",
  "search_queries_en": [
    "capacitive steering wheel hands on detection",
    "torque sensor hands on detection driver assistance"
  ],
  "intent_summary_en": "Explain the difference between capacitive and torque sensors for steering-wheel hands-on detection."
}
```"""

        plan, draft = pipeline.ResearchWriterAgent._parse_output(raw)

        self.assertEqual(
            plan["canonical_topic_en"],
            "Capacitive vs torque steering-wheel hands-on detection",
        )
        self.assertIn("```json_meta", draft)
        self.assertIn('"title": "Capacitive vs torque steering-wheel hands-on detection"', draft)


if __name__ == "__main__":
    unittest.main()
