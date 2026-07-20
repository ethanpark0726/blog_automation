#!/usr/bin/env python3
"""
Multi-Agent Blog Generation System
====================================
Telegram input → [Research Writer] → [English Research/Editor] → [KO Localizer] → Jekyll Markdown

Agent configuration:
  1. ResearchWriterAgent  : Resolve English queries and create a provisional draft
  2. ScholarlySearchAgent : Collect English-language source facts without Gemini
  3. EnglishEditorAgent   : Ground and validate the canonical English article
  4. KoreanLocalizerAgent : Localize the validated article without adding claims
  5. FileWriterAgent      : Save paired Jekyll posts with duplicate fingerprints
"""

import os
import sys
import json
import hashlib
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google import genai

from content_quality import (
    ContentValidationError,
    append_missing_metadata_block,
    append_references,
    build_search_queries,
    classify_query,
    extract_references,
    is_usable_search_result,
    source_quality_score,
    validate_post,
)
from gemini_runtime import (
    UsageTracker,
    call_gemini as call_gemini_with_tracking,
    reset_pipeline_result,
    write_pipeline_result,
)
from generate_knowledge_notes import generate_knowledge_notes

# ── Load environment variables ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
QUERY_INPUT = os.environ.get("QUERY_INPUT", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-3.1-flash-lite"

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY environment variable is not set.")
    sys.exit(1)

if not QUERY_INPUT:
    print("❌ ERROR: QUERY_INPUT is empty.")
    sys.exit(1)

# ── Initialize Gemini ───────────────────────────────────────────────────────
class GeminiModelAdapter:
    """Expose the legacy model.generate_content shape over google-genai Client."""

    def __init__(self, client: genai.Client, model_name: str) -> None:
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt: str, generation_config: dict | None = None):
        kwargs = {
            "model": self.model_name,
            "contents": prompt,
        }
        if generation_config is not None:
            kwargs["config"] = generation_config
        return self.client.models.generate_content(**kwargs)


client = genai.Client(api_key=GEMINI_API_KEY)
model = GeminiModelAdapter(client, GEMINI_MODEL)
usage_tracker = UsageTracker()

STAGE_GENERATION_CONFIGS = {
    "research_writer_en": {"temperature": 0.6, "max_output_tokens": 12288},
    "editor_en": {"temperature": 0.2, "max_output_tokens": 12288},
    "localizer_ko": {"temperature": 0.2, "max_output_tokens": 8192},
}

STANDARD_SUCCESSFUL_CALLS = 3
CACHE_DIR = Path(".pipeline_cache")

KST = timezone(timedelta(hours=9))


def send_telegram(chat_id: str, text: str) -> None:
    """Send a Telegram message (progress notification)"""
    if not chat_id or not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[Telegram] Failed to send notification: {e}")


def call_gemini(prompt: str, stage: str, retry: int = 3) -> str:
    """Call Gemini through the shared quota-aware runtime."""
    return call_gemini_with_tracking(
        model=model,
        prompt=prompt,
        stage=stage,
        tracker=usage_tracker,
        retry=retry,
        generation_config=STAGE_GENERATION_CONFIGS.get(stage),
    )


def search_duckduckgo(query: str) -> str:
    """Collect fact data via DuckDuckGo Abstract API"""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "BlogBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        results = []
        if data.get("Abstract"):
            results.append(f"[Overview] {data['Abstract']}")
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"[Related] {topic['Text'][:200]}")
        return "\n".join(results) if results else "No search results"
    except Exception as e:
        return f"Search API error: {e}"


