# Changelog

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.7.0] — 2026-07-11

### Added
- **Dynamic Model Selection**: Enabled model customization to support upgrading or switching Gemini models dynamically as new models are released or billing tiers change.
  - Implemented the `GEMINI_MODEL` environment variable in `scripts/multi_agent.py` to override the default model, falling back to stable `gemini-2.5-flash` if unconfigured.
  - Printed active model name at script startup to improve pipeline transparency in GitHub Actions logs.
  - Configured `.github/workflows/telegram_trigger.yml` to inject `GEMINI_MODEL` from GitHub Action variables or secrets.

---

## [1.6.3] — 2026-07-11

### Fixed
- **Cloudflare Worker Security Hardening**: Made the `ALLOWED_CHAT_ID` environment variable check mandatory in `worker.js`.
  - Previously, if the variable was undefined or empty, it allowed any Telegram chat to trigger dispatches. It now safely blocks requests and throws a 403 Forbidden error if this variable is unconfigured or empty.
  - Trimmed inputs to prevent validation mismatches from trailing/leading whitespace.

---

## [1.6.2] — 2026-07-11

### Changed
- **Documentation Update Rules Enforcement**: Updated the blog's contribution guidelines and local/CI validation checks to ensure project information remains accurate.
  - Aligned `README.md`'s **Current Version** and **Roadmap** sections with the actual state of the repository (`v1.6.2`).
  - Added new checklist instructions to [CONTRIBUTING.md](CONTRIBUTING.md) to explicitly require updating the version summary and shifting roadmap milestones when releasing changes.
  - Appended reminders to the GitHub Actions `check_docs.yml` validation script failure console, ensuring developers are prompted to verify the roadmap on build issues.

---

## [1.6.1] — 2026-07-11

### Fixed
- **Client-side Mermaid Diagram Rendering**: Integrated client-side Mermaid.js rendering engine in `_layouts/default.html` to dynamic-parse and draw SVG block diagrams from raw markdown ` ```mermaid ` tags.
  - Custom styling in `custom.css` ensures diagrams are centered, fully responsive (mobile-friendly), and wrap cleanly in Dark Tech Theme cards.
  - Conditional load logic prevents loading Mermaid JS assets on pages that do not contain diagrams, optimizing speed.

---

## [1.6.0] — 2026-07-11

### Added
- **Smart i18n Language Handling**: Completely revamped multilingual content display to eliminate duplicate post clutter on the main feed.
  - **Browser language auto-detection**: Automatically filters posts to match the user's browser language (Korean → KO posts, English → EN posts) on page load.
  - **`localStorage` preference persistence**: Once a user selects a language, the preference is stored and remembered across visits.
  - **`topic_id` post pairing system**: KO/EN posts of the same topic are now linked via a shared `topic_id` front matter field.
  - **Translation switch banner**: Each post detail page shows a prominent banner at the top to switch to the paired translation (e.g., "🇺🇸 Read this post in English").
  - **Inline pair links**: Post cards on the home feed and category pages show a small language toggle badge linking to the paired translation.
  - **Fade-in animation**: Smooth opacity transition when switching language filters.
- **`scripts/add_topic_id.py`**: Migration script to retroactively add `topic_id` to all 6 existing posts.

### Changed
- **`_layouts/home.html`**: Replaced static filter logic with auto-detect + animated filter system; added `data-lang` attributes for sidebar recent posts filtering.
- **`_layouts/post.html`**: Added translation banner component using Liquid `topic_id` matching.
- **`trivia.md` / `engineer.md`**: Added language filter tabs with auto-detect, matching main feed UX.
- **`scripts/multi_agent.py`**: `FileWriterAgent` now generates a shared `topic_id` for each KO/EN post pair.
- **`assets/css/custom.css`**: Added `.translation-banner` and `.pair-link-inline` styles with gradient backgrounds and hover animations.

---

## [1.5.0] — 2026-07-10

### Changed
- **Trivia Vault Migration**: Migrated the "Dad Mode" category to "Trivia Vault" to better align with the blog's general knowledge, science, and history focus.
  - Updated classification model logic in `multi_agent.py` to route general knowledge inquiries to `trivia` mode instead of `dad`.
  - Refactored `FileWriterAgent` to output posts with the `Trivia` category instead of `Dad`.
  - Created a database migration script `scripts/migrate_categories.py` and successfully migrated all 6 existing posts to `categories: [Trivia]`.
  - Deleted `dad.md` and created `trivia.md` as the new category archive page under `/trivia/`.
  - Renamed CSS variables (e.g. `--dad-color` to `--trivia-color`) and element selectors (e.g. `.cat-dad` to `.cat-trivia`) in `custom.css` to clean up old design artifacts.
  - Updated headers, footers, badges, and sidebar counts in `default.html`, `home.html`, and `post.html` templates to link and render the new `💡 Trivia` vault badge.

### Removed
- **`dad.md`**: Permanently removed the obsolete category page.

---

## [1.4.2] — 2026-07-10

### Changed
- **Non-AI Branding Alignment**: Re-branded the blog's content identity to remove obvious AI references, shifting to a premium human-centric general knowledge and engineering repository.
  - Updated subtitle description to: `"A curated repository bridging software engineering logbooks, scientific curiosity, and general trivia in Korean and English."`
  - Replaced footer notice with: `"Tech & Knowledge | Handcrafted Insights on Tech, Science, and Everyday Wisdom."`
  - Set author name to: `"The Knowledge Logbook"`.
  - Swapped header logo icon from `🤖` to `📚` (book) to reflect the new knowledge-centric identity.
  - Unified all pages, category templates (`dad.md`, `engineer.md`), and post templates to inherit `_layouts/default.html` to guarantee consistent dark mode rendering.

---

## [1.4.1] — 2026-07-10

### Fixed
- **Stats Widget English Count Bug**: Fixed a variable naming collision in `_layouts/home.html` where `eng_posts` (Engineer category posts) was mistakenly used instead of `en_posts` (English language posts) to display the English post count.

---

## [1.4.0] — 2026-07-10

### Changed
- **New Dark Tech Theme**: Revamped the entire blog design using the color scheme `#1E1E24` (dark charcoal gray) and `#4ADE80` (neon green accent).
  - Configured deep dark background (`#121214`) and rich card/sidebar background elements.
  - Added modern glassmorphism blur effects to the sticky header.
  - Implemented neon green accent glow effects for active filter tabs and hover states.
  - Re-styled badges (KO/EN and Dad/Engineer) with subtle borders and semi-transparent fills for high-contrast dark mode readability.

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
