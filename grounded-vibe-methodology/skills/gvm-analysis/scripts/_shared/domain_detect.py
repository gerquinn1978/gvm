"""Domain detection from column-name activation signals (ADR-105).

Scans input-file column names against the ``activation_signals`` /
``strong_signals`` declared in the YAML frontmatter of industry files.
A match is confirmed when:

* at least 2 distinct ``activation_signals`` appear in the column set, OR
* at least 1 ``strong_signals`` appears.

The module returns ``{"matched", "signals", "candidate_domain"}`` matching
the stdout JSON contract in ADR-105. Row data NEVER flows through this
module — only column names.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

__all__ = ["detect", "MalformedIndustryFileError"]


# "Identifiable but no industry file" signals — lets AN-7 recognise a
# domain even when no frontmatter-declared file exists. Kept intentionally
# small. Expand via `/gvm-requirements` when new candidate domains emerge.
_CANDIDATE_SIGNAL_MAP: dict[str, list[str]] = {
    "clinical": [
        "hba1c",
        "ldl",
        "triglycerides",
        "creatinine",
        "patient_id",
        "diagnosis_code",
        "icd10",
    ],
}

_REQUIRED_FRONTMATTER_KEYS = {"domain_name", "activation_signals"}


class MalformedIndustryFileError(Exception):
    """Raised when an industry file cannot be parsed or is missing required keys."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"malformed industry file {path}: {reason}")


def _parse_industry_file(path: Path) -> dict:
    """Parse YAML frontmatter from an industry ``.md`` file.

    Raises :class:`MalformedIndustryFileError` if the file has no
    frontmatter block, required keys are missing, or
    ``activation_signals`` is absent / empty.
    """
    # Use utf-8-sig to strip BOM; also tolerate a leading newline so files
    # authored on Windows or with trailing newline after a blank first line
    # still parse. Frontmatter-before-content is the load-bearing contract.
    text = path.read_text(encoding="utf-8-sig")
    text_for_check = text.lstrip("\r\n")
    if not text_for_check.startswith("---"):
        raise MalformedIndustryFileError(path, "no YAML frontmatter")
    text = text_for_check

    # Split on the SECOND "---" line to isolate the frontmatter block.
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise MalformedIndustryFileError(path, "frontmatter not closed")

    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        raise MalformedIndustryFileError(path, f"YAML parse error: {exc}") from exc

    if not isinstance(data, dict):
        raise MalformedIndustryFileError(path, "frontmatter is not a mapping")
    missing = _REQUIRED_FRONTMATTER_KEYS - data.keys()
    if missing:
        raise MalformedIndustryFileError(
            path, f"missing required keys: {sorted(missing)}"
        )
    activation = data.get("activation_signals")
    if not isinstance(activation, list) or not activation:
        raise MalformedIndustryFileError(
            path, "activation_signals must be a non-empty list"
        )
    strong = data.get("strong_signals")
    if strong is None:
        strong = []
    elif not isinstance(strong, list):
        raise MalformedIndustryFileError(path, "strong_signals must be a list")

    return {
        "domain_name": str(data["domain_name"]),
        "activation_signals": [str(s).lower() for s in activation],
        "strong_signals": [str(s).lower() for s in strong],
        "path": path,
    }


def _load_industry_index(industry_dir: Path) -> list[dict]:
    """Parse every ``*.md`` in ``industry_dir`` in sorted order.

    Malformed files are skipped with a warning to stderr — the user's data
    might match a *different* industry file, and one broken file should
    not block the whole pipeline. The caller receives only the valid
    entries.
    """
    industry_dir = Path(industry_dir)
    if not industry_dir.exists():
        return []
    out: list[dict] = []
    for p in sorted(industry_dir.glob("*.md")):
        try:
            out.append(_parse_industry_file(p))
        except MalformedIndustryFileError as exc:
            print(f"WARNING: skipping malformed industry file: {exc}", file=sys.stderr)
    return out


def _normalise(columns: list[str]) -> list[str]:
    return [str(c).strip().lower() for c in columns]


def _match_domain(columns_lower: set[str], industry: dict) -> tuple[bool, list[str]]:
    """Return ``(is_match, signals_fired)`` for one industry entry.

    ``columns_lower`` is the pre-lowercased column-name set. Signals are
    reported in the order they appear in the industry frontmatter so the
    output is deterministic.
    """
    strong_hits = [s for s in industry["strong_signals"] if s in columns_lower]
    if strong_hits:
        return True, strong_hits
    activation_hits = [s for s in industry["activation_signals"] if s in columns_lower]
    if len(activation_hits) >= 2:
        return True, activation_hits
    return False, []


def _candidate_domain(columns_lower: set[str]) -> str | None:
    """Return the first candidate-domain label whose signal list intersects."""
    for domain, signals in _CANDIDATE_SIGNAL_MAP.items():
        if any(s in columns_lower for s in signals):
            return domain
    return None


def detect(columns: list[str], industry_dir: Path) -> dict:
    """Return ``{matched, signals, candidate_domain}`` for ``columns``.

    ``matched`` is the first domain (sorted filename order) whose
    activation or strong signals are hit. ``signals`` is the list of
    column names (as they appear in the input, case-preserved) that
    drove the match. ``candidate_domain`` is populated only when
    ``matched`` is ``None`` and the columns resemble a recognised-but-
    unconfigured domain.
    """
    raw_columns = list(columns)
    columns_lower = set(_normalise(raw_columns))

    industries = _load_industry_index(Path(industry_dir))
    for industry in industries:
        is_match, fired = _match_domain(columns_lower, industry)
        if is_match:
            # Echo back the ORIGINAL column spelling for each fired signal.
            # Use setdefault so the FIRST occurrence wins if multiple columns
            # normalise to the same lowercase form.
            lower_to_original: dict[str, str] = {}
            for c in raw_columns:
                lower_to_original.setdefault(c.strip().lower(), c)
            signals_out = [lower_to_original.get(s, s) for s in fired]
            return {
                "matched": industry["domain_name"],
                "signals": signals_out,
                "candidate_domain": None,
            }

    candidate = _candidate_domain(columns_lower)
    return {
        "matched": None,
        "signals": [],
        "candidate_domain": candidate,
    }
