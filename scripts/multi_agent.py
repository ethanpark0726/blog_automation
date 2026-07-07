#!/usr/bin/env python3
"""
Multi-Agent Blog Generation System
====================================
텔레그램 입력 → [Classifier] → [Search] → [Writer KO/EN] → [Editor] → Jekyll Markdown 파일 생성

에이전트 구성:
  1. ClassifierAgent  : 주제 분류 (아빠 모드 / 엔지니어 모드) 및 키워드 추출
  2. SearchAgent      : DuckDuckGo/Wikipedia API로 팩트 수집 (Hallucination 방지)
  3. WriterAgent      : Gemini API 호출로 KO + EN 초안 생성
  4. EditorAgent      : 팩트 체크, 톤앤매너 검증, 마크다운 포맷 수정
  5. FileWriterAgent  : Jekyll Front Matter 병합 후 _posts/ko/, _posts/en/ 저장
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

# ── 환경변수 로드 ────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
QUERY_INPUT = os.environ.get("QUERY_INPUT", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    sys.exit(1)

if not QUERY_INPUT:
    print("❌ ERROR: QUERY_INPUT이 비어 있습니다.")
    sys.exit(1)

# ── Gemini 초기화 ────────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-3.1-pro-preview",
    generation_config=genai.types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=65536,  # 3.1-pro는 최대 65536 토큰 지원
    )
)

KST = timezone(timedelta(hours=9))


def send_telegram(chat_id: str, text: str) -> None:
    """텔레그램 메시지 전송 (진행 상황 알림)"""
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
        print(f"[Telegram] 알림 전송 실패: {e}")


def call_gemini(prompt: str, retry: int = 3) -> str:
    """Gemini API 호출 (재시도 포함)"""
    for attempt in range(retry):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[Gemini] 시도 {attempt+1}/{retry} 실패: {e}")
            if attempt < retry - 1:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError("Gemini API 호출에 반복적으로 실패했습니다.")


def search_duckduckgo(query: str) -> str:
    """DuckDuckGo Abstract API로 팩트 데이터 수집"""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "BlogBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        results = []
        
        # Abstract (위키피디아 요약)
        if data.get("Abstract"):
            results.append(f"[개요] {data['Abstract']}")
        
        # Related Topics
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"[관련] {topic['Text'][:200]}")
        
        return "\n".join(results) if results else "검색 결과 없음 (Gemini 기반 지식으로 대체)"
    except Exception as e:
        return f"검색 API 오류: {e} (Gemini 기반 지식으로 대체)"


# ═══════════════════════════════════════════════════════════════════════════
# Agent 1: ClassifierAgent
# ═══════════════════════════════════════════════════════════════════════════
class ClassifierAgent:
    def run(self, query: str) -> dict:
        print(f"\n[ClassifierAgent] 입력 분류 중: '{query}'")
        prompt = f"""
다음 입력 텍스트를 분석해서 JSON으로만 응답해줘. (코드 블록 없이 순수 JSON만)

입력: "{query}"

분석 기준:
- mode: 입력이 일반인/아이 대상("dad")인지 전문 기술("engineer")인지 판단
  - dad: 일상적 질문, "쉽게 설명", "초등학생", 비유적 표현이 적합한 주제
  - engineer: 기술 용어, 개발, 시스템, 알고리즘, 특정 기술 스택 관련
- topic_ko: 한국어 핵심 주제 (10자 이내)
- topic_en: 영어 핵심 주제 (5단어 이내)
- keywords: 핵심 키워드 배열 (최대 5개)
- search_query: 팩트 검색에 적합한 영어 검색어

응답 형식:
{{"mode": "dad|engineer", "topic_ko": "...", "topic_en": "...", "keywords": ["kw1", "kw2"], "search_query": "..."}}
"""
        result_str = call_gemini(prompt)
        # JSON 파싱
        try:
            # 혹시 마크다운 코드블록이 포함된 경우 제거
            result_str = re.sub(r"```json?\s*", "", result_str)
            result_str = re.sub(r"```", "", result_str).strip()
            result = json.loads(result_str)
        except json.JSONDecodeError:
            print(f"[ClassifierAgent] JSON 파싱 실패, 기본값 사용. 원본:\n{result_str}")
            result = {
                "mode": "engineer",
                "topic_ko": query[:20],
                "topic_en": query[:30],
                "keywords": [query.split()[0]] if query.split() else ["tech"],
                "search_query": query
            }
        print(f"[ClassifierAgent] 분류 완료: {result}")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# Agent 2: SearchAgent
# ═══════════════════════════════════════════════════════════════════════════
class SearchAgent:
    def run(self, classification: dict) -> str:
        query = classification.get("search_query", classification.get("topic_en", ""))
        print(f"\n[SearchAgent] 정보 수집 중: '{query}'")
        
        facts = search_duckduckgo(query)
        print(f"[SearchAgent] 수집 완료:\n{facts[:300]}...")
        
        # Gemini로 수집된 팩트 + 자체 지식 통합
        enrich_prompt = f"""
다음 주제에 대한 팩트 기반 정보를 정리해줘.

