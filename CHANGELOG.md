# Changelog

## [1.20.7] — 2026-07-20

### Fixed
- **Review Note Placeholder Safety**: Ready Obsidian review notes with a missing or template `target_post_id` are skipped before post lookup so `/revise` does not fail on copied templates.
- **Revision Research Fallback**: Korean-only review notes now seed research from the English post title so enrichment does not start with zero queries.

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.20.6] — 2026-07-20

### Fixed
- **Source Coverage Test Isolation**: Mocked Crossref in the missing-source integration test so GitHub Actions cannot accidentally hit the live Crossref API after trivia-mode research started using it.

---

## [1.20.5] — 2026-07-20

### Changed
- **Review Note Retention**: Successfully processed Obsidian review notes are now deleted instead of moved to `_reviews/completed`.
- **Revision Notifications**: Revision change summaries now include the deleted pending review note path instead of an archived completed-note path.

### Removed
- **Completed Review Archive**: Removed tracked `_reviews/completed` files because Git history already records successful revisions.

---

## [1.20.4] — 2026-07-20

### Changed
- **Trivia Source Diversity**: Trivia-mode research now reuses Crossref alongside DuckDuckGo, Wikipedia, and Google Books to increase independent-domain coverage without adding another dependency or API key.
- **Reference Extraction**: Reference extraction now caps one domain at four references so a single source such as Wikipedia cannot dominate all displayed references and source-quality scoring.

---

## [1.20.3] — 2026-07-20

### Added
- **Project-Scoped Agent Skills**: Added `.agents/` and `skills-lock.json` so the installed engineering skills are reproducible across local checkouts and future agent sessions.

---

## [1.20.2] — 2026-07-20

### Added
- **Agent Domain Glossary**: Added `CONTEXT.md` so installed engineering skills share the same project language for blog generation, post pairs, Obsidian review notes, knowledge notes, and workflow concepts.

---

## [1.20.1] — 2026-07-19

### Added
- **README Version Metadata Guard**: Added a CI validation script that fails when the README version badge, Current Version section, Roadmap entry, and latest CHANGELOG version drift apart.

### Fixed
- **README Version Badge**: Updated the stale README version badge so it matches the current release metadata.

---

## [1.20.0] — 2026-07-19

### Added
- **Telegram Revision Commands**: Added `/reviews` and `/revise` Cloudflare Worker commands so Obsidian review revisions can be triggered from Telegram.
- **Revision Workflow Inputs**: Added optional `chat_id` and `review_filter` inputs to the Obsidian revision workflow, supporting `/revise`, `/revise latest`, and filtered revision runs.
- **Revision Result Notifications**: Added Telegram success/failure notifications for Obsidian revision workflow runs.

### Changed
- **Operations Status**: Telegram `/status` now includes the latest Obsidian revision workflow run alongside generation and Pages deployment.

---

## [1.19.9] — 2026-07-17

### Added
- **Review Completion Audit Trail**: Completed Obsidian review notes now record completion time and the exact post/knowledge files changed by the revision workflow.

### Changed
- **Revision Model Visibility**: The revision workflow now prints the active Gemini model before applying ready review notes.
- **Regeneration Model Configuration**: The manual regeneration workflow now uses the same explicit `GEMINI_MODEL` fallback chain as the Telegram and Obsidian revision workflows.

---

## [1.19.8] — 2026-07-17

### Added
- **Phase 4.1 Review Enrichment**: Added lightweight review-driven research from DuckDuckGo and Wikipedia before applying Obsidian revision notes.
- **Enrichment Preservation Guardrails**: Added validation that blocks revision responses that overly truncate the original post or remove too many existing level-2 headings.

### Changed
- **Revision Prompt Strategy**: Reframed Phase 4 from whole-article rewriting toward minimal enrichment that preserves the existing article while adding review-requested context.

---

## [1.19.7] — 2026-07-17

### Fixed
- **Revision Full-Body Repair**: Added a repair attempt when Gemini returns a shortened revision response, preventing partial English/Korean bodies from being written and retrying with explicit full-body validation errors.

---

## [1.19.6] — 2026-07-17

### Fixed
- **Revision Target Lookup**: Allowed `_reviews/pending` notes to use a unique short `post_id` suffix, such as `0e0dace8`, instead of requiring the full generated post ID.

---

## [1.19.5] — 2026-07-17

### Fixed
- **Docs Rule Exemptions**: Excluded `_reviews/` and `_knowledge/` operational content changes from the README/CHANGELOG enforcement rule, so review-note inputs can be committed without unrelated documentation updates.

