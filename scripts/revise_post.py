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

from content_quality import ContentValidationError, append_references, validate_post
from content_quality import build_search_queries, extract_references, is_usable_search_result
from gemini_runtime import UsageTracker, call_gemini
from generate_knowledge_notes import generate_knowledge_notes


DEFAULT_REVIEW_DIR = Path("_reviews/pending")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-3.1-flash-lite"
REVISION_PLAN_CONFIG = {
    "temperature": 0.1,
    "max_output_tokens": 4096,
    "response_mime_type": "application/json",
}
REVISION_EDIT_CONFIG = {
    "temperature": 0.2,
    "max_output_tokens": 16384,
    "response_mime_type": "application/json",
}
PLACEHOLDER_POST_IDS = {"", "replace-with-real-post-id"}


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


def normalize_legacy_section_headings(body: str) -> str:
    """Promote H3 sections when a legacy post has no H2 sections."""
    if re.search(r"^##\s+", body, re.MULTILINE):
        return body
    return re.sub(r"^###(?=\s+)", "##", body, flags=re.MULTILINE)


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


def is_placeholder_post_id(post_id: str) -> bool:
    return post_id.strip().casefold() in PLACEHOLDER_POST_IDS


def discover_ready_reviews(directory: Path = DEFAULT_REVIEW_DIR) -> list[ReviewRequest]:
    reviews = []
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue
        if path.name.startswith("example-"):
            continue
        review = parse_review_note(path)
        if review.status.casefold() == "ready":
            if is_placeholder_post_id(review.target_post_id):
                print(
                    f"[Revision] Skipping {path}: target_post_id is missing or still a template placeholder"
                )
                continue
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


def front_matter_title(front_matter: str) -> str:
    metadata, _body = parse_front_matter(front_matter)
    return str(metadata.get("title") or "").strip()


def collect_review_research(
    review: ReviewRequest,
    bodies: dict[str, str],
    front_matters: dict[str, str] | None = None,
    search_queries: list[str] | None = None,
) -> str:
    """Collect lightweight English facts for review-driven enrichment."""
    seeds = list(search_queries or [])
    instruction_text = " ".join(review.instructions)
    if instruction_text:
        seeds.extend(build_search_queries(instruction_text, limit=4))
    if front_matters:
        title = front_matter_title(front_matters.get("en", ""))
        if title:
            seeds.extend(build_search_queries(title, limit=3))
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


