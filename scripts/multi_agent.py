#!/usr/bin/env python3
"""
Multi-Agent Blog Generation System
====================================
Telegram input → [Classifier] → [Search] → [Writer KO/EN] → [Editor] → Jekyll Markdown file generation

Agent configuration:
  1. ClassifierAgent  : Topic classification (Dad Mode / Engineer Mode) and keyword extraction
  2. SearchAgent      : Fact collection via DuckDuckGo/Wikipedia API (hallucination prevention)
  3. WriterAgent      : KO + EN draft generation via Gemini API
  4. EditorAgent      : Fact-checking, tone-and-manner validation, markdown format correction
  5. FileWriterAgent  : Merge Jekyll Front Matter and save to _posts/ko/, _posts/en/
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import google.generativeai as genai

from content_quality import (
    ContentValidationError,
    append_references,
    build_search_queries,
    classify_query,
    extract_references,
    is_usable_search_result,
    validate_post,
)
from gemini_runtime import (
    UsageTracker,
    call_gemini as call_gemini_with_tracking,
    reset_pipeline_result,
    write_pipeline_result,
)

# ── Load environment variables ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
QUERY_INPUT = os.environ.get("QUERY_INPUT", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-2.5-flash"

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY environment variable is not set.")
    sys.exit(1)

if not QUERY_INPUT:
    print("❌ ERROR: QUERY_INPUT is empty.")
    sys.exit(1)

# ── Initialize Gemini ───────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name=GEMINI_MODEL)
usage_tracker = UsageTracker()

STAGE_GENERATION_CONFIGS = {
    "writer_ko": {"temperature": 0.7, "max_output_tokens": 8192},
    "writer_en": {"temperature": 0.7, "max_output_tokens": 12288},
    "editor_ko": {"temperature": 0.2, "max_output_tokens": 8192},
    "editor_en": {"temperature": 0.2, "max_output_tokens": 12288},
}

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


# ═══════════════════════════════════════════════════════════════════════════
# Agent 2: ScholarlySearchAgent
# ═══════════════════════════════════════════════════════════════════════════
class ScholarlySearchAgent:
    def run(self, classification: dict) -> str:
        mode = classification.get("mode", "engineer")
        query = classification.get("search_query", classification.get("topic_en", ""))
        print(f"\n[ScholarlySearchAgent] Collecting information for '{query}' (mode: {mode})...")
        
        queries = build_search_queries(query)
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

        primary_query = queries[-1] if queries else query
        if mode == "trivia":
            add_result("Book References (Google Books)", search_google_books(primary_query))
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
        if len(combined_facts) < 300:
            print(
                "[ScholarlySearchAgent] Warning: source coverage is sparse; "
                "writer/editor prompts must avoid unsupported specifics."
            )
        return combined_facts or "No external reference facts were available. Avoid unsupported specifics."


# ═══════════════════════════════════════════════════════════════════════════
# Agent 3: WriterAgent
# ═══════════════════════════════════════════════════════════════════════════
class WriterAgent:
    def run(self, query: str, classification: dict, facts: str) -> dict:
        mode = classification.get("mode", "engineer")
        print(f"\n[WriterAgent] Drafting post (mode: {mode})...")
        
        # ─── Korean draft ─────────────────────────────────────────────
        ko_style = self._get_ko_style(mode)
        ko_prompt = f"""
You are a professional tech blogger. Write a blog post in Korean on the following topic.
The post must be highly detailed, comprehensive, and structured as an in-depth article.

Topic: {query}
Reference facts: {facts}
{ko_style}

**Required Format & Content Rules (KOR):**
- Length: 3000-5000 characters (including markdown) for deep, comprehensive coverage. Do NOT summarize or write briefly.
- No H1 title (it goes into Front Matter separately)
- Use ## or ### for subheadings
- Use **bold** or `code` for emphasis
- Use > blockquotes for key insights
- Include a detailed step-by-step technical mechanism or conceptual process breakdown.
- Include concrete code examples (with syntax highlighting), config snippets, or mathematical formulas.
- Include a comparison/evaluation markdown table (e.g. Pros & Cons, or feature comparison).
- Include historical context, origins, or real-world background.
- For technical topics, include at least 1 Mermaid diagram:
  ```mermaid
  graph TD
      A["Start"] --> B["Process"]
  ```
- ⚠️ **Mermaid CRITICAL Rule**: Always wrap ALL node labels in double quotes.
  Parentheses (), Korean characters, and special chars cause parse errors — always write like this:
  Correct: `A["Sun-dried (adobe brick)"]`
  Wrong:   `A[Sun-dried (adobe brick)]`

