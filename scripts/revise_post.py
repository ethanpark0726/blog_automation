#!/usr/bin/env python3
"""Apply Obsidian review notes to paired blog posts."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from content_quality import ContentValidationError, validate_post
from gemini_runtime import UsageTracker, call_gemini
from generate_knowledge_notes import generate_knowledge_notes


DEFAULT_REVIEW_DIR = Path("_reviews/pending")
COMPLETED_REVIEW_DIR = Path("_reviews/completed")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-3.1-flash-lite"
REVISION_CONFIG = {"temperature": 0.2, "max_output_tokens": 16384}


@dataclass
class ReviewRequest:
    path: Path
    target_post_id: str
    scope: str = "bilingual"
    status: str = "ready"
    instructions: list[str] = field(default_factory=list)


class GeminiModelAdapter:
    def __init__(self, client: Any, model_name: str) -> None:
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt: str, generation_config: dict | None = None):
        kwargs = {"model": self.model_name, "contents": prompt}
        if generation_config is not None:
            kwargs["config"] = generation_config
        return self.client.models.generate_content(**kwargs)


def parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    metadata: dict[str, object] = {}
    current_list: str | None = None
    for raw_line in text[4:end].splitlines():
        line = raw_line.rstrip()
        if current_list and line.startswith("  - "):
            metadata.setdefault(current_list, []).append(line[4:].strip().strip('"'))
            continue
        current_list = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            metadata[key] = []
            current_list = key
        else:
            metadata[key] = value.strip('"')
    return metadata, text[end + 5 :]


def split_front_matter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end < 0:
        return "", text
    return text[: end + 5], text[end + 5 :].lstrip()


def parse_review_note(path: Path) -> ReviewRequest:
    text = path.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(text)
    instructions = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            instructions.append(stripped[2:].strip())
    return ReviewRequest(
        path=path,
        target_post_id=str(metadata.get("target_post_id") or "").strip(),
        scope=str(metadata.get("scope") or "bilingual").strip(),
        status=str(metadata.get("status") or "ready").strip(),
        instructions=instructions,
    )


def discover_ready_reviews(directory: Path = DEFAULT_REVIEW_DIR) -> list[ReviewRequest]:
    reviews = []
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue
        if path.name.startswith("example-"):
            continue
        review = parse_review_note(path)
        if review.status.casefold() == "ready":
            reviews.append(review)
    return reviews


def find_posts_by_post_id(post_id: str) -> dict[str, Path]:
    matches: dict[str, Path] = {}
    for path in Path("_posts").glob("*/*.md"):
        metadata, _body = parse_front_matter(path.read_text(encoding="utf-8"))
        if metadata.get("post_id") == post_id:
            lang = str(metadata.get("lang") or path.parent.name)
            matches[lang] = path
    return matches


def revision_prompt(review: ReviewRequest, posts: dict[str, str]) -> str:
    instructions = "\n".join(f"- {item}" for item in review.instructions)
    return f"""
You are revising an already-published bilingual blog post from an Obsidian review note.

Rules:
1. Apply the requested changes to both Korean and English when scope is bilingual.
2. Preserve front matter exactly outside the body. Return body content only.
3. Preserve the existing Markdown style, headings, tables, code blocks, and references.
4. Do not add unsupported facts, fake URLs, or invented citations.
5. Keep at least two level-2 headings in each body.

Review scope: {review.scope}
Review instructions:
{instructions}

Current Korean body:
---
{posts.get("ko", "")}
---

Current English body:
---
{posts.get("en", "")}
---

Return JSON only:
{{
  "ko": "complete revised Korean body",
  "en": "complete revised English body"
}}
"""


def parse_revision_response(raw: str) -> dict[str, str]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    return {lang: str(payload.get(lang) or "").strip() for lang in ("ko", "en")}


def validate_revised_body(front_matter: str, body: str, lang: str) -> None:
    content = f"{front_matter}{body.strip()}\n"
    result = validate_post(content, lang, [])
    # Published posts no longer include json_meta after FileWriter strips it.
    result.errors = [error for error in result.errors if error != "missing json_meta block"]
    if not result.valid:
        raise ContentValidationError(lang, result.errors)


def apply_revision(review: ReviewRequest, model: GeminiModelAdapter, tracker: UsageTracker) -> list[str]:
    post_paths = find_posts_by_post_id(review.target_post_id)
    missing = {"ko", "en"} - set(post_paths)
    if missing:
        raise ValueError(f"Missing target posts for post_id {review.target_post_id}: {sorted(missing)}")
    if not review.instructions:
        raise ValueError(f"Review note has no instructions: {review.path}")

    front_matters: dict[str, str] = {}
    bodies: dict[str, str] = {}
    for lang, path in post_paths.items():
        front_matter, body = split_front_matter(path.read_text(encoding="utf-8"))
        front_matters[lang] = front_matter
        bodies[lang] = body

    raw = call_gemini(
        model,
        revision_prompt(review, bodies),
        "revision_bilingual",
        tracker,
        generation_config=REVISION_CONFIG,
    )
    revised = parse_revision_response(raw)

    updated_paths = []
    for lang, path in post_paths.items():
        body = revised.get(lang, "").strip()
        if not body:
            raise ValueError(f"Revision response missing {lang} body")
        validate_revised_body(front_matters[lang], body, lang)
        path.write_text(f"{front_matters[lang]}{body}\n", encoding="utf-8")
        updated_paths.append(str(path))

    updated_paths.extend(generate_knowledge_notes(updated_paths))
    return updated_paths


def complete_review(review: ReviewRequest) -> Path:
    COMPLETED_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    stamped_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{review.path.name}"
    target = COMPLETED_REVIEW_DIR / stamped_name
    shutil.move(str(review.path), str(target))
    return target


def main(argv: Iterable[str] | None = None) -> None:
    del argv
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required")

    reviews = discover_ready_reviews()
    if not reviews:
        print("No ready review notes found.")
        return

    from google import genai

    client = genai.Client(api_key=api_key)
    model = GeminiModelAdapter(client, GEMINI_MODEL)
    tracker = UsageTracker()
    changed_files: list[str] = []
    completed_files: list[str] = []

    for review in reviews:
        print(f"[Revision] Applying {review.path}")
        changed_files.extend(apply_revision(review, model, tracker))
        completed_files.append(str(complete_review(review)))

    env_path = os.environ.get("GITHUB_ENV")
    if env_path:
        with open(env_path, "a", encoding="utf-8") as env_file:
            env_file.write(f"REVISION_CHANGED_FILES={','.join(changed_files + completed_files)}\n")
    print("Updated files:")
    for path in changed_files + completed_files:
        print(f"  - {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