def search_google_books(query: str) -> str:
    """Search Google Books API for general science and trivia books"""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.googleapis.com/books/v1/volumes?q={encoded}&maxResults=3"
        req = urllib.request.Request(url, headers={"User-Agent": "BlogBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        results = []
        for item in data.get("items", []):
            volume_info = item.get("volumeInfo", {})
            title = volume_info.get("title", "Untitled Book")
            authors = ", ".join(volume_info.get("authors", ["Unknown Author"]))
            description = volume_info.get("description", "No description available.")
            description = re.sub(r'\s+', ' ', description)[:250]
            info_url = volume_info.get("infoLink", "")
            results.append(f"[Book] Title: {title}\nAuthor(s): {authors}\nSummary: {description}\nLink: {info_url}")
        return "\n\n".join(results) if results else "No books found."
    except Exception as e:
        return f"Google Books Search Error: {e}"


def search_arxiv(query: str) -> str:
    """Search arXiv API for academic papers and technical content"""
    try:
        encoded = urllib.parse.quote(query)
        url = f"http://export.arxiv.org/api/query?search_query=all:{encoded}&max_results=3"
        req = urllib.request.Request(url, headers={"User-Agent": "BlogBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
        
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        results = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.strip()
            title = re.sub(r'\s+', ' ', title)
            summary = entry.find('atom:summary', ns).text.strip()
            summary = re.sub(r'\s+', ' ', summary)[:250]
            url = entry.find('atom:id', ns).text.strip()
            results.append(f"[Academic Paper] Title: {title}\nAbstract: {summary}\nLink: {url}")
        return "\n\n".join(results) if results else "No papers found."
    except Exception as e:
        return f"arXiv Search Error: {e}"


def search_crossref(query: str) -> str:
    """Search Crossref API for scholarly work and DOI info"""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.crossref.org/works?query={encoded}&rows=3"
        req = urllib.request.Request(url, headers={
            "User-Agent": "BlogBot/1.0 (mailto:blog-bot@github-actions.com)"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        results = []
        items = data.get("message", {}).get("items", [])
        for item in items:
            title = " ".join(item.get("title", ["Untitled"]))
            authors_list = []
            for a in item.get("author", []):
                authors_list.append(f"{a.get('given', '')} {a.get('family', '')}".strip())
            authors = ", ".join(authors_list) if authors_list else "Unknown Author"
            
            abstract = item.get("abstract", "")
            if abstract:
                abstract = re.sub(r'<[^>]*>', '', abstract)
                abstract = re.sub(r'\s+', ' ', abstract)[:250]
            else:
                container = item.get("container-title", [""])[0]
                publisher = item.get("publisher", "")
                abstract = f"Published in: {container} by {publisher}"
            
            doi_url = item.get("URL", f"https://doi.org/{item.get('DOI', '')}")
            results.append(f"[Scholarly Publication] Title: {title}\nAuthor(s): {authors}\nAbstract: {abstract}\nDOI Link: {doi_url}")
        return "\n\n".join(results) if results else "No publications found."
    except Exception as e:
        return f"Crossref Search Error: {e}"


def search_wikipedia(query: str) -> str:
    """Search Wikipedia API for clean factual references"""
    try:
        encoded = urllib.parse.quote(query)
        wiki_lang = "ko" if re.search(r"[가-힣]", query) else "en"
        url = f"https://{wiki_lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&origin=*"
        req = urllib.request.Request(url, headers={"User-Agent": "BlogBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        results = []
        search_items = data.get("query", {}).get("search", [])[:3]
        for item in search_items:
            title = item.get("title")
            snippet = item.get("snippet", "")
            snippet = re.sub(r'<[^>]*>', '', snippet)
            snippet = re.sub(r'\s+', ' ', snippet)
            page_url = f"https://{wiki_lang}.wikipedia.org/wiki/{urllib.parse.quote(title)}"
            results.append(f"[Wikipedia] Title: {title}\nSnippet: {snippet}\nLink: {page_url}")
        return "\n\n".join(results) if results else "No Wikipedia pages found."
    except Exception as e:
        return f"Wikipedia Search Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Agent 1: ClassifierAgent
# ═══════════════════════════════════════════════════════════════════════════
class ClassifierAgent:
    def run(self, query: str) -> dict:
        print(f"\n[ClassifierAgent] Classifying input locally: '{query}'")
        result = classify_query(query)
        print(f"[ClassifierAgent] Classification complete: {result}")
        return result


class ResearchPlanError(ValueError):
    """Raised when the English research plan cannot be used safely."""

    category = "research_plan_error"
    stage = "research_writer_en"


class SourceCoverageError(ValueError):
    """Raised before long-form calls when English evidence is insufficient."""

    category = "source_coverage_error"
    stage = "english_source_coverage"


class DuplicateRequestError(ValueError):
    """Raised before API use when the same request was already published."""

    category = "duplicate_request"
    stage = "duplicate_guard"


class PipelineCheckpoint:
    """Persist completed model stages so a failed workflow rerun can resume."""

    def __init__(self, fingerprint: str) -> None:
        self.path = CACHE_DIR / f"{fingerprint}.json"
        self.data = self._load(fingerprint)

    def _load(self, fingerprint: str) -> dict:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {"fingerprint": fingerprint}
        if payload.get("fingerprint") != fingerprint:
            return {"fingerprint": fingerprint}
        print(f"[Checkpoint] Restored stages: {sorted(payload.get('stages', []))}")
        return payload

    def has(self, stage: str) -> bool:
        return stage in self.data.get("stages", [])

    def get(self, key: str):
        return self.data.get(key)

    def save(self, stage: str, **values) -> None:
        stages = set(self.data.get("stages", []))
        stages.add(stage)
        self.data.update(values)
        self.data["stages"] = sorted(stages)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
        print(f"[Checkpoint] Saved stage: {stage}")


def request_fingerprint(query: str) -> str:
    normalized = re.sub(r"\s+", " ", query).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def ensure_request_is_new(fingerprint: str) -> None:
    marker = f'request_fingerprint: "{fingerprint}"'
    for post_path in Path("_posts").glob("*/*.md"):
        try:
            header = post_path.read_text(encoding="utf-8")[:2000]
        except OSError:
            continue
        if marker in header:
            raise DuplicateRequestError(
                f"This Telegram request was already published in {post_path.as_posix()}"
            )


class ResearchWriterAgent:
    RESEARCH_PATTERN = re.compile(
        r"```json_research\s*(\{.*?\})\s*```",
        re.DOTALL,
    )

    def run(self, query: str, classification: dict) -> tuple[dict, str]:
        mode = classification.get("mode", "trivia")
        print("\n[ResearchWriterAgent] Resolving research intent and drafting English...")
        prompt = f"""
You are a multilingual research planner and professional English blog writer.
Interpret the user's question, disambiguate names from context, and write a provisional English article that will be fact-checked against external sources in the next stage.

User input: {query}
Local topic mode: {mode}

Article requirements:
- Write 1200-2000 English words with at least two `##` headings.
- Include detailed mechanisms, a comparison table, historical context, and practical examples.
- For technical topics, include code/configuration and a valid Mermaid diagram with quoted labels.
- Clearly qualify uncertain claims because external fact-checking happens after this draft.
- End the article with a valid `json_meta` block containing title, description, and tags.

After `json_meta`, append this machine-readable block:
```json_research
{{
  "canonical_topic_en": "clear natural-English topic",
  "search_queries_en": ["specific English query 1", "specific English query 2"],
  "intent_summary_en": "one-sentence interpretation"
}}
```

All research-plan values must be English. Provide 2-4 queries ordered from specific to broad.
Output only the complete English article followed by the `json_research` block.
"""
        raw = call_gemini(prompt, stage="research_writer_en")
        plan, draft = self._parse_output(raw)
        classification["topic_en"] = plan["canonical_topic_en"][:60]
        print(f"[ResearchWriterAgent] Plan and provisional draft complete: {plan}")
        return plan, draft

    @classmethod
    def _parse_output(cls, raw: str) -> tuple[dict, str]:
        match = cls.RESEARCH_PATTERN.search(raw)
        if not match:
            raise ResearchPlanError("Research writer did not return json_research metadata")
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise ResearchPlanError("Research writer returned invalid json_research JSON") from exc

        topic = str(payload.get("canonical_topic_en") or "").strip()
        raw_queries = payload.get("search_queries_en")
        queries = []
        if isinstance(raw_queries, list):
            for item in raw_queries:
                normalized = re.sub(r"\s+", " ", str(item)).strip()
                if normalized and normalized.casefold() not in {
                    query.casefold() for query in queries
                }:
                    queries.append(normalized[:160])

        if not topic or not re.search(r"[A-Za-z]", topic):
            raise ResearchPlanError("Research writer did not return an English canonical topic")
        if not queries or not all(re.search(r"[A-Za-z]", query) for query in queries):
            raise ResearchPlanError("Research writer did not return usable English search queries")

        draft = cls.RESEARCH_PATTERN.sub("", raw).strip()
        if "```json_meta" not in draft:
            draft = append_missing_metadata_block(
                draft,
                title=topic,
                description=str(payload.get("intent_summary_en") or f"An article about {topic}."),
                tags=queries[:3],
            )
        plan = {
            "canonical_topic_en": topic[:160],
            "search_queries_en": queries[:4],
            "intent_summary_en": str(payload.get("intent_summary_en") or "").strip()[:300],
        }
        return plan, draft


# ═══════════════════════════════════════════════════════════════════════════
# Agent 2: ScholarlySearchAgent
# ═══════════════════════════════════════════════════════════════════════════
class ScholarlySearchAgent:
    def run(self, classification: dict, plan: dict) -> str:
        mode = classification.get("mode", "engineer")
        seeds = [plan.get("canonical_topic_en", ""), *plan.get("search_queries_en", [])]
        queries = []
        for seed in seeds:
            if not seed or re.search(r"[가-힣]", seed):
                continue
            for variant in build_search_queries(seed, limit=4):
                if variant.casefold() not in {item.casefold() for item in queries}:
                    queries.append(variant)
                if len(queries) >= 8:
                    break
            if len(queries) >= 8:
                break

        if not queries:
            raise ResearchPlanError("No English search query was available")

        print(
            f"\n[ScholarlySearchAgent] Collecting English information for "
            f"'{plan.get('canonical_topic_en', queries[0])}' (mode: {mode})..."
        )
        print(f"[ScholarlySearchAgent] Search variants: {queries}")

        facts = []
        seen_results = set()

        def add_result(label: str, result: str) -> None:
            normalized = result.strip()
            if not is_usable_search_result(normalized) or normalized in seen_results:
                return
            seen_results.add(normalized)
            facts.append(f"=== {label} ===\n{normalized}")

        # DuckDuckGo's instant-answer endpoint is useful for broad queries but
        # not for every keyword fragment, so limit it to the first two variants.
        for search_query in queries[:2]:
            add_result("Web Summary (DuckDuckGo)", search_duckduckgo(search_query))

        # Wikipedia full-text search is cheap and benefits from pairwise entity
        # queries such as "Santa Fe" and "turquoise jewelry".
        for search_query in queries:
            add_result("Authoritative Reference (Wikipedia)", search_wikipedia(search_query))

        primary_query = plan.get("search_queries_en", [queries[0]])[0]
        if mode == "trivia":
            add_result("Book References (Google Books)", search_google_books(primary_query))
            add_result("Scholarly Publications (Crossref)", search_crossref(primary_query))
        else:
            # Engineer mode: arXiv, Crossref, and standards/vendor references.
            add_result("Academic Literature (arXiv)", search_arxiv(primary_query))
            add_result("Scholarly Publications (Crossref)", search_crossref(primary_query))

            vendor_query = (
                f"{primary_query} "
                "(site:cisco.com OR site:arista.com OR site:ietf.org OR site:rfc-editor.org)"
            )
            add_result(
                "Vendor Whitepapers & Standards (Cisco/Arista/IETF)",
                search_duckduckgo(vendor_query),
            )
        
        combined_facts = "\n\n".join(facts)
        print(f"[ScholarlySearchAgent] Collection complete (length: {len(combined_facts)} chars)")
        references = extract_references(combined_facts)
        domains = {
            urllib.parse.urlparse(reference["url"]).netloc.lower()
            for reference in references
            if reference.get("url")
        }
        print(
            f"[ScholarlySearchAgent] Source coverage: {len(references)} references, "
            f"{len(domains)} domains"
        )
        if len(combined_facts) < 500 or len(references) < 2:
            raise SourceCoverageError(
                "English source coverage is below the publication floor: "
                f"{len(combined_facts)} fact characters, {len(references)} references, "
                f"{len(domains)} domains"
            )
        if len(domains) < 2:
            print(
                "[ScholarlySearchAgent] Warning: references come from a single domain; "
                "the editor must qualify unsupported claims."
            )
        return combined_facts


# ═══════════════════════════════════════════════════════════════════════════
# Agent 3: EnglishEditorAgent (canonical fact verification + copyediting)
# ═══════════════════════════════════════════════════════════════════════════
class EditorAgent:
    def run(self, draft: str, classification: dict, facts: str) -> tuple[str, str]:
        print("\n[EditorAgent] Fact-checking the canonical English draft...")
        references = extract_references(facts)
        reviewed = self._review_and_fix(draft, classification, facts)
        final = append_references(reviewed, "en", references)
        validation = validate_post(
            final,
            "en",
            source_urls=[reference["url"] for reference in references],
        )
        for warning in validation.warnings:
            print(f"[ContentValidator:en] Warning: {warning}")
        if not validation.valid:
            raise ContentValidationError("en", validation.errors)

        print("[EditorAgent] Canonical English review and validation complete")
        return reviewed, final

    def _review_and_fix(self, draft: str, classification: dict, facts: str) -> str:
        prompt = f"""
You are both a strict scientific fact-checker and a professional English blog editor.
Review the draft directly against the collected reference facts, correct it, and return the complete final article in one pass.

**Topic mode:** {classification.get('mode', 'trivia')}

**Collected reference facts:**
---
{facts}
---

**Review checklist:**
1. Fact-check every statistic, definition, causal claim, and technical assertion against the collected facts.
2. Remove, qualify, or correct claims that the references do not support. Never invent a correction.
3. Preserve the requested depth, examples, tables, code/configuration, and overall article length.
   - English output must remain at least 450 words.
   - Keep at least two level-2 (`##`) section headings.
4. Make tone and phrasing natural for English readers.
5. Repair Markdown syntax and keep at least two `##` sections.
6. Preserve a valid `json_meta` block containing title, description, and a tags array.
7. Ensure all Mermaid node labels are wrapped in double quotes.
   - Correct: `A["text (with parentheses)"]`
   - Wrong: `A[text (with parentheses)]`
8. Do not add a References/참고자료 section and do not invent URLs. The pipeline appends verified source links deterministically.

**Draft:**
---
{draft}
---

**Output rules:**
- Output only the corrected final article in English.
- Ensure the `json_meta` block is included at the very end of your response.
- Do NOT output any editor comments, explanations, or notes outside the draft body.
"""
        final = call_gemini(prompt, stage="editor_en")
        return final.strip()


# ═══════════════════════════════════════════════════════════════════════════
# Agent 5: KoreanLocalizerAgent
# ═══════════════════════════════════════════════════════════════════════════
class KoreanLocalizerAgent:
    def run(
        self,
        reviewed_english: str,
        original_query: str,
        classification: dict,
        facts: str,
    ) -> str:
        print("\n[KoreanLocalizerAgent] Localizing the validated English article...")
        prompt = f"""
You are a professional Korean localization editor. Translate and culturally localize the validated English article into natural Korean.

Original user question: {original_query}
Topic mode: {classification.get('mode', 'trivia')}

**Validated canonical English article:**
---
{reviewed_english}
---

Rules:
1. Preserve every factual claim, qualification, section, table, code block, formula, and Mermaid diagram from the English canonical article.
2. Do not add new claims, examples, statistics, citations, or URLs.
3. Produce 3000-5000 Korean characters and keep at least two level-2 (`##`) headings.
4. Use natural Korean rather than literal machine-translation phrasing.
5. Keep code/configuration identifiers unchanged and translate explanatory comments only when safe.
6. Keep all Mermaid node labels wrapped in double quotes.
7. Do not add a 참고자료 section. The pipeline appends verified references locally.
8. End with a valid `json_meta` block containing a Korean title, Korean description, and Korean tags array.

Output only the complete Korean article and its final `json_meta` block.
"""
        localized = call_gemini(prompt, stage="localizer_ko")
        localized = append_missing_metadata_block(
            localized,
            title=classification.get("topic_ko", original_query),
            description=f"{classification.get('topic_ko', original_query)}에 대한 한국어 블로그 글입니다.",
            tags=classification.get("keywords", []),
        )
        references = extract_references(facts)
        final = append_references(localized, "ko", references)
        validation = validate_post(
            final,
            "ko",
            source_urls=[reference["url"] for reference in references],
        )
        for warning in validation.warnings:
            print(f"[ContentValidator:ko] Warning: {warning}")
        if not validation.valid:
            raise ContentValidationError("ko", validation.errors)

        print("[KoreanLocalizerAgent] Korean localization and validation complete")
        return final


# ═══════════════════════════════════════════════════════════════════════════
# Agent 5: FileWriterAgent
# ═══════════════════════════════════════════════════════════════════════════
class FileWriterAgent:
    def run(self, posts: dict, classification: dict, fingerprint: str) -> list:
        now_kst = datetime.now(KST)
        date_str = now_kst.strftime("%Y-%m-%d")
        datetime_str = now_kst.strftime("%Y-%m-%d %H:%M:%S +0900")
        
        mode = classification.get("mode", "engineer")
        category = "Trivia" if mode == "trivia" else "Engineer"
        keywords = classification.get("keywords", [])
        
        # Generate a shared topic_id and post_id for KO/EN post pairing
        topic_en = classification.get("topic_en", "post")
        topic_id = re.sub(r"[^\w\s-]", "", topic_en.lower())
        topic_id = re.sub(r"[\s_]+", "-", topic_id).strip("-")[:40]
        if not topic_id:
            topic_id = f"topic-{date_str}"
            
        post_id_hash = hashlib.sha256((topic_id + date_str).encode('utf-8')).hexdigest()[:8]
        post_id = f"{topic_id}-{post_id_hash}"
        
        created_files = []
        
        for lang, content in posts.items():
            # Extract json_meta block
            meta = self._extract_meta(content, lang, classification)
            title = meta.get("title", classification.get(f"topic_{lang}", "Untitled"))
            description = meta.get("description", "")
            tags = meta.get("tags", keywords)
            
            # Pure body content with json_meta/json block removed
            body = re.sub(r"```(?:json_meta|json)\s*\{.*?\}\s*```", "", content,
                         flags=re.DOTALL).strip()
            
            # Generate slug (for filename)
            slug = self._make_slug(title, lang)
            filename = f"{date_str}-{slug}.md"
            
            # Assemble Jekyll Front Matter
            tags_yaml = "\n".join([f"  - {t}" for t in tags])
            front_matter = f"""---
layout: post
title: "{self._escape_yaml(title)}"
date: {datetime_str}
categories: [{category}]
tags:
{tags_yaml}
lang: {lang}
topic_id: "{topic_id}"
post_id: "{post_id}"
request_fingerprint: "{fingerprint}"
description: "{self._escape_yaml(description)}"
---

"""
            final_content = front_matter + body
            
            # Create directory and save file
            output_dir = Path(f"_posts/{lang}")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            
            print(f"[FileWriterAgent] File created: {output_path}")
            created_files.append(str(output_path))
        
        return created_files
    
    def _extract_meta(self, content: str, lang: str, classification: dict) -> dict:
        """Extract metadata from the json_meta block"""
        match = re.search(r"```json_meta\s*(\{.*?\})\s*```", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Fallback: generate title with Gemini
        topic = classification.get("topic_ko" if lang == "ko" else "topic_en", "Tech Post")
        return {
            "title": topic,
            "description": f"A blog post about {topic}",
            "tags": classification.get("keywords", ["tech"])
        }
    
    def _make_slug(self, title: str, lang: str) -> str:
        """Generate a slug for use in filenames"""
        # Convert Korean titles to English keyword-based slugs
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        slug = slug[:50]  # max 50 characters
        if not slug:
            slug = f"post-{lang}"
        return slug
    
    def _escape_yaml(self, text: str) -> str:
        """Escape YAML string"""
        return text.replace('"', '\\"').replace("\n", " ")


# ═══════════════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════
def main():
    reset_pipeline_result()
    print("=" * 60)
    print(f"🤖 Multi-Agent Blog Generator started")
    print(f"📝 Input: {QUERY_INPUT}")
    print(f"🧠 Model: {GEMINI_MODEL}")
    print("=" * 60)
    
    send_telegram(
        CHAT_ID,
        f"🤖 *Agent pipeline started*\n\n📝 Topic: `{QUERY_INPUT}`\n\n"
        f"Gemini budget: `3` successful calls\n`[1/5]` Resolving and drafting English...",
    )
    
    try:
        fingerprint = request_fingerprint(QUERY_INPUT)
        ensure_request_is_new(fingerprint)
        checkpoint = PipelineCheckpoint(fingerprint)
        executed_model_stages = 0

        # ─── Step 1: Resolve research intent and draft English ─────────
        classifier = ClassifierAgent()
        classification = classifier.run(QUERY_INPUT)

        if (
            checkpoint.has("research_writer")
            and checkpoint.get("research_plan")
            and checkpoint.get("english_draft")
        ):
            research_plan = checkpoint.get("research_plan")
            english_draft = checkpoint.get("english_draft")
            classification["topic_en"] = research_plan["canonical_topic_en"][:60]
            print("[Checkpoint] Reusing research plan and provisional English draft")
        else:
            research_writer = ResearchWriterAgent()
            research_plan, english_draft = research_writer.run(
                QUERY_INPUT,
                classification,
            )
            executed_model_stages += 1
            checkpoint.save(
                "research_writer",
                research_plan=research_plan,
                english_draft=english_draft,
            )

        send_telegram(CHAT_ID, 
            f"✅ `[1/5]` English plan and provisional draft complete: `{research_plan['canonical_topic_en']}`\n"
            f"🔍 `[2/5]` Collecting English scholarly facts..."
        )
        
        # ─── Step 2: Search or restore collected facts ────────────────
        if checkpoint.has("english_research") and checkpoint.get("facts"):
            facts = checkpoint.get("facts")
            print("[Checkpoint] Reusing English research facts")
        else:
            search = ScholarlySearchAgent()
            facts = search.run(classification, research_plan)
            checkpoint.save("english_research", facts=facts)

        source_quality = source_quality_score(facts)
        print(
            "[SourceQuality] "
            f"{source_quality['score']}/100 ({source_quality['grade']}), "
            f"{source_quality['reference_count']} references across "
            f"{source_quality['domain_count']} domains"
        )
        
        send_telegram(CHAT_ID, 
            f"✅ `[2/5]` English source coverage gate passed\n"
            f"🛡️ `[3/5]` Fact-checking the canonical English article..."
        )

        # ─── Step 3: Fact-check English or restore validated content ──
        if (
            checkpoint.has("english_editor")
            and checkpoint.get("reviewed_english")
            and checkpoint.get("final_english")
        ):
            reviewed_english = checkpoint.get("reviewed_english")
            final_english = checkpoint.get("final_english")
            print("[Checkpoint] Reusing validated English article")
        else:
            editor = EditorAgent()
            reviewed_english, final_english = editor.run(
                english_draft,
                classification,
                facts,
            )
            executed_model_stages += 1
            checkpoint.save(
                "english_editor",
                reviewed_english=reviewed_english,
                final_english=final_english,
            )

        send_telegram(CHAT_ID, 
            f"✅ `[3/5]` Canonical English validation complete\n"
            f"🇰🇷 `[4/5]` Localizing validated content into Korean..."
        )

        # ─── Step 4: Localize Korean or restore completed localization ─
        if checkpoint.has("korean_localizer") and checkpoint.get("final_korean"):
            final_korean = checkpoint.get("final_korean")
            print("[Checkpoint] Reusing validated Korean localization")
        else:
            localizer = KoreanLocalizerAgent()
            final_korean = localizer.run(
                reviewed_english,
                QUERY_INPUT,
                classification,
                facts,
            )
            executed_model_stages += 1
            checkpoint.save("korean_localizer", final_korean=final_korean)

        final_posts = {"ko": final_korean, "en": final_english}

        if executed_model_stages > STANDARD_SUCCESSFUL_CALLS:
            raise RuntimeError(
                "Gemini call budget exceeded: "
                f"standard {STANDARD_SUCCESSFUL_CALLS}, executed {executed_model_stages}"
            )
        if usage_tracker.successful_calls != executed_model_stages:
            raise RuntimeError(
                "Gemini call budget mismatch: "
                f"expected {executed_model_stages}, got {usage_tracker.successful_calls}"
            )
        print(
            f"[GeminiBudget] Pipeline completed with "
            f"{usage_tracker.successful_calls} successful calls "
            f"({usage_tracker.api_attempts} total attempts; "
            f"standard budget {STANDARD_SUCCESSFUL_CALLS})."
        )

        send_telegram(CHAT_ID, 
            f"✅ `[4/5]` English validation and Korean localization complete\n"
            f"💾 `[5/5]` Saving files and pushing to Git..."
        )
        
        # ─── Step 5: Save files ──────────────────────────────────────
        file_writer = FileWriterAgent()
        created_files = file_writer.run(final_posts, classification, fingerprint)
        knowledge_files = generate_knowledge_notes(created_files)
        created_files.extend(knowledge_files)
        
        print("\n" + "=" * 60)
        print("✅ All agent pipeline steps complete!")
        print("Created files:")
        for f in created_files:
            print(f"  - {f}")
        print("=" * 60)
        
        # Pass file list via environment variable (shared between GitHub Actions steps)
        with open(os.environ.get("GITHUB_ENV", "/dev/null"), "a") as env_file:
            env_file.write(f"CREATED_FILES={','.join(created_files)}\n")

        write_pipeline_result(
            "success",
            usage_tracker,
            created_files=created_files,
            metrics={"source_quality": source_quality},
        )
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        write_pipeline_result("failed", usage_tracker, error=e)
        # GitHub Actions sends the single final error notification in notify.py.
        # Keep direct execution useful without producing duplicate workflow messages.
        if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
            send_telegram(CHAT_ID, f"❌ *Error occurred*\n\n`{str(e)[:200]}`")
        sys.exit(1)


if __name__ == "__main__":
    main()
