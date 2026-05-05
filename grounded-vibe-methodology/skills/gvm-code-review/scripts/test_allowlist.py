"""Tests for `_allowlist.load_allowlist` (honesty-triad ADR-108)."""

from __future__ import annotations

from pathlib import Path

import pytest

from _allowlist import (
    KIND_VALUES,
    Allowlist,
    AllowlistEntry,
    AllowlistError,
    MalformedAllowlistLineError,
    MissingPathError,
    UnknownKindError,
    load_allowlist,
)


def _assert_allowlist(obj) -> None:
    assert isinstance(obj, Allowlist)


def _touch(root: Path, rel: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")


def test_kind_values_constant():
    assert KIND_VALUES == frozenset({"enum", "constant", "fixture"})


def test_empty_file_yields_empty_allowlist(tmp_path: Path):
    f = tmp_path / ".stub-allowlist"
    f.write_text("")
    out = load_allowlist(f, project_root=tmp_path)
    _assert_allowlist(out)
    assert out.entries == ()
    assert out.pairs == frozenset()
    assert out.kinds == {}


def test_blank_and_comment_lines_skipped(tmp_path: Path):
    _touch(tmp_path, "constants/iso.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text(
        "# header comment\n"
        "\n"
        "   \n"
        "constants/iso.py::ISO_CODES | enum | ISO 3166 country codes\n"
        "# trailing comment\n"
    )
    out = load_allowlist(f, project_root=tmp_path)
    assert len(out.entries) == 1
    assert out.entries[0].symbol == "ISO_CODES"


def test_single_valid_entry_round_trips(tmp_path: Path):
    _touch(tmp_path, "constants/iso.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("constants/iso.py::ISO_CODES | enum | ISO codes\n")
    out = load_allowlist(f, project_root=tmp_path)
    entry = out.entries[0]
    assert isinstance(entry, AllowlistEntry)
    assert entry.path == Path("constants/iso.py")
    assert entry.symbol == "ISO_CODES"
    assert entry.kind == "enum"
    assert entry.justification == "ISO codes"
    assert ("constants/iso.py", "ISO_CODES") in out.pairs
    assert out.kinds[("constants/iso.py", "ISO_CODES")] == "enum"


def test_multiple_entries(tmp_path: Path):
    _touch(tmp_path, "a.py")
    _touch(tmp_path, "b.py")
    _touch(tmp_path, "c.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text(
        "a.py::A | enum | first\n"
        "b.py::B | constant | second\n"
        "c.py::C | fixture | third\n"
    )
    out = load_allowlist(f, project_root=tmp_path)
    assert len(out.entries) == 3
    assert {e.kind for e in out.entries} == {"enum", "constant", "fixture"}
    assert out.pairs == {("a.py", "A"), ("b.py", "B"), ("c.py", "C")}


def test_whitespace_around_pipes_stripped(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("   x.py::SYM   |   enum   |   reason   \n")
    out = load_allowlist(f, project_root=tmp_path)
    e = out.entries[0]
    assert e.symbol == "SYM"
    assert e.kind == "enum"
    assert e.justification == "reason"


def test_missing_kind_field_raises_with_line_no(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text(
        "# header\n"
        "x.py::SYM | enum | ok\n"
        "x.py::OTHER | missing-justification\n"  # only 1 pipe
    )
    with pytest.raises(MalformedAllowlistLineError, match=r":3:"):
        load_allowlist(f, project_root=tmp_path)


def test_too_many_pipes_raises(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::SYM | enum | a | b\n")
    with pytest.raises(MalformedAllowlistLineError, match=r":1:"):
        load_allowlist(f, project_root=tmp_path)


def test_path_symbol_separator_missing_raises(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py-SYM | enum | reason\n")
    with pytest.raises(MalformedAllowlistLineError, match="::"):
        load_allowlist(f, project_root=tmp_path)


def test_multiple_double_colons_raises(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::Class::method | enum | reason\n")
    with pytest.raises(MalformedAllowlistLineError):
        load_allowlist(f, project_root=tmp_path)


def test_unknown_kind_raises(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::SYM | enums | reason\n")
    with pytest.raises(UnknownKindError, match="enums"):
        load_allowlist(f, project_root=tmp_path)


def test_unknown_kind_lists_valid_options(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::SYM | bogus | reason\n")
    with pytest.raises(UnknownKindError, match="constant.*enum.*fixture"):
        load_allowlist(f, project_root=tmp_path)


def test_missing_path_raises(tmp_path: Path):
    f = tmp_path / ".stub-allowlist"
    f.write_text("does/not/exist.py::SYM | enum | reason\n")
    with pytest.raises(MissingPathError, match="does/not/exist.py"):
        load_allowlist(f, project_root=tmp_path)


def test_missing_path_names_line_number(tmp_path: Path):
    _touch(tmp_path, "ok.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("ok.py::A | enum | ok\nmissing.py::B | enum | ok\n")
    with pytest.raises(MissingPathError, match=r":2:"):
        load_allowlist(f, project_root=tmp_path)


def test_first_error_aborts_no_partial_load(tmp_path: Path):
    """ADR-108: 'no partial load'."""
    _touch(tmp_path, "ok.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text(
        "ok.py::A | enum | first\n"
        "ok.py::B | bogus | bad-kind\n"  # error on line 2
        "ok.py::C | constant | would-be-third\n"
    )
    with pytest.raises(UnknownKindError):
        load_allowlist(f, project_root=tmp_path)


def test_all_errors_inherit_base(tmp_path: Path):
    assert issubclass(MalformedAllowlistLineError, AllowlistError)
    assert issubclass(UnknownKindError, AllowlistError)
    assert issubclass(MissingPathError, AllowlistError)


def test_allowlist_is_immutable(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::SYM | enum | reason\n")
    out = load_allowlist(f, project_root=tmp_path)
    with pytest.raises(Exception):  # FrozenInstanceError, AttributeError, TypeError
        out.entries = ()  # type: ignore[misc]


def test_project_root_defaults_to_cwd(tmp_path: Path, monkeypatch):
    _touch(tmp_path, "rel.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("rel.py::SYM | enum | reason\n")
    monkeypatch.chdir(tmp_path)
    out = load_allowlist(f)
    assert len(out.entries) == 1


def test_load_accepts_str_path(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::SYM | enum | reason\n")
    out = load_allowlist(str(f), project_root=str(tmp_path))
    assert len(out.entries) == 1


def test_loading_nonexistent_file_raises_allowlist_error(tmp_path: Path):
    with pytest.raises(AllowlistError, match="not found"):
        load_allowlist(tmp_path / "missing", project_root=tmp_path)


def test_pairs_and_kinds_consistent(tmp_path: Path):
    _touch(tmp_path, "x.py")
    _touch(tmp_path, "y.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::A | enum | a\ny.py::B | constant | b\n")
    out = load_allowlist(f, project_root=tmp_path)
    assert set(out.kinds.keys()) == set(out.pairs)


def test_justification_with_internal_pipes_rejected(tmp_path: Path):
    """ADR-108 says 'splits on |' — internal pipes break the parse and must error."""
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::SYM | enum | uses | as separator\n")
    with pytest.raises(MalformedAllowlistLineError):
        load_allowlist(f, project_root=tmp_path)


def test_empty_field_after_strip_rejected(tmp_path: Path):
    _touch(tmp_path, "x.py")
    f = tmp_path / ".stub-allowlist"
    f.write_text("x.py::SYM |  | reason\n")  # empty kind
    with pytest.raises(UnknownKindError):
        load_allowlist(f, project_root=tmp_path)
