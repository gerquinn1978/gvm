"""Walking-skeleton single-flow lint (P11-C03 — ADR-405).

Counts test-function declarations in a generated skeleton test file. Empty
list = pass (count <= max_tests). Single-element list = fail; the calling
skill (`/gvm-walking-skeleton`) emits the AskUserQuestion override flow on
non-empty return.

This module is pure — no AskUserQuestion, no filesystem mutation. Per
Clements decomposition, it does NOT import `_skeleton_gen`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"python", "typescript", "go"})


@dataclass(frozen=True)
class OvercountError:
    file: Path
    count: int
    max_tests: int
    matched_lines: tuple[int, ...]


def lint(
    test_file_path: Path,
    *,
    max_tests: int = 3,
    language: str = "python",
) -> list[OvercountError]:
    """Count test functions in `test_file_path`. Return empty list when count
    <= max_tests; otherwise return a single OvercountError.

    Raises:
        FileNotFoundError when the file does not exist
        ValueError when language is not in {"python", "typescript", "go"}
    """

    lang = language.lower()
    if lang not in _SUPPORTED_LANGUAGES:
        raise ValueError(
            f"unsupported language {language!r}; expected one of "
            f"{sorted(_SUPPORTED_LANGUAGES)}"
        )

    text = test_file_path.read_text(encoding="utf-8")
    matched_lines = _matched_lines(text, lang)
    if len(matched_lines) <= max_tests:
        return []
    return [
        OvercountError(
            file=test_file_path,
            count=len(matched_lines),
            max_tests=max_tests,
            matched_lines=tuple(matched_lines),
        )
    ]


def _matched_lines(text: str, language: str) -> list[int]:
    out: list[int] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if _line_declares_test(raw, language):
            out.append(line_no)
    return out


def _line_declares_test(raw: str, language: str) -> bool:
    # Indented declarations are NOT counted: pytest only collects top-level
    # `test_*` functions; a `def test_inner` nested inside another function
    # is a helper, not a test.
    if raw and raw[0] in (" ", "\t"):
        return False
    stripped = raw.lstrip()
    if language == "python":
        return stripped.startswith("def test_") or stripped.startswith(
            "async def test_"
        )
    if language == "typescript":
        # Cover all three quote styles practitioners use for the test name —
        # single, double, and template literal — for both `test(` and `it(`.
        return (
            stripped.startswith("test('")
            or stripped.startswith('test("')
            or stripped.startswith("test(`")
            or stripped.startswith("it('")
            or stripped.startswith('it("')
            or stripped.startswith("it(`")
        )
    if language == "go":
        return stripped.startswith("func Test")
    # Unreachable — `lint` validates language before calling this helper.
    return False
