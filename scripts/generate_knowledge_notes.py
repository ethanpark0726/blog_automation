#!/usr/bin/env python3
"""Generate Obsidian knowledge notes from newly created blog posts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
REFERENCE_PATTERN = re.compile(r"^\s*-\s+\[([^\]\n]+)\]\((https?://[^)\s]+)\)", re.MULTILINE)


@dataclass
class PostInfo:
    path: Path
    title: str
    lang: str
    topic_id: str
    post_id: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    references: list[tuple[str, str]] = field(default_factory=list)


def slugify(value: str, fallback: str = "note") -> str:
    value = re.sub(r"[^\w\s-]", "", value.lower(), flags=re.UNICODE)
    value = re.sub(r"[\s_]+", "-", value).strip("-")
    return value[:80] or fallback


def parse_front_matter(text: str) -> dict:
    match = FRONT_MATTER_PATTERN.search(text)
    if not match:
        return {}
    metadata: dict[str, object] = {}
    current_list: str | None = None
    for raw_line in match.group(1).splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
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
    return metadata


def parse_post(path: Path) -> PostInfo:
    text = path.read_text(encoding="utf-8")
    metadata = parse_front_matter(text)
    topic_id = str(metadata.get("topic_id") or slugify(path.stem))
    return PostInfo(
        path=path,
        title=str(metadata.get("title") or path.stem),
        lang=str(metadata.get("lang") or path.parent.name),
        topic_id=topic_id,
        post_id=str(metadata.get("post_id") or topic_id),
        description=str(metadata.get("description") or ""),
        tags=list(metadata.get("tags") or []),
        references=REFERENCE_PATTERN.findall(text),
    )


def wikilink(path: Path, label: str) -> str:
    return f"[[{path.stem}|{label}]]"


def concept_note_path(label: str) -> Path:
    return Path("_knowledge/concepts") / f"{slugify(label)}.md"


def source_note_path(url: str) -> Path:
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "") or "source"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return Path("_knowledge/sources") / f"{slugify(domain)}-{digest}.md"


def write_if_missing(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def write_topic_note(posts: list[PostInfo]) -> Path:
    posts = sorted(posts, key=lambda item: item.lang)
    primary = next((post for post in posts if post.lang == "en"), posts[0])
    all_tags = []
    for post in posts:
        for tag in post.tags:
            if tag and tag.casefold() not in {item.casefold() for item in all_tags}:
                all_tags.append(tag)

    path = Path("_knowledge/concepts") / f"{primary.topic_id}.md"
    concept_links = [f"- [[{concept_note_path(tag).stem}|{tag}]]" for tag in all_tags[:12]]
    post_links = [
        f"- {post.lang.upper()}: {wikilink(post.path, post.title)} (`{post.path.as_posix()}`)"
        for post in posts
    ]
    source_links = []
    seen_urls = set()
    for post in posts:
        for title, url in post.references:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            source_links.append(f"- [[{source_note_path(url).stem}|{title}]]")

    content = f"""---
type: topic
topic_id: "{primary.topic_id}"
post_id: "{primary.post_id}"
aliases:
  - "{primary.title}"
tags:
  - knowledge
  - generated
---

# {primary.title}

## Summary
{primary.description or "Generated from the paired blog posts."}

## Related Posts
{chr(10).join(post_links) if post_links else "- "}

## Related Concepts
{chr(10).join(concept_links) if concept_links else "- "}

## Sources
{chr(10).join(source_links) if source_links else "- "}

## Follow-up Questions
- What adjacent concept should be explained next?
- Which source or claim deserves a deeper review?
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def generate_knowledge_notes(post_paths: list[str]) -> list[str]:
    posts = [parse_post(Path(path)) for path in post_paths if Path(path).exists()]
    grouped: dict[str, list[PostInfo]] = {}
    for post in posts:
        grouped.setdefault(post.topic_id, []).append(post)

    created_or_updated: list[str] = []
    for group_posts in grouped.values():
        topic_path = write_topic_note(group_posts)
        created_or_updated.append(str(topic_path))

        primary = next((post for post in group_posts if post.lang == "en"), group_posts[0])
        topic_link = f"[[{topic_path.stem}|{primary.title}]]"
        for tag in primary.tags[:12]:
            concept_path = concept_note_path(tag)
            if write_if_missing(
                concept_path,
                f"""---
type: concept
concept_id: "{concept_path.stem}"
aliases:
  - "{tag}"
tags:
  - concept
---

# {tag}

## Description
Concept note generated from {topic_link}.

## Related Topics
- {topic_link}
""",
            ):
                created_or_updated.append(str(concept_path))

        seen_urls = set()
        for post in group_posts:
            for title, url in post.references:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                source_path = source_note_path(url)
                if write_if_missing(
                    source_path,
                    f"""---
type: source
source_id: "{source_path.stem}"
url: "{url}"
tags:
  - source
---

# {title}

URL: {url}

## Related Topics
- {topic_link}
""",
                ):
                    created_or_updated.append(str(source_path))

    return created_or_updated


def main() -> None:
    import sys

    for path in generate_knowledge_notes(sys.argv[1:]):
        print(path)


if __name__ == "__main__":
    main()
