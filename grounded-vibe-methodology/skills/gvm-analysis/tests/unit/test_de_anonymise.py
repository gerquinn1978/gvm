"""Unit tests for ``scripts/de_anonymise.py`` (anonymisation-pipeline ADR-405).

Test cases TC-AN-37-01..04. P14-C03.
"""

from __future__ import annotations

import csv
import html
import html.parser
from pathlib import Path

import pytest

import de_anonymise


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_mapping(path: Path, rows: list[tuple[str, str, str]]) -> None:
    """Write a mapping CSV in the canonical format produced by anonymise.py."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(("column", "original_value", "token"))
        for r in rows:
            writer.writerow(r)


@pytest.fixture()
def basic_mapping(tmp_path: Path) -> Path:
    p = tmp_path / "mapping.csv"
    _write_mapping(
        p,
        [
            ("department", "Sales", "TOK_department_001"),
            ("department", "Engineering", "TOK_department_002"),
            ("region", "North", "TOK_region_001"),
            ("region", "South", "TOK_region_002"),
        ],
    )
    return p


# ---------------------------------------------------------------------------
# 1. Basic substitution
# ---------------------------------------------------------------------------


def test_basic_substitution_single_file(tmp_path: Path, basic_mapping: Path) -> None:
    inp = tmp_path / "report.html"
    inp.write_text(
        "<html><body><p>Top: TOK_department_001 / TOK_region_002</p></body></html>"
    )
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        [
            "--input",
            str(inp),
            "--mapping",
            str(basic_mapping),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    text = out.read_text()
    assert "TOK_department_001" not in text
    assert "TOK_region_002" not in text
    assert "Sales" in text
    assert "South" in text


# ---------------------------------------------------------------------------
# 2. HTML escaping (TC-AN-37-04 — AT&T round-trip)
# ---------------------------------------------------------------------------


def test_html_special_char_escaping_at_and_t(tmp_path: Path) -> None:
    mapping = tmp_path / "mapping.csv"
    _write_mapping(
        mapping,
        [
            ("vendor", "AT&T", "TOK_vendor_001"),
            ("vendor", '"Risky" & <Co>', "TOK_vendor_002"),
        ],
    )
    inp = tmp_path / "report.html"
    inp.write_text(
        "<html><body><p>Vendor: TOK_vendor_001</p>"
        "<p>Other: TOK_vendor_002</p></body></html>"
    )
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        [
            "--input",
            str(inp),
            "--mapping",
            str(mapping),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    text = out.read_text()
    # AT&T -> AT&amp;T (escaped &)
    assert "AT&amp;T" in text
    assert "AT&T" not in text  # raw must not appear (escape must happen)
    # The double-quoted, ampersand and angle-bracket value escaped.
    expected = html.escape('"Risky" & <Co>', quote=True)
    assert expected in text


def test_mapping_storing_pre_escaped_values_is_double_escaped(
    tmp_path: Path,
) -> None:
    """Spec guard: mapping CSV stores RAW values; if a builder pre-escapes,
    the round-trip is broken. Document the failure mode by asserting it."""
    mapping = tmp_path / "mapping.csv"
    _write_mapping(
        mapping,
        [("vendor", "AT&amp;T", "TOK_vendor_001")],  # bug: pre-escaped
    )
    inp = tmp_path / "r.html"
    inp.write_text("<p>TOK_vendor_001</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(mapping), "--output", str(out)]
    )
    assert rc == 0
    # Double-escaped because mapping was wrong; this is a builder bug.
    assert "AT&amp;amp;T" in out.read_text()


# ---------------------------------------------------------------------------
# 3. Idempotence (TC-AN-37-02)
# ---------------------------------------------------------------------------


def test_idempotent_second_run_no_change(tmp_path: Path, basic_mapping: Path) -> None:
    inp = tmp_path / "r.html"
    inp.write_text("<p>TOK_department_001 and TOK_region_001</p>")
    out1 = tmp_path / "out1.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(out1)]
    )
    assert rc == 0
    out2 = tmp_path / "out2.html"
    rc = de_anonymise.main(
        ["--input", str(out1), "--mapping", str(basic_mapping), "--output", str(out2)]
    )
    assert rc == 0
    assert out1.read_bytes() == out2.read_bytes()


# ---------------------------------------------------------------------------
# 4. False-positive guards (TC-AN-37-02)
# ---------------------------------------------------------------------------


def test_literal_tok_outside_column_list_not_replaced(
    tmp_path: Path, basic_mapping: Path
) -> None:
    """A token-shaped string for an UNKNOWN column must not be replaced."""
    inp = tmp_path / "r.html"
    inp.write_text("<p>Known: TOK_department_001. Unknown: TOK_unrelated_999.</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(out)]
    )
    assert rc == 0
    text = out.read_text()
    assert "Sales" in text
    assert "TOK_unrelated_999" in text  # untouched


def test_partial_digit_suffix_not_matched(tmp_path: Path, basic_mapping: Path) -> None:
    """Producer pads to >=3 digits; the regex enforces \\d{3,}.
    A two-digit suffix must NOT match (would be a false positive)."""
    inp = tmp_path / "r.html"
    inp.write_text("<p>Short suffix: TOK_department_00 (literal)</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(out)]
    )
    assert rc == 0
    assert "TOK_department_00" in out.read_text()


def test_token_in_attribute_value_replaced(tmp_path: Path, basic_mapping: Path) -> None:
    inp = tmp_path / "r.html"
    inp.write_text('<a href="/x" data-name="TOK_department_001">click</a>')
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(out)]
    )
    assert rc == 0
    text = out.read_text()
    assert "TOK_department_001" not in text
    assert "Sales" in text


# ---------------------------------------------------------------------------
# 5. Directory walk (TC-AN-37-03)
# ---------------------------------------------------------------------------


def test_directory_walk_replaces_all_html_files(
    tmp_path: Path, basic_mapping: Path
) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "hub.html").write_text("<p>TOK_department_001</p>")
    sub = site / "drill"
    sub.mkdir()
    (sub / "a.html").write_text("<p>TOK_department_002</p>")
    (sub / "b.html").write_text("<p>TOK_region_001</p>")
    # A non-HTML file must be left untouched.
    (sub / "data.json").write_text('{"x": "TOK_department_001"}')

    rc = de_anonymise.main(
        ["--input", str(site), "--mapping", str(basic_mapping), "--in-place"]
    )
    assert rc == 0

    assert "Sales" in (site / "hub.html").read_text()
    assert "Engineering" in (sub / "a.html").read_text()
    assert "North" in (sub / "b.html").read_text()
    # Non-HTML untouched
    assert "TOK_department_001" in (sub / "data.json").read_text()


def test_directory_walk_with_no_html_files_succeeds_quietly(
    tmp_path: Path, basic_mapping: Path
) -> None:
    site = tmp_path / "empty"
    site.mkdir()
    rc = de_anonymise.main(
        ["--input", str(site), "--mapping", str(basic_mapping), "--in-place"]
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# 6. --in-place vs --output
# ---------------------------------------------------------------------------


def test_in_place_overwrites_input(tmp_path: Path, basic_mapping: Path) -> None:
    inp = tmp_path / "r.html"
    inp.write_text("<p>TOK_department_001</p>")
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--in-place"]
    )
    assert rc == 0
    assert "Sales" in inp.read_text()


def test_output_flag_writes_separate_file_input_unchanged(
    tmp_path: Path, basic_mapping: Path
) -> None:
    inp = tmp_path / "r.html"
    inp.write_text("<p>TOK_department_001</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(out)]
    )
    assert rc == 0
    assert "TOK_department_001" in inp.read_text()  # untouched
    assert "Sales" in out.read_text()


def test_in_place_and_output_mutually_exclusive(
    tmp_path: Path, basic_mapping: Path
) -> None:
    inp = tmp_path / "r.html"
    inp.write_text("<p>TOK_department_001</p>")
    out = tmp_path / "out.html"
    with pytest.raises(SystemExit):
        rc = de_anonymise.main(
            [
                "--input",
                str(inp),
                "--mapping",
                str(basic_mapping),
                "--output",
                str(out),
                "--in-place",
            ]
        )
        assert rc == 0


def test_neither_in_place_nor_output_refuses(
    tmp_path: Path, basic_mapping: Path, capsys: pytest.CaptureFixture
) -> None:
    inp = tmp_path / "r.html"
    inp.write_text("<p>TOK_department_001</p>")
    rc = de_anonymise.main(["--input", str(inp), "--mapping", str(basic_mapping)])
    assert rc == 1
    assert "ERROR" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 7. Diagnostics on missing mapping
# ---------------------------------------------------------------------------


def test_missing_mapping_file_emits_diagnostic_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    inp = tmp_path / "r.html"
    inp.write_text("<p>x</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        [
            "--input",
            str(inp),
            "--mapping",
            str(tmp_path / "no-such.csv"),
            "--output",
            str(out),
        ]
    )
    assert rc == 1
    assert "ERROR" in capsys.readouterr().err


def test_missing_input_file_emits_diagnostic_exit_1(
    tmp_path: Path, basic_mapping: Path, capsys: pytest.CaptureFixture
) -> None:
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        [
            "--input",
            str(tmp_path / "no-such.html"),
            "--mapping",
            str(basic_mapping),
            "--output",
            str(out),
        ]
    )
    assert rc == 1


# ---------------------------------------------------------------------------
# 8. HTML structure preservation (TC-AN-37-04)
# ---------------------------------------------------------------------------


class _StrictParser(html.parser.HTMLParser):
    def error(self, message: str) -> None:  # pragma: no cover - py3.10+ no-op
        raise AssertionError(f"HTML parse error: {message}")


def test_html_structure_preserved_parses(tmp_path: Path, basic_mapping: Path) -> None:
    inp = tmp_path / "r.html"
    inp.write_text(
        "<!DOCTYPE html><html><head><title>x</title></head>"
        "<body><main><section><p>TOK_department_001</p></section></main>"
        "</body></html>"
    )
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(out)]
    )
    assert rc == 0
    parser = _StrictParser()
    parser.feed(out.read_text())  # must not raise


# ---------------------------------------------------------------------------
# 9. Property: every token in the mapping is replaced when present
# ---------------------------------------------------------------------------


def test_property_every_token_in_mapping_is_replaced(
    tmp_path: Path, basic_mapping: Path
) -> None:
    inp = tmp_path / "r.html"
    body = " ".join(
        [
            "TOK_department_001",
            "TOK_department_002",
            "TOK_region_001",
            "TOK_region_002",
        ]
    )
    inp.write_text(f"<p>{body}</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(out)]
    )
    assert rc == 0
    text = out.read_text()
    for token in [
        "TOK_department_001",
        "TOK_department_002",
        "TOK_region_001",
        "TOK_region_002",
    ]:
        assert token not in text
    for value in ["Sales", "Engineering", "North", "South"]:
        assert html.escape(value, quote=True) in text


# ---------------------------------------------------------------------------
# 10. Idempotence property — byte-equal second run
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        "<p>TOK_department_001</p>",
        "<p>multiple TOK_department_001 and TOK_region_002</p>",
        '<a href="/x">TOK_department_002</a>',
        "<p>no tokens here at all</p>",
    ],
)
def test_idempotence_property_run_twice_byte_equal(
    tmp_path: Path, basic_mapping: Path, body: str
) -> None:
    inp = tmp_path / "in.html"
    inp.write_text(body)
    once = tmp_path / "once.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(basic_mapping), "--output", str(once)]
    )
    assert rc == 0
    twice = tmp_path / "twice.html"
    rc = de_anonymise.main(
        ["--input", str(once), "--mapping", str(basic_mapping), "--output", str(twice)]
    )
    assert rc == 0
    assert once.read_bytes() == twice.read_bytes()


# ---------------------------------------------------------------------------
# 11. Residual-token guard (ADR-405 step 5 — core safety net)
# ---------------------------------------------------------------------------


def test_residual_known_column_token_refuses_and_does_not_write_output(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """ADR-405 step 5: post-replace there must be no token of any form
    `TOK_{any_known_column}_\\d+`. If the input contains a token whose
    column IS in the mapping but whose index has no entry, ``_substitute``
    leaves it in place and the post-check must refuse.

    This is the core safety net: removing or inverting `_has_residual_token`
    would silently produce partially-de-anonymised HTML. Without this test,
    the regression would not be caught.
    """
    mapping = tmp_path / "mapping.csv"
    _write_mapping(
        mapping,
        [("department", "Sales", "TOK_department_001")],  # only index 001
    )
    inp = tmp_path / "r.html"
    inp.write_text("<p>known: TOK_department_001 unknown: TOK_department_099</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(mapping), "--output", str(out)]
    )
    assert rc == 1
    assert "residual token" in capsys.readouterr().err
    assert not out.exists(), "partial output must not be written"


# ---------------------------------------------------------------------------
# 12. Empty mapping refused (consumer-of-build_match_regex contract)
# ---------------------------------------------------------------------------


def test_empty_mapping_refused(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    mapping = tmp_path / "empty.csv"
    _write_mapping(mapping, [])  # header only
    inp = tmp_path / "r.html"
    inp.write_text("<p>x</p>")
    out = tmp_path / "out.html"
    rc = de_anonymise.main(
        ["--input", str(inp), "--mapping", str(mapping), "--output", str(out)]
    )
    assert rc == 1
    assert "ERROR" in capsys.readouterr().err
