# 🤖 Blog Automation — 텔레그램 자동 다국어 블로그 플랫폼

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/ethanpark0726/blog_automation/telegram_trigger.yml?label=Blog%20Pipeline&logo=github)](https://github.com/ethanpark0726/blog_automation/actions)
[![Jekyll](https://img.shields.io/badge/Jekyll-4.3-red?logo=jekyll)](https://jekyllrb.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-blue?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.2.1-purple)](CHANGELOG.md)

> 텔레그램에 한 줄 메시지를 보내면, AI가 자동으로 **한국어 + 영어** 블로그 포스트를 생성하고 GitHub Pages에 배포합니다. **비용 $0, 사람 개입 0회.**

**🌐 라이브 블로그**: [ethanpark0726.github.io/blog_automation](https://ethanpark0726.github.io/blog_automation)

---

## ✨ 주요 기능

| 기능 | 설명 |
|---|---|
| 📱 **텔레그램 트리거** | 봇에 메시지 전송 → 자동 파이프라인 시작 |
| 🔍 **자동 분류** | 아빠 모드(친근한 설명) / 엔지니어 모드(기술 심층) 자동 판별 |
| 🌐 **다국어 생성** | 한국어 + 영어 포스트 동시 생성 |
| ✍️ **멀티 에이전트** | Writer → Editor 교차 검수 및 자동 수정 |
| 🚀 **자동 배포** | Git Push → GitHub Pages 자동 빌드 |
| 📩 **완료 알림** | 배포 완료 시 텔레그램으로 알림 전송 |

---

## 🏗️ 아키텍처

```
📱 Telegram Message
        ↓
☁️  Cloudflare Worker  (무료 웹훅 중계)
        ↓
⚡ GitHub Actions  (workflow_dispatch)
        ↓
🔍 ClassifierAgent  →  아빠/엔지니어 모드 분류
🌐 SearchAgent      →  DuckDuckGo 팩트 수집
✍️  WriterAgent      →  Gemini KO + EN 초안
📝 EditorAgent      →  팩트체크 + 자동 교정
💾 FileWriterAgent  →  Jekyll Markdown 생성
        ↓
🇰🇷 _posts/ko/   +   🇺🇸 _posts/en/
        ↓
🚀 Git Push → 🌐 GitHub Pages → 📩 완료 알림
```

---

## 📁 프로젝트 구조

```
blog_automation/
├── 📁 .github/workflows/
│   ├── telegram_trigger.yml   # 텔레그램 트리거 → 에이전트 실행
│   └── deploy.yml             # Jekyll → GitHub Pages 자동 배포
│
├── 📁 cloudflare-worker/
│   ├── worker.js              # 텔레그램 웹훅 수신 → GitHub API 중계
│   └── wrangler.toml          # Cloudflare 배포 설정
│
├── 📁 scripts/
│   ├── multi_agent.py         # 5개 에이전트 파이프라인 (핵심)
│   ├── notify.py              # 텔레그램 완료 알림
│   ├── fix_mermaid.py         # Mermaid 노드 레이블 자동 교정 유틸리티
│   └── requirements.txt       # Python 의존성
│
├── 📁 _layouts/
│   └── home.html              # 사이드바 + 카드형 커스텀 홈 레이아웃
│
├── 📁 assets/css/
│   └── custom.css             # 블로그 커스텀 스타일
│
├── 📁 _posts/
│   ├── ko/                    # 한국어 포스트
│   └── en/                    # 영어 포스트
│
├── _config.yml                # Jekyll 설정
├── Gemfile                    # Ruby 의존성
├── index.md                   # 블로그 홈
├── dad.md                     # Dad 카테고리 페이지
├── engineer.md                # Engineer 카테고리 페이지
├── CHANGELOG.md               # 버전 변경 이력
└── .gitignore
```

---

## 🚀 빠른 시작 (Quick Start)

### 1단계 — 필요한 계정 및 키 준비

| 항목 | 링크 | 비용 |
|---|---|---|
| 텔레그램 봇 토큰 | [@BotFather](https://t.me/botfather) | 무료 |
| Gemini API 키 | [AI Studio](https://aistudio.google.com/app/apikey) | 무료 |
| GitHub PAT | [Settings > Tokens](https://github.com/settings/tokens) | 무료 |
| Cloudflare 계정 | [dash.cloudflare.com](https://dash.cloudflare.com) | 무료 |

### 2단계 — GitHub Secrets 등록

저장소 → **Settings → Secrets → Actions** 에서 4개 등록:

```
GEMINI_API_KEY      # Google AI Studio API 키
TELEGRAM_BOT_TOKEN  # BotFather 토큰
TELEGRAM_CHAT_ID    # 내 텔레그램 Chat ID
GH_PAT              # GitHub Personal Access Token
```

### 3단계 — Cloudflare Worker 배포

1. `cloudflare-worker/worker.js` 내용을 Cloudflare Worker에 붙여넣기
2. 환경변수 4개 설정:
   ```
   TELEGRAM_BOT_TOKEN  (Secret)
   GITHUB_TOKEN        (Secret)
   GITHUB_REPO         (Variable) → "ethanpark0726/blog_automation"
   ALLOWED_CHAT_ID     (Variable) → 내 Chat ID
   ```

### 4단계 — 텔레그램 Webhook 등록

```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>
```

### 5단계 — 테스트

텔레그램 봇에 메시지 전송:
```
쿠버네티스란 무엇인가?
```

약 2~4분 후 GitHub Pages에 KO + EN 포스트가 자동 생성됩니다! 🎉

---

## ⚙️ 에이전트 파이프라인 상세

### ClassifierAgent
입력 텍스트를 분석해 두 가지 모드로 분류합니다:
- **Dad Mode**: 일상적 질문, 쉬운 설명이 적합한 주제 → 친근한 비유 사용
- **Engineer Mode**: 기술 용어, 개발/시스템 관련 → 전문 용어 + 다이어그램

### SearchAgent
DuckDuckGo Abstract API로 실시간 팩트를 수집해 Hallucination을 방지합니다.

### WriterAgent
Gemini API를 호출해 수집된 팩트 기반으로 KO/EN 초안을 동시에 생성합니다.
- 마크다운 형식 (`##`, `>`, **bold**, `code`)
- 기술 주제는 Mermaid 다이어그램 자동 삽입

### EditorAgent
Writer 초안을 3가지 기준으로 검수하고 스스로 수정합니다:
1. 팩트 체크 (허위 사실, 논리적 비약)
2. 톤앤매너 (기계 번역투 제거)
3. 마크다운 포맷 (문법 오류)

### FileWriterAgent
Jekyll Front Matter를 자동 생성하고 `_posts/ko/`, `_posts/en/`에 저장합니다.

---

## 🔧 환경변수 전체 목록

### GitHub Actions Secrets

| 이름 | 설명 |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API 키 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 완료 알림 수신용 Chat ID |
| `GH_PAT` | Git Push 권한용 Personal Access Token |

### Cloudflare Worker Variables

| 이름 | 타입 | 설명 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Secret | 봇 토큰 |
| `GITHUB_TOKEN` | Secret | GitHub PAT |
| `GITHUB_REPO` | Variable | `username/repo` 형식 |
| `ALLOWED_CHAT_ID` | Variable | 허용할 Chat ID (보안) |

---

## 📊 현재 버전

**v1.2.1** — Mermaid 다이어그램 파싱 오류 수정

전체 변경 이력: [CHANGELOG.md](CHANGELOG.md)

---

## 🗺️ 로드맵

- **v1.3.0**: Gemini API 유료 빌링 → `gemini-3.1-pro` 복원, 태그 필터 페이지
- **v2.0.0**: 음성 인식 입력, 포스트 이미지 자동 생성, 소셜 미디어 공유

---

## 🤝 기여 규칙

> **코드/설정을 변경할 때마다 `README.md`와 `CHANGELOG.md`를 반드시 함께 수정해야 합니다.**  
> GitHub Actions가 자동으로 이를 검사하며, 위반 시 빌드가 실패합니다.

자세한 버전 관리 규칙: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 라이선스

MIT License — 자유롭게 사용, 수정, 배포 가능합니다.
