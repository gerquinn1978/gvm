"""P11-C01 unit tests for `_discovery.py` — the boundary source-scanner.

Spec ref: walking-skeleton ADR-402.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _discovery
from _discovery import BoundaryCandidate, load_heuristics, scan


HEURISTICS_FIXTURE = """\
# Boundary Discovery Heuristics

## Python
- HTTP outbound: `requests.`, `httpx.`
- Database: `psycopg2.`
- Filesystem: `open(`

## TypeScript
- HTTP outbound: `fetch(`, `axios.`
"""


def _write_heuristics(tmp_path: Path, body: str = HEURISTICS_FIXTURE) -> Path:
    p = tmp_path / "boundary-discovery.md"
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------- load_heuristics


def test_load_heuristics_python_returns_category_token_pairs(tmp_path: Path) -> None:
    path = _write_heuristics(tmp_path)
    pairs = load_heuristics(path, language="python")
    assert ("http_api", "requests.") in pairs
    assert ("http_api", "httpx.") in pairs
    assert ("database", "psycopg2.") in pairs
    assert ("filesystem", "open(") in pairs
    assert all(t != "fetch(" for _c, t in pairs), "TypeScript tokens leaked into Python"


def test_load_heuristics_typescript(tmp_path: Path) -> None:
    path = _write_heuristics(tmp_path)
    pairs = load_heuristics(path, language="typescript")
    assert ("http_api", "fetch(") in pairs
    assert ("http_api", "axios.") in pairs


def test_load_heuristics_unknown_language_raises(tmp_path: Path) -> None:
    path = _write_heuristics(tmp_path)
    with pytest.raises(KeyError) as exc:
        load_heuristics(path, language="cobol")
    assert "cobol" in str(exc.value)


def test_load_heuristics_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_heuristics(tmp_path / "does-not-exist.md", language="python")


# ---------------------------------------------------------------- scan


def test_scan_finds_python_http_call(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    src = tmp_path / "src" / "client.py"
    src.parent.mkdir(parents=True)
    src.write_text(
        "import requests\n\nrequests.get('https://example.com')\n", encoding="utf-8"
    )

    candidates = scan(tmp_path, language="python", heuristics_path=heur)

    matches = [c for c in candidates if c.name == "requests."]
    assert len(matches) >= 1
    assert matches[0].type == "http_api"
    # Path is relative to project root.
    assert matches[0].file == Path("src/client.py")
    assert matches[0].line >= 1


def test_scan_returns_empty_for_empty_project(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    candidates = scan(tmp_path, language="python", heuristics_path=heur)
    assert candidates == []


def test_scan_skips_files_outside_language(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    # A .ts file with `fetch(` should NOT be picked up when scanning python.
    ts = tmp_path / "app.ts"
    ts.write_text("fetch('https://example.com')", encoding="utf-8")
    candidates = scan(tmp_path, language="python", heuristics_path=heur)
    assert candidates == []


def test_scan_skips_binary_and_unreadable_files(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    # Binary content with the bytes that decode to `requests.` — even if it
    # decodes loosely, the scanner must not crash.
    binfile = tmp_path / "blob.py"
    binfile.write_bytes(b"\x80\x81\x82requests.\xff\xfe")

    # Should not raise. May or may not produce a candidate (depends on
    # `errors="replace"` behaviour) — what matters is no crash.
    scan(tmp_path, language="python", heuristics_path=heur)


def test_scan_results_are_sorted_stable(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    (tmp_path / "b.py").write_text("requests.get('x')\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("requests.get('x')\n", encoding="utf-8")
    candidates = scan(tmp_path, language="python", heuristics_path=heur)
    files = [c.file for c in candidates]
    assert files == sorted(files), "scan results must be sorted by file"


def test_scan_records_line_number(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    src = tmp_path / "x.py"
    src.write_text(
        "# blank\n# blank\nimport requests\nrequests.get('x')\n", encoding="utf-8"
    )
    candidates = [
        c
        for c in scan(tmp_path, language="python", heuristics_path=heur)
        if c.name == "requests."
    ]
    # Two matches: line 3 (import requests — but `requests.` requires the dot,
    # so only the call site on line 4 matches).
    lines = sorted(c.line for c in candidates)
    assert lines == [4]


def test_scan_missing_project_root_raises(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    with pytest.raises((FileNotFoundError, NotADirectoryError)):
        scan(tmp_path / "nope", language="python", heuristics_path=heur)


def test_scan_project_root_must_be_directory(tmp_path: Path) -> None:
    heur = _write_heuristics(tmp_path)
    afile = tmp_path / "afile.py"
    afile.write_text("requests.get('x')", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        scan(afile, language="python", heuristics_path=heur)


@pytest.mark.parametrize(
    "category, pattern, expected_type",
    [
        ("HTTP outbound", "requests.", "http_api"),
        ("Database", "psycopg2.", "database"),
        ("Filesystem", "open(", "filesystem"),
        ("Cloud SDK", "boto3.", "cloud_sdk"),
        ("Subprocess", "subprocess.run", "subprocess"),
        ("Email", "smtplib.", "email"),
    ],
)
def test_category_to_type_mapping(
    category: str, pattern: str, expected_type: str
) -> None:
    assert _discovery._category_to_type(category) == expected_type


def test_boundary_candidate_is_frozen() -> None:
    bc = BoundaryCandidate(name="x", type="http_api", file=Path("a.py"), line=1)
    with pytest.raises(Exception):
        bc.line = 2  # type: ignore[misc]
