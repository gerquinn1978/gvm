"""Panel E dispatch-prompt assembler (honesty-triad ADR-107).

Mechanical assembly only: no classification logic. The heuristic file is the
spec; this module concatenates STUBS.md, .stub-allowlist, and the language-
matching section into a single prompt string for the Panel E Agent dispatch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

Language = Literal["Python", "TypeScript", "Go"]
_LANGUAGE_HEADERS: dict[str, str] = {
    "Python": "## Python",
    "TypeScript": "## TypeScript / JavaScript",
    "Go": "## Go",
}
_EMPTY_PLACEHOLDER = "(empty — no entries)"


class PanelEPromptError(Exception):
    """Base class for Panel E prompt assembly failures."""


class UnknownLanguageError(PanelEPromptError):
    """Raised when `language` is outside the supported triple."""


class HeuristicSectionMissingError(PanelEPromptError):
    """Raised when the heuristic file lacks the requested language section."""


def _read_optional(path: Path | str | None) -> str:
    if path is None:
        return _EMPTY_PLACEHOLDER
    p = Path(path)
    if not p.exists():
        return _EMPTY_PLACEHOLDER
    text = p.read_text(encoding="utf-8")
    return text if text.strip() else _EMPTY_PLACEHOLDER


def _read_required(path: Path | str) -> str:
    p = Path(path)
    if not p.exists():
        raise PanelEPromptError(f"heuristic file not found: {p}")
    return p.read_text(encoding="utf-8")


def _extract_section(heuristic_text: str, language: Language) -> str:
    header = _LANGUAGE_HEADERS[language]
    lines = heuristic_text.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            start = i + 1
            break
    if start is None:
        raise HeuristicSectionMissingError(
            f"heuristic file has no '{header}' section (language={language})"
        )
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    section = "\n".join(lines[start:end]).strip()
    if not section:
        raise HeuristicSectionMissingError(
            f"'{header}' section is empty (language={language})"
        )
    return section


def assemble_panel_e_prompt(
    *,
    stubs_md_path: Path | str | None,
    allowlist_path: Path | str | None,
    heuristic_md_path: Path | str,
    language: Language,
) -> str:
    """Return the Panel E dispatch prompt as a single string.

    All three artefact bodies are embedded verbatim. STUBS.md and the allowlist
    fall back to an explicit placeholder when missing or empty. The heuristic
    file is required and must contain a `## {language}` section.
    """
    if language not in _LANGUAGE_HEADERS:
        raise UnknownLanguageError(
            f"unsupported language: {language!r} (expected one of "
            f"{sorted(_LANGUAGE_HEADERS)})"
        )

    stubs_body = _read_optional(stubs_md_path)
    allowlist_body = _read_optional(allowlist_path)
    heuristic_body = _extract_section(_read_required(heuristic_md_path), language)

    return _PROMPT_TEMPLATE.format(
        language=language,
        stubs=stubs_body,
        allowlist=allowlist_body,
        heuristic=heuristic_body,
    )


_PROMPT_TEMPLATE = """You are Panel E of /gvm-code-review. Your single defect lane is stub detection.

You do not decide what counts as a stub. Match each function body against the heuristic below. If the body matches the iff-rule and is not in the excluded list, emit a finding.

Namespace policy (HS-5, honesty-triad ADR-104) — apply this BEFORE step 1 below:
0. If the heuristic matches AND the file path does NOT contain a `stubs/` directory segment, emit a finding with severity="Critical" and violation_type="namespace_violation" — regardless of STUBS.md registration or allowlist entry. A `stubs/` segment means any path component equals `stubs` (so `stubs/x.py`, `app/stubs/x.py`, and `pkg/stubs/x.py` are in-namespace; `providers/mock.py`, `mocks/x.py`, `fixtures/x.py` are violations). For namespace violations DO NOT proceed to steps 1-3.

For every match that IS under `stubs/`:
1. Reconcile against STUBS.md — if the path::symbol is registered and unexpired, classify Informational and do not emit a finding; if registered but expired, emit a finding with violation_type="expired" and severity="Critical" (stub past expiry); if unregistered, proceed to step 2.
2. Reconcile against the .stub-allowlist — if path::symbol appears, classify Legitimate (kind=<allowlist kind>) and do not emit a violation.
3. Otherwise (unregistered AND not on allowlist), emit a finding with violation_type="unregistered" and severity="Critical" and a stable signature.

Project language: {language}

---

## STUBS.md (verbatim)

```
{stubs}
```

---

## .stub-allowlist (verbatim)

```
{allowlist}
```

---

## Stub-detection heuristic ({language}, verbatim from references/stub-detection.md)

```
{heuristic}
```
"""