**SEO Meta (at the end as JSON):**
```json_meta
{{"title": "Compelling Korean title", "description": "Meta description within 150 characters", "tags": ["tag1", "tag2", "tag3"], "search_query_en": "concise English source-search query"}}
```
- `search_query_en` must identify the intended place, person, object, or concept in natural English so the pipeline can collect English references without another Gemini call.
"""
        ko_draft = call_gemini(ko_prompt, stage="writer_ko")

        supplemental_query = self._extract_english_search_query(ko_draft)
        english_topic = supplemental_query or query
        if supplemental_query and supplemental_query.casefold() != query.casefold():
            print(
                "[WriterAgent] Expanding references with writer-provided English query: "
                f"'{supplemental_query}'"
            )
            supplemental_facts = ScholarlySearchAgent().run(
                {
                    "mode": mode,
                    "search_query": supplemental_query,
                    "topic_en": supplemental_query,
                }
            )
            if (
                not supplemental_facts.startswith("No external reference facts were available")
                and supplemental_facts not in facts
            ):
                facts = f"{facts}\n\n{supplemental_facts}".strip()
            classification["topic_en"] = supplemental_query[:60]
        
        # ─── English draft ────────────────────────────────────────────
        en_style = self._get_en_style(mode)
        en_prompt = f"""
You are a professional tech blogger. Write a blog post in natural, fluent English on the following topic.
The post must be an in-depth, comprehensive technical article.

Topic: {english_topic}
Reference facts: {facts}
{en_style}

