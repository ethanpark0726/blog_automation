# Revision Workflow contract proposal

Status: deferred proposal, not implemented. As of 2026-10-17 the user prefers free
generation, manual enrichment, and existing translation synchronization; see
`MANUAL_CONTENT_WORKFLOW.md`. Keep this document as future design context.
Existing `scripts/revise_post.py` remains unchanged.

## Public interface and test seams

Keep the workflow-facing Python entry point `apply_revision(review, model, tracker)`
while redesigning its internals. Preserve its successful changed-path return for
compatibility until callers migrate together. Workflow processing owns review
completion; model or research helpers must not delete review files.

Test via parsing a real Review Note and invoking the public revision entry point
against a temporary repository. Replace Gemini and retrieval at their external
provider interfaces; do not mock plan creation, validation, or edit application.
Observe output files, review retention, structured outcome, and usage. A second
integration seam is the workflow coordinator that finalizes content and deletes a
processed note. Confirm these seams before writing the first behavioral test.

## Input

| Field | Contract |
|---|---|
| target_post_id | Resolve exactly one Post Pair; ambiguous or missing IDs stop before model calls |
| scope | `ko`, `en`, or `bilingual`; code derives allowed languages and rejects expansion |
| status | Only `ready` is processed; templates and index notes remain excluded |
| mode | `revision` or `sync_translation`; unsupported values are rejected before calls |
| source_lang / target_lang | For sync, distinct supported languages; source is immutable |
| instructions | Preserve complete bullet content, including indented continuation text; metadata is not an editorial action |
| original Post Pair | Raw front matter and body plus content hash; recheck hash before saving |

Ordinary revision uses scope. Translation sync uses source/target language metadata;
scope must include the target, and its source remains read-only even if bilingual.
Existing notes need compatibility checks before changing parser defaults.

## Internal behavior to implement

1. Validate the request, resolve posts, and snapshot inputs before network calls.
2. Derive tasks from the review; distinguish editorial work from scope/context.
   Each task has an outcome: applied, already satisfied, ambiguous, or unresolved.
3. Retrieve evidence only for new factual content. Style, deletion, and translation
   do not trigger research merely because an article mentions a factual topic.
4. Produce candidate changes to selected source sections. Preserve untouched
   sections in code. Use stable original identifiers; model-produced block indexes
   are not trusted executable commands. The exact candidate schema is the next
   implementation design decision, not a promise to retain the old operation DSL.
5. Validate request compliance, structure, source support, and language scope.
   Missing action operations must not be silently guessed and claimed complete.
6. Prepare the whole result including Knowledge Notes before applying replacements.
   Keep originals/review if validation fails. For interrupted multi-file saves,
   use staged replacements and a recoverable transaction record; design and test
   recovery before claiming multi-file atomicity. Separate Git publication.

## Outcomes and preservation

| Outcome | Files / review | Meaning |
|---|---|---|
| applied | Save validated requested changes; coordinator removes review after successful finalization | Every requested task resolved |
| already_satisfied | No content change; explicit successful no-op; coordinator may remove review after recording outcome | All requests already satisfied, not merely missing model operations |
| needs_clarification | No source changes; retain review | Ambiguous or unresolved instruction |
| rejected | No source changes; retain review | Invalid candidate, language expansion, unsupported response |
| failed | Preserve/recover originals; retain review; diagnostic and usage | Provider, filesystem, or processing failure |

Add structured outcome reporting without silently changing existing callers' list
contract. Migrate workflow and Telegram result handling in the same vertical slice
that introduces a new result type. Do not report published from revision success;
Pages deployment confirmation remains a separate outcome.

## Quality policy

- Requested deletion can reduce length; do not impose a relative growth requirement.
- Enrichment must add the requested explanation and retain unrequested original
  information. Do not accept a shorter generic rewrite because it passes word count.
- Validate edited languages; untouched EN length must not block a KO-only change.
- Target-language structure and publication safety criteria still apply. If a
  candidate falls below them, preserve it as a diagnostic candidate outside the
  published post paths and retain the review; do not silently publish or discard it.
- Compare translation claims, numbers, units, and qualifications against the source.
- Preserve filenames, Post ID, and front matter unless the request explicitly asks
  for a supported metadata change. Title sync is not implicit.

## Proposed API limits (not authorization to call)

Count every provider attempt, including retries, against the per-review cap.
Propose at most 4 attempts for KO-only revision or translation sync, and 6 for a
bilingual revision. At most one repair attempt across the whole review, within that
cap; retry only errors classified as transient. Stop on exhausted daily quota.
Record per-stage input/output tokens and finish reason. No live calls in Step 2.
Actual token ceilings depend on article size and provider configuration and must be
set before live testing; these caps do not guarantee a monetary or token budget.

## First implementation slice after approval

The octane KO-only style/deletion case in `tests/fixtures/revision/` is the first
case. Verify EN and metadata preservation and failure retention at the public seam.
Then add one malformed provider response case. Extend to enrichment, sync, and
interruption only after the preceding behavior works. Do not rewrite the entire
workflow at once or treat synthetic response tests as live-provider validation.
