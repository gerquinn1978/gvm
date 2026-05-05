"""Walking-skeleton validator (P11-C02 — Hard Gates 1, 2, 3).

Spec ref: walking-skeleton ADR-403 (schema), ADR-404 (mock-refusal),
ADR-407 (deferred-stub registration via STUBS.md).

Test cases: TC-WS-2-01..02, TC-WS-3-01..03.

Wraps the shared `_boundaries_parser` (P7-C04) and `_stubs_parser` (P7) and
surfaces parse / cross-artefact / mock-detection failures as a list of
`ValidationError` records rather than raising. Mirrors the shape of
`gvm-impact-map/scripts/_validator.py:full_check` so calling skills share
one error-handling vocabulary.

Scope:
- HG-1: every detected boundary registered (delegated to `_boundaries_parser`).
- HG-2 schema: `wired_sandbox` requires non-trivial divergence (delegated;
  parser raises `DivergenceMissingError`, validator surfaces it as WS-2).
- HG-2 deferred-stub cross-check: `deferred_stub` rows must have a matching
  STUBS.md entry at `walking-skeleton/stubs/<name>.<ext>` per ADR-407.
- HG-3 mock-refusal: skeleton test file scanned for language-specific mock
  signatures; matches emit WS-3.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# `_boundaries_parser` and `_stubs_parser` live in the gvm-design-system skill.
# Insert its scripts dir on sys.path so this module imports cleanly from any
# cwd. Mirrors the established pattern in `_validator.py` (gvm-impact-map).
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _boundaries_parser import (  # noqa: E402
    Boundaries,
    BoundariesParseError,
    load_boundaries,
)
from _stubs_parser import StubsParseError, load_stubs  # noqa: E402


# Mock signatures per language. Substring match; case-sensitive. Conservative
# (Rainsberger): false positives block legitimate skeletons but the patterns
# are specific enough to make false positives unlikely.
_MOCK_PATTERNS: dict[str, tuple[str, ...]] = {
    "python": (
        "unittest.mock",
        "from mock import",
        "import mock",
        "MagicMock",
        "Mock(",
        "monkeypatch",
        "pytest_mock",
        "mocker.",
    ),
    "typescript": (
        "vi.mock(",
        "vi.fn(",
        "jest.mock(",
        "jest.fn(",
        "sinon.stub(",
        "sinon.fake(",
    ),
    "go": (
        "gomock.NewController",
        "gomock.Any(",
        "mockery",
    ),
}

_LANGUAGE_EXTENSIONS: dict[str, str] = {
    "python": ".py",
    "typescript": ".ts",
    "go": ".go",
}


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str


def full_check(
    boundaries_path: str | os.PathLike[str],
    *,
    skeleton_test_path: str | os.PathLike[str] | None = None,
    stubs_path: str | os.PathLike[str] | None = None,
    primary_language: str = "python",
) -> tuple[Boundaries | None, list[ValidationError]]:
    """Validate boundaries.md against schema, mock-refusal, and deferred-stub
    registration. Never raises. Pass condition: ``len(errors) == 0``.

    When parsing fails, ``boundaries`` is ``None`` and ``errors`` carries the
    parse failure under code ``WS-2``. Otherwise ``boundaries`` is the parsed
    registry and ``errors`` lists every cross-artefact / mock-detection
    failure found — collected, not short-circuited (Hunt & Thomas: tell the
    user everything they need to fix, not just the first thing).
    """

    errors: list[ValidationError] = []

    try:
        boundaries = load_boundaries(boundaries_path)
    except FileNotFoundError as exc:
        return None, [ValidationError(code="WS-2", message=str(exc))]
    except BoundariesParseError as exc:
        return None, [ValidationError(code="WS-2", message=str(exc))]
    except Exception as exc:  # noqa: BLE001
        return None, [ValidationError(code="WS-2", message=str(exc))]

    errors.extend(
        _check_deferred_stubs_registered(
            boundaries,
            stubs_path=Path(stubs_path) if stubs_path is not None else None,
            primary_language=primary_language,
        )
    )

    if skeleton_test_path is not None:
        errors.extend(
            _check_no_mocks(
                Path(skeleton_test_path),
                language=primary_language,
                wired_count=sum(
                    1
                    for r in boundaries.rows
                    if r.real_call_status in ("wired", "wired_sandbox")
                ),
            )
        )

    return boundaries, errors


def _check_deferred_stubs_registered(
    boundaries: Boundaries,
    *,
    stubs_path: Path | None,
    primary_language: str,
) -> list[ValidationError]:
    """For every `deferred_stub` row, confirm a STUBS.md entry exists at
    `walking-skeleton/stubs/<name>.<ext>` per ADR-407 / WS-6."""

    deferred = [r for r in boundaries.rows if r.real_call_status == "deferred_stub"]
    if not deferred:
        return []

    if stubs_path is None:
        return [
            ValidationError(
                code="WS-6",
                message=(
                    f"Boundary {row.name!r} is deferred_stub but no STUBS.md "
                    f"path was supplied; per ADR-407 every deferred boundary "
                    f"requires a STUBS.md entry"
                ),
            )
            for row in deferred
        ]

    try:
        entries = load_stubs(stubs_path)
    except FileNotFoundError as exc:
        return [
            ValidationError(
                code="WS-6",
                message=(
                    f"STUBS.md not found at {stubs_path} but {len(deferred)} "
                    f"deferred boundary row(s) require entries: {exc}"
                ),
            )
        ]
    except StubsParseError as exc:
        return [
            ValidationError(
                code="WS-6",
                message=f"STUBS.md parse error: {exc}",
            )
        ]

    ext = _LANGUAGE_EXTENSIONS.get(primary_language.lower(), ".py")
    registered_paths = {e.path for e in entries}
    errors: list[ValidationError] = []
    for row in deferred:
        expected = f"walking-skeleton/stubs/{row.name}{ext}"
        if expected not in registered_paths:
            errors.append(
                ValidationError(
                    code="WS-6",
                    message=(
                        f"Boundary {row.name!r} is deferred_stub but STUBS.md "
                        f"has no entry at {expected!r} (per ADR-407 / HS-1)"
                    ),
                )
            )
    return errors


def _check_no_mocks(
    skeleton_test_path: Path,
    *,
    language: str,
    wired_count: int,
) -> list[ValidationError]:
    """Scan the skeleton test file for mock signatures. WS-3 fires on
    any match. Empty file with at least one wired boundary also fires —
    the skeleton must exercise something."""

    if not skeleton_test_path.exists():
        return [
            ValidationError(
                code="WS-3",
                message=(
                    f"Skeleton test file not found at {skeleton_test_path}; "
                    f"per ADR-404 every wired boundary must be exercised by "
                    f"a runnable test"
                ),
            )
        ]

    try:
        text = skeleton_test_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            ValidationError(
                code="WS-3",
                message=f"Could not read skeleton test file {skeleton_test_path}: {exc}",
            )
        ]

    if not text.strip() and wired_count > 0:
        return [
            ValidationError(
                code="WS-3",
                message=(
                    f"Skeleton test file {skeleton_test_path.name} is empty "
                    f"but {wired_count} wired boundary row(s) require runnable "
                    f"calls (ADR-404)"
                ),
            )
        ]

    patterns = _MOCK_PATTERNS.get(language.lower(), ())
    errors: list[ValidationError] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            if pattern in line:
                errors.append(
                    ValidationError(
                        code="WS-3",
                        message=(
                            f"Mock signature {pattern!r} detected at "
                            f"{skeleton_test_path.name}:{line_no} — wired "
                            f"boundaries must be exercised by real calls "
                            f"(ADR-404, Rainsberger)"
                        ),
                    )
                )
    return errors
