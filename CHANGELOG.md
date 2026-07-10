# Changelog

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.3.0] — 2026-07-10

### Changed
- **Full English localization**: Converted all Korean comments, docstrings, print statements, UI strings, and documentation to English across the entire codebase
  - `scripts/multi_agent.py` — comments, docstrings, log output, Gemini prompts
  - `scripts/notify.py` — comments, log output
  - `scripts/fix_mermaid.py` — comments, docstrings
  - `.github/workflows/*.yml` — step names, echo messages, comments
  - `cloudflare-worker/worker.js` — comments, user-facing bot messages
  - `_layouts/home.html` — all UI labels, navigation, sidebar, filter tabs
  - `assets/css/custom.css` — comments
  - `dad.md`, `engineer.md`, `index.md` — page content
  - `_config.yml` — comments
  - `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md` — full rewrite in English

---

## [1.2.1] — 2026-07-09

### Fixed
- **Mermaid diagram parse error**: Fixed crash when node labels contained parentheses `()` or Korean characters
  - Added mandatory quoting rule to `WriterAgent` prompt — all node labels must be wrapped in `""`
  - Added Mermaid syntax check (item 6) to `EditorAgent` QA checklist
  - Batch-fixed 4 existing posts using `scripts/fix_mermaid.py`

### Added
- **`scripts/fix_mermaid.py`**: Utility to auto-correct Mermaid node labels in existing posts

---

## [1.2.0] — 2026-07-09

### Added
- **Custom home layout** (`_layouts/home.html`): Sidebar + card-style post list
- **Sidebar widgets**: Categories, language filter, recent posts, tag cloud, stats
- **Language filter tabs**: All / 🇰🇷 Korean / 🇺🇸 English instant filtering (JavaScript)
- **Category pages**: Standalone `/dad/` and `/engineer/` pages
- **Badge system**: KO/EN language badges + Dad/Engineer category badges
- **Custom CSS** (`assets/css/custom.css`): Card hover effects, responsive layout

### Changed
- `index.md`: Moved content to `_layouts/home.html`, simplified
- `_config.yml`: Updated `baseurl` and `url` with real values

---

## [1.1.2] — 2026-07-09

### Added
- 4 auto-generated posts via Telegram (KO/EN): Adobe architecture, CrossFit science

---

## [1.1.1] — 2026-07-07

### Fixed
- **Jekyll permalink error**: `/:lang/:year/:month/:day/:title/` → `/:categories/:year/:month/:day/:title/`  
  (minima theme does not support `:lang` as a custom permalink variable)
- **Jekyll build failure**: Removed `bundler-cache: true`, added explicit `bundle install` step  
  (build failed when `Gemfile.lock` did not exist)

---

## [1.1.0] — 2026-07-07

### Added
- 2 auto-generated posts via Telegram (KO/EN): Solar system formation

### Changed
- **Gemini model downgrade**: `gemini-3.1-pro-preview` → `gemini-2.5-flash`  
  (free API tier does not support `gemini-3.1-pro`; upgrade available with billing enabled)
- `_config.yml`: Initial GitHub Pages URL and `baseurl` configuration

---

## [1.0.0] — 2026-07-06

### Added (Initial Release)

#### Phase 0 — Webhook Infrastructure
- **`cloudflare-worker/worker.js`**: Receives Telegram webhook POST → triggers GitHub Actions `workflow_dispatch`
- **`cloudflare-worker/wrangler.toml`**: Cloudflare Worker deployment config

#### Phase 1 — GitHub Actions Pipeline
- **`.github/workflows/telegram_trigger.yml`**: Telegram trigger → multi-agent execution → Git push automation
- **`.github/workflows/deploy.yml`**: Jekyll build → GitHub Pages auto-deploy

#### Phase 1 — Multi-Agent System
- **`scripts/multi_agent.py`**: 5-agent pipeline
  - `ClassifierAgent`: Auto-detects Dad Mode vs Engineer Mode
  - `SearchAgent`: DuckDuckGo API fact collection (hallucination prevention)
  - `WriterAgent`: Gemini API simultaneous KO + EN draft generation
  - `EditorAgent`: Fact-check + tone + Markdown auto-correction
  - `FileWriterAgent`: Jekyll Front Matter merge + file save
- **`scripts/notify.py`**: Telegram completion notification after GitHub Actions
- **`scripts/requirements.txt`**: Python dependencies (`google-generativeai`, `requests`)

#### Jekyll Blog Structure
- **`_config.yml`**: Jekyll config (minima theme, SEO plugins, multilingual defaults)
- **`Gemfile`**: Ruby dependencies (Jekyll 4.3, minima, feed/seo/sitemap plugins)
- **`index.md`**: Blog home page
- **`_posts/ko/`**, **`_posts/en/`**: Korean/English post directories
- **`.gitignore`**: Excludes env files and build artifacts

---

## Roadmap

### [1.4.0] — Planned
- [ ] Enable Gemini API billing → restore `gemini-3.1-pro-preview`
- [ ] Tag filter pages
- [ ] Mermaid diagram rendering support in posts

### [2.0.0] — V2 Planned
- [ ] Voice input (Telegram voice messages → blog posts)
- [ ] Auto post image generation (Imagen API)
- [ ] Social media auto-sharing (Twitter/X, LinkedIn)
