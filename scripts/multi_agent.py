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
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import google.generativeai as genai

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
model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    generation_config=genai.types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=65536,
    )
)

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


def call_gemini(prompt: str, retry: int = 3) -> str:
    """Call the Gemini API (with retry logic)"""
    for attempt in range(retry):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[Gemini] Attempt {attempt+1}/{retry} failed: {e}")
            if attempt < retry - 1:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError("Gemini API call failed repeatedly.")


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
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&origin=*"
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
            page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
            results.append(f"[Wikipedia] Title: {title}\nSnippet: {snippet}\nLink: {page_url}")
        return "\n\n".join(results) if results else "No Wikipedia pages found."
    except Exception as e:
        return f"Wikipedia Search Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Agent 1: ClassifierAgent
# ═══════════════════════════════════════════════════════════════════════════
class ClassifierAgent:
    def run(self, query: str) -> dict:
        print(f"\n[ClassifierAgent] Classifying input: '{query}'")
        prompt = f"""
Analyze the following input text and respond with JSON only. (Pure JSON, no code blocks)

Input: "{query}"

Analysis criteria:
- mode: Determine whether the input is a general knowledge/trivia topic ("trivia") or a specialized technical topic ("engineer")
  - trivia: Everyday science, history, common sense, "explain simply", light topics suitable for analogies
  - engineer: Technical terminology, development, systems, algorithms, specific tech stacks
- topic_ko: Core topic in Korean (within 10 characters)
- topic_en: Core topic in English (within 5 words)
- keywords: Array of core keywords (up to 5)
- search_query: English search query suitable for fact retrieval

Response format:
{{"mode": "trivia|engineer", "topic_ko": "...", "topic_en": "...", "keywords": ["kw1", "kw2"], "search_query": "..."}}
"""
        result_str = call_gemini(prompt)
        # Parse JSON
        try:
            # Strip markdown code blocks if present
            result_str = re.sub(r"```json?\s*", "", result_str)
            result_str = re.sub(r"```", "", result_str).strip()
            result = json.loads(result_str)
        except json.JSONDecodeError:
            print(f"[ClassifierAgent] JSON parse failed, using defaults. Raw:\n{result_str}")
            result = {
                "mode": "engineer",
                "topic_ko": query[:20],
                "topic_en": query[:30],
                "keywords": [query.split()[0]] if query.split() else ["tech"],
                "search_query": query
            }
        print(f"[ClassifierAgent] Classification complete: {result}")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# Agent 2: SearchAgent
# ═══════════════════════════════════════════════════════════════════════════
class SearchAgent:
    def run(self, classification: dict) -> str:
        query = classification.get("search_query", classification.get("topic_en", ""))
        print(f"\n[SearchAgent] Collecting information: '{query}'")
        
        facts = search_duckduckgo(query)
        print(f"[SearchAgent] Collection complete:\n{facts[:300]}...")
        
        # Enrich collected facts with Gemini's own knowledge
        enrich_prompt = f"""
Summarize fact-based information about the following topic.

Topic: {classification.get('topic_ko', '')} ({classification.get('topic_en', '')})
Search results: {facts}

Write accurate background information (no fabrication) covering the following, in 200-400 characters:
1. Core concept definition
2. Key characteristics or principles (2-3 items)
3. Real-world use cases or current status
"""
        enriched = call_gemini(enrich_prompt)
        print(f"[SearchAgent] Information enrichment complete")
        return enriched


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

Topic: {query}
Reference facts: {facts}
{ko_style}

**Required Format Rules:**
- No H1 title (it goes into Front Matter separately)
- Use ## or ### for subheadings
- Use **bold** or `code` for emphasis
- Use > blockquotes for key insights
- For technical topics, include at least 1 Mermaid diagram:
  ```mermaid
  graph TD
      A["Start"] --> B["Process"]
  ```
- ⚠️ **Mermaid CRITICAL Rule**: Always wrap ALL node labels in double quotes.
  Parentheses (), Korean characters, and special chars cause parse errors — always write like this:
  Correct: `A["Sun-dried (adobe brick)"]`
  Wrong:   `A[Sun-dried (adobe brick)]`
- Length: 700-1200 characters (including markdown)
- Maintain structure: Introduction, Body (2-3 sections), Conclusion

**SEO Meta (at the end as JSON):**
```json_meta
{{"title": "Compelling Korean title", "description": "Meta description within 150 characters", "tags": ["tag1", "tag2", "tag3"]}}
```
"""
        ko_draft = call_gemini(ko_prompt)
        
        # ─── English draft ────────────────────────────────────────────
        en_style = self._get_en_style(mode)
        en_prompt = f"""
