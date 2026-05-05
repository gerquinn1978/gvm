"""Defect-intake tests for `/gvm-explore-test` (P11-C07).

Covers:
  - TC-ET-3-01: GWT defect with reproduction path accepted as DefectEntry
  - TC-ET-3-02: Defect with no reproduction path re-filed as ObservationEntry
  - TC-ET-3-03 boundary: XSS-laden GWT stored verbatim (escape happens in
    P11-C08's renderer, not here)

Plus defensive coverage of every ADR-203 / ADR-205 / ADR-206 branch:
severity enum, blank GWT rejection, ID auto-increment, separate D / O
namespaces, partial handover atomic write, session_nnn format.
"""

from __future__ import annotations

import pytest

from _defect_intake import (
    DefectEntry,
    IntakeError,
    IntakeSession,
    ObservationEntry,
    remove_partial_handover,
    write_partial_handover,
)


# ----------------------------------------------------------------- TC-ET-3-01


def test_gwt_defect_with_reproduction_accepted_as_defect():
    """TC-ET-3-01: severity=Important + non-empty reproduction → DefectEntry."""
    session = IntakeSession("001")
    entry = session.record(
        severity="Important",
        given="the report renderer is invoked",
        when="the input contains a malformed defect",
        then="the output is still well-formed HTML",
        reproduction="run pytest test_report_writer.py::test_malformed",
    )
    assert isinstance(entry, DefectEntry)
    assert entry.severity == "Important"
    assert entry.id == "D-001"
    assert entry in session.defects
    assert entry not in session.observations


# ----------------------------------------------------------------- TC-ET-3-02


def test_gwt_defect_without_reproduction_refiled_as_observation():
    """TC-ET-3-02: severity ≥ Minor + blank reproduction → ObservationEntry."""
    session = IntakeSession("001")
    entry = session.record(
        severity="Important",
        given="x",
        when="y",
        then="z",
        reproduction="",
    )
    assert isinstance(entry, ObservationEntry)
    assert not hasattr(entry, "severity")
    assert entry.id == "O-001"
    assert entry in session.observations
    assert entry not in session.defects


@pytest.mark.parametrize("sev", ["Critical", "Important", "Minor"])
def test_blank_reproduction_refiles_at_every_defect_severity(sev):
    session = IntakeSession("001")
    entry = session.record(severity=sev, given="g", when="w", then="t", reproduction="")
    assert isinstance(entry, ObservationEntry)


@pytest.mark.parametrize("sev", ["Critical", "Important", "Minor"])
def test_defect_path_at_every_defect_severity(sev):
    """Symmetric happy-path coverage to the blank-repro re-filing test —
    every defect severity with non-blank reproduction → DefectEntry."""
    session = IntakeSession("001")
    entry = session.record(severity=sev, given="g", when="w", then="t", reproduction="r")
    assert isinstance(entry, DefectEntry)
    assert entry.severity == sev


def test_observation_severity_with_reproduction_still_observation():
    """ADR-203: severity=Observation takes priority over reproduction state.
    A practitioner who types reproduction steps but classifies the entry as
    Observation still gets an ObservationEntry — the helper does NOT
    second-guess (ADR-205)."""
    session = IntakeSession("001")
    entry = session.record(
        severity="Observation",
        given="g",
        when="w",
        then="t",
        reproduction="full repro steps here",
    )
    assert isinstance(entry, ObservationEntry)


@pytest.mark.parametrize("blank", ["", "   ", "\n", "\t \t"])
def test_whitespace_only_reproduction_treated_as_blank(blank):
    session = IntakeSession("001")
    entry = session.record(
        severity="Critical", given="g", when="w", then="t", reproduction=blank
    )
    assert isinstance(entry, ObservationEntry)


# ----------------------------------------------------------------- TC-ET-3-03 boundary


def test_xss_payload_stored_verbatim_at_intake():
    """TC-ET-3-03 boundary: practitioner strings are opaque payload at intake.
    The actual `html.escape()` lives in P11-C08's renderer; intake must NOT
    pre-process or strip the payload, otherwise the renderer's escape pass
    is operating on already-modified content (which would silently mask
    bugs in either layer)."""
    payload = "<script>alert(1)</script>"
    session = IntakeSession("001")
    entry = session.record(
        severity="Critical",
        given=payload,
        when="b",
        then="c",
        reproduction="r",
    )
    assert isinstance(entry, DefectEntry)
    assert entry.given == payload  # verbatim — no escape, no normalisation


