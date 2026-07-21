#!/usr/bin/env python3
"""Apply Obsidian review notes to paired blog posts."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from content_quality import ContentValidationError, validate_post
from content_quality import build_search_queries, extract_references, is_usable_search_result
from gemini_runtime import UsageTracker, call_gemini
from generate_knowledge_notes import generate_knowledge_notes


DEFAULT_REVIEW_DIR = Path("_reviews/pending")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-3.1-flash-lite"
REVISION_CONFIG = {"temperature": 0.2, "max_output_tokens": 16384}
MAX_REVISION_ATTEMPTS = 2
MIN_REVISION_WORD_RETENTION = 0.70
MIN_REVISION_CHAR_RETENTION = 0.70


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


def filter_reviews(reviews: list[ReviewRequest], filter_text: str | None) -> list[ReviewRequest]:
    value = (filter_text or "").strip().lower()
    if not value:
        return reviews

    if value == "latest":
        if not reviews:
            return []
        return [max(reviews, key=lambda review: review.path.stat().st_mtime)]

    def matches(review: ReviewRequest) -> bool:
        haystacks = [
            review.target_post_id.lower(),
            review.path.name.lower(),
            review.path.stem.lower(),
        ]
        return any(value in haystack for haystack in haystacks)

    return [review for review in reviews if matches(review)]


def find_posts_by_post_id(post_id: str) -> dict[str, Path]:
    post_id = post_id.strip()
    matches: dict[str, Path] = {}
    suffix_candidates: dict[str, dict[str, Path]] = {}
    for path in Path("_posts").glob("*/*.md"):
        metadata, _body = parse_front_matter(path.read_text(encoding="utf-8"))
        current_post_id = str(metadata.get("post_id") or "").strip()
        lang = str(metadata.get("lang") or path.parent.name)
        if current_post_id == post_id:
            matches[lang] = path
        if current_post_id.endswith(f"-{post_id}"):
            suffix_candidates.setdefault(current_post_id, {})[lang] = path
    if matches:
        return matches
    if len(suffix_candidates) == 1:
        resolved_post_id, resolved_matches = next(iter(suffix_candidates.items()))
        print(f"[Revision] Resolved short target_post_id '{post_id}' to '{resolved_post_id}'")
        return resolved_matches
    if len(suffix_candidates) > 1:
        raise ValueError(
            f"Ambiguous short target_post_id {post_id}; matching post_ids: {sorted(suffix_candidates)}"
        )
    return matches


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "blog-automation-revision/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def search_duckduckgo(query: str) -> str:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
    )
    try:
        data = fetch_json(f"https://api.duckduckgo.com/?{params}")
    except Exception as exc:
        return f"Search API error: {exc}"

    parts = []
    if data.get("AbstractText"):
        parts.append(
            "Title: "
            + str(data.get("Heading") or query)
            + "\n"
            + str(data["AbstractText"])
            + "\nLink: "
            + str(data.get("AbstractURL") or "")
        )
    for topic in data.get("RelatedTopics", [])[:4]:
        if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
            parts.append(f"Title: {topic.get('Text')}\nLink: {topic.get('FirstURL')}")
    return "\n\n".join(parts) if parts else "No search results."


def search_wikipedia(query: str) -> str:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 3,
        }
    )
    try:
        data = fetch_json(f"https://en.wikipedia.org/w/api.php?{params}")
    except Exception as exc:
        return f"Search API error: {exc}"

    results = []
    for item in data.get("query", {}).get("search", []):
        title = str(item.get("title") or "").strip()
        snippet = re.sub("<.*?>", "", str(item.get("snippet") or "")).strip()
        if not title:
            continue
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        results.append(f"Title: {title}\n{snippet}\nLink: {url}")
    return "\n\n".join(results) if results else "No Wikipedia pages found."


def collect_review_research(review: ReviewRequest, bodies: dict[str, str]) -> str:
    """Collect lightweight English facts for review-driven enrichment."""
    seeds = []
    instruction_text = " ".join(review.instructions)
    if instruction_text:
        seeds.extend(build_search_queries(instruction_text, limit=4))
    heading_match = re.search(r"^#\s+(.+)$", bodies.get("en", ""), re.MULTILINE)
    if heading_match:
        seeds.extend(build_search_queries(heading_match.group(1), limit=2))

    queries = []
    for seed in seeds:
        if not seed or not re.search(r"[A-Za-z]", seed):
            continue
        normalized = seed.casefold()
        if normalized not in {query.casefold() for query in queries}:
            queries.append(seed)
        if len(queries) >= 5:
            break

    facts = []
    seen = set()
    for query in queries:
        for label, result in (
            ("Revision Web Summary", search_duckduckgo(query)),
            ("Revision Reference", search_wikipedia(query)),
        ):
            normalized = result.strip()
            if normalized in seen or not is_usable_search_result(normalized):
                continue
            seen.add(normalized)
            facts.append(f"=== {label}: {query} ===\n{normalized}")

    combined = "\n\n".join(facts)
    references = extract_references(combined)
    print(
        f"[RevisionResearch] Collected {len(combined)} fact chars, "
        f"{len(references)} references from {len(queries)} queries"
    )
    return combined


def revision_prompt(review: ReviewRequest, posts: dict[str, str], research_facts: str) -> str:
    instructions = "\n".join(f"- {item}" for item in review.instructions)
    research_block = research_facts.strip() or "No additional external facts were collected. Use only the existing post."
    return f"""
