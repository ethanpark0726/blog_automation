# 📋 Contributing Guide

## 🔴 Required Rule: Documentation Must Be Updated With Every Change

> **Every code or configuration change MUST also update `README.md` and `CHANGELOG.md`.**  
> GitHub Actions (`check_docs.yml`) automatically enforces this. Violations will fail the build.

---

## 🌿 Required Rule: Branch and Pull Request Workflow

> **New features and fixes MUST be developed in a separate feature branch.**  
> Never commit directly to the `main` branch. After testing is complete and validated, create a Pull Request (PR) and merge it into `main`.
> After a feature branch is merged, delete the merged branch from the remote repository immediately.

### Mandatory pre-merge branch audit

Feature branches can receive additional commits from GitHub Actions after manual testing, especially Telegram-generated posts and Obsidian `_knowledge/` notes. Before merging or deleting any feature branch, verify the branch's final remote HEAD and all commits that are not yet in `main`.

Required checks:

```bash
git fetch origin
git log --oneline main..origin/<feature-branch>
git diff --name-only main..origin/<feature-branch>
```

Do not merge or delete the feature branch until:

1. The log output includes every expected implementation commit and every GitHub Actions generated-post commit.
2. The diff output includes every expected `_posts/`, `_knowledge/`, workflow, script, test, README, and CHANGELOG change.
3. If GitHub Actions pushed a generated post to the feature branch, that generated-post commit is included in the merge target.
4. After merging, `git log --oneline origin/main..origin/<feature-branch>` returns no commits that still need to be preserved.

If a feature branch was deleted too early, recover the missing commit from GitHub Actions logs before continuing:

```bash
gh run view <run-id> --log
git fetch origin <missing-commit-sha>
git merge --ff-only FETCH_HEAD
git push origin main
```

---

## Versioning (Semantic Versioning)

```
MAJOR.MINOR.PATCH
  │     │     └── Bug fixes, doc-only updates         e.g. 1.2.0 → 1.2.1
  │     └──────── New features (backward compatible)  e.g. 1.2.1 → 1.3.0
  └────────────── Breaking / major changes            e.g. 1.3.0 → 2.0.0
```

---

## Change Checklist

### 1. Update CHANGELOG.md

Add a new version entry at the top of the file:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- New features or files

### Changed
- Modifications to existing behavior

### Fixed
- Bug fixes

### Removed
- Deleted features or files
```

### 2. Update README.md

① Update the version badge at the top:
```markdown
[![Version](https://img.shields.io/badge/Version-X.Y.Z-purple)](CHANGELOG.md)
```

② Update the **"Current Version"** section with a concise summary:
```markdown
## 📊 Current Version

**vX.Y.Z** — One-line summary of the changes/features
```

③ Check and update the **"Roadmap"** section:
- Mark completed milestones/tasks as done.
- Shift upcoming version targets/features if necessary to maintain chronological accuracy.

---

## Exceptions (Auto-skipped by CI)

The following commits do **not** require documentation updates:
- Changes only to `_posts/ko/` or `_posts/en/` (auto-generated Telegram bot posts)

---

## Commit Message Convention

```
feat:     New feature added
fix:      Bug fix
docs:     Documentation only
config:   Configuration change
refactor: Code refactor (no behavior change)
```

---

## 🛡️ Verification Checklist Before Pushing

Before committing and pushing any code changes, always perform these validation checks:
1. **Syntax & Compilation Check**:
   - Run `python -m py_compile scripts/multi_agent.py` to ensure that python scripts have no syntax errors or unresolved symbols.
2. **Verify Tool Application**:
   - Check if all code replacement chunks applied completely and cleanly without warnings.
3. **Markdown Conformity**:
   - Make sure all newly added Jekyll front matter variables and page formatting guidelines are followed.

---

## 🚫 Safe File Editing Rules (CRITICAL)

To prevent accidental data loss or code corruption during AI modifications:
1. **Never guess the content**: Always view the file or `grep` the exact lines before attempting a replacement.
2. **Minimal scoping**: Match the smallest, most unique block of text possible. Do NOT match entire large classes or functions if you only need to change one line.
3. **Verify post-edit**: Immediately run `git diff` after making a file modification to ensure no extraneous code was duplicated or deleted.
4. **Use `multi_replace_file_content`** when making changes in multiple separate places in the same file to prevent overlapping context issues.