---

## [1.19.4] — 2026-07-17

### Fixed
- **Revision Example Safety**: Changed the pending example review note to `draft` and taught the revision workflow to ignore `example-*.md` files so sample notes cannot break production runs.

---

## [1.19.3] — 2026-07-17

### Changed
- **Workflow Display Name**: Added a leading emoji to the Obsidian review revision workflow for consistency with the other GitHub Actions entries.

---

## [1.19.2] — 2026-07-17

### Added
- **Post ID Backfill for Phase 4 Testing**: Hardened `scripts/backfill_post_ids.py` so legacy KO/EN post pairs sharing a `topic_id` receive the same stable `post_id`.
- **Backfill Tests**: Added coverage to verify bilingual pairs receive matching IDs and existing IDs are reused.

### Changed
- **Legacy Posts**: Backfilled missing `post_id` front matter across existing posts so older content can be targeted by Obsidian review revision notes.

---

## [1.19.1] — 2026-07-17

### Changed
- **Pre-Merge Branch Audit Rule**: Added a mandatory final branch audit to `CONTRIBUTING.md` so GitHub Actions generated post commits on feature branches are not missed before merge or branch deletion.

---

## [1.19.0] — 2026-07-17

### Added
- **Obsidian Review Revision Workflow (Phase 4)**: Added `scripts/revise_post.py` and `.github/workflows/revise.yml` to apply ready `_reviews/pending` notes to paired KO/EN posts.
- **Revision Tests**: Added parser and paired-post revision coverage for review notes.

### Changed
- **Review Templates**: Rewrote the review-note template and example in clearer English so generated review requests are easier to validate and automate.

---

## [1.18.0] — 2026-07-17

### Added
- **Obsidian Knowledge Notes (Phase 3)**: Added deterministic knowledge-note generation for each newly created paired blog post. The pipeline now writes topic, concept, and source notes under `_knowledge/` without spending another Gemini call.
- **Knowledge Note Tests**: Added coverage for topic/concept/source note generation and full pipeline integration.
- **Merged Branch Cleanup Rule**: Added a contribution rule requiring merged feature branches to be deleted from the remote repository immediately.

### Changed
- **Default Gemini Model**: Changed the default model from `gemini-2.5-flash` to `gemini-3.1-flash-lite`, matching the higher-quota model available in the current Google API dashboard.
- **Workflow Commit Scope**: `telegram_trigger.yml` now commits `_knowledge/` together with `_posts/` so Obsidian notes are persisted after generation.

### Removed
- **Private Stabilization Note**: Removed `OBSIDIAN_PHASE2_STABILIZATION_PLAN.md` from the public repository and added it to `.gitignore`.

### Roadmap
- **Model Fallback Pool**: Keep multi-model fallback as an outstanding item rather than implementing it now.

---

## [1.17.0] — 2026-07-17

### Changed
- **Gemini SDK Migration**: Replaced the deprecated `google-generativeai` dependency with the GA `google-genai` SDK and now initialize Gemini through `genai.Client`.
- **Runtime Compatibility Adapter**: Added a small adapter that preserves the existing `model.generate_content(...)` runtime contract, keeping quota-aware retries, usage accounting, and stage generation settings centralized in `gemini_runtime.py`.

### Testing
- **Updated Integration Fakes**: Updated pipeline integration tests to fake `google.genai` instead of the deprecated `google.generativeai` module.

---

## [1.16.2] — 2026-07-17

### Fixed
- **Feature Branch Pages Wait**: `telegram_trigger.yml` now waits for GitHub Pages deployment only on `main`. Feature-branch runs write a skipped Pages result instead of polling for a `deploy.yml` run that cannot exist because Pages auto-deploy is configured for `main` pushes only.

---

## [1.16.1] — 2026-07-16

### Fixed
- **Model Metadata Recovery**: Added deterministic local fallbacks that append a valid `json_meta` block when Gemini returns either the provisional English draft or the translated Korean article without metadata, preventing `missing json_meta block` validation failures without spending another API call.

### Added
- **Regression Coverage**: Added tests for metadata fallback, Research Writer recovery, and Korean Localizer recovery.
- **Gemini SDK Migration Plan**: Documented the move from deprecated `google.generativeai` to `google.genai` as a required stabilization step before Phase 3.

---

## [1.16.0] — 2026-07-16

