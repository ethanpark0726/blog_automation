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
from datetime import datetime, timezone, timedelta
from pathlib import Path

import google.generativeai as genai

# ── Load environment variables ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
QUERY_INPUT = os.environ.get("QUERY_INPUT", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY environment variable is not set.")
    sys.exit(1)

if not QUERY_INPUT:
    print("❌ ERROR: QUERY_INPUT is empty.")
    sys.exit(1)

# ── Initialize Gemini ───────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
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
        
        # Abstract (Wikipedia summary)
        if data.get("Abstract"):
            results.append(f"[Overview] {data['Abstract']}")
        
        # Related Topics
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"[Related] {topic['Text'][:200]}")
        
        return "\n".join(results) if results else "No search results (falling back to Gemini knowledge)"
    except Exception as e:
        return f"Search API error: {e} (falling back to Gemini knowledge)"


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
# Agent 4: EditorAgent
# ═══════════════════════════════════════════════════════════════════════════
class EditorAgent:
    def run(self, drafts: dict, classification: dict, facts: str) -> dict:
        print(f"\n[EditorAgent] Cross-reviewing and revising...")
        
        result = {}
        for lang, draft in drafts.items():
            print(f"[EditorAgent] Reviewing {lang.upper()}...")
            result[lang] = self._review_and_fix(draft, lang, classification, facts)
        
        print("[EditorAgent] Review complete (KO + EN)")
        return result
    
    def _review_and_fix(self, draft: str, lang: str, classification: dict, facts: str) -> str:
        lang_name = "Korean" if lang == "ko" else "English"
        lang_instruction = "in Korean" if lang == "ko" else "in English"
        
        prompt = f"""
You are a strict blog editor. Review the following {lang_name} draft and immediately output the corrected final version if there are any issues.

**Reference facts (verification basis):**
{facts}

**Review checklist:**
1. ✅ Fact check: Are there any false claims, exaggerations, or logical leaps?
2. ✅ Tone and manner: Is the tone consistent and natural? (No machine-translation feel)
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
- If revisions are needed, output the entire corrected body ({lang_instruction})
- If no revisions are needed, output the original as-is
- Output the final version only — no editor comments or explanations
- The json_meta block must be included
"""
        final = call_gemini(prompt)
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
    print("=" * 60)
    
    send_telegram(CHAT_ID, f"🤖 *Agent pipeline started*\n\n📝 Topic: `{QUERY_INPUT}`\n\n`[1/5]` Classifying topic...")
    
    try:
        # ─── Step 1: Classify ─────────────────────────────────────────
        classifier = ClassifierAgent()
        classification = classifier.run(QUERY_INPUT)
        
        send_telegram(CHAT_ID, 
            f"✅ `[1/5]` Classification complete: *{'Trivia Vault' if classification['mode'] == 'trivia' else 'Engineer Mode'}*\n"
            f"🔍 `[2/5]` Collecting information..."
        )
        
        # ─── Step 2: Search ───────────────────────────────────────────
        search = SearchAgent()
        facts = search.run(classification)
        
        send_telegram(CHAT_ID, 
            f"✅ `[2/5]` Information collection complete\n✍️ `[3/5]` Writer agent drafting post..."
        )
        
        # ─── Step 3: Write ────────────────────────────────────────────
        writer = WriterAgent()
        drafts = writer.run(QUERY_INPUT, classification, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[3/5]` Drafts complete (KO + EN)\n🔍 `[4/5]` Editor agent reviewing..."
        )
        
        # ─── Step 4: Edit ─────────────────────────────────────────────
        editor = EditorAgent()
        final_posts = editor.run(drafts, classification, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[4/5]` Review complete\n💾 `[5/5]` Saving files and pushing to Git..."
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
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        send_telegram(CHAT_ID, f"❌ *Error occurred*\n\n`{str(e)[:200]}`")
        sys.exit(1)


if __name__ == "__main__":
    main()
