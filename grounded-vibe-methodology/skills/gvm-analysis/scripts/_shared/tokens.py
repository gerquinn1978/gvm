"""Token format generator + de-anonymisation regex builder.

Anonymisation-pipeline ADR-403 (P14-C01, originally P7-C01 in the
gvm-analysis impl-guide; renumbered to avoid plugin-build clash).

Public API
----------

* :data:`TOK_PREFIX` — the literal ``"TOK_"`` prefix shared by every token.
* :func:`normalise_column` — column-name normaliser used by both producer
  (``make_token``) and consumer (``build_match_regex``); single source of
  truth (Brooks: conceptual integrity).
* :func:`make_token` — produces a column-prefixed, zero-padded token. Pad
  width is ``max(3, len(str(total)))`` so the de-anonymisation regex's
  ``\\d{3,}`` floor always holds.
* :func:`build_match_regex` — compiled ``re.Pattern`` matching every token
  produced by ``make_token`` for the given column list. Compiled once per
  ``de_anonymise.py`` invocation and reused.

Out of scope: anonymisation orchestration (P14-C02), de-anonymisation
script (P14-C03), and AN-40 detection (P14-C04). This module is
pure helpers.
"""

from __future__ import annotations

import re

# ADR-403: chosen to be vanishingly rare in normal text; easy to grep.
TOK_PREFIX: str = "TOK_"

# Hard cap on the column slot per ADR-403 — keeps tokens short and the
# regex alternation fast.
_COLUMN_MAX_LEN: int = 30
_COLUMN_NORMALISE_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]")


def normalise_column(name: str) -> str:
    """Lowercase + non-alphanumerics → ``_`` + truncate to 30 chars.

    Used by both ``make_token`` (producer side) and ``build_match_regex``
    (consumer side). Both sites MUST call this function — duplicating
    the rule is a Brooks conceptual-integrity violation that lets the
    producer and consumer drift silently.
    """
    return _COLUMN_NORMALISE_RE.sub("_", name.lower())[:_COLUMN_MAX_LEN]


def make_token(column: str, index: int, *, total: int) -> str:
    """Pad ``index`` to ``max(3, len(str(total)))`` digits.

    ADR-403: zero-padded 3 digits minimum; widens automatically for
    n ≥ 1000 to 4 digits (and so on). The pad floor matches the
    ``\\d{3,}`` floor in :func:`build_match_regex` — change one and the
    other breaks (covered by the regex tests).
    """
    width = max(3, len(str(total)))
    return f"{TOK_PREFIX}{normalise_column(column)}_{index:0{width}d}"


def build_match_regex(columns: list[str]) -> re.Pattern[str]:
    """Compile a single regex matching tokens for the supplied columns.

    The pattern is ``TOK_(?:col1|col2|...)_\\d{3,}`` where each ``colN``
    is the normalised form of the supplied column name (so callers may
    pass raw header names). Each part is escaped via :func:`re.escape`
    before joining — defensive even though :func:`normalise_column`
    already strips regex meta-characters.

    Empty ``columns`` is rejected: an empty alternation compiles to a
    pattern that matches nothing useful, and the caller almost certainly
    has a typo or empty mapping bug. Fail loudly (McConnell).

    Post-R3 fix M-6: ``\\d{3,}`` (not ``\\d+``) — minimum 3 digits matches
    the producer's zero-padding guarantee from :func:`make_token`. This
    eliminates false-positive matches on partial digit suffixes
    (``_0``, ``_00``).
    """
    if not columns:
        raise ValueError(
            "build_match_regex requires at least one column; got empty list"
        )
    parts = "|".join(re.escape(normalise_column(c)) for c in columns)
    return re.compile(rf"{re.escape(TOK_PREFIX)}(?:{parts})_\d{{3,}}")
