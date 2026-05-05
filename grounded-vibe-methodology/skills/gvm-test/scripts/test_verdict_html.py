"""Tests for `_verdict_html` (honesty-triad ADR-105, TC-VV-5-01..02)."""

from __future__ import annotations

import pytest

from _verdict_html import (
    FreeTextOnlyRationaleError,
    InvalidVerdictError,
    render_verdict,
    validate_rationale,
)
from gvm_verdict import Criterion, Verdict, VerdictResult


def _ship_ready_result() -> VerdictResult:
    crits = (
        Criterion("VV-2(a)", "PASS", "no MUST through stub"),
        Criterion("VV-2(b)", "PASS", "all four risks evaluated"),
        Criterion("VV-2(c)", "PASS", "zero critical findings"),
        Criterion("VV-3(a)", "PASS", "stubs registered + HS-4"),
        Criterion("VV-3(b)", "PASS", "demo line present"),
        Criterion("VV-3(c)", "PASS", "no critical non-stub"),
        Criterion("VV-3(d)", "NA", "no wired_sandbox boundaries"),
        Criterion("VV-4(a)", "PASS", "no Panel E unregistered"),
        Criterion("VV-4(b)", "PASS", "no MUST via fixture"),
        Criterion("VV-4(c)", "PASS", "no unevaluated risks"),
        Criterion("VV-4(d)", "PASS", "no critical exploratory"),
        Criterion("VV-4(e)", "PASS", "no expired stub"),
        Criterion("VV-4(f)", "PASS", "no unknown plan"),
    )
    return VerdictResult(verdict=Verdict.SHIP_READY, criteria=crits)


def _demo_ready_result() -> VerdictResult:
    return VerdictResult(
        verdict=Verdict.DEMO_READY,
        criteria=(Criterion("VV-2(a)", "FAIL", "MUST through stub"),),
    )


def test_render_contains_verdict_string():
    out = render_verdict(_ship_ready_result())
    assert "Ship-ready" in out


def test_render_contains_every_criterion_row():
    result = _ship_ready_result()
    out = render_verdict(result)
    for c in result.criteria:
        assert c.name in out


def test_render_contains_pass_fail_na_statuses():
    crits = (
        Criterion("VV-2(a)", "PASS", "ev1"),
        Criterion("VV-2(b)", "FAIL", "ev2"),
        Criterion("VV-3(d)", "NA", "ev3"),
    )
    result = VerdictResult(verdict=Verdict.NOT_SHIPPABLE, criteria=crits)
    out = render_verdict(result)
    assert "PASS" in out
    assert "FAIL" in out
    assert "N/A" in out or "NA" in out


def test_render_contains_evidence_text():
    out = render_verdict(_ship_ready_result())
    assert "no MUST through stub" in out


def test_render_escapes_html_in_evidence():
    crits = (Criterion("VV-2(a)", "FAIL", "<script>alert(1)</script>"),)
    result = VerdictResult(verdict=Verdict.NOT_SHIPPABLE, criteria=crits)
    out = render_verdict(result)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_render_rejects_non_verdict_instance():
    bad = VerdictResult.__new__(VerdictResult)
    object.__setattr__(bad, "verdict", "Ship-ready")  # plain str, not Verdict
    object.__setattr__(bad, "criteria", ())
    with pytest.raises(InvalidVerdictError):
        render_verdict(bad)


def test_render_includes_free_text_rationale_block_when_provided():
    out = render_verdict(
        _ship_ready_result(), free_text_rationale="Project is healthy overall."
    )
    assert "Project is healthy overall." in out


def test_render_omits_free_text_block_when_empty():
    out = render_verdict(_ship_ready_result(), free_text_rationale="")
    # No empty <p class="vv-free-text"></p> noise
    assert 'class="vv-free-text"' not in out


def test_render_escapes_html_in_free_text():
    out = render_verdict(_ship_ready_result(), free_text_rationale="<b>bold</b>")
    assert "<b>bold</b>" not in out
    assert "&lt;b&gt;bold&lt;/b&gt;" in out


def test_validate_rationale_passes_when_table_present():
    out = render_verdict(_ship_ready_result())
    validate_rationale(out)  # does not raise


def test_validate_rationale_raises_when_only_free_text():
    fragment = (
        "<section><p>This is just prose without a structured table.</p></section>"
    )
    with pytest.raises(FreeTextOnlyRationaleError):
        validate_rationale(fragment)


def test_demo_ready_verdict_renders_not_user_deployable_string():
    out = render_verdict(_demo_ready_result())
    assert "NOT user-deployable" in out


def test_ship_ready_verdict_does_not_render_not_user_deployable_string():
    out = render_verdict(_ship_ready_result())
    assert "NOT user-deployable" not in out


def test_render_output_is_str():
    assert isinstance(render_verdict(_ship_ready_result()), str)


def test_table_class_is_vv_rationale():
    out = render_verdict(_ship_ready_result())
    assert 'class="vv-rationale"' in out


def test_section_class_is_vv_verdict():
    out = render_verdict(_ship_ready_result())
    assert 'class="vv-verdict"' in out