# ----------------------------------------------------------------- severity enum


def test_observation_severity_always_routes_to_observations():
    session = IntakeSession("001")
    entry = session.record(severity="Observation", given="g", when="w", then="t")
    assert isinstance(entry, ObservationEntry)


def test_observation_severity_no_reproduction_required():
    session = IntakeSession("001")
    # Should not raise even with blank reproduction
    entry = session.record(
        severity="Observation", given="g", when="w", then="t", reproduction=""
    )
    assert isinstance(entry, ObservationEntry)


@pytest.mark.parametrize(
    "bad_sev", ["critical", "Severe", "minor", "", "Show-stopper", None]
)
def test_invalid_severity_rejected(bad_sev):
    session = IntakeSession("001")
    with pytest.raises(IntakeError) as exc:
        session.record(
            severity=bad_sev, given="g", when="w", then="t", reproduction="r"
        )
    assert exc.value.field == "severity"


# ----------------------------------------------------------------- GWT validation


@pytest.mark.parametrize("blank_field", ["given", "when", "then"])
def test_blank_gwt_field_rejected(blank_field):
    kwargs = dict(severity="Important", given="g", when="w", then="t", reproduction="r")
    kwargs[blank_field] = ""
    session = IntakeSession("001")
    with pytest.raises(IntakeError) as exc:
        session.record(**kwargs)
    assert exc.value.field == blank_field


@pytest.mark.parametrize("blank_field", ["given", "when", "then"])
def test_whitespace_only_gwt_field_rejected(blank_field):
    kwargs = dict(severity="Important", given="g", when="w", then="t", reproduction="r")
    kwargs[blank_field] = "   \t  "
    session = IntakeSession("001")
    with pytest.raises(IntakeError) as exc:
        session.record(**kwargs)
    assert exc.value.field == blank_field


# ----------------------------------------------------------------- IDs


def test_defect_ids_auto_increment():
    session = IntakeSession("001")
    a = session.record(
        severity="Important", given="g", when="w", then="t", reproduction="r"
    )
    b = session.record(
        severity="Critical", given="g", when="w", then="t", reproduction="r"
    )
    assert a.id == "D-001"
    assert b.id == "D-002"


def test_observation_ids_auto_increment():
    session = IntakeSession("001")
    a = session.record(severity="Observation", given="g", when="w", then="t")
    b = session.record(
        severity="Important", given="g", when="w", then="t", reproduction=""
    )
    assert a.id == "O-001"
    assert b.id == "O-002"


def test_defect_and_observation_id_namespaces_independent():
    """ADR-206 — D-NNN and O-NNN are separate sequences."""
    session = IntakeSession("001")
    d1 = session.record(
        severity="Critical", given="g", when="w", then="t", reproduction="r"
    )
    o1 = session.record(severity="Observation", given="g", when="w", then="t")
    d2 = session.record(
        severity="Minor", given="g", when="w", then="t", reproduction="r"
    )
    o2 = session.record(
        severity="Important", given="g", when="w", then="t", reproduction=""
    )
    assert (d1.id, d2.id) == ("D-001", "D-002")
    assert (o1.id, o2.id) == ("O-001", "O-002")


# ----------------------------------------------------------------- session_nnn


@pytest.mark.parametrize("ok", ["001", "042", "999", "000"])
def test_session_nnn_accepts_three_digit(ok):
    s = IntakeSession(ok)
    assert s.session_nnn == ok


@pytest.mark.parametrize("bad", ["1", "01", "0001", "abc", "", "00a"])
def test_session_nnn_rejects_non_three_digit(bad):
    with pytest.raises(IntakeError) as exc:
        IntakeSession(bad)
    assert exc.value.field == "session_nnn"


# ----------------------------------------------------------------- stub_path


def test_stub_path_captured_when_provided():
    session = IntakeSession("001")
    entry = session.record(
        severity="Critical",
        given="g",
        when="w",
        then="t",
        reproduction="r",
        stub_path="STUBS.md#provider-x",
    )
    assert entry.stub_path == "STUBS.md#provider-x"


