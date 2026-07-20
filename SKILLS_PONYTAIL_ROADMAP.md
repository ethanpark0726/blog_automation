# Skills and Ponytail Integration Roadmap

This roadmap explains how `mattpocock/skills` and `ponytail` can fit into the `blog_automation` project.

## Why this matters

The blog automation project is no longer a simple script. It now has:

- Telegram-triggered post generation
- GitHub Actions orchestration
- Gemini quota and usage handling
- Obsidian knowledge notes
- Review-note based post revision
- Cloudflare Worker command routing

As the project grows, the main risk is not missing capability. The risk is accidental complexity: too many workflows, too many scripts, and unclear rules for when the AI should ask, plan, test, or stop.

`mattpocock/skills` and `ponytail` solve different parts of that problem.

## Integration value

| Tool | Value for this project | Best use |
|---|---|---|
| `mattpocock/skills` | Gives AI work repeatable engineering workflows instead of ad-hoc prompting | Planning, diagnosis, TDD, architecture review, code review |
| `ponytail` | Pushes the AI toward the smallest working change and away from over-engineering | Feature implementation, bug fixes, cleanup, PR review |

## Recommended skills to start with

Do not install everything at once. Start with a small set that matches this repository's actual workflow.

| Skill | Why it fits `blog_automation` |
|---|---|
| `setup-matt-pocock-skills` | Defines repo-specific conventions once so later skills do not guess |
| `diagnose` / `diagnosing-bugs` | Useful for GitHub Actions failures, Gemini quota issues, and pipeline regressions |
| `tdd` | Fits scripts like `revise_post.py`, `notify_revision.py`, and CI guard scripts |
| `implement` | Useful after a feature plan is already agreed |
| `code-review` / `review` | Good before merging workflow or automation changes |
| `codebase-design` | Helps keep scripts, workflows, and Worker commands from turning into a ball of mud |
| `obsidian-vault` | Directly relevant to the `_knowledge`, `_reviews`, and Obsidian Graph View strategy |

## Phase 1 — Skills evaluation, no production behavior change

Goal: understand and select the skills before wiring them into the working process.

Checklist:

- [ ] Review `mattpocock/skills` installation options.
- [ ] Pick the minimum initial skill set.
- [ ] Decide whether repo-local config should live under `docs/agents/`, `.agents/`, or another folder.
- [ ] Do not change the blog generation pipeline yet.

Deliverable:

- A small integration decision document describing selected skills and rejected skills.

## Phase 2 — Repository context for skills

Goal: make the skills understand this project without repeatedly re-explaining it.

Checklist:

- [ ] Create a repo context document, such as `docs/agents/CONTEXT.md`.
- [ ] Document core domain terms:
  - blog generation pipeline
  - paired KO/EN posts
  - Obsidian knowledge notes
  - review revision workflow
  - Gemini quota handling
  - Cloudflare Worker bridge
- [ ] Document safety rules:
  - never mutate `_posts` without validation
  - never skip README/CHANGELOG for code/config changes
  - always audit feature branches before merge if Actions generated commits
  - keep generated posts, knowledge notes, and review notes operationally separate

Deliverable:

- Repo context that AI agents can read before planning or implementing.

## Phase 3 — Skill-assisted development workflow

Goal: use skills as a repeatable operating model.

Suggested flow:

1. `diagnose` for failures.
2. `to-spec` or planning for new features.
3. `tdd` for script changes.
4. `implement` only after the feature scope is agreed.
5. `code-review` before PR merge.

Deliverable:

- A documented development loop for future blog automation changes.

## Phase 4 — Ponytail pilot

Goal: add restraint before implementation, not after the codebase bloats.

Use Ponytail first in review mode, not as a blanket rule.

Checklist:

- [ ] Run Ponytail-style review on one small future feature.
- [ ] Ask it to identify:
  - unnecessary files
  - duplicate helpers
  - over-generalized abstractions
  - dependencies that can be avoided
  - logic that can be replaced by an existing script or standard library feature
- [ ] Keep the existing validation/test requirements. Ponytail should reduce code, not reduce safety.

Deliverable:

- A before/after PR review note showing what code was avoided or simplified.

## Phase 5 — Ponytail as a PR gate

Goal: make "least code that works" part of the project's review habit.

Checklist:

- [ ] Add an optional local review checklist:
  - Could this be solved by existing code?
  - Could this be smaller?
  - Is a new file actually needed?
  - Is a new dependency actually needed?
  - Is there at least one runnable check for non-trivial logic?
- [ ] Consider a non-blocking CI job or PR checklist item before making it mandatory.
- [ ] Keep exceptions explicit for safety, validation, auth, quota handling, and content preservation.

Deliverable:

- Ponytail checklist added to `CONTRIBUTING.md` or PR template after one successful pilot.

## Recommended decision

Start with skills first, then Ponytail.

Reason:

- Skills help define the workflow and shared language.
- Ponytail is most valuable once the workflow exists, because it can then challenge implementation size without fighting the project direction.

Suggested first implementation after approval:

1. Add repo context docs for skills.
2. Add a lightweight AI workflow section to `CONTRIBUTING.md`.
3. Pilot Ponytail on the next small feature or bug fix.

