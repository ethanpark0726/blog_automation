# Obsidian Phase 2 Stabilization Plan

Date: 2026-07-16
Branch: `feature/phase2-post-id`

This document tracks the stabilization work required before moving from Obsidian Phase 2 to Phase 3.

## Current Status

Phase 1 is considered complete:

- Obsidian folder structure exists.
- `_knowledge`, `_ideas`, `_reviews`, and `_templates` are present.
- Basic review and concept note templates are present.
- The repository can be opened and used as an Obsidian Vault.

Phase 2 is implemented but must be stabilized before Phase 3:

- Post pairing fields must remain stable across KO and EN posts.
- The existing Telegram blog generation pipeline must still pass.
- Feature-branch testing should be done by manually running GitHub Actions on `feature/phase2-post-id`.
- Telegram normally dispatches the workflow on `main`, so it is not the best way to test this feature branch.

## Bug Found During Phase 2 Testing

Failure:

```text
Local validation failed for ko: missing json_meta block
```

Cause:

- The Korean localization Gemini call sometimes returns a valid Korean article body but omits the final `json_meta` block.
- The validator correctly blocks publication because `json_meta` is required by the downstream file writer.
- This is a model-output contract failure, not an Obsidian folder-structure issue.

Fix:

- Add a deterministic local fallback after `localizer_ko`.
- If the localized content has no `json_meta` block, append one using the original Korean topic and local classification keywords.
- Do not make another Gemini call for this repair.
- Keep validation strict after the fallback.

Completion gate:

- `tests.test_content_quality` passes.
- `tests.test_pipeline_integration` passes.
- A manual GitHub Actions run on `feature/phase2-post-id` successfully generates KO and EN posts.

## Gemini SDK Migration Plan

The current pipeline still imports the deprecated package:

```python
import google.generativeai as genai
```

GitHub Actions now reports that `google.generativeai` is no longer supported. This warning did not cause the `json_meta` validation failure, but it should be resolved before Phase 3 because Phase 3 will add more automation on top of Gemini output.

Recommended migration timing:

- Treat this as `Phase 2.5`.
- Complete it after Phase 2 post-ID stabilization.
- Complete it before Phase 3 knowledge-note generation.

Implementation plan:

1. Replace `google-generativeai` with `google-genai` in `scripts/requirements.txt`.
2. Update `scripts/multi_agent.py` to create a `google.genai.Client`.
3. Keep the existing `call_gemini` wrapper contract unchanged so usage tracking, retry behavior, and quota-aware error reporting stay centralized.
4. Update `scripts/gemini_runtime.py` only where response text, usage metadata, and exception shapes differ.
5. Update fake Gemini modules in integration tests.
6. Run the full offline test suite.
7. Run one feature-branch GitHub Actions generation before merging.

Risk notes:

- Response text access may differ between SDKs.
- Usage metadata field names may differ.
- Exception classes and status-code fields may differ.
- Quota classification must still detect RPD, RPM, and TPM failures.

Phase 3 should start only after this migration is either completed or explicitly deferred.
