"""Tests for `gvm_verdict.evaluate` (honesty-triad ADR-105 + ADR-106)."""

from __future__ import annotations

from gvm_verdict import (
    Criterion,
    Verdict,
    VerdictInputs,
    VerdictResult,
    evaluate,
)


def _all_pass() -> dict:
    """Inputs where every VV-2, VV-3, VV-4 criterion is PASS."""
    return {
        "vv2_a": ("PASS", "no MUST through stub"),
        "vv2_b": ("PASS", "all four risks evaluated"),
        "vv2_c": ("PASS", "zero critical findings"),
        "vv3_a": ("PASS", "all stubs registered + HS-4"),
        "vv3_b": ("PASS", "report contains NOT user-deployable"),
        "vv3_c": ("PASS", "no critical in non-stub paths"),
        "vv3_d": ("NA", "no wired_sandbox boundaries"),
        "vv4_a": ("PASS", "no Panel E unregistered"),
        "vv4_b": ("PASS", "no MUST via fixture without HS-4"),
        "vv4_c": ("PASS", "no unevaluated risks"),
        "vv4_d": ("PASS", "no critical exploratory in non-stub"),
        "vv4_e": ("PASS", "no expired stub"),
        "vv4_f": ("PASS", "no unknown plan"),
    }


def test_verdict_enum_string_values():
    assert Verdict.SHIP_READY.value == "Ship-ready"
    assert Verdict.DEMO_READY.value == "Demo-ready"
    assert Verdict.NOT_SHIPPABLE.value == "Not shippable"
    # str-Enum interop
    assert Verdict.SHIP_READY == "Ship-ready"


def test_all_vv2_pass_returns_ship_ready():
    result = evaluate(VerdictInputs(**_all_pass()))
    assert result.verdict == Verdict.SHIP_READY


def test_vv2_a_fail_with_vv3_pass_returns_demo_ready():
    inputs = _all_pass()
    inputs["vv2_a"] = ("FAIL", "MUST traces through stub")
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.DEMO_READY


def test_vv2_b_fail_with_vv3_pass_returns_demo_ready():
    inputs = _all_pass()
    inputs["vv2_b"] = ("FAIL", "Value risk blank")
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.DEMO_READY


def test_vv4_d_fired_overrides_vv2_returns_not_shippable():
    inputs = _all_pass()
    inputs["vv4_d"] = ("FAIL", "1 critical exploratory in non-stub path")
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.NOT_SHIPPABLE


def test_vv3_a_fail_returns_not_shippable_via_fallthrough():
    inputs = _all_pass()
    inputs["vv2_a"] = ("FAIL", "MUST through stub")
    inputs["vv3_a"] = ("FAIL", "stub missing HS-4 marker")
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.NOT_SHIPPABLE


def test_vv4_a_fired_returns_not_shippable():
    inputs = _all_pass()
    inputs["vv4_a"] = ("FAIL", "Panel E unregistered Critical")
    assert evaluate(VerdictInputs(**inputs)).verdict == Verdict.NOT_SHIPPABLE


def test_vv4_b_fired_returns_not_shippable():
    inputs = _all_pass()
    inputs["vv4_b"] = ("FAIL", "REQ-X MUST via fixture without HS-4")
    assert evaluate(VerdictInputs(**inputs)).verdict == Verdict.NOT_SHIPPABLE


def test_vv4_c_fired_returns_not_shippable():
    inputs = _all_pass()
    inputs["vv4_c"] = ("FAIL", "Value Risk blank on new project")
    assert evaluate(VerdictInputs(**inputs)).verdict == Verdict.NOT_SHIPPABLE


def test_vv4_e_fired_returns_not_shippable():
    inputs = _all_pass()
    inputs["vv4_e"] = ("FAIL", "stub past expiry")
    assert evaluate(VerdictInputs(**inputs)).verdict == Verdict.NOT_SHIPPABLE


def test_vv4_f_fired_returns_not_shippable():
    inputs = _all_pass()
    inputs["vv4_f"] = ("FAIL", "real-provider plan: unknown")
    assert evaluate(VerdictInputs(**inputs)).verdict == Verdict.NOT_SHIPPABLE


def test_vv3_d_na_treated_as_pass():
    inputs = _all_pass()
    # Force fall-through to VV-3 evaluation
    inputs["vv2_a"] = ("FAIL", "demo path")
    # vv3_d is already NA in _all_pass; expect DEMO_READY
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.DEMO_READY


def test_oq5_user_chooses_ship():
    inputs = _all_pass()
    inputs["oq5_applies"] = True
    inputs["oq5_user_choice"] = "ship"
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.SHIP_READY


def test_oq5_non_interactive_defaults_to_demo():
    inputs = _all_pass()
    inputs["oq5_applies"] = True
    inputs["oq5_user_choice"] = None
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.DEMO_READY


def test_oq5_user_chooses_demo():
    inputs = _all_pass()
    inputs["oq5_applies"] = True
    inputs["oq5_user_choice"] = "demo"
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.DEMO_READY


def test_returned_criteria_include_all_vv2_vv3_vv4_rows():
    result = evaluate(VerdictInputs(**_all_pass()))
    names = {c.name for c in result.criteria}
    expected = {
        "VV-2(a)",
        "VV-2(b)",
        "VV-2(c)",
        "VV-3(a)",
        "VV-3(b)",
        "VV-3(c)",
        "VV-3(d)",
        "VV-4(a)",
        "VV-4(b)",
        "VV-4(c)",
        "VV-4(d)",
        "VV-4(e)",
        "VV-4(f)",
    }
    assert expected.issubset(names)


def test_criteria_are_frozen_immutable():
    result = evaluate(VerdictInputs(**_all_pass()))
    c = result.criteria[0]
    assert isinstance(c, Criterion)
    # frozen dataclass: assignment raises
    import dataclasses

    try:
        c.status = "FAIL"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Criterion should be frozen")


def test_evaluator_is_pure_idempotent():
    inputs = VerdictInputs(**_all_pass())
    a = evaluate(inputs)
    b = evaluate(inputs)
    assert a == b


def test_fallthrough_returns_not_shippable_when_neither_set_passes():
    inputs = _all_pass()
    inputs["vv2_a"] = ("FAIL", "x")
    inputs["vv3_a"] = ("FAIL", "y")
    result = evaluate(VerdictInputs(**inputs))
    assert result.verdict == Verdict.NOT_SHIPPABLE


def test_result_is_verdict_result_dataclass():
    result = evaluate(VerdictInputs(**_all_pass()))
    assert isinstance(result, VerdictResult)
    assert isinstance(result.criteria, tuple)
