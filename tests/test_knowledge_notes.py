import tempfile
import unittest
from pathlib import Path

import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_knowledge_notes import generate_knowledge_notes  # noqa: E402


class KnowledgeNoteTests(unittest.TestCase):
    def test_generates_topic_concept_and_source_notes(self):
        post = """---
layout: post
title: "Capacitive vs Torque Sensors"
lang: en
topic_id: "capacitive-vs-torque"
post_id: "capacitive-vs-torque-12345678"
description: "A comparison of hands-on detection sensors."
tags:
  - ADAS
  - capacitive sensor
---

# Capacitive vs Torque Sensors

## References

- [Example Source](https://example.com/source)
"""

        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            post_path = root / "_posts" / "en" / "post.md"
            post_path.parent.mkdir(parents=True)
            post_path.write_text(post, encoding="utf-8")
            try:
                import os

                os.chdir(root)
                created = generate_knowledge_notes([str(post_path)])
            finally:
                os.chdir(original_cwd)

            topic = root / "_knowledge" / "concepts" / "capacitive-vs-torque.md"
            concept = root / "_knowledge" / "concepts" / "adas.md"
            source = list((root / "_knowledge" / "sources").glob("examplecom-*.md"))

            self.assertIn(str(Path("_knowledge/concepts/capacitive-vs-torque.md")), created)
            self.assertTrue(topic.exists())
            self.assertTrue(concept.exists())
            self.assertEqual(len(source), 1)
            self.assertIn("[[adas|ADAS]]", topic.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
