---
name: gvm-deploy
description: Use when preparing a release — version bump, release notes, documentation accuracy check, changelog, and git tag. Triggered by /gvm-deploy command, requests to prepare a release, cut a version, or generate release notes. Does NOT execute deployment — that is organisation-specific.
---


# Release Preparation

## Overview

Prepares a release from the current pipeline state. Aggregates review verdicts, checks that documentation matches the build, increments the version, generates release notes, updates the changelog, and tags the release in git.

This skill does not deploy anything. Deployment mechanisms (CI/CD, cloud providers, container orchestration, manual processes) are organisation-specific and outside the pipeline's scope. This skill produces a release-ready tagged commit with accurate documentation and a clear record of what changed.

**Pipeline position:** `/gvm-build` → `/gvm-code-review` → `/gvm-test` → `/gvm-doc-write` → `/gvm-doc-review` → **`/gvm-deploy`**

The release preparation is the final pipeline phase. It runs after the build is verified, reviewed, tested, and documented.

**Shared rules:** At the start of this skill, load `~/.claude/skills/gvm-design-system/references/shared-rules.md` and follow all rules throughout execution. Load `~/.claude/skills/gvm-design-system/references/expert-scoring.md` when scoring experts.

## Hard Gates

These steps are non-negotiable. If you skip any of them, the release output is invalid.

1. **QUALITY GATE CHECK.** YOU MUST verify that no review verdict blocks the release. If any review produced a "not ready" verdict (Do not merge, Do not build, Revise first, Do not publish, Do not present, Do not send, Do not deliver, Do not ship, Do not release), the release is blocked. DO NOT proceed past this step with a blocking verdict.

2. **DOCUMENTATION ACCURACY CHECK.** YOU MUST verify that README.md and any user-facing documentation match the current build. DO NOT tag a release with stale documentation.

3. **VERSION AND TAG.** YOU MUST create a git tag for the release. DO NOT end the skill without a tagged commit.

## Process

> **Sub-step convention:** Steps use lettered sub-steps (e.g., 1b, 2c). All sub-steps within a step are sequential and always run unless the sub-step heading states a condition.

### Step 0: Bootstrap

Per shared rule 14, verify `~/.claude/gvm/` exists before writing output.

### Step 1: Gather Release Context

1a. **Read calibration** — Read `reviews/calibration.md` to confirm prior reviews exist. If no calibration file exists, warn the user (step 1b will attempt to find verdicts directly from report files). If no calibration file exists, warn the user: "No review history found. Run `/gvm-code-review` and `/gvm-test` before releasing." If no calibration file exists AND no review reports are found in step 1b, Hard Gate 1 cannot be satisfied. Present to the user via AskUserQuestion: 'No review history found. Release quality cannot be verified. Proceed without review history (not recommended) or run required reviews first?' If the user selects **Proceed without review history**: this is an explicit user override — record it in `RELEASE-NOTES` under "Known gaps / overrides" and continue to step 1b. If the user selects **Run required reviews first**: STOP the skill. Tell the user: "Run `/gvm-code-review` and `/gvm-test` (and `/gvm-design-review` / `/gvm-doc-review` if applicable), then re-run `/gvm-deploy`." Do not proceed to step 1b.

1b. **Read review reports** — scan `code-review/`, `doc-review/`, `design-review/`, and `test/` for the most recent report files. Extract the verdict from each. If reports exist but have no verdict (pre-verdict-system reports), treat as "no verdict available" and warn.