### Added
- **Obsidian Integration Foundation**: Set up directories (`_knowledge`, `_ideas`, `_reviews`, `_templates`) and basic `.gitignore` / `_config.yml` rules for using the repository as an Obsidian Vault (Phase 1).
- **Safe Editing Rules**: Added strict AI file editing instructions to `CONTRIBUTING.md` to prevent accidental code deletion.
- **Branch/PR Workflow Rule**: Enforced a new rule in `CONTRIBUTING.md` requiring all features/fixes to be developed on feature branches and merged via Pull Request.

---

## [1.15.1] — 2026-07-15

### Fixed
- **Docs Rule False Positive on Korean Post Paths**: `check_docs.yml` now disables Git path quoting before analyzing changed files, so `_posts/ko/...` updates with non-ASCII filenames are correctly treated as post-only changes.
- **Line Ending Drift in Local Editors**: Added a repository-level `.gitattributes` so Markdown, workflow, script, and stylesheet files stay on LF and are less likely to show noisy status changes after opening them in Obsidian or Windows editors.

---

## [1.15.0] — 2026-07-14

### Added
- **Source Quality Score**: Calculates a deterministic `0-100` score from verified reference count, domain diversity, evidence volume, and authoritative domains without another Gemini call.
- **Operations Dashboard**: Publishes pipeline status, source quality, total usage, and per-stage token consumption to the GitHub Actions job summary.
- **Pages Completion Monitor**: Waits for the `deploy.yml` run associated with the generated post commit and records success, failure, timeout, or monitor errors.
- **Telegram Operations Commands**: `/status` reports recent generation and Pages workflow states, while `/help` documents the bot commands.

### Changed
- **Verified Completion Notification**: Telegram now reports the actual GitHub Pages deployment result instead of only reporting that deployment started.
- **Transparent Quota Reporting**: Completion messages show measured per-run and per-stage Gemini consumption and explicitly avoid estimating an exact remaining free-tier quota that the API does not expose.

---

## [1.14.0] — 2026-07-14

### Added
- **Failed-Run Checkpoints**: Research drafts, collected facts, validated English content, and Korean localization are cached after each completed stage and restored on a GitHub Actions rerun.
- **Duplicate Request Guard**: Generated posts store a normalized request fingerprint; already-published Telegram inputs are blocked before any Gemini call.
- **Checkpoint Workflow Cache**: GitHub Actions restores checkpoint data for subsequent attempts of the same workflow run and clears it after a successful push.

### Changed
- **Three-Call Pipeline**: Research planning and provisional English drafting now share `research_writer_en`, followed by `editor_en` and `localizer_ko`.
- **Dynamic Resume Budget**: A fresh run uses three successful Gemini calls, while a resumed run invokes only unfinished model stages.

---

## [1.13.0] — 2026-07-14

### Added
- **English Research Planner**: A compact first call resolves multilingual input into an English canonical topic and 2-4 English source queries.
- **English Source Coverage Gate**: Long-form calls start only after local checks find at least 500 fact characters and two verified references.
- **Korean Localizer Agent**: The validated English canonical article is localized into Korean without adding claims, statistics, citations, or URLs.
- **Phase 3 Pipeline Tests**: Offline integration coverage verifies the exact four-call order and confirms that sparse sources stop before long-form generation.

### Changed
- **Canonical Content Flow**: Replaced independent KO/EN writing and editing with `research_planner → writer_en → editor_en → localizer_ko`.
- **English-First Research**: Wikipedia and other research APIs now receive only planner-approved English queries.
- **Quality-Preserving Localization**: English validation completes before Korean localization begins, keeping both language versions factually aligned.

---

## [1.12.1] — 2026-07-14

### Fixed
- **Sparse Source Collection**: Long question-style inputs now produce compact and pairwise keyword queries. The existing Korean Writer call also returns an English source-search query, which expands references before English drafting and editing without adding Gemini calls.
- **False Source Data**: Placeholder responses such as `No search results` and `No Wikipedia pages found` are no longer passed to Writer and Editor agents as reference facts.
- **Editor Over-Compression Prevention**: The Editor contract now explicitly preserves minimum length and section structure; invalid reviewed content remains blocked rather than falling back to an unreviewed draft.
- **Actionable Validation Notifications**: Telegram failure messages now include the exact local validation reason recorded in the structured pipeline result.

### Changed
- **Editor Output Contract**: The review prompt explicitly preserves at least two `##` headings and the Korean/English publication safety floors without adding a repair call.

---

## [1.12.0] — 2026-07-14

