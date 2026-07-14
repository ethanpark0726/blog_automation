import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from content_quality import (  # noqa: E402
    ContentValidationError,
    append_references,
    classify_query,
    extract_references,
    normalize_metadata_block,
    validate_post,
)


class ContentQualityTests(unittest.TestCase):
    def test_classifies_engineering_topics_locally(self):
        self.assertEqual(classify_query("How does Kubernetes networking work?")["mode"], "engineer")
        self.assertEqual(classify_query("BGP 라우팅 동작 원리")["mode"], "engineer")

    def test_defaults_general_topics_to_trivia(self):
        self.assertEqual(classify_query("How was our Solar System formed?")["mode"], "trivia")
        self.assertEqual(classify_query("Discovering Adobe Architecture")["mode"], "trivia")

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