def parse_json_response(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Gemini response must be a JSON object")
    return payload


def split_markdown_sections(body: str) -> list[dict[str, str]]:
    """Split a post body into a preamble and stable H2 section IDs."""
    sections = [{"id": "preamble", "content": ""}]
    fence = ""
    section_index = 0
    for line in body.strip().splitlines():
        marker = line.strip()[:3]
        if marker in {"```", "~~~"}:
            fence = "" if fence == marker else marker if not fence else fence
        if not fence and re.match(r"^##\s+", line):
            section_index += 1
            sections.append({"id": f"section_{section_index}", "content": line})
        else:
            sections[-1]["content"] += ("\n" if sections[-1]["content"] else "") + line
    return sections


def section_catalog(body: str) -> str:
    catalog = []
    for section in split_markdown_sections(body):
        first_line = section["content"].splitlines()[0] if section["content"] else "(empty)"
        catalog.append(f"- {section['id']}: {first_line}")
    return "\n".join(catalog)


def split_markdown_blocks(content: str) -> tuple[str, list[str]]:
    """Split one section into its heading and fence-aware paragraph blocks."""
    lines = content.strip().splitlines()
    heading = lines.pop(0).strip() if lines and re.match(r"^##\s+", lines[0]) else ""
    blocks: list[str] = []
    current: list[str] = []
    fence = ""
    for line in lines:
        marker = line.strip()[:3]
        if not fence and not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
        if marker in {"```", "~~~"}:
            fence = "" if fence == marker else marker if not fence else fence
    if current:
        blocks.append("\n".join(current).strip())
    return heading, blocks


def block_catalog(body: str) -> str:
    catalog = []
    for section in split_markdown_sections(body):
        heading, blocks = split_markdown_blocks(section["content"])
        catalog.append(f"- {section['id']}: {heading or '(preamble)'}")
        for index, block in enumerate(blocks, 1):
            preview = re.sub(r"\s+", " ", block)[:160]
            catalog.append(f"  - {section['id']}.block_{index}: {preview}")
    return "\n".join(catalog)


def replace_markdown_block(content: str, block_number: int, replacement: str) -> str:
    heading, blocks = split_markdown_blocks(content)
    if block_number < 1 or block_number > len(blocks):
        raise ValueError(f"Unknown Markdown block: block_{block_number}")
    blocks[block_number - 1] = replacement
    return "\n\n".join(part for part in [heading, *blocks] if part)


def revision_plan_prompt(review: ReviewRequest, bodies: dict[str, str]) -> str:
    instructions = "\n".join(
        f"R{index}: {instruction}" for index, instruction in enumerate(review.instructions, 1)
    )
    return f"""
Convert this Obsidian Review Note into a deterministic bilingual edit plan.

Review scope: {review.scope}
Instructions:
{instructions}

Korean section catalog:
{section_catalog(bodies['ko'])}

English section catalog:
{section_catalog(bodies['en'])}

For each instruction return one action with the same R-number.
Kinds: delete, replace, enrich, style.
Set requires_research only when new factual content is requested.
Create short English search queries only for factual enrichment.
Create literal must_include and must_exclude checks when the instruction names required or forbidden wording.

Return JSON only:
{{
  "actions": [
    {{
      "id": "R1",
      "instruction": "original instruction",
      "kind": "delete|replace|enrich|style",
      "languages": ["en", "ko"],
      "requires_research": false,
      "must_include": {{"en": [], "ko": []}},
      "must_exclude": {{"en": [], "ko": []}}
    }}
  ],
  "search_queries_en": []
}}
"""


def validate_revision_plan(review: ReviewRequest, payload: dict[str, Any]) -> dict[str, Any]:
    actions = payload.get("actions")
    if not isinstance(actions, list):
        raise ValueError("Revision plan is missing actions")
    expected = {f"R{index}" for index in range(1, len(review.instructions) + 1)}
    actual = {str(action.get("id") or "") for action in actions if isinstance(action, dict)}
    if actual != expected:
        raise ValueError(f"Revision plan action IDs must be {sorted(expected)}; received {sorted(actual)}")
    allowed_kinds = {"delete", "replace", "enrich", "style"}
    for action in actions:
        if action.get("kind") not in allowed_kinds:
            raise ValueError(f"Unsupported revision action kind: {action.get('kind')}")
        languages = action.get("languages")
        if not isinstance(languages, list) or not languages or not set(languages) <= {"en", "ko"}:
            raise ValueError(f"Revision action {action['id']} has invalid languages")
        for field_name in ("must_include", "must_exclude"):
            values = action.get(field_name) or {}
            if not isinstance(values, dict):
                raise ValueError(f"Revision action {action['id']} has invalid {field_name}")
            for lang in ("en", "ko"):
                if not isinstance(values.get(lang, []), list):
                    raise ValueError(
                        f"Revision action {action['id']} has invalid {field_name}.{lang}"
                    )
    queries = payload.get("search_queries_en") or []
    if not isinstance(queries, list):
        raise ValueError("Revision plan search_queries_en must be a list")
    if any(action.get("requires_research") for action in actions) and not queries:
        raise ValueError("Factual revision actions require at least one English search query")
    payload["search_queries_en"] = [
        str(query).strip()
        for query in queries
        if str(query).strip() and re.search(r"[A-Za-z]", str(query))
    ][:5]
    if any(action.get("requires_research") for action in actions) and not payload["search_queries_en"]:
        raise ValueError("Factual revision actions require usable English search queries")
    return payload


def create_revision_plan(
    review: ReviewRequest,
    bodies: dict[str, str],
    model: GeminiModelAdapter,
    tracker: UsageTracker,
) -> dict[str, Any]:
    raw = call_gemini(
        model,
        revision_plan_prompt(review, bodies),
        "revision_plan",
        tracker,
        generation_config=REVISION_PLAN_CONFIG,
    )
    plan = validate_revision_plan(review, parse_json_response(raw))
    summary = ", ".join(
        f"{action['id']}:{action['kind']}[{','.join(action['languages'])}]"
        for action in plan["actions"]
    )
    print(f"[RevisionPlan] Actions: {summary}")
    print(f"[RevisionPlan] English search queries: {plan['search_queries_en']}")
    return plan


def language_edit_prompt(
    lang: str,
    body: str,
    plan: dict[str, Any],
    research_facts: str,
) -> str:
    language = "Korean" if lang == "ko" else "English"
    language_plan = {
        **plan,
        "actions": [action for action in plan["actions"] if lang in action["languages"]],
    }
    return f"""
Apply the structured Review Note plan to this existing {language} Markdown article.
Return only operations for sections that must change. Unmentioned sections will be preserved by code.

Rules:
1. Targets are stable section or paragraph-block IDs from the catalog.
2. replace content must contain the complete replacement block, including its ## heading for a section.
3. Use replace_block for wording and style changes. Return only the new paragraph content.
4. Prefer insert_after for enrichment. Use replace_block only when expanding one existing paragraph.
5. delete removes the target block. insert_after adds a complete new block after the target.
6. Preserve facts, tables, Mermaid diagrams, code blocks, headings, and references unless an action changes them.
7. Every action ID must appear in applied or unresolved. Do not claim applied unless its operation is present.
8. Use declarative Korean endings such as ~이다/~했다 when the plan requests a neutral style.
Plan:
{json.dumps(language_plan, ensure_ascii=False)}

Research facts:
---
{research_facts.strip() or "No additional research was required."}
---

Section catalog:
{block_catalog(body)}

Current body:
---
{body}
---

Return JSON only:
{{
  "operations": [
    {{"action_ids": ["R1"], "operation": "replace|replace_block|delete|insert_after", "target": "preamble|section_N|section_N.block_N", "content": ""}}
  ],
  "applied": ["R1"],
  "unresolved": []
}}
"""


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


def heading_preservation_errors(original: str, revised: str) -> list[str]:
    """Guard against removing most existing sections."""
    errors = []
    original_headings = set(re.findall(r"^##\s+(.+)$", original, re.MULTILINE))
    revised_headings = set(re.findall(r"^##\s+(.+)$", revised, re.MULTILINE))
    if len(original_headings) >= 2:
        retained = len(original_headings & revised_headings)
        if retained < max(1, len(original_headings) // 2):
            errors.append("too many original level-2 headings were removed")
    return errors


def plan_criteria(plan: dict[str, Any], field_name: str, lang: str) -> list[str]:
    values = []
    for action in plan["actions"]:
        if lang not in action["languages"]:
            continue
        lang_values = (action.get(field_name) or {}).get(lang) or []
        values.extend(str(value).strip() for value in lang_values if str(value).strip())
    return values


def plan_applies_to(plan: dict[str, Any], lang: str) -> bool:
    return any(lang in action["languages"] for action in plan["actions"])


def apply_section_operations(
    original: str,
    payload: dict[str, Any],
    plan: dict[str, Any],
    lang: str,
) -> str:
    required = {
        str(action["id"])
        for action in plan["actions"]
        if lang in action["languages"]
    }
    applied = {str(action_id) for action_id in payload.get("applied") or []}
    unresolved = [str(action_id) for action_id in payload.get("unresolved") or []]
    if unresolved:
        raise ValueError(f"Unresolved {lang} revision actions: {unresolved}")
    if applied != required:
        raise ValueError(
            f"Applied {lang} revision actions must be {sorted(required)}; received {sorted(applied)}"
        )

    operations = payload.get("operations")
    if not isinstance(operations, list):
        raise ValueError(f"{lang} revision response is missing operations")
    sections = split_markdown_sections(original)
    operation_actions = set()
    touched = set()
    action_kinds = {str(action["id"]): str(action["kind"]) for action in plan["actions"]}
    allowed_operations = {
        "delete": {"delete"},
        "replace": {"replace", "replace_block"},
        "enrich": {"insert_after", "replace_block"},
        "style": {"replace_block"},
    }
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError(f"Invalid {lang} revision operation")
        action_ids = operation.get("action_ids")
        if action_ids is None:
            action_ids = [operation.get("action_id")]
        if not isinstance(action_ids, list) or not action_ids:
            raise ValueError(f"Invalid {lang} revision action IDs")
        action_ids = {str(action_id or "") for action_id in action_ids}
        operation_name = str(operation.get("operation") or "")
        target = str(operation.get("target") or "")
        content = str(operation.get("content") or "").strip()
        unknown_actions = action_ids - required
        if unknown_actions:
            raise ValueError(f"Unknown {lang} revision actions: {sorted(unknown_actions)}")
        if operation_name not in {"replace", "replace_block", "delete", "insert_after"}:
            raise ValueError(f"Unsupported {lang} revision operation: {operation_name}")
        incompatible = {
            action_id
            for action_id in action_ids
            if operation_name not in allowed_operations[action_kinds[action_id]]
        }
        if incompatible:
            raise ValueError(
                f"Unsafe {lang} {operation_name} operation for actions: {sorted(incompatible)}"
            )
        touch_key = (operation_name, target)
        if touch_key in touched:
            raise ValueError(f"Duplicate {lang} revision operation for {target}")
        block_match = re.fullmatch(r"(preamble|section_\d+)\.block_(\d+)", target)
        section_target = block_match.group(1) if block_match else target
        target_index = next(
            (index for index, section in enumerate(sections) if section["id"] == section_target),
            None,
        )
        if target_index is None:
            raise ValueError(f"Unknown {lang} revision target: {target}")
        if operation_name != "delete" and not content:
            raise ValueError(f"{operation_name} requires content for {lang} target {target}")

        if operation_name == "replace":
            sections[target_index]["content"] = content
        elif operation_name == "replace_block":
            if not block_match:
                raise ValueError(f"replace_block requires a block target for {lang}: {target}")
            sections[target_index]["content"] = replace_markdown_block(
                sections[target_index]["content"], int(block_match.group(2)), content
            )
        elif operation_name == "delete":
            sections[target_index]["content"] = ""
        else:
            sections.insert(
                target_index + 1,
                {"id": f"inserted_{len(sections)}", "content": content},
            )
        touched.add(touch_key)
        operation_actions.update(action_ids)

    if operation_actions != required:
        raise ValueError(
            f"Operations for {lang} must cover {sorted(required)}; received {sorted(operation_actions)}"
        )

    revised = "\n\n".join(
        section["content"].strip() for section in sections if section["content"].strip()
    )
    for value in plan_criteria(plan, "must_include", lang):
        if value.casefold() not in revised.casefold():
            raise ValueError(f"Revised {lang} body is missing required content: {value}")
    for value in plan_criteria(plan, "must_exclude", lang):
        if value.casefold() in revised.casefold():
            raise ValueError(f"Revised {lang} body still contains forbidden content: {value}")
    if revised.strip() == original.strip():
        raise ValueError(f"Revision operations did not change the {lang} body")
    return normalize_legacy_section_headings(revised)


def request_language_revision(
    lang: str,
    model: GeminiModelAdapter,
    tracker: UsageTracker,
    body: str,
    plan: dict[str, Any],
    research_facts: str,
) -> str:
    raw = call_gemini(
        model,
        language_edit_prompt(lang, body, plan, research_facts),
        f"revision_{lang}",
        tracker,
        generation_config=REVISION_EDIT_CONFIG,
    )
    payload = parse_json_response(raw)
    print(
        f"[Revision:{lang}] Received {len(payload.get('operations') or [])} operations; "
        f"applied={payload.get('applied') or []}; unresolved={payload.get('unresolved') or []}"
    )
    return apply_section_operations(body, payload, plan, lang)


def request_revision(
    model: GeminiModelAdapter,
    tracker: UsageTracker,
    bodies: dict[str, str],
    front_matters: dict[str, str],
    plan: dict[str, Any],
    research_facts: str,
) -> dict[str, str]:
    revised_english = bodies["en"]
    if plan_applies_to(plan, "en"):
        revised_english = request_language_revision(
            "en", model, tracker, bodies["en"], plan, research_facts
        )
        english_errors = revised_body_errors(front_matters["en"], revised_english, "en")
        english_errors.extend(heading_preservation_errors(bodies["en"], revised_english))
        if english_errors:
            raise ContentValidationError("en", english_errors)

    revised_korean = bodies["ko"]
    if plan_applies_to(plan, "ko"):
        revised_korean = request_language_revision(
            "ko", model, tracker, bodies["ko"], plan, research_facts
        )
        korean_errors = revised_body_errors(front_matters["ko"], revised_korean, "ko")
        korean_errors.extend(heading_preservation_errors(bodies["ko"], revised_korean))
        if korean_errors:
            raise ContentValidationError("ko", korean_errors)
    return {"en": revised_english, "ko": revised_korean}


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
        bodies[lang] = normalize_legacy_section_headings(body)

    plan = create_revision_plan(review, bodies, model, tracker)
    search_queries = plan["search_queries_en"]
    research_facts = (
        collect_review_research(review, bodies, front_matters, search_queries)
        if search_queries
        else ""
    )
    revised = request_revision(model, tracker, bodies, front_matters, plan, research_facts)
    references = extract_references(research_facts)
    if references:
        revised = {
            lang: append_references(body, lang, references) if plan_applies_to(plan, lang) else body
            for lang, body in revised.items()
        }

    validated_bodies: dict[str, str] = {}
    for lang, path in post_paths.items():
        if not plan_applies_to(plan, lang):
            continue
        body = revised.get(lang, "").strip()
        validate_revised_body(front_matters[lang], body, lang)
        validated_bodies[lang] = body

    updated_paths = []
    for lang, body in validated_bodies.items():
        path = post_paths[lang]
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
