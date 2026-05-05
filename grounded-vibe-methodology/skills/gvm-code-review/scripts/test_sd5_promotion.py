"""Tests for `_sd5_promotion` (honesty-triad ADR-109)."""

from __future__ import annotations

import pytest

from _sd5_promotion import (
    BuildCheckPromotion,
    FindingInput,
    PromotedFinding,
    SD5Result,
    apply_sd5,
    compute_signature,
)
from _calibration_parser import RecurringFinding


# --- compute_signature ---


def test_signature_is_12_hex_chars():
    sig = compute_signature("a.py", "X", "Python-1", "unregistered")
    assert len(sig) == 12
    assert all(c in "0123456789abcdef" for c in sig)


def test_signature_is_deterministic():
    a = compute_signature("a.py", "X", "Python-1", "unregistered")
    b = compute_signature("a.py", "X", "Python-1", "unregistered")
    assert a == b


def test_signature_changes_with_file_path():
    a = compute_signature("a.py", "X", "Python-1", "unregistered")
    b = compute_signature("b.py", "X", "Python-1", "unregistered")
    assert a != b


def test_signature_changes_with_symbol():
    a = compute_signature("a.py", "X", "Python-1", "unregistered")
    b = compute_signature("a.py", "Y", "Python-1", "unregistered")
    assert a != b


def test_signature_changes_with_heuristic_class():
    a = compute_signature("a.py", "X", "Python-1", "unregistered")
    b = compute_signature("a.py", "X", "Python-2", "unregistered")
    assert a != b


def test_signature_changes_with_violation_type():
    a = compute_signature("a.py", "X", "Python-1", "unregistered")
    b = compute_signature("a.py", "X", "Python-1", "namespace_violation")
    assert a != b


# --- apply_sd5: round 1 (new signature) ---


def _f(
    file_path="a.py",
    symbol="X",
    heuristic="Python-1",
    violation="unregistered",
    severity="Important",
) -> FindingInput:
    return FindingInput(
        file_path=file_path,
        symbol=symbol,
        heuristic_class=heuristic,
        violation_type=violation,
        initial_severity=severity,
    )


def test_round_1_new_signature_severity_unchanged():
    result = apply_sd5([_f()], current_recurring=(), current_round=1)
    assert isinstance(result, SD5Result)
    assert len(result.promoted_findings) == 1
    pf = result.promoted_findings[0]
    assert pf.severity == "Important"
    assert pf.round_count == 1
    assert len(result.updated_recurring) == 1
    rr = result.updated_recurring[0]
    assert rr.first_round == 1
    assert rr.last_round == 1
    assert rr.severity_history == "Important"
    assert result.build_check_promotions == ()


def test_round_1_signature_field_set():
    result = apply_sd5([_f()], current_recurring=(), current_round=1)
    pf = result.promoted_findings[0]
    expected_sig = compute_signature("a.py", "X", "Python-1", "unregistered")
    assert pf.signature == expected_sig
    assert result.updated_recurring[0].signature == expected_sig


# --- TC-SD-5-01: round 2 → Critical ---


def test_tc_sd_5_01_round_2_promotes_to_critical():
    sig = compute_signature("providers/mock.py", "fetch", "Python-1", "unregistered")
    existing = (
        RecurringFinding(
            signature=sig,
            first_round=1,
            last_round=1,
            severity_history="Important",
        ),
    )
    finding = _f(file_path="providers/mock.py", symbol="fetch")
    result = apply_sd5([finding], current_recurring=existing, current_round=2)
    pf = result.promoted_findings[0]
    assert pf.severity == "Critical"
    assert pf.round_count == 2
    rr = result.updated_recurring[0]
    assert rr.first_round == 1
    assert rr.last_round == 2
    assert rr.severity_history == "Important,Critical"
    assert result.build_check_promotions == ()


# --- TC-SD-5-02: round 3 → build check ---


def test_tc_sd_5_02_round_3_emits_build_check_promotion():
    sig = compute_signature("providers/mock.py", "fetch", "Python-1", "unregistered")
    existing = (
        RecurringFinding(
            signature=sig,
            first_round=1,
            last_round=2,
            severity_history="Important,Critical",
        ),
    )
    finding = _f(file_path="providers/mock.py", symbol="fetch")
    result = apply_sd5([finding], current_recurring=existing, current_round=3)
    pf = result.promoted_findings[0]
    assert pf.severity == "Critical"
    assert pf.round_count == 3
    assert len(result.build_check_promotions) == 1
    bc = result.build_check_promotions[0]
    assert isinstance(bc, BuildCheckPromotion)
    assert bc.signature == sig
    assert bc.heuristic_class == "Python-1"
    assert bc.file_path == "providers/mock.py"
    assert bc.symbol == "fetch"
    rr = result.updated_recurring[0]
    assert rr.first_round == 1
    assert rr.last_round == 3
    assert rr.severity_history == "Important,Critical,Critical"


# --- Round 4+: no new BC promotion ---


