"""Tests for `_stubs_parser.append` (P11-C11, honesty-triad spec).

Covers atomic-write semantics, duplicate refusal, frontmatter
preservation, requirement-column round-trip, and missing-file behaviour.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest import mock

import pytest

from _stubs_parser import (
    DuplicatePathError,
    StubEntry,
    append,
    load_stubs,
    serialise,
)


# ----------------------------------------------------------- helpers


def _entry(
    path: str = "stubs/foo.py",
    reason: str = "placeholder reason text",
    plan: str = "real provider plan",
    owner: str = "gerard",
    expiry: dt.date = dt.date(2099, 12, 31),
    requirement: str | None = None,
) -> StubEntry:
    return StubEntry(
        path=path,
        reason=reason,
        real_provider_plan=plan,
        owner=owner,
        expiry=expiry,
        requirement=requirement,
    )


def _write_initial(path: Path, entries: list[StubEntry]) -> None:
    path.write_text(serialise(entries), encoding="utf-8")


# ----------------------------------------------------------- happy path


def test_append_to_empty_stubs_file(tmp_path):
    p = tmp_path / "STUBS.md"
    _write_initial(p, [])
    e = _entry(path="stubs/sorter.py")
    append(p, e)
    loaded = load_stubs(p)
    assert len(loaded) == 1
    assert loaded[0].path == "stubs/sorter.py"
    assert loaded[0].reason == e.reason


def test_append_to_non_empty_stubs_file_preserves_existing(tmp_path):
    p = tmp_path / "STUBS.md"
    existing = _entry(path="stubs/existing.py", reason="existing reason text")
    _write_initial(p, [existing])
    new = _entry(path="stubs/new.py", reason="new reason text exists")
    append(p, new)
    loaded = load_stubs(p)
    paths = [e.path for e in loaded]
    assert paths == ["stubs/existing.py", "stubs/new.py"]


def test_append_preserves_schema_version_frontmatter(tmp_path):
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry()])
    append(p, _entry(path="stubs/another.py"))
    text = p.read_text(encoding="utf-8")
    assert text.startswith("---\nschema_version: 1\n---\n")


def test_append_round_trips_requirement_column(tmp_path):
    p = tmp_path / "STUBS.md"
    _write_initial(p, [])
    e = _entry(path="stubs/req.py", requirement="RE-42")
    append(p, e)
    loaded = load_stubs(p)
    assert len(loaded) == 1
    assert loaded[0].requirement == "RE-42"


# ----------------------------------------------------------- duplicate detection


def test_append_duplicate_path_raises(tmp_path):
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/dup.py")])
    with pytest.raises(DuplicatePathError) as excinfo:
        append(p, _entry(path="stubs/dup.py", reason="different reason text"))
    assert excinfo.value.path == "stubs/dup.py"


def test_append_duplicate_does_not_modify_file(tmp_path):
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/dup.py", reason="original reason text")])
    before = p.read_text(encoding="utf-8")
    with pytest.raises(DuplicatePathError):
        append(p, _entry(path="stubs/dup.py", reason="different reason text"))
    after = p.read_text(encoding="utf-8")
    assert before == after


def test_append_path_substring_is_not_treated_as_duplicate(tmp_path):
    """`stubs/foo.py` and `stubs/foo_helper.py` are distinct."""
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/foo.py")])
    append(p, _entry(path="stubs/foo_helper.py"))
    paths = [e.path for e in load_stubs(p)]
    assert "stubs/foo.py" in paths
    assert "stubs/foo_helper.py" in paths


# ----------------------------------------------------------- atomic-write semantics


def test_append_uses_atomic_rename(tmp_path):
    """Mid-write failure leaves STUBS.md unchanged and no tmp file behind."""
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/orig.py", reason="original reason text")])
    before = p.read_text(encoding="utf-8")

    with mock.patch("_stubs_parser.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            append(p, _entry(path="stubs/new.py"))

    after = p.read_text(encoding="utf-8")
    assert before == after, "STUBS.md must not be modified when rename fails"
    leftovers = list(tmp_path.glob("*.tmp")) + list(tmp_path.glob("STUBS.md.*"))
    # Any tmp file must NOT contain "stubs/new.py" — but better: there must be no leftover
    assert not leftovers, f"tmp file leaked after failed rename: {leftovers}"


# ----------------------------------------------------------- missing file


def test_append_missing_stubs_file_raises_filenotfound(tmp_path):
    p = tmp_path / "does-not-exist-STUBS.md"
    with pytest.raises(FileNotFoundError):
        append(p, _entry())


# ----------------------------------------------------------- invalid entry


def test_append_invalid_entry_does_not_modify_file(tmp_path):
    """An entry with '|' in a field must be rejected before writing."""
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/orig.py")])
    before = p.read_text(encoding="utf-8")

    bad = _entry(path="stubs/bad.py", reason="reason with | pipe in it")
    from _stubs_parser import StubsParseError

    with pytest.raises(StubsParseError):
        append(p, bad)

    after = p.read_text(encoding="utf-8")
    assert before == after


def test_append_invalid_path_prefix_rejected_before_write(tmp_path):
    """A path that does not start with stubs/ or walking-skeleton/stubs/
    must be rejected pre-write — otherwise the next load_stubs would
    fail and STUBS.md would be permanently unloadable."""
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/orig.py")])
    before = p.read_text(encoding="utf-8")

    from _stubs_parser import StubsParseError

    with pytest.raises(StubsParseError):
        append(p, _entry(path="src/stubs/foo.py"))

    assert p.read_text(encoding="utf-8") == before
    # File still loadable: confirms append did not corrupt it.
    assert load_stubs(p)[0].path == "stubs/orig.py"


def test_append_short_reason_rejected_before_write(tmp_path):
    """Reason shorter than MIN_REASON_LEN must fail before write."""
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/orig.py")])
    before = p.read_text(encoding="utf-8")

    from _stubs_parser import StubsParseError

    with pytest.raises(StubsParseError):
        append(p, _entry(path="stubs/short.py", reason="too short"))

    assert p.read_text(encoding="utf-8") == before


def test_append_empty_plan_rejected_before_write(tmp_path):
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/orig.py")])
    before = p.read_text(encoding="utf-8")
    from _stubs_parser import StubsParseError

    with pytest.raises(StubsParseError):
        append(p, _entry(path="stubs/x.py", plan=""))
    assert p.read_text(encoding="utf-8") == before


def test_append_empty_owner_rejected_before_write(tmp_path):
    p = tmp_path / "STUBS.md"
    _write_initial(p, [_entry(path="stubs/orig.py")])
    before = p.read_text(encoding="utf-8")
    from _stubs_parser import StubsParseError

    with pytest.raises(StubsParseError):
        append(p, _entry(path="stubs/x.py", owner=""))
    assert p.read_text(encoding="utf-8") == before


def test_append_walking_skeleton_path_prefix_accepted(tmp_path):
    """Both PATH_PREFIXES are valid: stubs/ AND walking-skeleton/stubs/."""
    p = tmp_path / "STUBS.md"
    _write_initial(p, [])
    append(p, _entry(path="walking-skeleton/stubs/foo.py"))
    paths = [e.path for e in load_stubs(p)]
    assert paths == ["walking-skeleton/stubs/foo.py"]