주제: {classification.get('topic_ko', '')} ({classification.get('topic_en', '')})
검색 결과: {facts}

다음 항목을 포함한 정확한 배경 정보를 200-400자 정도로 작성해 (허구 없이):
1. 핵심 개념 정의
2. 주요 특징 또는 원리 (2-3가지)
3. 실제 활용 사례 또는 현황
"""
        enriched = call_gemini(enrich_prompt)
        print(f"[SearchAgent] 정보 보강 완료")
        return enriched


# ═══════════════════════════════════════════════════════════════════════════
# Agent 3: WriterAgent
# ═══════════════════════════════════════════════════════════════════════════
class WriterAgent:
    def run(self, query: str, classification: dict, facts: str) -> dict:
        mode = classification.get("mode", "engineer")
        print(f"\n[WriterAgent] 글 초안 작성 중 (모드: {mode})...")
        
        # ─── 한국어 초안 ───────────────────────────────────────────────
        ko_style = self._get_ko_style(mode)
        ko_prompt = f"""
당신은 전문 기술 블로그 작가입니다. 다음 주제로 한국어 블로그 포스트를 작성해주세요.

주제: {query}
참고 팩트: {facts}
{ko_style}

**필수 포맷 규칙:**
- 제목(H1): 사용 안 함 (Front Matter에 별도 입력됨)
- 소제목: ## 또는 ### 사용
- 강조: **굵게** 또는 `코드`
- 인용/핵심 포인트: > 블록 인용 활용
- 기술 주제라면 Mermaid 다이어그램 최소 1개 포함:
  ```mermaid
  graph TD
      A[시작] --> B[과정]
  ```
- 분량: 700-1200자 (마크다운 포함)
- 서론, 본론(2-3섹션), 결론 구조 유지

**SEO 최적화 메타 정보 (마지막에 JSON으로):**
```json_meta
{{"title": "매력적인 한국어 제목", "description": "150자 이내 메타 설명", "tags": ["태그1", "태그2", "태그3"]}}
```
"""
        ko_draft = call_gemini(ko_prompt)
        
        # ─── 영어 초안 ───────────────────────────────────────────────
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
      A[Start] --> B[Process]
  ```
- Length: 600-1000 words
- Structure: Introduction, Body (2-3 sections), Conclusion

**SEO Meta (at the end as JSON):**
```json_meta
{{"title": "Compelling English Title", "description": "Under 150 char meta description", "tags": ["tag1", "tag2", "tag3"]}}
```
"""
        en_draft = call_gemini(en_prompt)
        
        print("[WriterAgent] 초안 작성 완료 (KO + EN)")
        return {"ko": ko_draft, "en": en_draft}
    
    def _get_ko_style(self, mode: str) -> str:
        if mode == "dad":
            return """
**글쓰기 스타일: 아빠 모드**
- 독자: 초등학생 ~ 일반 성인
- 어투: 친근하고 따뜻한 설명체 ("~해요", "~랍니다")
- 복잡한 개념은 반드시 생활 속 비유로 설명 (예: "컴퓨터의 CPU는 사람의 두뇌와 같아요")
- 전문 용어 최소화, 사용 시 괄호로 쉽게 설명
- 이모지 적절히 활용 (🎯, 💡, 🔧 등)
"""
        else:
            return """
**글쓰기 스타일: 엔지니어 모드**
- 독자: 개발자, IT 전문가
- 어투: 명확하고 논리적인 기술 문서체
- 전문 용어 자유롭게 사용
- 구체적인 예시 코드, 수치, 벤치마크 포함
- 트레이드오프와 실무 적용 관점 언급
- Mermaid 다이어그램, 코드 블록 적극 활용
"""
    
    def _get_en_style(self, mode: str) -> str:
        if mode == "dad":
            return """
**Writing Style: Dad Mode**
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
        print(f"\n[EditorAgent] 교차 검수 및 수정 중...")
        
        result = {}
        for lang, draft in drafts.items():
            print(f"[EditorAgent] {lang.upper()} 검수 중...")
            result[lang] = self._review_and_fix(draft, lang, classification, facts)
        
        print("[EditorAgent] 검수 완료 (KO + EN)")
        return result
    
    def _review_and_fix(self, draft: str, lang: str, classification: dict, facts: str) -> str:
        lang_name = "한국어" if lang == "ko" else "English"
        lang_instruction = "한국어로" if lang == "ko" else "in English"
        
        prompt = f"""
당신은 엄격한 블로그 편집장입니다. 다음 {lang_name} 초안을 심사하고, 문제가 있다면 즉시 수정된 최종본을 출력하세요.

**참고 팩트 (검증 기준):**
{facts}

**검수 체크리스트:**
1. ✅ 팩트 체크: 허위 사실, 과장, 논리적 비약이 없는가?
2. ✅ 톤앤매너: 어조가 일관되고 자연스러운가? (기계 번역투 없는지)
3. ✅ 마크다운: ## 헤더, **, `, > 등 문법이 올바른가?
4. ✅ 구조: 서론-본론-결론이 명확한가?
5. ✅ json_meta 블록: 제목, 설명, 태그가 포함되어 있는가?

