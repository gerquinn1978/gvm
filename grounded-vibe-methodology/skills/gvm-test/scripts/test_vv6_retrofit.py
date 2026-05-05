"""Tests for `_vv6_retrofit` (honesty-triad ADR-105 + PP-ADR-604)."""

from __future__ import annotations

import pytest

from _vv6_retrofit import (
    MissingManualChoiceError,
    RetrofitPlan,
    RowDecision,
    VV6AlreadyAppliedError,
    apply_retrofit,
    plan_retrofit,
)
from _calibration_parser import (
    Calibration,
    ScoreHistoryRow,
    UnknownVerdictError,
    serialise,
    load_calibration,
)
from gvm_verdict import Verdict


# --- helpers ---


def _v0_row(round_n: int, verdict: str) -> ScoreHistoryRow:
    return ScoreHistoryRow(
        round=round_n,
        date=f"2025-01-0{round_n}",
        type="full",
        verdict=verdict,
        verdict_under_schema=None,
        per_dimension_scores="x",
    )


def _v0_cal(*rows: ScoreHistoryRow, trailing: str = "") -> Calibration:
    return Calibration(
        schema_version=0,
        score_history=tuple(rows),
        recurring_findings=(),
        trailing_body=trailing,
    )


def _v1_row(round_n: int, verdict: str, vus: int) -> ScoreHistoryRow:
    return ScoreHistoryRow(
        round=round_n,
        date=f"2025-02-0{round_n}",
        type="full",
        verdict=verdict,
        verdict_under_schema=vus,
        per_dimension_scores="y",
    )


# --- plan_retrofit ---


def test_plan_on_schema_1_reports_already_applied():
    cal = Calibration(
        schema_version=1,
        score_history=(_v1_row(1, "Ship-ready", 1),),
        recurring_findings=(),
        trailing_body="",
    )
    plan = plan_retrofit(cal)
    assert isinstance(plan, RetrofitPlan)
    assert plan.already_applied is True
    assert plan.decisions == ()
    assert plan.manual_required == ()


def test_plan_on_empty_schema_0_returns_empty_decisions():
    cal = _v0_cal()
    plan = plan_retrofit(cal)
    assert plan.already_applied is False
    assert plan.decisions == ()
    assert plan.manual_required == ()


def test_plan_classifies_pass_as_auto_ship_ready():
    cal = _v0_cal(_v0_row(1, "Pass"))
    plan = plan_retrofit(cal)
    assert plan.already_applied is False
    assert len(plan.decisions) == 1
    d = plan.decisions[0]
    assert isinstance(d, RowDecision)
    assert d.round == 1
    assert d.original_verdict == "Pass"
    assert d.auto_mapping == Verdict.SHIP_READY
    assert d.needs_manual_choice is False
    assert plan.manual_required == ()


def test_plan_classifies_do_not_release_as_auto_not_shippable():
    cal = _v0_cal(_v0_row(2, "Do not release"))
    plan = plan_retrofit(cal)
    d = plan.decisions[0]
    assert d.auto_mapping == Verdict.NOT_SHIPPABLE
    assert d.needs_manual_choice is False


def test_plan_flags_pass_with_gaps_as_manual():
    cal = _v0_cal(_v0_row(3, "Pass with gaps"))
    plan = plan_retrofit(cal)
    d = plan.decisions[0]
    assert d.auto_mapping is None
    assert d.needs_manual_choice is True
    assert plan.manual_required == (d,)


def test_plan_mixed_rows_preserves_input_order():
    cal = _v0_cal(
        _v0_row(1, "Pass"),
        _v0_row(2, "Pass with gaps"),
        _v0_row(3, "Do not release"),
        _v0_row(4, "Pass with gaps"),
    )
    plan = plan_retrofit(cal)
    rounds = [d.round for d in plan.decisions]
    assert rounds == [1, 2, 3, 4]
    manual_rounds = [d.round for d in plan.manual_required]
    assert manual_rounds == [2, 4]


def test_plan_unknown_verdict_propagates():
    cal = _v0_cal(_v0_row(1, "Indeterminate"))
    with pytest.raises(UnknownVerdictError):
        plan_retrofit(cal)


# --- apply_retrofit: idempotency (TC-VV-6-02) ---


def test_tc_vv_6_02_apply_on_schema_1_raises_already_applied():
    cal = Calibration(
        schema_version=1,
        score_history=(_v1_row(1, "Demo-ready", 1),),
        recurring_findings=(),
        trailing_body="",
    )
    with pytest.raises(VV6AlreadyAppliedError):
        apply_retrofit(cal, manual_choices={})


# --- apply_retrofit: auto-mapping rows preserve verdict text ---


def test_apply_pass_row_preserves_verdict_text_vus_0():
    cal = _v0_cal(_v0_row(1, "Pass"))
    new_cal = apply_retrofit(cal, manual_choices={})
    assert new_cal.schema_version == 1
    assert len(new_cal.score_history) == 1
    row = new_cal.score_history[0]
    assert row.verdict == "Pass"  # preserved
    assert row.verdict_under_schema == 0
    assert row.round == 1


def test_apply_do_not_release_row_preserves_verdict_text_vus_0():
    cal = _v0_cal(_v0_row(5, "Do not release"))
    new_cal = apply_retrofit(cal, manual_choices={})
    row = new_cal.score_history[0]
    assert row.verdict == "Do not release"
    assert row.verdict_under_schema == 0