**Required Format & Content Rules (ENG):**
- Length: 1200-2000 words. Provide rich, detailed explanations. Do NOT summarize or write briefly.
- No H1 title (it's in Front Matter)
- Use ## or ### for subheadings
- Use **bold** and `code` for emphasis
- Use > blockquotes for key insights
- Include a comprehensive technical analysis or detailed step-by-step conceptual breakdown.
- Include concrete code blocks, configurations, or mathematical formulas.
- Include a Markdown table summarizing features or Pros & Cons.
- Include historical background or industry trade-offs.
- For technical topics, include at least 1 Mermaid diagram:
  ```mermaid
  graph TD
      A["Start"] --> B["Process"]
  ```
- ⚠️ **Mermaid Rule (CRITICAL)**: Always wrap ALL node labels in double quotes.
  Parentheses (), Korean characters, and special chars break the parser.
  Correct: `A["Hot CrossFit (heat stress)"]`
  Wrong:   `A[Hot CrossFit (heat stress)]`

**SEO Meta (at the end as JSON):**
```json_meta
{{"title": "Compelling English Title", "description": "Under 150 char meta description", "tags": ["tag1", "tag2", "tag3"]}}
```
"""
        en_draft = call_gemini(en_prompt, stage="writer_en")
        
        print("[WriterAgent] Draft writing complete (KO + EN)")
        return {"ko": ko_draft, "en": en_draft}, facts

    @staticmethod
    def _extract_english_search_query(draft: str) -> str:
        match = re.search(r"```json_meta\s*(\{.*?\})\s*```", draft, re.DOTALL)
        if not match:
            return ""
        try:
            metadata = json.loads(match.group(1))
        except json.JSONDecodeError:
            return ""
        query = str(metadata.get("search_query_en") or "").strip()
        return re.sub(r"\s+", " ", query)[:160]
    
    def _get_ko_style(self, mode: str) -> str:
        if mode == "trivia":
            return """
**Writing Style: Trivia Vault**
- Audience: General public interested in trivia and science
- Tone: Friendly and warm explanatory style ("~해요", "~랍니다")
- Explain complex concepts using everyday analogies (e.g., "A computer's CPU is like the human brain")
- Minimize jargon; when used, explain in parentheses
- Use emojis appropriately (🎯, 💡, 🔧, etc.)
"""
        else:
            return """
**Writing Style: Engineer Mode**
- Audience: Developers, IT professionals
- Tone: Clear, logical technical documentation style
- Use technical terminology freely
- Include concrete code examples, figures, and benchmarks
- Mention trade-offs and real-world application perspectives
- Actively use Mermaid diagrams and code blocks
"""
    
    def _get_en_style(self, mode: str) -> str:
        if mode == "trivia":
            return """
**Writing Style: Trivia Vault**
- Audience: General public, beginners
- Tone: Warm, friendly, conversational
- Use everyday analogies to explain complex concepts
- Minimize jargon; explain technical terms in parentheses
- Use emojis appropriately (🎯, 💡, 🔧)
"""
        else:
            return """
**Writing Style: Engineer Mode**
- Audience: Developers, IT professionals
- Tone: Clear, authoritative, technical
- Use technical terminology freely
- Include code examples, benchmarks, and specifics
- Discuss trade-offs and real-world implications
- Leverage Mermaid diagrams and code blocks
"""


# ═══════════════════════════════════════════════════════════════════════════
# Agent 4: EditorAgent (combined fact verification + copyediting)
# ═══════════════════════════════════════════════════════════════════════════
class EditorAgent:
    def run(self, drafts: dict, classification: dict, facts: str) -> dict:
        print("\n[EditorAgent] Fact-checking and copyediting drafts in one pass...")
        references = extract_references(facts)
        result = {}
        for lang, draft in drafts.items():
            print(f"[EditorAgent] Reviewing {lang.upper()} against collected sources...")
            reviewed = self._review_and_fix(draft, lang, classification, facts)
            final = append_references(reviewed, lang, references)
            validation = validate_post(
                final,
                lang,
                source_urls=[reference["url"] for reference in references],
            )
            for warning in validation.warnings:
                print(f"[ContentValidator:{lang}] Warning: {warning}")
            if not validation.valid:
                raise ContentValidationError(lang, validation.errors)
            result[lang] = final

        print("[EditorAgent] Combined verification and copyediting complete (KO + EN)")
        return result

    def _review_and_fix(self, draft: str, lang: str, classification: dict, facts: str) -> str:
        lang_name = "Korean" if lang == "ko" else "English"
        lang_instruction = "in Korean" if lang == "ko" else "in English"

        prompt = f"""
You are both a strict scientific fact-checker and a professional {lang_name} blog editor.
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
   - Korean output must remain at least 1200 characters.
   - English output must remain at least 450 words.
   - Keep at least two level-2 (`##`) section headings.
4. Make tone and phrasing natural for {lang_name} readers.
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
- Output only the corrected final article {lang_instruction}.
- Ensure the `json_meta` block is included at the very end of your response.
- Do NOT output any editor comments, explanations, or notes outside the draft body.
"""
        final = call_gemini(prompt, stage=f"editor_{lang}")
        return final.strip()


# ═══════════════════════════════════════════════════════════════════════════
# Agent 5: FileWriterAgent
# ═══════════════════════════════════════════════════════════════════════════
class FileWriterAgent:
    def run(self, posts: dict, classification: dict) -> list:
        now_kst = datetime.now(KST)
        date_str = now_kst.strftime("%Y-%m-%d")
        datetime_str = now_kst.strftime("%Y-%m-%d %H:%M:%S +0900")
        
        mode = classification.get("mode", "engineer")
        category = "Trivia" if mode == "trivia" else "Engineer"
        keywords = classification.get("keywords", [])
        
        # Generate a shared topic_id for KO/EN post pairing
        topic_en = classification.get("topic_en", "post")
        topic_id = re.sub(r"[^\w\s-]", "", topic_en.lower())
        topic_id = re.sub(r"[\s_]+", "-", topic_id).strip("-")[:40]
        if not topic_id:
            topic_id = f"topic-{date_str}"
        
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
        f"Gemini budget: `4` successful calls\n`[1/5]` Classifying topic locally...",
    )
    
    try:
        # ─── Step 1: Classify ─────────────────────────────────────────
        classifier = ClassifierAgent()
        classification = classifier.run(QUERY_INPUT)
        
        send_telegram(CHAT_ID, 
            f"✅ `[1/5]` Local classification complete: *{'Trivia Vault' if classification['mode'] == 'trivia' else 'Engineer Mode'}*\n"
            f"🔍 `[2/5]` Collecting scholarly facts (arXiv/Crossref/Books)..."
        )
        
        # ─── Step 2: Search ───────────────────────────────────────────
        search = ScholarlySearchAgent()
        facts = search.run(classification)
        
        send_telegram(CHAT_ID, 
            f"✅ `[2/5]` Fact collection complete without Gemini summarization\n"
            f"✍️ `[3/5]` Writer agent drafting KO + EN posts..."
        )
        
        # ─── Step 3: Write ────────────────────────────────────────────
        writer = WriterAgent()
        drafts, facts = writer.run(QUERY_INPUT, classification, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[3/5]` Drafts complete (KO + EN)\n"
            f"🛡️ `[4/5]` Combined fact-check and copyedit in progress..."
        )

        # ─── Step 4: Combined fact verification, editing, and local validation
        editor = EditorAgent()
        final_posts = editor.run(drafts, classification, facts)

        expected_successful_calls = 4
        if usage_tracker.successful_calls != expected_successful_calls:
            raise RuntimeError(
                "Gemini call budget mismatch: "
                f"expected {expected_successful_calls}, got {usage_tracker.successful_calls}"
            )
        print(
            f"[GeminiBudget] Standard pipeline completed with "
            f"{usage_tracker.successful_calls} successful calls "
            f"({usage_tracker.api_attempts} total attempts)."
        )

        send_telegram(CHAT_ID, 
            f"✅ `[4/5]` Fact-check, copyedit, and local validation complete\n"
            f"💾 `[5/5]` Saving files and pushing to Git..."
        )
        
        # ─── Step 5: Save files ──────────────────────────────────────
        file_writer = FileWriterAgent()
        created_files = file_writer.run(final_posts, classification)
        
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