def test_stub_path_defaults_to_none():
    session = IntakeSession("001")
    entry = session.record(
        severity="Critical", given="g", when="w", then="t", reproduction="r"
    )
    assert entry.stub_path is None


# ----------------------------------------------------------------- immutability


def test_defects_returns_tuple_not_list():
    session = IntakeSession("001")
    session.record(severity="Critical", given="g", when="w", then="t", reproduction="r")
    assert isinstance(session.defects, tuple)
    assert isinstance(session.observations, tuple)


def test_defect_entry_is_frozen():
    session = IntakeSession("001")
    entry = session.record(
        severity="Critical", given="g", when="w", then="t", reproduction="r"
    )
    with pytest.raises(Exception):
        entry.severity = "Minor"  # type: ignore[misc]


def test_observation_entry_is_frozen():
    session = IntakeSession("001")
    entry = session.record(severity="Observation", given="g", when="w", then="t")
    with pytest.raises(Exception):
        entry.given = "tampered"  # type: ignore[misc]


# ----------------------------------------------------------------- IntakeError


def test_intake_error_carries_field_and_reason():
    err = IntakeError("severity", "must be one of Critical/Important/Minor/Observation")
    assert err.field == "severity"
    assert err.reason.startswith("must be one of")
    assert "severity" in str(err)


# ----------------------------------------------------------------- partial handover


def test_write_partial_handover_creates_file_at_canonical_path(tmp_path):
    session = IntakeSession("042")
    session.record(severity="Critical", given="g", when="w", then="t", reproduction="r")
    out = write_partial_handover(session, tmp_path)
    assert out == tmp_path / "explore-042-partial.md"
    assert out.exists()


def test_write_partial_handover_includes_session_nnn_and_counts(tmp_path):
    session = IntakeSession("007")
    session.record(severity="Critical", given="g", when="w", then="t", reproduction="r")
    session.record(severity="Observation", given="g", when="w", then="t")
    out = write_partial_handover(session, tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "explore-007" in text
    assert "1 defect" in text or "Defects: 1" in text
    assert "1 observation" in text or "Observations: 1" in text


def test_write_partial_handover_is_atomic(tmp_path):
    """ADR-204: write to .tmp, then os.replace. After completion no .tmp
    should remain in the handovers dir."""
    session = IntakeSession("001")
    session.record(severity="Critical", given="g", when="w", then="t", reproduction="r")
    write_partial_handover(session, tmp_path)
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_write_partial_handover_overwrites_prior_write(tmp_path):
    """Successive intakes must update the same partial-handover file
    in-place, not append a new one."""
    session = IntakeSession("001")
    session.record(severity="Critical", given="g", when="w", then="t", reproduction="r")
    write_partial_handover(session, tmp_path)
    session.record(
        severity="Important", given="g", when="w", then="t", reproduction="r"
    )
    write_partial_handover(session, tmp_path)
    files = list(tmp_path.glob("explore-*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    # Both defects should appear in the latest write
    assert "D-001" in text and "D-002" in text


def test_write_partial_handover_creates_dir_if_missing(tmp_path):
    target = tmp_path / "handovers"
    assert not target.exists()
    session = IntakeSession("001")
    session.record(severity="Observation", given="g", when="w", then="t")
    out = write_partial_handover(session, target)
    assert out.exists()
    assert out.parent == target


# ----------------------------------------------------------------- regression: P11-C06 untouched


def test_charter_module_still_importable():
    """Sanity: P11-C06's _charter module should still import alongside
    _defect_intake; this catches accidental side-effects in the package."""
    import _charter  # noqa: F401


# ----------------------------------------------------------------- R24 I-6: remove_partial_handover


def test_remove_partial_handover_deletes_existing_file(tmp_path):
    target = tmp_path / "handovers"
    session = IntakeSession("042")
    session.record(severity="Observation", given="g", when="w", then="t")
    out = write_partial_handover(session, target)
    assert out.exists()
    removed = remove_partial_handover(session, target)
    assert removed is True
    assert not out.exists()


def test_remove_partial_handover_returns_false_when_absent(tmp_path):
    """Idempotent: calling on a non-existent partial returns False, does
    not raise. The skill's DEBRIEF flow can call unconditionally without
    branching on prior state."""
    target = tmp_path / "handovers"
    target.mkdir()
    session = IntakeSession("099")
    removed = remove_partial_handover(session, target)
    assert removed is False
