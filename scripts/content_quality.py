"""Deterministic classification, references, and post validation utilities."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Iterable


ENGINEER_TERMS = (
    "api",
    "backend",
    "bgp",
    "cloud computing",
    "compiler",
    "container orchestration",
    "database",
    "devops",
    "docker",
    "frontend",
    "http",
    "javascript",
    "kubernetes",
    "linux",
    "machine learning",
    "microservice",
    "network protocol",
    "neural network",
    "operating system",
    "programming",
    "python",
    "software architecture",
    "software engineering",
    "sql",
    "tcp",
    "네트워크",
    "데이터베이스",
    "데브옵스",
    "도커",
    "리눅스",
    "머신러닝",
    "백엔드",
    "보안 프로토콜",
    "소프트웨어 아키텍처",
    "소프트웨어 개발",
    "알고리즘",
    "운영체제",
    "인공지능 모델",
    "자바스크립트",
    "앱 개발",
    "컴파일러",
    "컨테이너 오케스트레이션",
    "클라우드 컴퓨팅",
    "쿠버네티스",
    "파이썬",
    "프로그래밍",
    "프론트엔드",
    "웹 개발",
)

STOPWORDS = {
    "about",
    "and",
    "blog",
    "explain",
    "for",
    "from",
    "how",
    "into",
    "please",
    "does",
    "the",
    "this",
    "what",
    "why",
    "work",
    "글",
    "대해",
    "대한",
    "설명",
    "알려줘",
    "어떻게",
    "왜",
    "작성",
    "포스팅",
}

META_PATTERN = re.compile(r"```json_meta\s*(\{.*?\})\s*```", re.DOTALL)
JSON_FENCE_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
URL_PATTERN = re.compile(r"https?://[^\s)>\]}`]+")


def _contains_term(text: str, term: str) -> bool:
    if re.search(r"[가-힣]", term) or " " in term:
        return term in text
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def classify_query(query: str) -> dict:
    """Classify a topic locally so classification consumes no Gemini request."""
    cleaned = re.sub(r"\s+", " ", query).strip()
    lowered = cleaned.lower()
    matched_terms = [term for term in ENGINEER_TERMS if _contains_term(lowered, term)]
    mode = "engineer" if matched_terms else "trivia"

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]*|[가-힣]{2,}", cleaned)
    keywords = []
    seen = set()
    for token in tokens:
        normalized = token.lower()
        if normalized in STOPWORDS or normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(token)
        if len(keywords) == 5:
            break
    if not keywords:
        keywords = matched_terms[:5] or ["knowledge"]

    topic = cleaned or "Untitled topic"
    return {
        "mode": mode,
        "topic_ko": topic[:40],
        "topic_en": topic[:60],
        "keywords": keywords,
        "search_query": topic,
        "classification_source": "local_rules",
    }


def extract_references(facts: str, limit: int = 12) -> list[dict[str, str]]:
    """Extract source titles and URLs from normalized search output."""
    references: list[dict[str, str]] = []
    seen_urls = set()
    current_title = "Source"

    for raw_line in facts.splitlines():
        line = raw_line.strip()
        title_match = re.match(r"(?:\[[^]]+\]\s*)?Title:\s*(.+)", line, re.IGNORECASE)
        if title_match:
            current_title = title_match.group(1).strip()
            continue

        link_match = re.match(r"(?:DOI\s+)?Link:\s*(https?://\S+)", line, re.IGNORECASE)
        if not link_match:
            continue
        url = link_match.group(1).rstrip(".,;)")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        safe_title = current_title.replace("[", "").replace("]", "")
        references.append({"title": safe_title, "url": url})
        if len(references) == limit:
            break

    return references


def normalize_metadata_block(content: str) -> str:
    """Convert a metadata-shaped generic JSON fence into json_meta locally."""
    if META_PATTERN.search(content):
        return content

    matches = list(JSON_FENCE_PATTERN.finditer(content))
    for match in reversed(matches):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if all(field_name in payload for field_name in ("title", "description", "tags")):
            replacement = f"```json_meta\n{match.group(1)}\n```"
            return content[: match.start()] + replacement + content[match.end() :]
    return content


def append_references(content: str, lang: str, references: Iterable[dict[str, str]]) -> str:
    """Append deterministic references immediately before the json_meta block."""
    content = normalize_metadata_block(content)
    references = list(references)
    if not references:
        return content.strip()

    meta_match = META_PATTERN.search(content)
    meta_block = meta_match.group(0) if meta_match else ""
    body = content[: meta_match.start()].strip() if meta_match else content.strip()

    # Replace a trailing model-written reference section to prevent duplicates.
    body = re.sub(
        r"\n##\s+(?:References|참고자료)\s*"
        r"(?:\n+\s*-\s+\[[^\]\n]+\]\([^)\n]+\)\s*)+$",
        "",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    heading = "참고자료" if lang == "ko" else "References"
    lines = [f"- [{item['title']}]({item['url']})" for item in references]
    result = f"{body}\n\n## {heading}\n\n" + "\n".join(lines)
    if meta_block:
        result += f"\n\n{meta_block}"
    return result


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


class ContentValidationError(ValueError):
    """Raised when deterministic post validation blocks publication."""

    category = "content_validation_error"

    def __init__(self, lang: str, errors: Iterable[str]) -> None:
        self.stage = f"local_validation_{lang}"
        self.errors = list(errors)
        super().__init__(f"Local validation failed for {lang}: " + "; ".join(self.errors))


def validate_post(content: str, lang: str, source_urls: Iterable[str]) -> ValidationResult:
    """Validate structural requirements without spending another model call."""
    result = ValidationResult()
    meta_match = META_PATTERN.search(content)
    if not meta_match:
        result.errors.append("missing json_meta block")
        metadata = {}
    else:
        try:
            metadata = json.loads(meta_match.group(1))
        except json.JSONDecodeError:
            metadata = {}
            result.errors.append("invalid json_meta JSON")

    if metadata:
        for field_name in ("title", "description", "tags"):
            if not metadata.get(field_name):
                result.errors.append(f"json_meta missing {field_name}")
        if metadata.get("tags") and not isinstance(metadata["tags"], list):
            result.errors.append("json_meta tags must be an array")

    body = META_PATTERN.sub("", content).strip()
    if len(re.findall(r"^##\s+", body, re.MULTILINE)) < 2:
        result.errors.append("post requires at least two level-2 headings")
    if content.count("```") % 2:
        result.errors.append("unbalanced fenced code block")

    if lang == "ko":
        if len(body) < 1200:
            result.errors.append("Korean body is below the 1200-character safety floor")
        elif len(body) < 3000:
            result.warnings.append("Korean body is below the 3000-character target")
    else:
        word_count = len(re.findall(r"\b[\w'-]+\b", body))
        if word_count < 450:
            result.errors.append("English body is below the 450-word safety floor")
        elif word_count < 1200:
            result.warnings.append("English body is below the 1200-word target")

    allowed_urls = set(source_urls)
    content_urls = set(URL_PATTERN.findall(content))
    unknown_urls = sorted(content_urls - allowed_urls)
    if unknown_urls:
        result.warnings.append(
            "post contains URLs not present in collected sources: " + ", ".join(unknown_urls[:3])
        )

    if allowed_urls and not re.search(r"^##\s+(?:References|참고자료)\s*$", body, re.MULTILINE):
        result.errors.append("deterministic references section is missing")

    for mermaid in re.findall(r"```mermaid\s*(.*?)```", content, re.DOTALL):
        if re.search(r'\b[A-Za-z]\w*\[([^\]"].*?)\]', mermaid):
            result.warnings.append("Mermaid block may contain an unquoted node label")
            break

    return result
