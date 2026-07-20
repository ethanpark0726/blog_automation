import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from check_version_metadata import collect_metadata, validation_errors  # noqa: E402


README_TEMPLATE = """# Project

[![Version](https://img.shields.io/badge/Version-{badge}-purple)](CHANGELOG.md)

## Current Version

**v{current}** — Summary.

## Roadmap

- **`[x]` v{roadmap}**: Done
"""


CHANGELOG_TEMPLATE = """# Changelog

## [{latest}] — 2026-07-19

### Added
- Change.
"""


class VersionMetadataTests(unittest.TestCase):
    def test_accepts_matching_readme_and_changelog_versions(self):
        metadata = collect_metadata(
            README_TEMPLATE.format(badge="1.20.1", current="1.20.1", roadmap="1.20.1"),
            CHANGELOG_TEMPLATE.format(latest="1.20.1"),
        )

        self.assertEqual([], validation_errors(metadata))

    def test_rejects_stale_readme_badge(self):
        metadata = collect_metadata(
            README_TEMPLATE.format(badge="1.19.8", current="1.20.1", roadmap="1.20.1"),
            CHANGELOG_TEMPLATE.format(latest="1.20.1"),
        )

        self.assertIn(
            "README Version badge is 1.19.8, but latest CHANGELOG version is 1.20.1.",
            validation_errors(metadata),
        )

    def test_rejects_missing_roadmap_entry(self):
        metadata = collect_metadata(
            README_TEMPLATE.format(badge="1.20.1", current="1.20.1", roadmap="1.20.0"),
            CHANGELOG_TEMPLATE.format(latest="1.20.1"),
        )

        self.assertIn(
            "README Roadmap is missing a completed '[x] v1.20.1' entry.",
            validation_errors(metadata),
        )


if __name__ == "__main__":
    unittest.main()
