---
name: blog-pipeline-evaluation
description: Evaluate this repository's generation, Obsidian revision, and translation-sync behavior using real failures and observable acceptance criteria. Use for pipeline regression tests or release-readiness checks.
---

# Blog pipeline evaluation

Read repository `CONTEXT.md` for terminology and `AGENTS.md` for ownership and
handoff rules. Inspect the actual workflow entry point and affected callers before
choosing tests. Do not assume proposed rebuild behavior exists in the current code.

## Build a useful case

Start from a real Review Note, original Post Pair, and failing response/log when
available. Copy only necessary artifacts to temporary test data; redact credentials
and personal data. Do not consume or rewrite an operational pending review.

Express expected behavior as observable properties: language scope, requested
deletion, added explanation, preserved content, source-language immutability,
metadata preservation, and file state on failure. Do not require one exact wording
for a free translation or prose improvement. Assert exact text only where the user
requested a literal change or a structural contract requires it.

For a bug, demonstrate failure before changing production code. Test through the
same callable interface used by the workflow and include the parser/application
path; mocking the entire revision function does not verify revision behavior.
Replay real provider payloads at the provider seam, alongside malformed/truncated
output and wrong-language/invalid-target cases relevant to the change.

## Preserve operational behavior

- Verify unrequested language bodies and front matter remain unchanged.
- Verify failed candidate validation leaves originals and Ready Review Note intact.
- Verify interruption/retry does not duplicate edits or delete unprocessed reviews.
- Distinguish a no-op, unresolved request, preserved draft, and published result.
- For deletion requests, test the intended deletion; do not demand that the article
  become longer. For enrichment, check meaningful additions and retained context.
- Test publication notification against the actual result, not merely a successful
  model response or successful Git commit.

## Evidence and budgets

Run deterministic regression tests first. Report which provider and filesystem
effects were simulated. Offline success is not evidence of live model reliability.
Before a live test, establish the authorized topic/review, call or token cap, and
whether saving/publishing is permitted. Stop at the cap; preserve the failing
response metadata for offline diagnosis instead of repeated blind retries.

Return a compact matrix of scenario, expected behavior, observed result, and
offline/live status. Separate blocking defects from content-quality concerns and
untested cases. Never claim independent verification if you implemented the same
change without an independent pass.