### Added
- **Local Content Quality Layer**: Added deterministic topic classification, source-title/URL extraction, reference insertion, metadata checks, Markdown fence checks, minimum content floors, and structural validation without additional Gemini requests.
- **Four-Call Budget Guard**: The standard pipeline now verifies that exactly four Gemini calls succeeded before writing posts.
- **Stage-Specific Generation Settings**: Draft stages retain creative temperature while source-based editing uses a lower temperature and bounded output limits.
- **Localized Wikipedia Search**: Korean queries now use Korean Wikipedia while other queries continue to use English Wikipedia.
- **Pipeline Budget Tests**: Added offline tests that reject reintroduction of classifier, search-enrichment, or standalone verifier Gemini stages, plus a fake-service integration test that generates both post files with exactly four successful calls.

### Changed
- **Gemini Calls Reduced by 50%**: Normal KO+EN generation now uses four successful calls instead of eight: two drafts and two combined fact-check/edit calls.
- **Local Classification**: Replaced the Gemini classifier request with deterministic bilingual topic rules and local keyword extraction.
- **Direct Search Facts**: Removed the Gemini search-enrichment request and pass collected source data directly to both writing and review stages.
- **Combined Verification and Editing**: Merged the separate per-language FactVerifier and Editor calls into one source-grounded review call per language.
- **Deterministic References**: Source links are extracted from collected API results and appended locally so the editor cannot invent citation URLs.

### Removed
- **Standalone FactVerifierAgent**: Removed the two-call verification pass and its unsafe behavior that treated malformed verification JSON as a successful fact check.

---

## [1.11.1] — 2026-07-14

### Added
- **Gemini Usage Tracking**: Added a shared runtime that records API attempts and response token usage for every pipeline stage.
- **Structured Pipeline Result**: Added `.pipeline_result.json` handoff data so the final notification step can report the exact failed stage, error category, retry metadata, and per-run usage.
- **Offline Runtime Tests**: Added unit coverage for daily and per-minute quota classification, daily-quota no-retry behavior, transient retries, token aggregation, structured results, and Telegram quota wording. The Telegram workflow runs these tests before making any Gemini request.

### Changed
- **Quota-Aware Retry Policy**: Daily request quota (`RPD`) exhaustion now stops immediately, while `RPM`, `TPM`, timeouts, and temporary service failures retain bounded retries.
- **Actionable Telegram Errors**: Replaced the generic repeated-call failure with distinct messages for daily quota exhaustion, per-minute request/token limits, authentication errors, invalid requests, timeouts, and service outages.
- **Accurate Completion Wording**: The generation workflow now reports that content was saved and Pages deployment started instead of claiming that the separate Pages workflow has already completed.

---

## [1.11.0] — 2026-07-11

### Added
- **Global Client-Side Search Engine**: Implemented an elegant search bar in the header navigation that filters post titles, excerpts, and tags in real-time.
  - **Auto-expansion**: Search input expands smoothly from 130px to 190px on focus.
  - **Unified Filtering**: Integrates with language tags so users can filter by language and search query simultaneously.
  - **Smart Detail-Page Redirects**: If a user initiates a search while on a post detail page, pressing Enter seamlessly redirects them to the home page with a `?q=query` parameter, which is auto-parsed and filtered on load.
  - **No-Results Empty State**: Dynamic, stylized placeholder overlay indicating when no posts match search criteria.

---

## [1.10.1] — 2026-07-11

### Fixed
- **Post Metadata Parsing Bug**: Resolved an issue where the JSON metadata block generated by `WriterAgent` was not removed from the final markdown file body if it was wrapped in a raw ````json` block instead of ````json_meta`.
  - Updated the regex replacement inside `FileWriterAgent` to strip both ````json_meta` and ````json` wrapped metadata blocks.
  - Manually cleaned up the unremoved raw JSON metadata block from the top of the English Solar System post.

---

## [1.10.0] — 2026-07-11

### Added
- **Deep Content Expansion**: Preserved the content quality upgrades.
  - Target writing length constraints expanded to KOR `3000-5000 characters` and ENG `1200-2000 words`.
  - Mandatory structural sections: Step-by-step logic/architecture explanations, code/config snippets, comparison markdown tables, and historical context are generated for all new posts.
  - ScholarlySearchAgent enriches facts to a larger pool of `1500-3000 characters`.
- **API Cooldown Delays**: Maintained rate limit mitigations of 5s on Gemini calls and 10s between posts in batch scripts to protect the Free Tier from 429 errors.