**초안:**
---
{draft}
---

**출력 규칙:**
- 수정이 필요하면 수정된 전체 본문을 출력 ({lang_instruction})
- 수정이 불필요하면 원본 그대로 출력
- Editor 코멘트나 설명 없이 최종본만 출력
- json_meta 블록은 반드시 포함
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
        category = "Dad" if mode == "dad" else "Engineer"
        keywords = classification.get("keywords", [])
        
        created_files = []
        
        for lang, content in posts.items():
            # json_meta 블록 추출
            meta = self._extract_meta(content, lang, classification)
            title = meta.get("title", classification.get(f"topic_{lang}", "Untitled"))
            description = meta.get("description", "")
            tags = meta.get("tags", keywords)
            
            # json_meta 블록 제거한 순수 본문
            body = re.sub(r"```json_meta\s*\{.*?\}\s*```", "", content,
                         flags=re.DOTALL).strip()
            
            # 슬러그 생성 (파일명용)
            slug = self._make_slug(title, lang)
            filename = f"{date_str}-{slug}.md"
            
            # Jekyll Front Matter 조합
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
            
            # 폴더 생성 및 파일 저장
            output_dir = Path(f"_posts/{lang}")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            
            print(f"[FileWriterAgent] 파일 생성: {output_path}")
            created_files.append(str(output_path))
        
        return created_files
    
    def _extract_meta(self, content: str, lang: str, classification: dict) -> dict:
        """json_meta 블록에서 메타데이터 추출"""
        match = re.search(r"```json_meta\s*(\{.*?\})\s*```", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 폴백: Gemini로 제목 생성
        topic = classification.get("topic_ko" if lang == "ko" else "topic_en", "Tech Post")
        return {
            "title": topic,
            "description": f"{topic}에 대한 블로그 포스트",
            "tags": classification.get("keywords", ["tech"])
        }
    
    def _make_slug(self, title: str, lang: str) -> str:
        """파일명용 슬러그 생성"""
        # 한글 제목은 영문 키워드로 변환
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        slug = slug[:50]  # 최대 50자
        if not slug:
            slug = f"post-{lang}"
        return slug
    
    def _escape_yaml(self, text: str) -> str:
        """YAML 문자열 이스케이프"""
        return text.replace('"', '\\"').replace("\n", " ")


# ═══════════════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print(f"🤖 Multi-Agent Blog Generator 시작")
    print(f"📝 입력: {QUERY_INPUT}")
    print("=" * 60)
    
    send_telegram(CHAT_ID, f"🤖 *에이전트 파이프라인 시작*\n\n📝 주제: `{QUERY_INPUT}`\n\n`[1/5]` 주제 분류 중...")
    
    try:
        # ─── Step 1: 분류 ────────────────────────────────────────────
        classifier = ClassifierAgent()
        classification = classifier.run(QUERY_INPUT)
        
        send_telegram(CHAT_ID, 
            f"✅ `[1/5]` 분류 완료: *{'아빠 모드' if classification['mode'] == 'dad' else '엔지니어 모드'}*\n"
            f"🔍 `[2/5]` 정보 수집 중..."
        )
        
        # ─── Step 2: 검색 ────────────────────────────────────────────
        search = SearchAgent()
        facts = search.run(classification)
        
        send_telegram(CHAT_ID, 
            f"✅ `[2/5]` 정보 수집 완료\n✍️ `[3/5]` Writer 에이전트 초안 작성 중..."
        )
        
        # ─── Step 3: 글쓰기 ──────────────────────────────────────────
        writer = WriterAgent()
        drafts = writer.run(QUERY_INPUT, classification, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[3/5]` 초안 완성 (KO + EN)\n🔍 `[4/5]` Editor 에이전트 검수 중..."
        )
        
        # ─── Step 4: 편집 ────────────────────────────────────────────
        editor = EditorAgent()
        final_posts = editor.run(drafts, classification, facts)
        
        send_telegram(CHAT_ID, 
            f"✅ `[4/5]` 검수 완료\n💾 `[5/5]` 파일 저장 및 Git Push 중..."
        )
        
        # ─── Step 5: 파일 저장 ───────────────────────────────────────
        file_writer = FileWriterAgent()
        created_files = file_writer.run(final_posts, classification)
        
        print("\n" + "=" * 60)
        print("✅ 모든 에이전트 파이프라인 완료!")
        print("생성된 파일:")
        for f in created_files:
            print(f"  - {f}")
        print("=" * 60)
        
        # 환경변수로 파일 목록 전달 (GitHub Actions 스텝 간 공유)
        with open(os.environ.get("GITHUB_ENV", "/dev/null"), "a") as env_file:
            env_file.write(f"CREATED_FILES={','.join(created_files)}\n")
        
    except Exception as e:
        print(f"\n❌ 파이프라인 오류: {e}")
        import traceback
        traceback.print_exc()
        send_telegram(CHAT_ID, f"❌ *오류 발생*\n\n`{str(e)[:200]}`")
        sys.exit(1)


if __name__ == "__main__":
    main()
