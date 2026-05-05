"""Session-report writer tests for `/gvm-explore-test` (P11-C08).

Covers TC-ET-4-01 (paired md+html), TC-ET-4-02 (five sections in order),
TC-ET-3-03 finalisation (XSS payload escaped at HTML render time), plus
defensive coverage of atomicity, naming, and the Stub-path contract that
`_explore_parser` (P11-C09) keys off.
"""

from __future__ import annotations

import pytest

from _charter import Charter
from _defect_intake import IntakeSession
from _report_writer import ReportError, write_report

VALID_CHARTER = Charter(
    schema_version=1,
    session_id="explore-003",
    mission="Probe the report renderer for honesty failures",
    timebox_minutes=60,
    target=("./report.html",),
    tour="data",
    runner="gerard",
)


def _make_session_with_one_defect(
    payload: str = "the renderer crashes",
) -> IntakeSession:
    s = IntakeSession("003")
    s.record(
        severity="Critical",
        given=payload,
        when="the input is malformed",
        then="we still get a valid HTML file",
        reproduction="run the failing test",
        stub_path="STUBS.md#renderer",
    )
    return s


# ----------------------------------------------------------------- TC-ET-4-01


def test_paired_md_and_html_emitted(tmp_path):
    session = _make_session_with_one_defect()
    md, html = write_report(
        VALID_CHARTER,
        session,
        session_log=("10:00 — start",),
        assessment="The product is shippable.",
        output_dir=tmp_path,
    )
    assert md == tmp_path / "explore-003.md"
    assert html == tmp_path / "explore-003.html"
    assert md.exists()
    assert html.exists()


# ----------------------------------------------------------------- TC-ET-4-02


@pytest.mark.parametrize("ext", ["md", "html"])
def test_all_five_sections_present_in_order(tmp_path, ext):
    session = _make_session_with_one_defect()
    md, html = write_report(
        VALID_CHARTER,
        session,
        session_log=("10:00 — start",),
        assessment="OK.",
        output_dir=tmp_path,
    )
    text = (md if ext == "md" else html).read_text(encoding="utf-8")
    expected_order = [
        "Charter",
        "Session Log",
        "Defects",
        "Observations",
        "Overall Assessment",
    ]
    last = -1
    for heading in expected_order:
        idx = text.find(heading)
        assert idx != -1, f"missing section heading: {heading} (in {ext})"
        assert idx > last, f"section out of order: {heading} (in {ext})"
        last = idx


# ----------------------------------------------------------------- TC-ET-3-03 finalisation


def test_xss_payload_escaped_in_html_report(tmp_path):
    """End-to-end boundary closing TC-ET-3-03. Intake stores verbatim
    (P11-C07); the renderer escapes once at HTML render time so the
    `<script>` payload cannot execute when the HTML is opened."""
    payload = "<script>alert(1)</script>"
    session = _make_session_with_one_defect(payload=payload)
    _, html = write_report(
        VALID_CHARTER,
        session,
        session_log=(),
        assessment="OK.",
        output_dir=tmp_path,
    )
    body = html.read_text(encoding="utf-8")
    assert payload not in body  # raw payload must not survive
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body


def test_xss_payload_escaped_in_assessment(tmp_path):
    payload = "<img src=x onerror=alert(1)>"
    session = IntakeSession("003")
    _, html = write_report(
        VALID_CHARTER,
        session,
        session_log=(),
        assessment=payload,
        output_dir=tmp_path,
    )
    body = html.read_text(encoding="utf-8")
    assert payload not in body
    assert "&lt;img src=x onerror=alert(1)&gt;" in body


def test_xss_payload_escaped_in_session_log(tmp_path):
    payload = "<script>x</script>"
    session = IntakeSession("003")
    _, html = write_report(
        VALID_CHARTER,
        session,
        session_log=(payload,),
        assessment="OK.",
        output_dir=tmp_path,
    )
    body = html.read_text(encoding="utf-8")
    assert payload not in body
    assert "&lt;script&gt;x&lt;/script&gt;" in body


def test_xss_payload_in_observation_escaped(tmp_path):
    payload = "<script>obs</script>"
    session = IntakeSession("003")
    session.record(severity="Observation", given=payload, when="w", then="t")
    _, html = write_report(
        VALID_CHARTER, session, session_log=(), assessment="OK.", output_dir=tmp_path
    )
    body = html.read_text(encoding="utf-8")
    assert payload not in body
    assert "&lt;script&gt;obs&lt;/script&gt;" in body


def test_xss_payload_in_charter_fields_escaped(tmp_path):
    """Charter fields (mission, target items, runner) must also pass through
    html.escape — TC-ET-3-03 names them in scope. Without this test a
    silent regression that drops `_e()` from the charter render block
    would not be caught."""
    payload = "<script>mission</script>"
    target_payload = "<img src=x onerror=alert(1)>"
    charter = Charter(
        schema_version=1,
        session_id="explore-003",
        mission=payload,
        timebox_minutes=60,
        target=(target_payload,),
        tour="data",
        runner="gerard",
    )
    session = IntakeSession("003")
    _, html = write_report(
        charter, session, session_log=(), assessment="OK.", output_dir=tmp_path
    )
    body = html.read_text(encoding="utf-8")
    assert payload not in body
    assert target_payload not in body
    assert "&lt;script&gt;mission&lt;/script&gt;" in body
    assert "&lt;img src=x onerror=alert(1)&gt;" in body