1c. **Read requirements** — load `requirements/requirements.md` (or the latest round's file). Extract the requirements index for release note generation.

1d. **Check version history** — run `git tag --list 'v*' --sort=-version:refname` to find the current version. If no tags exist, the release will be `v0.1.0`.

### Step 2: Pre-Release Quality Gate

Load `~/.claude/skills/gvm-design-system/references/review-reference.md` before step 2a to obtain the complete verdict string set for all review types.

2a. **Aggregate verdicts** — collect the most recent verdict from each review type:

| Verdict tier | Release decision |
|---|---|
| All reviews **ready** | Proceed to release |
| Any review **ready with caveats** | Present caveats to user via AskUserQuestion — user decides whether to proceed |
| Any review **not ready** | **Block.** Hard Gate 1. Report which review blocks and why. Stop. |
| No reviews exist | Warn and ask user whether to proceed without review history |

Verdict string mapping: Code review uses "Merge / Merge with caveats / Do not merge". Design review uses "Build from this / Build with caveats / Do not build". Doc review uses type-specific language — the complete middle-tier ("ready with caveats") strings are: "Proceed with caveats" (pipeline docs), "Publish with revisions" (whitepapers/strategy), "Present with revisions" (presentations), "Send with revisions" (newsletters), "Deliver with revisions" (training), "Ship with caveats" (user docs), "Merge with caveats" (code), "Build with caveats" (design). Test verification uses the three-verdict taxonomy "Ship-ready / Demo-ready / Not shippable" (per honesty-triad ADR-105). Map "Demo-ready" to the caveats tier. Match against the exact strings, not the tier labels.

2b. **Check test status** — if `build/handovers/` exists, verify the most recent handover indicates tests passed. If `/gvm-test` output exists, check its result. If no test evidence exists, warn.

2c. **Present gate summary** — show the user: verdicts by review type, test status, any caveats. If everything is ready, proceed. If caveats exist, wait for user confirmation.

### Step 3: Documentation Accuracy Check

This is a targeted accuracy check, not a full `/gvm-doc-review`. It verifies that documentation describes what was actually built — not what was planned, not what was true two rounds ago.

3a. **README check** — read `README.md`. Compare against the current requirements and build state:
- Do the described features match implemented requirements?
- Are setup/installation instructions accurate for the current dependency set?
- Are configuration options current?
- Are any described features not yet implemented (or removed)?

Flag any inaccuracy as a release blocker. Per Hard Gate 2 (non-overridable), the user must fix it or abort the release — see step 3c for the resolution flow.

3b. **User documentation check** (if user docs exist) — scan `docs/` for user-facing documentation. For each document, check whether it describes the current system state. Specific checks:
- Do navigation paths match the implemented UI?
- Do API endpoints match the implemented routes?
- Do screenshots (if any) match the current interface?
- Are there references to features that were descoped or changed?

3c. **Present findings** — if inaccuracies found, present them via AskUserQuestion with two options: **Fix now** or **Abort the release**. Hard Gate 2 applies: stale documentation blocks the tag. There is no "acknowledge and proceed" option at this step — Hard Gate 2 is non-overridable. If the user believes an inaccuracy is acceptable (e.g., a planned limitation), the correct action is to update the README to state the limitation explicitly, then re-verify, so the shipped README describes what is shipped.

3d. **Fix documentation** (if user chooses to fix) — apply fixes to README.md and user docs using the writing experts from `writing-reference.md` for prose quality. Update the documents in place. After fixing, re-verify the specific inaccuracies. Autonomous fix-and-re-verify is capped at 1 iteration. If the fix introduced new inaccuracies, present them to the user via AskUserQuestion rather than attempting a second fix autonomously.

### Step 4: Determine Version

4a. **Analyse changes and determine version bump:**

**Version bump analysis:**
- Pre-1.0 (v0.x.x): New features or breaking changes → minor bump. Bug fixes only → patch bump.
- Post-1.0: Breaking changes to public APIs or data formats → major bump. New features (backward-compatible) → minor bump. Bug fixes only → patch bump.

4b. **Propose version** — present the proposed version to the user with the reasoning. The user confirms or overrides. Semver rules:
- `MAJOR.MINOR.PATCH`
- First release is `0.1.0` (pre-1.0 signals early development)
- The user always has final say on the version number

### Step 5: Generate Release Notes and Changelog

Two release note outputs serve different audiences:

- **`RELEASE-NOTES.html`** — user-facing. Describes what changed in terms users care about: new capabilities, improved workflows, things they can now do that they couldn't before. Uses Tufte/Few design. No requirement IDs, no review scores, no implementation details. Written for someone who uses the product, not someone who builds it.
- **`RELEASE-NOTES.md`** — developer-facing. Structured summary with requirement IDs, review verdicts, quality scores, and technical detail. Written for someone maintaining or contributing to the project.

Both are overwritten each release — historical notes are in `CHANGELOG.md` and git tags.

5a. **Read the changes** — diff the pipeline artefacts against the previous version tag (or the full history if this is the first release). Identify what changed from both perspectives:
- User-facing: what can users do now? What works better? What was broken and is now fixed?
- Developer-facing: which requirements were implemented? What were the review verdicts? What's still open?

5b. **Write user-facing release notes** — load `~/.claude/skills/gvm-design-system/references/tufte-html-reference.md` and `~/.claude/skills/gvm-design-system/references/writing-reference.md`. Log all loaded experts to activation CSV (per shared rule 1). Write `RELEASE-NOTES.html` using Tufte/Few design.

**HTML generation:** Dispatch RELEASE-NOTES.html generation as a Haiku subagent (`model: haiku`). The subagent receives the RELEASE-NOTES.md content and the Tufte CSS shell. Per shared rule 22.

**Structure:** organise by what changed, not by pipeline phase. Group related changes under descriptive headings. Each item should answer "what can I do now?" not "what code changed." For the first release, describe the full capability set — the user guides are the detailed documentation, but the release notes orient the reader to what's available.

Apply the writing experts from `writing-reference.md`.

5c. **Write developer-facing release notes** — write `RELEASE-NOTES.md`:

```markdown
# v{VERSION} — {DATE}

## What's New
- {Requirement ID}: {Summary} — {one-line description of what was built}

## Improvements
- {Description of enhancements to existing features}

## Fixes
- {Description of bug fixes or review finding resolutions}

## Known Issues
- {Open questions from requirements, acknowledged review caveats}

## Quality Summary
- Code review: {verdict} ({score})
- Doc review: {verdict} ({score}) (if applicable)
- Design review: {verdict} ({score}) (if applicable)
- Test status: {pass/fail}
```

5d. **Update CHANGELOG.md** — if `CHANGELOG.md` exists, prepend the new release entry at the top (below the header). If it does not exist, create it with a header and the first entry. Format follows Keep a Changelog conventions:

```markdown
# Changelog

## [v{VERSION}] — {DATE}

### Added
- {New features}

### Changed
- {Changes to existing features}

### Fixed
- {Bug fixes}
```

### Step 6: Tag and Finalise

6a. **Stage and commit** — stage `RELEASE-NOTES.html`, `RELEASE-NOTES.md`, `CHANGELOG.md`, and any documentation fixes from Step 3. Commit with message: `Release v{VERSION}`.

6b. **Tag** — create an annotated git tag: `git tag -a v{VERSION} -m "Release v{VERSION}"`. The tag message includes a condensed version of the release notes.

6c. **Report** — present the release summary to the user:
- Version tagged
- Files changed
- Release notes preview
- Reminder: "Push with `git push && git push --tags` when ready to publish"

Do not push automatically. The user decides when to push.

## Extending for Your Environment

This skill produces a tagged commit. What happens after `git push --tags` is up to you. Common extensions:

- **CI/CD integration** — configure your pipeline to trigger on version tags (`v*`). The tag is the handoff point between GVM and your deployment infrastructure.
- **GitHub/GitLab releases** — add a `gh release create` or equivalent step after the tag.
- **Container builds** — trigger image builds from the tagged commit.
- **Notification** — post to Slack, email stakeholders, update a status page.

These are organisation-specific and intentionally outside this skill's scope. Extend the skill or add a post-push hook — the tagged commit is a stable interface that any downstream system can consume.

## What This Skill Does NOT Do

- **Deploy to any environment.** No CI/CD triggers, no cloud commands, no container pushes.
- **Generate runbooks.** Operational procedures are organisation-specific.
- **Manage environments.** Staging, production, feature flags — all out of scope.
- **Create GitHub/GitLab releases.** The git tag is the release. Platform-specific release objects are a CI/CD concern.
- **Roll back.** Rollback procedures depend on the deployment mechanism.

## Key Rules

**Model selection (per shared rule 22):** Steps 1--3 (gather context, quality gate check, documentation accuracy) use the primary model -- these require judgment. Step 5b (RELEASE-NOTES.html) dispatches HTML generation as a Haiku subagent (`model: haiku`). Step 5c (RELEASE-NOTES.md) uses `model: sonnet`. Step 5d (CHANGELOG.md) uses `model: sonnet` -- structured extraction from artefacts.

1. **The user controls the version number.** The skill proposes; the user decides.
2. **Stale documentation blocks the release.** README and user docs must describe what was built, not what was planned.
3. **Review verdicts are authoritative.** The deploy skill reads verdicts, it does not re-evaluate quality.
4. **No silent releases.** Every step that requires a decision uses AskUserQuestion.
5. **Do not push.** Stage, commit, and tag locally. The user pushes when ready.
6. **Experts who find should fix** — per shared rule 3. Documentation inaccuracies found in Step 3 are fixed using the same writing experts.
7. **Release notes are paired, changelog is not.** `RELEASE-NOTES.html` (user-facing, Tufte/Few) and `RELEASE-NOTES.md` (developer-facing) are both required. `CHANGELOG.md` is markdown-only — it follows Keep a Changelog conventions and is rendered by GitHub.

8. **Methodology-changelog inclusion heuristic (NFR-3).** When updating `methodology-changelog.md` (the project-root audit trail of behaviour-changing methodology evolutions, distinct from `CHANGELOG.md` for product releases), apply this heuristic: "if a chunk that was acceptable yesterday would be refused today (or vice versa), it's a changelog entry." Typo / formatting / comment-only edits are NOT entries — git history covers those. Without this heuristic, cosmetic edits flood the audit trail and obscure the rules that actually changed practitioner behaviour.