# --- TC-VV-6-01: Pass with gaps reclassification ---


def test_tc_vv_6_01_pass_with_gaps_to_demo_ready():
    cal = _v0_cal(_v0_row(7, "Pass with gaps"))
    new_cal = apply_retrofit(cal, manual_choices={7: Verdict.DEMO_READY})
    row = new_cal.score_history[0]
    assert row.verdict == "Demo-ready"
    assert row.verdict_under_schema == 1


def test_tc_vv_6_01_pass_with_gaps_to_not_shippable():
    cal = _v0_cal(_v0_row(7, "Pass with gaps"))
    new_cal = apply_retrofit(cal, manual_choices={7: Verdict.NOT_SHIPPABLE})
    row = new_cal.score_history[0]
    assert row.verdict == "Not shippable"
    assert row.verdict_under_schema == 1


def test_apply_rejects_ship_ready_for_pass_with_gaps():
    cal = _v0_cal(_v0_row(7, "Pass with gaps"))
    with pytest.raises(ValueError, match="Ship-ready"):
        apply_retrofit(cal, manual_choices={7: Verdict.SHIP_READY})


def test_apply_missing_manual_choice_raises_with_round():
    cal = _v0_cal(_v0_row(7, "Pass with gaps"))
    with pytest.raises(MissingManualChoiceError, match="7"):
        apply_retrofit(cal, manual_choices={})


def test_apply_missing_manual_choice_for_one_of_many():
    cal = _v0_cal(
        _v0_row(1, "Pass with gaps"),
        _v0_row(2, "Pass with gaps"),
    )
    with pytest.raises(MissingManualChoiceError, match="2"):
        apply_retrofit(cal, manual_choices={1: Verdict.DEMO_READY})


def test_apply_unknown_verdict_raises():
    cal = _v0_cal(_v0_row(1, "Garbage"))
    with pytest.raises(UnknownVerdictError):
        apply_retrofit(cal, manual_choices={})


# --- apply: structure preservation ---


def test_apply_preserves_row_order_and_count():
    cal = _v0_cal(
        _v0_row(1, "Pass"),
        _v0_row(2, "Pass with gaps"),
        _v0_row(3, "Do not release"),
    )
    new_cal = apply_retrofit(cal, manual_choices={2: Verdict.DEMO_READY})
    assert [r.round for r in new_cal.score_history] == [1, 2, 3]
    assert [r.verdict for r in new_cal.score_history] == [
        "Pass",
        "Demo-ready",
        "Do not release",
    ]
    assert [r.verdict_under_schema for r in new_cal.score_history] == [0, 1, 0]


def test_apply_clears_recurring_findings_on_v0_input():
    # schema-0 has no recurring_findings table; the migrated v1 should also have ().
    cal = _v0_cal(_v0_row(1, "Pass"))
    new_cal = apply_retrofit(cal, manual_choices={})
    assert new_cal.recurring_findings == ()


def test_apply_preserves_trailing_body():
    cal = _v0_cal(
        _v0_row(1, "Pass"),
        trailing="## Anchor Examples\n\nsome content\n",
    )
    new_cal = apply_retrofit(cal, manual_choices={})
    assert new_cal.trailing_body == "## Anchor Examples\n\nsome content\n"


def test_apply_extra_manual_choices_are_ignored():
    cal = _v0_cal(_v0_row(1, "Pass"))
    new_cal = apply_retrofit(
        cal,
        manual_choices={99: Verdict.DEMO_READY},  # extraneous
    )
    assert new_cal.score_history[0].verdict == "Pass"


def test_apply_returns_immutable_calibration():
    cal = _v0_cal(_v0_row(1, "Pass"))
    new_cal = apply_retrofit(cal, manual_choices={})
    assert isinstance(new_cal.score_history, tuple)
    assert isinstance(new_cal.recurring_findings, tuple)


# --- round-trip via serialise + load ---


def test_round_trip_via_calibration_parser(tmp_path):
    cal = _v0_cal(
        _v0_row(1, "Pass"),
        _v0_row(2, "Pass with gaps"),
        _v0_row(3, "Do not release"),
    )
    new_cal = apply_retrofit(cal, manual_choices={2: Verdict.NOT_SHIPPABLE})

    f = tmp_path / "calibration.md"
    f.write_text(serialise(new_cal))
    reloaded = load_calibration(f)

    assert reloaded.schema_version == 1
    assert len(reloaded.score_history) == 3
    verdicts = [r.verdict for r in reloaded.score_history]
    assert verdicts == ["Pass", "Not shippable", "Do not release"]
    vuses = [r.verdict_under_schema for r in reloaded.score_history]
    assert vuses == [0, 1, 0]


# --- plan + apply integration ---


def test_plan_decisions_drive_apply():
    cal = _v0_cal(
        _v0_row(1, "Pass"),
        _v0_row(2, "Pass with gaps"),
    )
    plan = plan_retrofit(cal)
    choices = {d.round: Verdict.DEMO_READY for d in plan.manual_required}
    new_cal = apply_retrofit(cal, manual_choices=choices)
    assert new_cal.score_history[1].verdict == "Demo-ready"