def test_md_output_preserves_raw_payload(tmp_path):
    """MD is parser-fodder for /gvm-test (via `_explore_parser`), not an
    HTML rendering target. Raw practitioner payload survives in the md so
    downstream tooling sees the practitioner's authoritative classification."""
    payload = "<script>alert(1)</script>"
    session = _make_session_with_one_defect(payload=payload)
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="OK.", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert payload in body


# ----------------------------------------------------------------- atomicity


def test_no_tmp_leftovers(tmp_path):
    session = _make_session_with_one_defect()
    write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_overwrites_prior_write(tmp_path):
    session = _make_session_with_one_defect()
    write_report(
        VALID_CHARTER, session, session_log=(), assessment="first", output_dir=tmp_path
    )
    write_report(
        VALID_CHARTER, session, session_log=(), assessment="second", output_dir=tmp_path
    )
    md_files = list(tmp_path.glob("explore-003.md"))
    assert len(md_files) == 1
    assert "second" in md_files[0].read_text(encoding="utf-8")


def test_creates_output_dir_if_missing(tmp_path):
    target = tmp_path / "test"
    assert not target.exists()
    session = _make_session_with_one_defect()
    md, html = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=target
    )
    assert md.exists() and html.exists()


# ----------------------------------------------------------------- charter section


def test_charter_section_contains_charter_values(tmp_path):
    session = _make_session_with_one_defect()
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    # charter values appear in the Charter section
    assert VALID_CHARTER.mission in body
    assert "60" in body  # timebox_minutes
    assert "data" in body  # tour
    assert "gerard" in body  # runner
    assert "explore-003" in body
    assert "./report.html" in body


# ----------------------------------------------------------------- defect block format


def test_defect_block_includes_stub_path_line(tmp_path):
    """ADR-206: each defect block carries `**Stub-path:**` line for
    `_explore_parser` to key off."""
    session = _make_session_with_one_defect()
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert "**Stub-path:**" in body
    assert "STUBS.md#renderer" in body


def test_defect_block_without_stub_path_renders_blank(tmp_path):
    """ADR-206: each defect block always carries a `**Stub-path:**` line so
    `_explore_parser` can rely on uniform shape. Empty value parses to
    `stub_path = None` per the parser's `fields.get('Stub-path') or None`."""
    session = IntakeSession("003")
    session.record(severity="Critical", given="g", when="w", then="t", reproduction="r")
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert "**Stub-path:**" in body
    # Blank value (not the legacy "(none)" sentinel) — parser maps "" → None.
    assert "(none)" not in body


def test_defect_block_carries_severity(tmp_path):
    session = _make_session_with_one_defect()
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert "Critical" in body


# ----------------------------------------------------------------- observation block format


def test_observation_block_has_no_severity(tmp_path):
    """ADR-206 severity-enum split: observations carry no severity field —
    the rendered block must not invent one."""
    session = IntakeSession("003")
    session.record(severity="Observation", given="benign-given", when="w", then="t")
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    # locate Observations section
    obs_idx = body.find("## Observations")
    assess_idx = body.find("## Overall Assessment")
    obs_section = body[obs_idx:assess_idx]
    assert "benign-given" in obs_section
    # no severity tags in the observations section
    for sev in ("Critical", "Important", "Minor"):
        assert sev not in obs_section


# ----------------------------------------------------------------- empty sections


def test_empty_defects_renders_gracefully(tmp_path):
    session = IntakeSession("003")
    md, html = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    md_body = md.read_text(encoding="utf-8")
    html_body = html.read_text(encoding="utf-8")
    # Section heading is still present
    assert "## Defects" in md_body
    assert "Defects" in html_body
    # No traceback, no error placeholder
    assert "Traceback" not in md_body
    assert "Traceback" not in html_body


def test_empty_observations_renders_gracefully(tmp_path):
    session = IntakeSession("003")
    session.record(
        severity="Critical", given="g", when="w", then="t", reproduction="r"
    )  # has a defect, no observations
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert "## Observations" in body


def test_empty_session_log_renders_gracefully(tmp_path):
    session = _make_session_with_one_defect()
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert "## Session Log" in body


# ----------------------------------------------------------------- naming


def test_session_nnn_mismatch_between_charter_and_session_rejected(tmp_path):
    """Conceptual integrity: charter.session_id == 'explore-NNN' must
    match session.session_nnn. A mismatch is a programming error — the
    skill runtime constructed both — so refuse the write."""
    session = IntakeSession("999")
    with pytest.raises(ReportError) as exc:
        write_report(
            VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
        )
    assert exc.value.field == "session_nnn"


