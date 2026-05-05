# Stub-Detection Heuristics

Panel E uses these heuristics mechanically. The LLM does not "decide what is a stub" — it matches a function body against the iff-rule for the project's primary language and emits a finding when the rule fires. Each section is a self-contained spec for one language.

## Python

A function body is a stub candidate iff one of these holds:

- It returns a literal — `dict`, `list`, `tuple`, `set`, `frozenset`, or scalar (`str`, `int`, `float`, `bool`, `None`) — with no parameter reference and no call expression.
- It returns a chained `.copy()` or `dict()` of a module-level literal.
- It contains only `pass`, a single `return` statement, or trivial local-assignment setup followed by a literal return.

Excluded — DO NOT flag — when the body contains any of:

- An I/O call (`open`, `read`, `write`, `requests.*`, `httpx.*`, `urllib.*`, `socket.*`).
- A cache lookup or ORM query (`cache.get`, `Model.objects.*`, `session.query`, `db.execute`).
- A network call or subprocess invocation.
- A parameter-dependent branch (`if param:`, ternary on parameter, parameter-indexed access).
- A call expression whose target is not a constant constructor (`list()`, `dict()` with non-literal args).

## TypeScript / JavaScript

A function body is a stub candidate iff one of these holds:

- It returns an object or array literal with no parameter reference and no call expression.
- It is an arrow function whose body is a literal expression.
- It returns a hardcoded `Promise.resolve(<literal>)` or `Promise.reject(<literal>)`.

Excluded — DO NOT flag — when the body contains any of:

- An `await` on a non-trivial promise (anything other than `Promise.resolve(<literal>)`).
- A `fetch`, `axios`, `XMLHttpRequest`, or any DOM call.
- A parameter-dependent branch or ternary.
- A reducer or `.map`/`.filter`/`.reduce` over a parameter.

## Go

A function body is a stub candidate iff one of these holds:

- It returns a literal struct, slice, or map.
- It returns a hardcoded zero value (`return 0`, `return ""`, `return nil`) with no input dependence.
- It returns a constant or package-level variable directly.

Excluded — DO NOT flag — when the body contains any of:

- A goroutine, channel send/receive, or `select` block.
- An `http.*`, `net.*`, `os.*`, or `sql.*` call.
- A parameter-dependent branch or switch.
- An error-wrapped return whose error originated from a real call.

## Namespace policy (HS-5)

Stub bodies are permitted only inside the `stubs/` namespace. Any function whose body matches the language heuristic above but whose file path does NOT begin with one of the recognised prefixes is a bounded-context violation regardless of whether it is registered in `STUBS.md` or listed in the `.stub-allowlist`.

For each match emit a finding with:

- `severity = "Critical"`
- `violation_type = "namespace_violation"`
- spec reference: honesty-triad ADR-104

This rule fires BEFORE registration reconciliation. A `STUBS.md` entry does not legitimise a stub at `providers/mock.py`; the only remedy is to move the body into a recognised `stubs/` prefix. The allowlist is not consulted for namespace violations — its purpose is to suppress legitimate non-stub literals (enums, constants), not to exempt mocks from the bounded-context rule.

A file is in-namespace iff its repo-relative path begins with one of the recognised prefixes (per `_stubs_parser.PATH_PREFIXES`):

- `stubs/`
- `walking-skeleton/stubs/`

So `stubs/mock_provider.py` and `walking-skeleton/stubs/x.py` are in-namespace; `providers/mock.py`, `app/stubs/mock.py`, `pkg/stubs/foo.py`, `mocks/foo.py`, and `fixtures/bar.py` are out-of-namespace. The prefix-based rule keeps the canonical-shape contract narrow: there is exactly one place a stub may live (modulo the walking-skeleton variant), and the parser, audit script, and Panel E all agree on that place.

## Canonical `STUBS.md` format

`STUBS.md` registers code-level placeholders. There is ONE canonical shape — a Markdown table with schema-1 frontmatter and the columns below. The authoritative parser is `~/.claude/skills/gvm-design-system/scripts/_stubs_parser.py`; HS-1, Panel E reconciliation, and the expiry check all consume this format. A reference audit script is shipped at `~/.claude/skills/gvm-design-system/references/check-stubs.py` for projects to copy into CI.

```markdown
---
schema_version: 1
---
# Stubs

| Path | Reason | Real-provider Plan | Owner | Expiry |
|---|---|---|---|---|
| stubs/parking.py | mock parking provider until DVLA API is wired | swap for `RealDvlaProvider` once contract is signed | gerard | 2026-09-30 |
```

Required columns (per `_stubs_parser.EXPECTED_COLUMNS`):

- **Path** — repo-relative file path. MUST begin with a recognised prefix per `_stubs_parser.PATH_PREFIXES` (`stubs/` or `walking-skeleton/stubs/`) — see HS-5 namespace policy below.
- **Reason** — why a stub exists rather than the real implementation (free text, ≥10 chars).
- **Real-provider Plan** — concrete plan to replace the stub with the real implementation. Use `unknown` only when the plan genuinely cannot be stated yet.
- **Owner** — name or handle of the person accountable for replacing the stub.
- **Expiry** — ISO-8601 (`YYYY-MM-DD`) date after which the stub is overdue. The `expired` violation type fires when `today > expiry`.

Optional column:

- **Requirement** — the `requirements.md` ID this stub satisfies (e.g. `GS-2`, `RE-7`, `R2-AUTH-3`). Recommended whenever a parent requirement exists. The link is one-way — `requirements.md` is the source of truth for *what* the system must do; `STUBS.md` is the source of truth for *which* placeholders exist in the code (per shared rule 27). When projects adopt the optional column, append it after Expiry.

## What `STUBS.md` is NOT

`STUBS.md` does NOT contain:

- A `## Surfaced Requirements` section, or any `STUB-SR-NN` IDs, or any other shape that records requirement gaps. Surfaced requirements promote to `requirements.md` per shared rule 27 — never park them here. Panel E does not look for or emit surfaced-requirement findings; that triage belongs to `/gvm-build` and `/gvm-code-review` (Panel C/D), not to Panel E.
- TODOs, design notes, or future-feature placeholders that are not stubbed code. Those belong in their respective artefacts (requirements, specs, handovers).