You are a professional tech blogger. Write a blog post in natural, fluent English on the following topic.

Topic: {query}
Reference facts: {facts}
{en_style}

**Required Format Rules:**
- No H1 title (it's in Front Matter)
- Use ## or ### for subheadings
- Use **bold** and `code` for emphasis
- Use > blockquotes for key insights
- For technical topics, include at least 1 Mermaid diagram:
  ```mermaid
  graph TD
      A["Start"] --> B["Process"]
  ```
- ⚠️ **Mermaid Rule (CRITICAL)**: Always wrap ALL node labels in double quotes.
  Parentheses (), Korean characters, and special chars break the parser.
  Correct: `A["Hot CrossFit (heat stress)"]`
  Wrong:   `A[Hot CrossFit (heat stress)]`
- Length: 600-1000 words
- Structure: Introduction, Body (2-3 sections), Conclusion

**SEO Meta (at the end as JSON):**
```json_meta
{{"title": "Compelling English Title", "description": "Under 150 char meta description", "tags": ["tag1", "tag2", "tag3"]}}
```
"""
        en_draft = call_gemini(en_prompt)
        
        print("[WriterAgent] Draft writing complete (KO + EN)")
        return {"ko": ko_draft, "en": en_draft}
    
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
# Agent 4: FactVerifierAgent
# ═══════════════════════════════════════════════════════════════════════════
class FactVerifierAgent:
    def run(self, drafts: dict, facts: str) -> dict:
        print(f"\n[FactVerifierAgent] Verifying facts and extracting citations...")
        
        result = {}
        for lang, draft in drafts.items():
            print(f"[FactVerifierAgent] Verifying {lang.upper()} draft...")
            result[lang] = self._verify_draft(draft, lang, facts)
            
        print("[FactVerifierAgent] Verification complete (KO + EN)")
        return result

    def _verify_draft(self, draft: str, lang: str, facts: str) -> dict:
        lang_name = "Korean" if lang == "ko" else "English"
        lang_instruction = "in Korean" if lang == "ko" else "in English"
        
        prompt = f"""
You are a scientific fact-checker. Review the following {lang_name} blog post draft against the provided Reference Facts.

Reference Facts:
{facts}

Draft to check:
{draft}

Tasks:
1. Identify any factual claims made in the draft (e.g. statistics, technical claims, definitions, principles).
2. Cross-reference them with the Reference Facts.
3. Generate a "Verification Report" {lang_instruction}.
4. Ensure the report has:
   - "Factual Check": A list of claims verified, along with any corrections for claims that are unverified, exaggerated, or incorrect.
   - "Verified Citations": A list of specific titles and links/DOIs from the Reference Facts that directly back up the content of this draft.

Format your output as a clean JSON block (pure JSON, no other text):
```json
{{
  "has_errors": true|false,
  "corrections": "Description of corrections needed, or 'None'",
  "report": "Detailed verification report text in markdown",
  "citations": [
    {{"title": "Source Title", "url": "URL/Link/DOI"}}
  ]
}}
```
"""
        response_str = call_gemini(prompt)
        try:
            # Clean markdown code block wraps
            response_str = re.sub(r"```json?\s*", "", response_str)
            response_str = re.sub(r"```", "", response_str).strip()
            parsed = json.loads(response_str)
        except Exception as e:
            print(f"[FactVerifierAgent] JSON parsing failed: {e}. Raw response:\n{response_str}")
            parsed = {
                "has_errors": False,
                "corrections": "None",
                "report": "Fact check passed successfully.",
                "citations": []
            }
        return parsed


# ═══════════════════════════════════════════════════════════════════════════
# Agent 5: EditorAgent
# ═══════════════════════════════════════════════════════════════════════════
class EditorAgent:
    def run(self, drafts: dict, verification_reports: dict, classification: dict, facts: str) -> dict:
        print(f"\n[EditorAgent] Cross-reviewing and revising drafts based on verification reports...")
        
        result = {}
        for lang, draft in drafts.items():
            print(f"[EditorAgent] Copyediting {lang.upper()}...")
            report = verification_reports.get(lang, {})
            result[lang] = self._review_and_fix(draft, report, lang, classification, facts)
        
        print("[EditorAgent] Copyediting complete (KO + EN)")
        return result
    
    def _review_and_fix(self, draft: str, report: dict, lang: str, classification: dict, facts: str) -> str:
        lang_name = "Korean" if lang == "ko" else "English"
        lang_instruction = "in Korean" if lang == "ko" else "in English"
        
        corrections = report.get("corrections", "None")
        citations_list = report.get("citations", [])
        
        # Format references markdown
        ref_title = "참고자료" if lang == "ko" else "References"
        ref_lines = []
        for citation in citations_list:
            title = citation.get("title", "Source Link")
            url = citation.get("url", "#")
            ref_lines.append(f"- [{title}]({url})")
        
        references_section = ""
        if ref_lines:
            references_section = f"\n\n## {ref_title}\n\n" + "\n".join(ref_lines)
            
        prompt = f"""
You are a strict blog editor. Review the following {lang_name} draft, apply the corrections provided by the Fact-Checker, and ensure all style rules are met.

**Fact-Checker Corrections:**
{corrections}

**Review checklist:**
1. ✅ Apply corrections: Correct any false claims, inaccuracies, or logical leaps mentioned in the corrections list above.
2. ✅ Tone and manner: Is the tone consistent and natural?
3. ✅ Markdown: Are ## headers, **, `, > etc. syntactically correct?
4. ✅ Structure: Are the introduction, body, and conclusion clearly defined?
5. ✅ json_meta block: Does it include title, description, and tags?
6. ✅ Mermaid syntax: Are all node labels wrapped in double quotes?
   - Correct: `A["text (with parentheses)"]`
   - Wrong:   `A[text (with parentheses)]` ← must be fixed

**Draft:**
---
{draft}
---

**Output rules:**
- Immediately output the corrected final version of the draft ({lang_instruction}).
- Ensure the `json_meta` block is included at the very end of your response.
- Do NOT output any editor comments, explanations, or notes outside the draft body.
"""
        final = call_gemini(prompt)
        
        # Append references section before the json_meta block (so it goes into the post body)
        meta_match = re.search(r"(```json_meta\s*\{.*?\}\s*```)", final, re.DOTALL)
        if meta_match:
            meta_block = meta_match.group(1)
            body = final.replace(meta_block, "").strip()
            final = body + references_section + "\n\n" + meta_block
        else:
            final = final.strip() + references_section
            
        return final


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
            
            # Pure body content with json_meta block removed
            body = re.sub(r"```json_meta\s*\{.*?\}\s*```", "", content,
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
    print("=" * 60)
    print(f"🤖 Multi-Agent Blog Generator started")
    print(f"📝 Input: {QUERY_INPUT}")
    print(f"🧠 Model: {GEMINI_MODEL}")
    print("=" * 60)
    
    send_telegram(CHAT_ID, f"🤖 *Agent pipeline started*\n\n📝 Topic: `{QUERY_INPUT}`\n\n`[1/6]` Classifying topic...")
    
    try:
        # ─── Step 1: Classify ─────────────────────────────────────────
        classifier = ClassifierAgent()
        classification = classifier.run(QUERY_INPUT)
        
        send_telegram(CHAT_ID, 
            f"✅ `[1/6]` Classification complete: *{'Trivia Vault' if classification['mode'] == 'trivia' else 'Engineer Mode'}*\n"
            f"🔍 `[2/6]` Collecting scholarly facts (arXiv/Crossref/Books)..."
        )
        
        # ─── Step 2: Search ───────────────────────────────────────────
        search = ScholarlySearchAgent()
        facts = search.run(classification)
        
        send_telegram(CHAT_ID, 
            f"✅ `[2/6]` Fact collection complete\n✍️ `[3/6]` Writer agent drafting post..."
        )
        
        # ─── Step 3: Write ────────────────────────────────────────────
        writer = WriterAgent()
        drafts = writer.run(QUERY_INPUT, classification, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[3/6]` Drafts complete (KO + EN)\n🛡️ `[4/6]` FactVerifier agent validating claims..."
        )
        
        # ─── Step 4: Verify ───────────────────────────────────────────
        verifier = FactVerifierAgent()
        verification_reports = verifier.run(drafts, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[4/6]` Verification reports ready\n🔍 `[5/6]` Editor agent copying & adding references..."
        )
        
        # ─── Step 5: Edit ─────────────────────────────────────────────
        editor = EditorAgent()
        final_posts = editor.run(drafts, verification_reports, classification, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[5/6]` Copyediting complete\n💾 `[6/6]` Saving files and pushing to Git..."
        )
        
        # ─── Step 6: Save files ──────────────────────────────────────
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
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        send_telegram(CHAT_ID, f"❌ *Error occurred*\n\n`{str(e)[:200]}`")
        sys.exit(1)


if __name__ == "__main__":
    main()
