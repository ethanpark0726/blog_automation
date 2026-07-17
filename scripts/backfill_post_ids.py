#!/usr/bin/env python3
"""Backfill stable post_id values for existing Jekyll posts.

Phase 4 review revisions target a bilingual post pair by `post_id`. Older posts
created before the post_id field existed can still participate as long as every
KO/EN file sharing the same `topic_id` receives the same deterministic post_id.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


FRONT_MATTER_RE = re.compile(r"\A---\n(?P<front_matter>.*?)\n---\n", re.DOTALL)
FIELD_RE = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*?)\s*$", re.MULTILINE)


@dataclass
class PostFile:
    path: Path
    content: str
    front_matter: str
    topic_id: str
    post_id: str


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_front_matter(content: str) -> str:
    match = FRONT_MATTER_RE.match(content)
    return match.group("front_matter") if match else ""


def front_matter_field(front_matter: str, key: str) -> str:
    for match in FIELD_RE.finditer(front_matter):
        if match.group("key") == key:
            return unquote(match.group("value"))
    return ""


def read_post(path: Path) -> PostFile:
    content = path.read_text(encoding="utf-8")
    front_matter = parse_front_matter(content)
    return PostFile(
        path=path,
        content=content,
        front_matter=front_matter,
        topic_id=front_matter_field(front_matter, "topic_id"),
        post_id=front_matter_field(front_matter, "post_id"),
    )


def deterministic_post_id(topic_id: str) -> str:
    suffix = hashlib.sha256(topic_id.encode("utf-8")).hexdigest()[:8]
    return f"{topic_id}-{suffix}"


def collect_posts(posts_dir: Path) -> list[PostFile]:
    return [read_post(path) for path in sorted(posts_dir.glob("*/*.md"))]


def post_ids_by_topic(posts: list[PostFile]) -> dict[str, str]:
    grouped: dict[str, set[str]] = {}
    for post in posts:
        if post.topic_id and post.post_id:
            grouped.setdefault(post.topic_id, set()).add(post.post_id)

    conflicts = {topic: ids for topic, ids in grouped.items() if len(ids) > 1}
    if conflicts:
        details = "; ".join(f"{topic}: {sorted(ids)}" for topic, ids in sorted(conflicts.items()))
        raise ValueError(f"Conflicting existing post_id values for topic_id: {details}")

    return {topic: next(iter(ids)) for topic, ids in grouped.items()}


def insert_post_id(content: str, post_id: str) -> str:
    if re.search(r"^post_id:\s*", content, re.MULTILINE):
        return content
    return re.sub(
        r"^(topic_id:\s*.*\n)",
        rf'\1post_id: "{post_id}"' + "\n",
        content,
        count=1,
        flags=re.MULTILINE,
    )


def backfill_post_ids(posts_dir: Path, dry_run: bool = False) -> tuple[list[Path], list[Path]]:
    posts = collect_posts(posts_dir)
    known_post_ids = post_ids_by_topic(posts)
    updated: list[Path] = []
    skipped: list[Path] = []

    for post in posts:
        if post.post_id:
            continue
        if not post.topic_id:
            skipped.append(post.path)
            continue

        post_id = known_post_ids.get(post.topic_id) or deterministic_post_id(post.topic_id)
        new_content = insert_post_id(post.content, post_id)
        if new_content == post.content:
            skipped.append(post.path)
            continue

        if not dry_run:
            post.path.write_text(new_content, encoding="utf-8", newline="\n")
        updated.append(post.path)
        print(f"{'Would update' if dry_run else 'Updated'} {post.path.as_posix()} -> {post_id}")

    return updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill missing post_id fields in _posts.")
    parser.add_argument("--posts-dir", default="_posts", help="Posts root directory. Defaults to _posts.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if any post with topic_id is missing post_id.",
    )
    args = parser.parse_args()

    posts_dir = Path(args.posts_dir)
    updated, skipped = backfill_post_ids(posts_dir, dry_run=args.dry_run or args.check)

    if skipped:
        print("\nSkipped files without usable topic_id/post_id placement:")
        for path in skipped:
            print(f"  - {path.as_posix()}")

    print(f"\nBackfill complete. Updated {len(updated)} files. Skipped {len(skipped)} files.")
    if args.check and updated:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