def test_round_4_no_additional_build_check():
    sig = compute_signature("a.py", "X", "Python-1", "unregistered")
    existing = (
        RecurringFinding(
            signature=sig,
            first_round=1,
            last_round=3,
            severity_history="Important,Critical,Critical",
        ),
    )
    result = apply_sd5([_f()], current_recurring=existing, current_round=4)
    pf = result.promoted_findings[0]
    assert pf.severity == "Critical"
    assert pf.round_count == 4
    assert result.build_check_promotions == ()
    assert (
        result.updated_recurring[0].severity_history
        == "Important,Critical,Critical,Critical"
    )


# --- Gap resets the row ---


def test_gap_resets_row_to_round_1():
    sig = compute_signature("a.py", "X", "Python-1", "unregistered")
    existing = (
        RecurringFinding(
            signature=sig,
            first_round=1,
            last_round=2,
            severity_history="Important,Critical",
        ),
    )
    # current_round = 4, last_round = 2 → gap of one round → reset
    result = apply_sd5([_f()], current_recurring=existing, current_round=4)
    pf = result.promoted_findings[0]
    assert pf.severity == "Important"  # reset
    assert pf.round_count == 1
    rr = result.updated_recurring[0]
    assert rr.first_round == 4
    assert rr.last_round == 4
    assert rr.severity_history == "Important"
    assert result.build_check_promotions == ()


# --- Resolution: signature absent this round → row dropped ---


def test_resolution_drops_row_from_updated_recurring():
    sig_old = compute_signature("old.py", "OLD", "Python-1", "unregistered")
    sig_new = compute_signature("new.py", "NEW", "Python-1", "unregistered")
    existing = (
        RecurringFinding(
            signature=sig_old,
            first_round=1,
            last_round=1,
            severity_history="Important",
        ),
    )
    finding = _f(file_path="new.py", symbol="NEW")
    result = apply_sd5([finding], current_recurring=existing, current_round=2)
    sigs_out = {r.signature for r in result.updated_recurring}
    assert sig_old not in sigs_out
    assert sig_new in sigs_out


def test_resolution_with_no_findings_clears_all_rows():
    sig = compute_signature("a.py", "X", "Python-1", "unregistered")
    existing = (
        RecurringFinding(
            signature=sig,
            first_round=1,
            last_round=1,
            severity_history="Important",
        ),
    )
    result = apply_sd5([], current_recurring=existing, current_round=2)
    assert result.updated_recurring == ()
    assert result.promoted_findings == ()
    assert result.build_check_promotions == ()


# --- Ordering ---


def test_input_order_preserved():
    findings = [
        _f(file_path="a.py", symbol="A"),
        _f(file_path="b.py", symbol="B"),
        _f(file_path="c.py", symbol="C"),
    ]
    result = apply_sd5(findings, current_recurring=(), current_round=1)
    paths = [pf.file_path for pf in result.promoted_findings]
    assert paths == ["a.py", "b.py", "c.py"]


# --- Duplicate signatures within one round ---


def test_duplicate_signatures_in_one_round_collapse_in_recurring():
    findings = [_f(), _f()]  # same signature
    result = apply_sd5(findings, current_recurring=(), current_round=1)
    # both findings produced (one PromotedFinding each), but only one row.
    assert len(result.promoted_findings) == 2
    assert len(result.updated_recurring) == 1


# --- Errors ---


def test_current_round_zero_raises():
    with pytest.raises(ValueError, match="current_round"):
        apply_sd5([], current_recurring=(), current_round=0)


def test_current_round_negative_raises():
    with pytest.raises(ValueError, match="current_round"):
        apply_sd5([], current_recurring=(), current_round=-1)


def test_empty_inputs_returns_empty_result():
    result = apply_sd5([], current_recurring=(), current_round=1)
    assert result.promoted_findings == ()
    assert result.updated_recurring == ()
    assert result.build_check_promotions == ()


# --- Mixed scenario ---


def test_mixed_round_3_build_check_and_round_1_new_finding():
    sig_old = compute_signature("recur.py", "F", "Python-1", "unregistered")
    existing = (
        RecurringFinding(
            signature=sig_old,
            first_round=1,
            last_round=2,
            severity_history="Important,Critical",
        ),
    )
    findings = [
        _f(file_path="recur.py", symbol="F"),  # round 3 → BC promotion
        _f(file_path="new.py", symbol="N"),  # round 1 → unchanged
    ]
    result = apply_sd5(findings, current_recurring=existing, current_round=3)
    severities = [pf.severity for pf in result.promoted_findings]
    assert severities == ["Critical", "Important"]
    assert len(result.build_check_promotions) == 1
    assert result.build_check_promotions[0].file_path == "recur.py"


# --- Output type sanity ---


def test_returns_immutable_tuples():
    result = apply_sd5([_f()], current_recurring=(), current_round=1)
    assert isinstance(result.promoted_findings, tuple)
    assert isinstance(result.updated_recurring, tuple)
    assert isinstance(result.build_check_promotions, tuple)
    assert isinstance(result.promoted_findings[0], PromotedFinding)


def test_promoted_finding_round_count_for_new_signature_is_one():
    result = apply_sd5([_f()], current_recurring=(), current_round=5)
    # current_round=5 with no recurring entry — treated as fresh, count=1.
    assert result.promoted_findings[0].round_count == 1
    assert result.promoted_findings[0].severity == "Important"
