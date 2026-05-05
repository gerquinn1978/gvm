# v2.0.0 — Release Notes

**Date:** 2026-04-26
**Reference:** This release implements `requirements/gvm-improvements-requirements.md` (Round 1 Approved 2026-04-22). Tag `v2.0.0` at commit `8cfb63b` to satisfy the `_verify_pp_cross_cutting.py` check-7 release-cut gate. Prior release: `v1.0.0`. Major bump per semver — this release introduces breaking changes (verdict vocabulary retirement, `/gvm-requirements` IM-4 refusal behaviour, calibration `schema_version` field).

## What's new

### New skills

- `/gvm-impact-map` (Track 3, Domain IM) — discovers Goals → Actors → Impacts → Deliverables before requirements gathering. Produces `impact-map.md` (four flat tables); downstream `/gvm-requirements` enforces IM-4 traceability (every Must/Should/Could requirement carries an `[impact-deliverable: D-N]` tag).
- `/gvm-walking-skeleton` (Track 3, Domain WS) — wires a thin end-to-end thread through every external integration boundary before feature work begins. Produces `boundaries.md` (real_call_status ∈ {wired, wired_sandbox, deferred_stub}); `/gvm-build` honours WS-5 red-skeleton refusal per chunk; `/gvm-test` audits VV-3(d), VV-4(d).
- `/gvm-explore-test` (Track 2, Domain ET) — runs a timeboxed exploratory charter against built code. Produces paired `test/explore-NNN.md` + `.html`; `/gvm-test` reads via VV-4(d) (ET-3 reproduction-or-Observation, ET-5 tour-completion gate).

### Modified skills

- `/gvm-build` — HS-1 unregistered-stub gate at handover, HS-6 retroactive-audit forward-pointer, WS-5 chunk refusal driven by `_skeleton_status.query_skeleton_status`.
- `/gvm-test` — three-verdict vocabulary (Ship-ready / Demo-ready / Not shippable) emitted by `gvm_verdict.evaluate`; VV-2..VV-5 evaluator gates calibration history and stub expiry.
- `/gvm-code-review` — Panel E (Stub Detection) added; mechanically-assembled prompt via `_panel_e_prompt.assemble_panel_e_prompt`; SD-5 severity promotion.
- `/gvm-requirements` — IM-4 (impact-map traceability) and RA-3 (risk-assessment completeness) gates at finalisation.
- `/gvm-test-cases` — EBT-1 (collaboration-vs-contract test partitioning); `[CONTRACT]` / `[COLLABORATION]` tags; `[PROPERTY]` test emission.

## Breaking changes (require migration)

- **Verdict vocabulary.** `/gvm-test` no longer emits "Pass with gaps". Existing report consumers must update to the three-verdict taxonomy. The v0→v1 mapping table (per ADR-604) is: Pass → SHIP_READY; Pass-with-gaps → None (practitioner review required); Do-not-release → NOT_SHIPPABLE.
- **`/gvm-requirements` refusal behaviour.** Requirements without an `[impact-deliverable: D-N]` tag are refused at finalisation (Won't requirements exempt). Existing requirements docs must add tags or be marked out-of-scope.
- **`reviews/calibration.md` schema.** Calibration files acquire a machine-readable `schema_version` field. Legacy files (no field present) are treated as `schema_version: 0` until migrated.

## Migration

Run `python -m gvm_migrate_calibration reviews/calibration.md` once per project to stamp `schema_version: 0` on existing calibration files; `/gvm-test` performs the VV-6 retrofit (interactive reclassification of historical "Pass with gaps" rows) on first invocation. See `~/.claude/skills/gvm-code-review/docs/user-guide.html` for details.

## Tracks

- Track 2: HS, VV, SD, ET — engineering discipline.
- Track 3: IM, RA, WS, EBT — discovery + integration discipline.
- Track P: PP — propagation editorial work.

Total: 60 requirements, 130 test cases.
