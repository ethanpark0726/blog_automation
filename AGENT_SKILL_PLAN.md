# Blog automation rebuild: agent and skill foundation

Status: Step 1 foundation complete. Step 2 corpus and proposed contract prepared.
As of 2026-10-17, paid search and the full Revision rebuild are deferred in favor
of manual Korean enrichment plus existing translation sync. Runtime implementation
has not started. Follow `MANUAL_CONTENT_WORKFLOW.md` for the current operating path.

## Goal and scope

Improve article usefulness and make Obsidian Revision Workflow reliable while
preserving existing posts and manual edits. Use only free research sources; do not
enable paid search or automatic paid fallback. Start with explicit roles, reusable
skills, and observable acceptance criteria. Replace failing modules incrementally
on feature branches; keep the working Telegram/Jekyll publication path available.

## Development team

The coordinator, implementer, verifier, and reviewer follow `AGENTS.md`.
Parallelize independent analysis and verification; serialize edits to shared files.
The coordinator is responsible for the final integrated result.

Repository-local skills live under `.agents/skills/`. Existing third-party skills
remain tracked by `skills-lock.json`. The two local authored skills are not external
packages and do not receive fabricated source hashes or lockfile entries.

| Skill | Purpose | Availability |
|---|---|---|
| domain-modeling / codebase-design | Domain terms and module responsibilities | Existing project skills |
| tdd / diagnosing-bugs | Reproducible failures and behavioral regression tests | Existing project skills |
| code-review | Independent specification and standards review | Existing project skill |
| ponytail / ponytail-review | Scope and complexity review | Environment plugin; not guaranteed on other machines |
| blog-pipeline-evaluation | Generation/revision acceptance and failure scenarios | New local skill |
| blog-research-editorial | Evidence, editorial, and translation criteria | New local skill |

## Runtime roles to design

| Role | Input | Output | When needed |
|---|---|---|---|
| Researcher | Topic or factual review request | Relevant excerpts, URLs, claim-to-source links, gaps | New article or factual enrichment |
| Writer/reviser | Evidence, source article, permitted edit scope | Article or candidate changes | Creation and revision |
| Quality reviewer | Request, evidence, original and candidate | Specific defects and release decision | Before saving/publishing |
| Translator | Validated source and target-language requirements | Meaning-aligned target article | Bilingual creation or explicit synchronization |

These are responsibilities, not a commitment to four API calls. Search, file I/O,
scope enforcement, deterministic validation, and publication remain ordinary code.
Development skills are not automatically loaded by Gemini in GitHub Actions.
Runtime rules will need explicit prompts, structured outputs, and code checks.

## Implementation sequence and gates

- [x] Define development roles, ownership, handoffs, and authorization rules.
- [x] Author two project-specific skills.
- [x] Independently review the foundation documents.
- [x] Preserve a real Post Pair snapshot and documented historical failures in `tests/fixtures/revision/` (raw provider payloads remain unavailable).
- [x] Draft `REVISION_CONTRACT.md` for input/output, preservation, testing seams, and API limits.
- [x] Document manual KO enrichment and targeted translation synchronization.
- [x] Run the existing offline translation-sync source-preservation test.
- [ ] Validate one manually enriched post with the existing free-tier sync flow (not run automatically).
- [ ] Deferred: agree on broader generation/revision contracts and bounded API budgets.
- [ ] Deferred: replace the Revision Workflow core, preserving untouched content and metadata.
- [ ] Deferred: share research collection between generation and revision; use free sources only.
- [ ] Evaluate article quality against representative topics and original outputs.
- [ ] Verify Telegram, Obsidian, bilingual sync, and publication together before rollout.

Before runtime implementation, review the contracts and acceptance cases with the
user. Foundation approval does not select a paid search provider, authorize live
Gemini spending, or authorize publication. Request those decisions only when needed.

## Acceptance cases to prepare next

| Case | Expected observation |
|---|---|
| KO style edit and introduction deletion | Requested text removed, surrounding facts preserved, EN unchanged |
| Factual enrichment | Adds relevant sourced explanation; retains unrequested original content |
| Already-applied deletion | Explicit no-op result without inventing replacement content |
| KO-to-EN sync after manual edit | Source unchanged; target matches source facts, structure, numbers |
| Incorrect language or nonexistent block in model response | Original files preserved; actionable diagnostic |
| Model output truncated or invalid | No source overwrite; bounded failure with response metadata |
| Interruption and rerun | Review retained until success; no duplicate enrichment |
| Below publication safety criteria | Draft preserved with reason; no false published notification |
| Sufficient but shorter article | Length warnings distinguished from factual/structural defects |

For each case store original Post Pair, Review Note, raw model response when
available, and semantic assertions. Redact secrets and personal data. Do not alter
pending operational review notes to turn them into fixtures.

## Quality and completion

Do not optimize the existing numerical source score as the goal. Evaluate relevance,
direct support for major claims, uncertainty, readability, and review compliance.
Use source counts and domain counts as diagnostics. A factual claim is not verified
merely because a URL or an authoritative domain appears in the reference list.

Completion requires independent verification evidence, a reviewed PR, and a final
remote-branch audit that includes posts generated during testing. Runtime changes
are complete only after the corresponding acceptance cases pass.
