# EBT Boundaries Defaults — ADR-504 Template

This file documents the default content for a project-level `.ebt-boundaries`
file. Copy it to your project root as `.ebt-boundaries` and extend it with
project-specific allowed mock boundaries.

The `_ebt_contract_lint.py` linter reads `.ebt-boundaries` at the path passed
to `lint(ebt_boundaries_path=...)`. If `ebt_boundaries_path=None`, the linter
uses the stack defaults below without reading any file.

## How it works

- One allowed mock-boundary pattern per line.
- `#` introduces a comment. Empty lines are ignored.
- Patterns are matched with `fnmatch.fnmatchcase` (glob-style, case-sensitive).
- Stack defaults are always merged in before project patterns. You cannot
  remove a stack default by omitting it here — only add project-specific extras.

## Template — copy to `<project-root>/.ebt-boundaries`

```
# .ebt-boundaries — one allowed mock boundary per line
# Patterns matched against the import path of the mocked symbol.
# Generated from GVM ADR-504 defaults. Extend with project-specific boundaries.

# Python defaults (always active when stack="python")
requests.*
httpx.*
psycopg2.*
sqlalchemy.engine.*
boto3.*

# Add project-specific allowed boundaries below.
# Examples:
#   myapp.adapters.stripe.*    — third-party payment adapter is an allowed seam
#   myapp.adapters.sendgrid.*  — email adapter is an allowed seam
```

## Rationale (ADR-504)

Mocking at the wrong boundary makes tests brittle and hides protocol drift
(Metz, POODR Ch. 9; Freeman & Pryce, *GOOS*). The allowlist codifies which
module paths are genuine architectural seams rather than internal-class
implementation details. Every entry here should correspond to a boundary
documented in `boundaries.md`.

## Per-stack defaults

| Stack      | Default patterns                                                      |
|------------|-----------------------------------------------------------------------|
| Python     | `requests.*`, `httpx.*`, `psycopg2.*`, `sqlalchemy.engine.*`, `boto3.*` |
| TypeScript | No file-based defaults — transport detection is regex-only.           |
| Go         | No file-based defaults — transport detection is regex-only.           |