### Removed
- **Automated Cover Image Generation (Reversion to v1.8.1 UI)**: Reverted the experimental image generation and template changes to restore clean text-based layouts.
  - Deleted `.post-card-image` and `.post-cover-image` layouts from `post.html`, `home.html`, `trivia.md`, `engineer.md`, and `custom.css`.
  - Removed image creation calls and front matter image properties from the python agents pipeline.

---

## [1.9.2] — 2026-07-11

### Fixed
- **Regeneration Rate-Limit & Git Crash Mitigation**: Corrected workflow execution issues on large batch generations.
  - Added a global `time.sleep(5)` delay before all Gemini calls in `call_gemini` and a `time.sleep(10)` delay between topics in `regenerate_posts.py` to prevent hitting the 15 RPM Free Tier rate limit.
  - Made the git staging step in `regenerate.yml` robust to avoid crashing with `fatal: pathspec` when `assets/images/` is missing on the filesystem.
  - Configured `regenerate_posts.py` to propagate subprocess failures to the CI runner by checking exit codes, ensuring the action fails correctly on error.

---

## [1.9.1] — 2026-07-11

### Added
- **One-Click Post Regeneration Workflow**: Created a manual trigger system to retroactively upgrade all existing posts to `v1.9.0` depth and image styling.
  - **`scripts/regenerate_posts.py`**: A python script that clears all old markdown files in `_posts/` and loops through the original topics (Adobe Architecture, Solar System, CrossFit) to run the upgraded multi-agent generation pipeline.
  - **`.github/workflows/regenerate.yml`**: A GitHub Actions workflow triggered via `workflow_dispatch` (manual button in GitHub UI) to execute the regeneration script in the secure GitHub environment and commit updated posts and images.

---

## [1.9.0] — 2026-07-11

### Added
- **Automated Cover Image Generation**: Implemented a dynamic image generation pipeline inside `FileWriterAgent`.
  - **Google Imagen 3 API**: Automatically attempts to generate 16:9 featured cover images for every post topic via `Imagen 3`.
  - **Topic-Aware Style Settings**: Generates photorealistic scenes for `trivia` mode (Style B) and minimalist tech illustrations / 3D renderings for `engineer` mode (Style A).
  - **Stock Fallback**: Gracefully falls back to Unsplash stock photo redirect search if Imagen 3 quota/billing errors occur, saving local cover files to `assets/images/`.
  - **UI Template Upgrades**: Refactored `home.html`, `trivia.md`, `engineer.md` post cards, and `post.html` layout templates to display the cover images with smooth hover scale zoom animations.
- **Deep Content Expansion**: Drastically increased word counts and content depth constraints.
  - **KOR posts**: Bumped target length to `3000-5000 characters` (previously 700-1200 chars).
  - **ENG posts**: Bumped target length to `1200-2000 words` (previously 600-1000 words).
  - **Facts Enrichment**: Injected larger fact pools (`1500-3000 characters`) into ScholarlySearchAgent summaries.
  - **Mandatory Sections**: Directs the WriterAgent to compile step-by-step logic/architecture explanations, code/config snippets, feature comparison tables, and historical context.

---

## [1.8.1] — 2026-07-11

### Fixed
- **ScholarlySearchAgent NameError**: Fixed a bug where `SearchAgent` was not fully replaced during previous refactoring, causing a runtime `NameError` crash when the pipeline initialized `ScholarlySearchAgent()`.
- **Pre-commit Checklist Verification**: Updated [CONTRIBUTING.md](CONTRIBUTING.md) to add a mandatory verification checklist requiring syntax check compilation tests (`python -m py_compile`) and clean code replacements review before staging and pushing.

---

## [1.8.0] — 2026-07-11

### Added
- **Scholarly & Literature Search Integration**: Re-routed data collection to query academic and authoritative reference sources based on topic mode.
  - **`trivia` mode**: Queries Google Books API and Wikipedia Search API alongside standard web summaries.
  - **`engineer` mode**: Queries arXiv API, Crossref API, and customized IETF/standards vendor whitepapers via search operators.
- **`FactVerifierAgent` (NEW)**: Built a specialized scientific verification agent that extracts factual assertions from drafts, cross-references them against the collected scholarly references, and generates validation reports with citation mappings.
- **Reference Generation**: Refactored the `EditorAgent` to consume verification reports and automatically append a formatted, hyperlinked "References" or "참고자료" section at the bottom of the blog posts.
- **6-Agent Pipeline Flow**: Updated `scripts/multi_agent.py` to route inputs through: Classifier → ScholarlySearch → Writer → FactVerifier → Editor → FileWriter.

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
