# Revision failure corpus

Prepared 2026-10-16. These files are inert test inputs, outside `_reviews/pending`.
Do not run the production workflow against the repository to exercise them.

## Provenance

`octane/ko.md` and `octane/en.md` are complete copies of the tracked Post Pair at
commit `7d1aa8b`, with line endings normalized to LF and a final newline added.
Content comparisons ignore final-newline differences. Sources:

- `_posts/ko/2026-07-12-자동차-옥탄가-주유소-프리미엄-등급이-다른-이유를-파헤쳐봐요.md`
- `_posts/en/2026-07-12-octane-unmasked-understanding-your-fuels-stress-re.md`

These historical snapshots contain the requested introduction. They are not proven
exact inputs of the failed runs. `octane/review.md` reconstructs the requested KO-only edits from the
conversation; it is not a downloaded Actions artifact. Confirm the deletion quote
against the snapshot before testing literal removal.

## Historical observations

The following excerpts were supplied in the prior debugging conversation. Full
provider responses and complete historical execution inputs are unavailable.
Do not invent a provider response and label it a captured response.

| Case | Observation | Context / limitation |
|---|---|---|
| octane-language-expansion | `Local validation failed for en: English body is below the 450-word safety floor` | Run 31145403011; bilingual review at that time, so not proof of a scope violation |
| octane-meta-as-action | `Operations for ko must cover ['R1', 'R2', 'R3']; received ['R2', 'R3']` | Run 31145873865; historical note included a KO-only scope instruction as a bullet |
| crossfit-section-target | `replace_block requires a block target for en: section_1` | User-supplied traceback; raw JSON unavailable |
| solar-length | `revised English body is too short relative to the original; Phase 4.1 requires enrichment, not replacement` | User-supplied traceback; not a complete response replay |

## Acceptance assertions for the first vertical slice

Use the public revision entry point and temporary filesystem; replace only network
providers. Proposed interface and outcomes are in `REVISION_CONTRACT.md`.

1. The KO-only case never modifies EN bytes or either language's front matter.
2. The requested greeting is removed when present; useful body facts remain.
3. Korean register is consistently 해라체. Human review or a recorded reviewer
   judgment is needed for semantic quality; an ending regex alone is insufficient.
4. An invalid/truncated response or unresolved request preserves both originals
   and the Ready Review Note.
5. The pre-existing EN safety-floor issue does not block a KO-only edit because EN
   is not an edit target. Target-language safety policy still applies.

## Gaps before claiming regression coverage

- No new automated behavior tests have been written or run for this corpus yet.
- Provider payloads must be captured in an authorized test or explicitly marked
  synthetic for malformed-response tests.
- Translation-sync and interruption/retry cases need their own inputs.
- These small articles cannot substitute for a representative enrichment corpus.
