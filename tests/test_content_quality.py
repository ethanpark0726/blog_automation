import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from content_quality import (  # noqa: E402
    ContentValidationError,
    append_references,
    build_search_queries,
    classify_query,
    extract_references,
    is_usable_search_result,
    normalize_metadata_block,
    source_quality_score,
    validate_post,
)


class ContentQualityTests(unittest.TestCase):
    def test_classifies_engineering_topics_locally(self):
        self.assertEqual(classify_query("How does Kubernetes networking work?")["mode"], "engineer")
        self.assertEqual(classify_query("BGP 라우팅 동작 원리")["mode"], "engineer")

    def test_defaults_general_topics_to_trivia(self):
        self.assertEqual(classify_query("How was our Solar System formed?")["mode"], "trivia")
        self.assertEqual(classify_query("Discovering Adobe Architecture")["mode"], "trivia")

    def test_builds_compact_korean_search_query(self):
        queries = build_search_queries("싼타페에는 왜 터키석 보석을 많이 팔지?")

        self.assertEqual(queries[0], "싼타페에는 왜 터키석 보석을 많이 팔지?")
        self.assertEqual(queries[1], "싼타페 터키석 보석")

    def test_builds_compact_english_search_query(self):
        queries = build_search_queries("How does Kubernetes networking work?")

        self.assertEqual(queries[1], "kubernetes networking")

    def test_rejects_placeholder_search_results(self):
        self.assertFalse(is_usable_search_result("No search results"))
        self.assertFalse(is_usable_search_result("No Wikipedia pages found."))
        self.assertFalse(is_usable_search_result("Wikipedia Search Error: timeout"))
        self.assertTrue(
            is_usable_search_result(
                "[Wikipedia] Title: Turquoise\nLink: https://en.wikipedia.org/wiki/Turquoise"
            )
        )

    def test_extracts_and_deduplicates_search_references(self):
        facts = """
[Wikipedia] Title: Kubernetes
Snippet: Container orchestration.
Link: https://en.wikipedia.org/wiki/Kubernetes

[Academic Paper] Title: Cluster Management
Abstract: Example.
Link: https://arxiv.org/abs/1234.5678

[Wikipedia] Title: Kubernetes duplicate
Link: https://en.wikipedia.org/wiki/Kubernetes
"""

        references = extract_references(facts)

        self.assertEqual(len(references), 2)
        self.assertEqual(references[0]["title"], "Kubernetes")
        self.assertEqual(references[1]["url"], "https://arxiv.org/abs/1234.5678")

    def test_source_quality_score_rewards_independent_authoritative_sources(self):
        facts = """
[Wikipedia] Title: Kubernetes
Snippet: Container orchestration background.
Link: https://en.wikipedia.org/wiki/Kubernetes

[Academic Paper] Title: Cluster Management
Abstract: Independent academic evidence.
Link: https://arxiv.org/abs/1234.5678
""" + ("evidence " * 80)

        quality = source_quality_score(facts)

        self.assertGreaterEqual(quality["score"], 75)
        self.assertEqual(quality["grade"], "good")
        self.assertEqual(quality["reference_count"], 2)
        self.assertEqual(quality["domain_count"], 2)

    def test_appends_references_before_metadata(self):
        content = """## Intro

Body

## Details

More body

```json_meta
{"title":"Title","description":"Description","tags":["one"]}
```"""
        references = [{"title": "Source", "url": "https://example.org/source"}]

        final = append_references(content, "en", references)

        self.assertIn("## References", final)
        self.assertLess(final.index("## References"), final.index("```json_meta"))
        self.assertEqual(final.count("https://example.org/source"), 1)

    def test_normalizes_generic_metadata_json_fence(self):
        content = """## Intro

Text

```json
{"title":"Title","description":"Description","tags":["one"]}
```"""

        normalized = normalize_metadata_block(content)

        self.assertIn("```json_meta", normalized)
        self.assertNotIn("```json\n", normalized)

    def test_validation_rejects_missing_metadata(self):
        result = validate_post("## One\ntext\n## Two\ntext", "en", [])

        self.assertFalse(result.valid)
        self.assertIn("missing json_meta block", result.errors)

    def test_validation_error_exposes_pipeline_stage(self):
        error = ContentValidationError("ko", ["missing json_meta block"])

        self.assertEqual(error.category, "content_validation_error")
        self.assertEqual(error.stage, "local_validation_ko")

    def test_validation_accepts_structurally_complete_article(self):
        body = "## Introduction\n" + ("word " * 500) + "\n## Details\n" + ("word " * 500)
        content = body + """

```json_meta
{"title":"Title","description":"Description","tags":["one"]}
```"""

        result = validate_post(content, "en", [])

        self.assertTrue(result.valid, result.errors)


if __name__ == "__main__":
    unittest.main()
