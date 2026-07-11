# 📋 Contributing Guide

## 🔴 Required Rule: Documentation Must Be Updated With Every Change

> **Every code or configuration change MUST also update `README.md` and `CHANGELOG.md`.**  
> GitHub Actions (`check_docs.yml`) automatically enforces this. Violations will fail the build.

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
