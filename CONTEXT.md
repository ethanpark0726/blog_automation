# Blog Automation Context

This context defines the domain language for the Telegram-triggered multilingual blog automation system. Use these terms when discussing generation, publication, Obsidian knowledge work, and review-driven revision.

## Language

**Blog Generation Request**:
A user request, usually sent through Telegram, to create a new bilingual article.
_Avoid_: prompt, query, input

**Post Pair**:
A Korean post and an English post that represent the same article.
_Avoid_: duplicate posts, translation files

**Canonical English Article**:
The English article treated as the source of truth before Korean localization.
_Avoid_: English draft, original post

**Korean Localization**:
The Korean article derived from the canonical English article while preserving meaning and structure.
_Avoid_: Korean rewrite, translation only

**Review Note**:
An Obsidian-authored markdown request that asks the revision workflow to enrich or correct an existing post pair.
_Avoid_: feedback file, edit request

**Ready Review Note**:
A review note that has been marked as ready for automated processing.
_Avoid_: pending task

**Completed Review Note**:
A review note that has already been processed by the revision workflow.
_Avoid_: archived request

**Knowledge Note**:
An Obsidian-oriented note that connects posts, concepts, and sources for graph-based knowledge exploration.
_Avoid_: blog post, draft note

**Post ID**:
A stable identifier shared by both posts in a post pair.
_Avoid_: slug, filename

**Topic ID**:
A grouping identifier used to connect related generated content and knowledge notes.
_Avoid_: category, tag

**Revision Workflow**:
The workflow that reads ready review notes and updates existing post pairs.
_Avoid_: regeneration workflow, rewrite workflow

**Regeneration Workflow**:
The workflow for reprocessing existing posts outside the review-note process.
_Avoid_: revision workflow

**Operational Content**:
Generated or user-authored content that is part of blog operations rather than project documentation.
_Avoid_: docs, config

**Version Metadata**:
The public release metadata that must stay synchronized across the README version badge, README current version, README roadmap, and latest changelog entry.
_Avoid_: version text, badge only