def test_html_has_minimal_html_skeleton(tmp_path):
    """HTML output must be a parsable HTML document, not a raw fragment."""
    session = _make_session_with_one_defect()
    _, html = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = html.read_text(encoding="utf-8")
    assert body.lstrip().lower().startswith("<!doctype html")
    assert "<html" in body
    assert "</html>" in body


# ----------------------------------------------------------------- ReportError contract


def test_report_error_carries_field_and_reason():
    err = ReportError("session_nnn", "mismatch")
    assert err.field == "session_nnn"
    assert err.reason == "mismatch"
    assert "session_nnn" in str(err)


# ----------------------------------------------------------------- writer/parser roundtrip (R24 CR-1)
#
# The writer's MD output is the consumer contract for `_explore_parser` in
# `/gvm-test`. R24 CR-1 found the two had drifted on five independent points
# (frontmatter, fenced YAML charter, defect heading regex, Tour field,
# bullet-prefix on labelled lines). These tests assert the seam end-to-end so
# any future drift fails immediately rather than silently breaking VV-4(d).


def _load_explore_parser():
    """Import `_explore_parser` from gvm-design-system/scripts/ — same pattern
    used by `_hs6_debrief.py` and `gvm_verdict.evaluate_vv4_d`.

    R25 M-1: walk up from this file looking for a sibling `gvm-design-system`
    rather than relying on a fixed `parents[N]` depth. A fixed offset silently
    surfaces as a collection error (not a test failure) if the tree shape
    shifts — leaving the CR-1 roundtrip contract effectively unlocked."""
    import importlib
    import sys as _sys
    from pathlib import Path as _Path

    here = _Path(__file__).resolve()
    ds_scripts = None
    for ancestor in here.parents:
        candidate = ancestor / "gvm-design-system" / "scripts"
        if candidate.is_dir():
            ds_scripts = candidate
            break
    if ds_scripts is None:
        raise RuntimeError(
            "Could not locate gvm-design-system/scripts/ from "
            f"{here} — walked all ancestors."
        )
    if str(ds_scripts) not in _sys.path:
        _sys.path.insert(0, str(ds_scripts))
    return importlib.import_module("_explore_parser")


def test_writer_output_parses_via_explore_parser_with_one_defect(tmp_path):
    """End-to-end seam: writer output must parse via `_explore_parser.load_explore`
    without raising. Catches frontmatter, charter YAML block, defect heading
    regex, Tour field, and labelled-field prefix simultaneously."""
    parser = _load_explore_parser()
    session = _make_session_with_one_defect()
    md, _ = write_report(
        VALID_CHARTER, session,
        session_log=("10:00 — start",),
        assessment="OK.",
        output_dir=tmp_path,
    )
    report = parser.load_explore(md)
    assert report.schema_version == 1
    assert report.session_id == "explore-003"
    assert report.runner == "gerard"
    assert len(report.defects) == 1
    d = report.defects[0]
    assert d.id == "D-001"
    assert d.severity == "Critical"
    assert d.tour == "data"
    assert d.given == "the renderer crashes"
    assert d.stub_path == "STUBS.md#renderer"


def test_writer_output_parses_with_observation(tmp_path):
    """Observation-side parity (R24 I-1) — the parser's `_parse_observations`
    requires `### O-N: <title>` heading + `**Tour:**` field."""
    parser = _load_explore_parser()
    session = IntakeSession("003")
    session.record(severity="Observation", given="g", when="w", then="t")
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="OK.", output_dir=tmp_path
    )
    report = parser.load_explore(md)
    assert len(report.observations) == 1
    o = report.observations[0]
    assert o.id == "O-001"
    assert o.given == "g"


def test_writer_output_parses_with_no_defects_or_observations(tmp_path):
    """Empty defect/observation sections must still parse — `_None recorded._`
    placeholder must not collide with the heading regexes."""
    parser = _load_explore_parser()
    session = IntakeSession("003")
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    report = parser.load_explore(md)
    assert report.defects == ()
    assert report.observations == ()


def test_writer_output_starts_with_frontmatter(tmp_path):
    """Sanity: explicit format gate per R24 CR-1 sub-issue 1."""
    session = _make_session_with_one_defect()
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert body.startswith("---\nschema_version: 1\n---\n")


def test_writer_charter_section_has_fenced_yaml(tmp_path):
    """Sanity: explicit format gate per R24 CR-1 sub-issue 2."""
    session = _make_session_with_one_defect()
    md, _ = write_report(
        VALID_CHARTER, session, session_log=(), assessment="x", output_dir=tmp_path
    )
    body = md.read_text(encoding="utf-8")
    assert "## Charter\n\n```yaml\n" in body
    # Charter YAML must contain session_id and runner — the only two scalars
    # the parser strictly requires.
    assert "session_id: explore-003" in body
    assert "runner: gerard" in body