You are enriching an already-published bilingual blog post from an Obsidian review note.

Primary goal:
- Preserve the existing article's structure, voice, useful explanations, code blocks, tables, diagrams, and references.
- Add or adjust only what is necessary to satisfy the review note.
- Treat this as minimal enrichment, not a fresh rewrite.

Rules:
1. Apply the requested changes to both Korean and English when scope is bilingual.
2. Use the review research facts when they are relevant; do not invent facts beyond the existing post and provided research.
3. Return the complete revised body for each language, not a summary, excerpt, diff, or only the changed paragraph.
4. Preserve the existing Markdown style, headings, tables, code blocks, and references unless the review explicitly asks to remove or change them.
5. Prefer inserting or lightly editing paragraphs over rewriting the whole article.
6. Keep at least two level-2 headings in each body.
7. The English body must remain at least 450 words. The Korean body must remain at least 1,200 characters.
8. Preserve front matter exactly outside the body. Return body content only.

Review scope: {review.scope}
Review instructions:
{instructions}

Review research facts:
---
{research_block}
---

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


def revision_retry_prompt(
    review: ReviewRequest,
    posts: dict[str, str],
    research_facts: str,
    previous_response: dict[str, str],
    errors: dict[str, list[str]],
) -> str:
    formatted_errors = "\n".join(
        f"- {lang}: {'; '.join(messages)}" for lang, messages in sorted(errors.items())
    )
    return f"""
The previous revision response failed local validation.

Validation errors:
{formatted_errors}

You must return JSON only with complete full revised bodies for both languages.
Do not return only the changed section. Do not summarize. Do not omit existing sections.
Preserve the existing article as much as possible; this is a minimal enrichment task, not a fresh rewrite.
The English body must be at least 450 words and the Korean body must be at least 1,200 characters.

Review research facts:
---
{research_facts.strip() or "No additional external facts were collected. Use only the existing post."}
---

Original Korean body:
---
{posts.get("ko", "")}
---

Original English body:
---
{posts.get("en", "")}
---

Previous invalid Korean response:
---
{previous_response.get("ko", "")}
---

Previous invalid English response:
---
{previous_response.get("en", "")}
---

Review scope: {review.scope}
Review instructions:
{chr(10).join(f"- {item}" for item in review.instructions)}

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


def revised_body_errors(front_matter: str, body: str, lang: str) -> list[str]:
    content = f"{front_matter}{body.strip()}\n"
    result = validate_post(content, lang, [])
    # Published posts no longer include json_meta after FileWriter strips it.
    result.errors = [error for error in result.errors if error != "missing json_meta block"]
    return [] if result.valid else result.errors


def validate_revised_body(front_matter: str, body: str, lang: str) -> None:
    errors = revised_body_errors(front_matter, body, lang)
    if errors:
        raise ContentValidationError(lang, errors)


def revision_preservation_errors(original: str, revised: str, lang: str) -> list[str]:
    """Guard against model responses that rewrite or truncate too aggressively."""
    errors = []
    if lang == "en":
        original_size = len(re.findall(r"\b[\w'-]+\b", original))
        revised_size = len(re.findall(r"\b[\w'-]+\b", revised))
        if original_size >= 450 and revised_size < original_size * MIN_REVISION_WORD_RETENTION:
            errors.append(
                "revised English body is too short relative to the original; "
                "Phase 4.1 requires enrichment, not replacement"
            )
    else:
        original_size = len(original.strip())
        revised_size = len(revised.strip())
        if original_size >= 1200 and revised_size < original_size * MIN_REVISION_CHAR_RETENTION:
            errors.append(
                "revised Korean body is too short relative to the original; "
                "Phase 4.1 requires enrichment, not replacement"
            )

    original_headings = set(re.findall(r"^##\s+(.+)$", original, re.MULTILINE))
    revised_headings = set(re.findall(r"^##\s+(.+)$", revised, re.MULTILINE))
    if len(original_headings) >= 2:
        retained = len(original_headings & revised_headings)
        if retained < max(1, len(original_headings) // 2):
            errors.append("too many original level-2 headings were removed")
    return errors


def request_revision(
    review: ReviewRequest,
    model: GeminiModelAdapter,
    tracker: UsageTracker,
    bodies: dict[str, str],
    front_matters: dict[str, str],
    research_facts: str,
) -> dict[str, str]:
    prompt = revision_prompt(review, bodies, research_facts)
    last_revised: dict[str, str] = {}
    last_errors: dict[str, list[str]] = {}

    for attempt in range(1, MAX_REVISION_ATTEMPTS + 1):
        raw = call_gemini(
            model,
            prompt,
            "revision_bilingual" if attempt == 1 else "revision_bilingual_repair",
            tracker,
            generation_config=REVISION_CONFIG,
        )
        revised = parse_revision_response(raw)

        errors: dict[str, list[str]] = {}
        for lang in ("ko", "en"):
            body = revised.get(lang, "").strip()
            if not body:
                errors[lang] = [f"Revision response missing {lang} body"]
                continue
            body_errors = revised_body_errors(front_matters[lang], body, lang)
            body_errors.extend(revision_preservation_errors(bodies[lang], body, lang))
            if body_errors:
                errors[lang] = body_errors

        if not errors:
            return revised

        last_revised = revised
        last_errors = errors
        if attempt < MAX_REVISION_ATTEMPTS:
            print(f"[Revision] Validation failed on attempt {attempt}; requesting full-body repair: {errors}")
            prompt = revision_retry_prompt(review, bodies, research_facts, revised, errors)

    first_lang, first_errors = next(iter(last_errors.items()))
    raise ContentValidationError(first_lang, first_errors)


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

    research_facts = collect_review_research(review, bodies)
    revised = request_revision(review, model, tracker, bodies, front_matters, research_facts)

    updated_paths = []
    for lang, path in post_paths.items():
        body = revised.get(lang, "").strip()
        validate_revised_body(front_matters[lang], body, lang)
        path.write_text(f"{front_matters[lang]}{body}\n", encoding="utf-8")
        updated_paths.append(str(path))

    updated_paths.extend(generate_knowledge_notes(updated_paths))
    return updated_paths


def complete_review(review: ReviewRequest) -> Path:
    deleted_path = review.path
    review.path.unlink()
    return deleted_path


def main(argv: Iterable[str] | None = None) -> None:
    del argv
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required")

    review_filter = os.environ.get("REVIEW_FILTER", "").strip()
    reviews = filter_reviews(discover_ready_reviews(), review_filter)
    if not reviews:
        if review_filter:
            print(f"No ready review notes matched filter: {review_filter}")
        else:
            print("No ready review notes found.")
        return

    from google import genai

    client = genai.Client(api_key=api_key)
    model = GeminiModelAdapter(client, GEMINI_MODEL)
    tracker = UsageTracker()
    changed_files: list[str] = []
    review_files: list[str] = []

    print(f"[Revision] Model: {GEMINI_MODEL}")

    for review in reviews:
        print(f"[Revision] Applying {review.path}")
        review_changed_files = apply_revision(review, model, tracker)
        changed_files.extend(review_changed_files)
        review_files.append(str(complete_review(review)))

    env_path = os.environ.get("GITHUB_ENV")
    if env_path:
        with open(env_path, "a", encoding="utf-8") as env_file:
            env_file.write(f"REVISION_CHANGED_FILES={','.join(changed_files + review_files)}\n")
    print("Updated files:")
    for path in changed_files + review_files:
        print(f"  - {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
