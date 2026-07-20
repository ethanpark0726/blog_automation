#!/usr/bin/env python3
"""Validate README version metadata against the latest CHANGELOG entry."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


VERSION_PATTERN = r"\d+\.\d+\.\d+"


@dataclass(frozen=True)
class VersionMetadata:
    changelog_latest: str
    readme_badge: str
    readme_current: str
    roadmap_done: set[str]


def latest_changelog_version(changelog_text: str) -> str:
    match = re.search(rf"^## \[({VERSION_PATTERN})\]", changelog_text, flags=re.MULTILINE)
    if not match:
        raise ValueError("CHANGELOG.md does not contain a top-level version entry like '## [1.2.3]'")
    return match.group(1)


def readme_badge_version(readme_text: str) -> str:
    match = re.search(
        r"https://img\.shields\.io/badge/Version-([^-)\s]+)-purple",
        readme_text,
    )
    if not match:
        raise ValueError("README.md does not contain a Version badge using shields.io")
    value = unquote(match.group(1)).replace("%2E", ".")
    if not re.fullmatch(VERSION_PATTERN, value):
        raise ValueError(f"README Version badge is not a semantic version: {value}")
    return value


def readme_current_version(readme_text: str) -> str:
    match = re.search(rf"^\*\*v({VERSION_PATTERN})\*\*", readme_text, flags=re.MULTILINE)
    if not match:
        raise ValueError("README.md Current Version section does not contain '**vX.Y.Z**'")
    return match.group(1)


def readme_roadmap_done_versions(readme_text: str) -> set[str]:
    return set(re.findall(rf"- \*\*`\[x\]` v({VERSION_PATTERN})\*\*:", readme_text))


def collect_metadata(readme_text: str, changelog_text: str) -> VersionMetadata:
    return VersionMetadata(
        changelog_latest=latest_changelog_version(changelog_text),
        readme_badge=readme_badge_version(readme_text),
        readme_current=readme_current_version(readme_text),
        roadmap_done=readme_roadmap_done_versions(readme_text),
    )


def validation_errors(metadata: VersionMetadata) -> list[str]:
    latest = metadata.changelog_latest
    errors: list[str] = []
    if metadata.readme_badge != latest:
        errors.append(
            f"README Version badge is {metadata.readme_badge}, but latest CHANGELOG version is {latest}."
        )
    if metadata.readme_current != latest:
        errors.append(
            f"README Current Version is {metadata.readme_current}, but latest CHANGELOG version is {latest}."
        )
    if latest not in metadata.roadmap_done:
        errors.append(f"README Roadmap is missing a completed '[x] v{latest}' entry.")
    return errors


def main() -> int:
    readme = Path("README.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    metadata = collect_metadata(readme, changelog)
    errors = validation_errors(metadata)
    if errors:
        print("ERROR: Version metadata mismatch detected:")
        for error in errors:
            print(f"- {error}")
        print("")
        print("Update README.md so the Version badge, Current Version section, and Roadmap match CHANGELOG.md.")
        return 1

    print(f"OK: Version metadata is consistent at v{metadata.changelog_latest}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
