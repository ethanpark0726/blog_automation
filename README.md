# 🤖 Blog Automation — Telegram-Triggered Multilingual Blog Platform

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/ethanpark0726/blog_automation/telegram_trigger.yml?label=Blog%20Pipeline&logo=github)](https://github.com/ethanpark0726/blog_automation/actions)
[![Jekyll](https://img.shields.io/badge/Jekyll-4.3-red?logo=jekyll)](https://jekyllrb.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-blue?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.6.0-purple)](CHANGELOG.md)

> Send a single message on Telegram and AI automatically generates **Korean + English** blog posts, then deploys them to GitHub Pages. **$0 cost. Zero human intervention.**

**🌐 Live Blog**: [ethanpark0726.github.io/blog_automation](https://ethanpark0726.github.io/blog_automation)

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 📱 **Telegram Trigger** | Send a message to the bot → pipeline starts automatically |
| 🔍 **Auto Classification** | Detects Trivia Mode (general wisdom) vs Engineer Mode (technical) |
| 🌐 **Multilingual** | Korean + English posts generated simultaneously |
| ✍️ **Multi-Agent QA** | Writer → Editor cross-review and auto-correction |
| 🚀 **Auto Deploy** | Git Push → GitHub Pages auto-build |
| 📩 **Completion Notify** | Telegram notification when deployment is done |

---

## 🏗️ Architecture

```
📱 Telegram Message
        ↓
☁️  Cloudflare Worker  (free serverless bridge)
        ↓
⚡ GitHub Actions  (workflow_dispatch)
        ↓
🔍 ClassifierAgent  →  Trivia / Engineer mode detection
🌐 SearchAgent      →  DuckDuckGo fact collection
✍️  WriterAgent      →  Gemini KO + EN draft generation
📝 EditorAgent      →  Fact-check + auto-correction
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
│   ├── multi_agent.py         # 5-agent pipeline (core)
│   ├── notify.py              # Telegram completion notification
│   ├── fix_mermaid.py         # Mermaid node label auto-fix utility
│   └── requirements.txt       # Python dependencies
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
Analyzes input and classifies into two modes:
- **Trivia Mode**: Casual questions, general knowledge, science trivia, and history → simple analogies
- **Engineer Mode**: Technical terms, dev/system topics → technical depth + diagrams

### SearchAgent
Collects real-time facts via DuckDuckGo Abstract API to prevent AI hallucinations.

### WriterAgent
Calls Gemini API to generate KO and EN drafts simultaneously based on collected facts.
- Markdown format (`##`, `>`, **bold**, `code`)
- Auto-inserts Mermaid diagrams for technical topics

### EditorAgent
Reviews Writer's draft against 6 criteria and self-corrects:
1. Fact check (no false claims or logical leaps)
2. Tone & manner (no machine-translation feel)
3. Markdown formatting (no broken syntax)
4. Structure (intro / body / conclusion)
5. `json_meta` block present
6. Mermaid node labels properly quoted

### FileWriterAgent
Auto-generates Jekyll Front Matter and saves to `_posts/ko/` and `_posts/en/`.

---

## 🔧 Environment Variables Reference

### GitHub Actions Secrets

| Name | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Chat ID for completion notifications |
| `GH_PAT` | Personal Access Token for Git push |

### Cloudflare Worker Variables

| Name | Type | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Secret | Bot token |
| `GITHUB_TOKEN` | Secret | GitHub PAT |
| `GITHUB_REPO` | Variable | `username/repo` format |
| `ALLOWED_CHAT_ID` | Variable | Allowed Chat ID (security) |

---

## 📊 Current Version

**v1.5.0** — Replaced Dad Mode with Trivia Vault

Full version history: [CHANGELOG.md](CHANGELOG.md)

---

## 🗺️ Roadmap

- **`[ ]` v1.6.0**: Enable Gemini API billing → upgrade to `gemini-3.1-pro`, tags filter pages
- **v2.0.0**: Voice input (Telegram voice messages), auto post images (Imagen API), social media sharing

---

## 🤝 Contributing

> **Every code or config change MUST include updates to `README.md` and `CHANGELOG.md`.**
> GitHub Actions automatically enforces this. The build will fail if violated.

See full version rules: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT License — Free to use, modify, and distribute.
