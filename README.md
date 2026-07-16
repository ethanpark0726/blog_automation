# 🤖 Blog Automation — Telegram-Triggered Multilingual Blog Platform

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/ethanpark0726/blog_automation/telegram_trigger.yml?label=Blog%20Pipeline&logo=github)](https://github.com/ethanpark0726/blog_automation/actions)
[![Jekyll](https://img.shields.io/badge/Jekyll-4.3-red?logo=jekyll)](https://jekyllrb.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-blue?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.15.1-purple)](CHANGELOG.md)

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
| 📉 **3-Call Budget** | Standard KO+EN generation uses three successful Gemini calls instead of eight |
| 🚀 **Auto Deploy** | Git Push → GitHub Pages auto-build |
| 📩 **Quota-Aware Notify** | Telegram reports generation status, Gemini usage, and actionable quota errors |
| 📡 **Operations Telemetry** | Actions summary and Telegram report per-stage tokens, source quality, and the actual Pages result |

---

## 🏗️ Architecture

```
📱 Telegram Message
        ↓
☁️  Cloudflare Worker  (free serverless bridge)
        ↓
⚡ GitHub Actions  (workflow_dispatch)
        ↓
🧭 Research Writer  →  English intent, queries, and provisional draft
🌐 SearchAgent      →  English source collection + coverage gate
📝 EditorAgent      →  English fact-check + validation
🇰🇷 KO Localizer     →  Validated English → natural Korean
💾 FileWriterAgent  →  Jekyll Markdown file creation
        ↓
🇰🇷 _posts/ko/   +   🇺🇸 _posts/en/
        ↓
🚀 Git Push → 🌐 Wait for GitHub Pages completion → 📩 Verified notification
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
│   ├── multi_agent.py         # English-first 5-agent / 3-call pipeline (core)
│   ├── content_quality.py     # Local classification, references, and validation
│   ├── gemini_runtime.py      # Gemini usage tracking, retry, and error classification
│   ├── notify.py              # Telegram completion notification
│   ├── pages_status.py        # Waits for the exact post commit's Pages deployment
│   ├── operations_summary.py  # GitHub Actions usage and quality dashboard
│   ├── fix_mermaid.py         # Mermaid node label auto-fix utility
│   └── requirements.txt       # Python dependencies
│
├── 📁 tests/
│   ├── test_content_quality.py # Offline classification/reference/validation tests
│   ├── test_gemini_runtime.py  # Offline quota/error/usage tests
│   ├── test_operations.py      # Pages monitoring and dashboard tests
│   ├── test_pipeline_budget.py # Static three-call architecture guard
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

### ResearchWriterAgent
Uses one Gemini call to disambiguate multilingual input, return 2-4 English search queries, and produce a provisional English draft. External sources are collected immediately afterward and the Editor grounds the draft against them.

### SearchAgent
Collects English facts directly from DuckDuckGo, English Wikipedia, Google Books, arXiv, and Crossref. A local coverage gate requires at least 500 fact characters and two references before long-form generation begins.

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
| English research planning + provisional draft | 1 |
| English source collection and coverage gate | 0 |
| English fact-check/edit | 1 |
| Korean localization | 1 |
| Local validation and file writing | 0 |
| **Total** | **3** |

Failed workflow reruns restore completed stages from `.pipeline_cache`, so only unfinished model stages are called again. Generated posts also carry a request fingerprint that blocks duplicate Telegram submissions before API use.

### FileWriterAgent
Auto-generates Jekyll Front Matter and saves to `_posts/ko/` and `_posts/en/`.

### Gemini Runtime & Quota Handling
All Gemini calls pass through a shared runtime that records API attempts and response token usage by pipeline stage.

- `429` errors are classified as daily requests (`RPD`), requests per minute (`RPM`), tokens per minute (`TPM`), or unknown quota pressure.
- Daily quota exhaustion stops immediately instead of spending retries that cannot succeed before reset.
- Only transient rate limits, timeouts, and service errors are retried with bounded exponential backoff.
- `.pipeline_result.json` carries structured usage and failure details to the final Telegram notification step.
- Successful notifications report per-run API attempts, per-stage tokens, and input/output totals.
- Gemini's generate-content response does not expose the exact remaining free-tier request count, so the bot reports measured consumption without inventing a remaining-quota estimate.

### Operations, Source Quality, and Pages Completion

- Source quality is scored locally from `0-100` using reference count, independent-domain diversity, evidence volume, and authoritative domains. This costs no Gemini request.
- Every run publishes a GitHub Actions job summary with pipeline status, Pages status, total tokens, per-stage token usage, and source quality.
- The generation workflow waits for the `deploy.yml` run associated with the exact generated-post commit. Telegram therefore distinguishes Pages success, failure, timeout, and monitor errors.
- Telegram `/status` reports the latest generation and Pages workflow states; `/help` lists supported commands. Deploy `cloudflare-worker/worker.js` again for these command changes to become active.

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

**v1.15.1** — Fixes docs-rule false positives for Korean post filenames and adds repository-wide LF normalization for Markdown and workflow files.

Full version history: [CHANGELOG.md](CHANGELOG.md)

---

## 🗺️ Roadmap

- **`[x]` v1.11.0**: Global Client-Side Search
- **`[x]` v1.11.1**: Gemini Usage Tracking & Quota-Aware Telegram Notifications
- **`[x]` v1.12.0**: Reduce the standard Gemini pipeline from 8 calls to 4 calls
- **`[x]` v1.12.1**: Harden bilingual source collection and Editor validation
- **`[x]` v1.13.0**: English-first canonical article and Korean localization pipeline
- **`[x]` v1.14.0**: Three-call optimization, failed-run checkpoints, and duplicate-request protection
- **`[x]` v1.15.0**: Usage dashboard, source-quality score, Pages completion, and Telegram operations
- **`[x]` v1.15.1**: Docs-rule Unicode path fix and `.gitattributes` line-ending normalization
- **v2.0.0**: Voice input (Telegram voice messages), social media sharing (Twitter/X, LinkedIn)

---

## 🤝 Contributing

> **Every code or config change MUST include updates to `README.md` and `CHANGELOG.md`.**
> GitHub Actions automatically enforces this. The build will fail if violated.

See full version rules: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT License — Free to use, modify, and distribute.
