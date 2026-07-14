# 🤖 Blog Automation — Telegram-Triggered Multilingual Blog Platform

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/ethanpark0726/blog_automation/telegram_trigger.yml?label=Blog%20Pipeline&logo=github)](https://github.com/ethanpark0726/blog_automation/actions)
[![Jekyll](https://img.shields.io/badge/Jekyll-4.3-red?logo=jekyll)](https://jekyllrb.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-blue?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.13.0-purple)](CHANGELOG.md)

> Send a single message on Telegram and AI automatically generates **Korean + English** blog posts, then deploys them to GitHub Pages. **$0 cost. Zero human intervention.**

**🌐 Live Blog**: [ethanpark0726.github.io/blog_automation](https://ethanpark0726.github.io/blog_automation)

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 📱 **Telegram Trigger** | Send a message to the bot → pipeline starts automatically |
| 🔍 **Local Classification** | Detects Trivia vs Engineer mode without spending a Gemini request |
| 🌐 **Multilingual** | Korean + English posts generated simultaneously |
| ✍️ **Multi-Agent QA** | Writer → Editor cross-review and auto-correction |
| 📉 **4-Call Budget** | Standard KO+EN generation uses four successful Gemini calls instead of eight |
| 🚀 **Auto Deploy** | Git Push → GitHub Pages auto-build |
| 📩 **Quota-Aware Notify** | Telegram reports generation status, Gemini usage, and actionable quota errors |

---

## 🏗️ Architecture

```
📱 Telegram Message
        ↓
☁️  Cloudflare Worker  (free serverless bridge)
        ↓
⚡ GitHub Actions  (workflow_dispatch)
        ↓
🧭 Research Planner →  English intent and query resolution
🌐 SearchAgent      →  English source collection + coverage gate
✍️  WriterAgent      →  Canonical English draft
📝 EditorAgent      →  English fact-check + validation
🇰🇷 KO Localizer     →  Validated English → natural Korean
💾 FileWriterAgent  →  Jekyll Markdown file creation
        ↓
🇰🇷 _posts/ko/   +   🇺🇸 _posts/en/
        ↓
🚀 Git Push → 🌐 GitHub Pages → 📩 Done notification
```

---

## 📁 Project Structure

```
blog_automation/
├── 📁 .github/workflows/
│   ├── telegram_trigger.yml   # Telegram trigger → agent execution
│   ├── deploy.yml             # Jekyll → GitHub Pages auto-deploy
│   └── check_docs.yml         # Enforces README+CHANGELOG update rule
│
├── 📁 cloudflare-worker/
│   ├── worker.js              # Telegram webhook → GitHub API bridge
│   └── wrangler.toml          # Cloudflare deployment config
│
├── 📁 scripts/
│   ├── multi_agent.py         # 5-agent / 4-call pipeline (core)
│   ├── content_quality.py     # Local classification, references, and validation
│   ├── gemini_runtime.py      # Gemini usage tracking, retry, and error classification
│   ├── notify.py              # Telegram completion notification
│   ├── fix_mermaid.py         # Mermaid node label auto-fix utility
│   └── requirements.txt       # Python dependencies
│
├── 📁 tests/
│   ├── test_content_quality.py # Offline classification/reference/validation tests
│   ├── test_gemini_runtime.py  # Offline quota/error/usage tests
│   ├── test_pipeline_budget.py # Static four-call architecture guard
│   └── test_pipeline_integration.py # Full pipeline test with fake services
│
├── 📁 _layouts/
│   └── home.html              # Custom home layout with sidebar + cards
│
├── 📁 assets/css/
│   └── custom.css             # Blog custom stylesheet
│
├── 📁 _posts/
│   ├── ko/                    # Korean posts (auto-generated)
│   └── en/                    # English posts (auto-generated)
│
├── _config.yml                # Jekyll configuration
├── Gemfile                    # Ruby dependencies
├── index.md                   # Blog home page
├── trivia.md                  # Trivia Vault category page
├── engineer.md                # Engineer category page
├── CHANGELOG.md               # Version history
├── CONTRIBUTING.md            # Contribution rules
└── .gitignore
```

---

## 🚀 Quick Start

### Step 1 — Gather Required Credentials

| Item | Link | Cost |
|---|---|---|
| Telegram Bot Token | [@BotFather](https://t.me/botfather) | Free |
| Gemini API Key | [AI Studio](https://aistudio.google.com/app/apikey) | Free |
| GitHub PAT | [Settings > Tokens](https://github.com/settings/tokens) | Free |
| Cloudflare Account | [dash.cloudflare.com](https://dash.cloudflare.com) | Free |

### Step 2 — Set GitHub Secrets

Go to your repo → **Settings → Secrets → Actions** and add:

```
GEMINI_API_KEY      # Google AI Studio API key
TELEGRAM_BOT_TOKEN  # BotFather token
TELEGRAM_CHAT_ID    # Your Telegram Chat ID
GH_PAT              # GitHub Personal Access Token
```

### Step 3 — Deploy Cloudflare Worker

1. Copy `cloudflare-worker/worker.js` into a new Cloudflare Worker
2. Set 4 environment variables:
   ```
   TELEGRAM_BOT_TOKEN  (Secret)
   GITHUB_TOKEN        (Secret)
   GITHUB_REPO         (Variable) → "your-username/blog_automation"
   ALLOWED_CHAT_ID     (Variable) → your Telegram Chat ID
   ```

### Step 4 — Register Telegram Webhook

```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>
```

### Step 5 — Test It

Send a message to your bot:
```
What is Kubernetes?
```

In ~2–4 minutes, KO + EN posts will appear on your GitHub Pages blog! 🎉

---

## ⚙️ Agent Pipeline Details

### ClassifierAgent
Classifies input locally without calling Gemini:
- **Trivia Mode**: Casual questions, general knowledge, science trivia, and history → simple analogies
- **Engineer Mode**: Technical terms, dev/system topics → technical depth + diagrams

### ResearchPlannerAgent
Uses a short Gemini call to disambiguate multilingual input and return an English canonical topic plus 2-4 English search queries.

### SearchAgent
Collects English facts directly from DuckDuckGo, English Wikipedia, Google Books, arXiv, and Crossref. A local coverage gate requires at least 500 fact characters and two references before long-form generation begins.

### WriterAgent
Calls Gemini API to generate the canonical English draft from the collected facts.
- Markdown format (`##`, `>`, **bold**, `code`)
- Auto-inserts Mermaid diagrams for technical topics

### EditorAgent
Combines source-based fact verification and English copyediting in one call:
1. Fact check (no false claims or logical leaps)
2. Tone & manner (no machine-translation feel)
3. Markdown formatting (no broken syntax)
4. Structure (intro / body / conclusion)
5. `json_meta` block present
6. Mermaid node labels properly quoted

Verified reference titles and URLs are extracted and appended by local code instead of being generated by the model. A local validator blocks missing metadata, broken code fences, insufficient structure, and severely truncated content without spending another API call.

### KoreanLocalizerAgent
Localizes only the validated English article. It must preserve claims, sections, tables, code, diagrams, and references without adding new facts or URLs.

### Standard Gemini Call Budget

| Stage | Calls |
|---|---:|
| Local classification | 0 |
| English research planner | 1 |
| English source collection and coverage gate | 0 |
| Canonical English draft | 1 |
| English fact-check/edit | 1 |
| Korean localization | 1 |
| Local validation and file writing | 0 |
| **Total** | **4** |

### FileWriterAgent
Auto-generates Jekyll Front Matter and saves to `_posts/ko/` and `_posts/en/`.

### Gemini Runtime & Quota Handling
All Gemini calls pass through a shared runtime that records API attempts and response token usage by pipeline stage.

- `429` errors are classified as daily requests (`RPD`), requests per minute (`RPM`), tokens per minute (`TPM`), or unknown quota pressure.
- Daily quota exhaustion stops immediately instead of spending retries that cannot succeed before reset.
- Only transient rate limits, timeouts, and service errors are retried with bounded exponential backoff.
- `.pipeline_result.json` carries structured usage and failure details to the final Telegram notification step.
- Successful notifications report per-run API attempts and input/output token usage. Project-wide remaining quota requires the planned Cloud Monitoring integration.

---

## 🔧 Environment Variables Reference

### GitHub Actions Secrets & Variables

| Name | Type | Description | Default / Requirement |
|---|---|---|---|
| `GEMINI_API_KEY` | Secret | Google Gemini API key | (Required) |
| `TELEGRAM_BOT_TOKEN` | Secret | Telegram bot token | (Required) |
| `TELEGRAM_CHAT_ID` | Secret/Var | Chat ID for completion notifications | (Optional) |
| `GH_PAT` | Secret | Personal Access Token for Git push | (Required) |
| `GEMINI_MODEL` | Secret/Var | Gemini model to run the pipeline (e.g. `gemini-2.5-pro`) | `gemini-2.5-flash` |

### Cloudflare Worker Variables

| Name | Type | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Secret | Bot token |
| `GITHUB_TOKEN` | Secret | GitHub PAT |
| `GITHUB_REPO` | Variable | `username/repo` format |
| `ALLOWED_CHAT_ID` | Variable | Allowed Chat ID (security) |

---

## 📊 Current Version

**v1.13.0** — Uses an English-first canonical content pipeline: research planning, English source coverage, English drafting and validation, then Korean localization within the same four-call budget.

Full version history: [CHANGELOG.md](CHANGELOG.md)

---

## 🗺️ Roadmap

- **`[x]` v1.11.0**: Global Client-Side Search
- **`[x]` v1.11.1**: Gemini Usage Tracking & Quota-Aware Telegram Notifications
- **`[x]` v1.12.0**: Reduce the standard Gemini pipeline from 8 calls to 4 calls
- **`[x]` v1.12.1**: Harden bilingual source collection and Editor validation
- **`[x]` v1.13.0**: English-first canonical article and Korean localization pipeline
- **v1.14.0**: Three-call optimization, research cache, and stage-level retry checkpoints
- **v1.15.0**: Usage dashboard, source-quality score, Pages completion, and Telegram operations
- **v2.0.0**: Voice input (Telegram voice messages), social media sharing (Twitter/X, LinkedIn)

---

## 🤝 Contributing

> **Every code or config change MUST include updates to `README.md` and `CHANGELOG.md`.**
> GitHub Actions automatically enforces this. The build will fail if violated.

See full version rules: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT License — Free to use, modify, and distribute.
