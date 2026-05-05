"""Tests for `_shared/diagnostics.py` — P2-C01 bootstrap + P2-C04 extension.

P2-C01 introduces two exception classes raised by `_shared/io.py`:
`EncryptedFileError` and `MalformedFileError`. P2-C04 extends the module with
`ColumnNotFoundError`, `ZeroVarianceTargetError`, `PrivacyBoundaryViolation`,
`DependencyError`, `JargonError`, `ReferentialIntegrityError`, and the
`format_diagnostic()` helper.
"""

from __future__ import annotations


# --- P2-C01 bootstrap ------------------------------------------------------


def test_encrypted_file_error_carries_path() -> None:
    from _shared import diagnostics

    err = diagnostics.EncryptedFileError("/data/locked.xlsx")
    assert err.path == "/data/locked.xlsx"
    assert "/data/locked.xlsx" in str(err)


def test_encrypted_file_error_is_exception() -> None:
    from _shared import diagnostics

    assert issubclass(diagnostics.EncryptedFileError, Exception)


def test_malformed_file_error_carries_path_row_col_kind() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/broken.csv", row=42, col=3, kind="truncated"
    )
    assert err.path == "/data/broken.csv"
    assert err.row == 42
    assert err.col == 3
    assert err.kind == "truncated"


def test_malformed_file_error_accepts_optional_row_col() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/empty.xlsx", row=None, col=None, kind="no_data_rows"
    )
    assert err.path == "/data/empty.xlsx"
    assert err.row is None
    assert err.col is None
    assert err.kind == "no_data_rows"


def test_malformed_file_error_is_exception() -> None:
    from _shared import diagnostics

    assert issubclass(diagnostics.MalformedFileError, Exception)


def test_malformed_file_error_row_without_col() -> None:
    """Boundary: row set, col=None — location string includes row only."""
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/broken.csv", row=5, col=None, kind="parser_error"
    )
    text = str(err)
    assert "row 5" in text
    assert "col" not in text


# --- P2-C04 extension: exception classes -----------------------------------


def test_column_not_found_error_carries_fields() -> None:
    from _shared import diagnostics

    err = diagnostics.ColumnNotFoundError("price", known_columns=("id", "name", "cost"))
    assert err.column == "price"
    assert tuple(err.known_columns) == ("id", "name", "cost")
    assert "price" in str(err)
    assert issubclass(diagnostics.ColumnNotFoundError, Exception)


def test_zero_variance_target_error_carries_target() -> None:
    from _shared import diagnostics

    err = diagnostics.ZeroVarianceTargetError("revenue")
    assert err.target == "revenue"
    assert "revenue" in str(err)
    assert issubclass(diagnostics.ZeroVarianceTargetError, Exception)


def test_privacy_boundary_violation_carries_token_and_context() -> None:
    from _shared import diagnostics

    err = diagnostics.PrivacyBoundaryViolation(
        token="ACME Corp", context="headline_findings[0].title"
    )
    assert err.token == "ACME Corp"
    assert err.context == "headline_findings[0].title"
    assert issubclass(diagnostics.PrivacyBoundaryViolation, Exception)


def test_dependency_error_carries_package_and_reason() -> None:
    from _shared import diagnostics

    err = diagnostics.DependencyError(
        "pymannkendall",
        reason="below version floor",
        required=">=1.4",
        found="1.2",
    )
    assert err.package == "pymannkendall"
    assert err.reason == "below version floor"
    assert err.required == ">=1.4"
    assert err.found == "1.2"
    assert issubclass(diagnostics.DependencyError, Exception)


def test_dependency_error_required_and_found_optional() -> None:
    from _shared import diagnostics

    err = diagnostics.DependencyError("foo", reason="missing")
    assert err.required is None
    assert err.found is None


def test_jargon_error_carries_term_and_location() -> None:
    from _shared import diagnostics

    err = diagnostics.JargonError("heteroskedasticity", "findings[3].question")
    assert err.term == "heteroskedasticity"
    assert err.location == "findings[3].question"
    assert issubclass(diagnostics.JargonError, Exception)


def test_referential_integrity_error_carries_reference_and_kind() -> None:
    from _shared import diagnostics

    err = diagnostics.ReferentialIntegrityError("col_99", kind="unknown_column")
    assert err.reference == "col_99"
    assert err.kind == "unknown_column"
    assert issubclass(diagnostics.ReferentialIntegrityError, Exception)


# --- P2-C04 extension: format_diagnostic helper ----------------------------


def _assert_canonical_shape(text: str) -> None:
    """Every diagnostic must contain the three canonical section headers."""
    assert "ERROR:" in text
    assert "What went wrong:" in text
    assert "What to try:" in text


def test_format_diagnostic_returns_string() -> None:
    from _shared import diagnostics

    err = diagnostics.EncryptedFileError("/data/x.xlsx")
    result = diagnostics.format_diagnostic(err)
    assert isinstance(result, str)
    _assert_canonical_shape(result)


def test_format_diagnostic_has_no_side_effects(capsys) -> None:
    """Helper returns a string — it does not write stderr or call sys.exit.

    Exercises every dispatch branch so no future edit can silently add
    logging / print side effects to any branch (NFR-3). The privacy-
    violation branch is particularly sensitive — stderr output there
    could expose token-adjacent context.
    """
    from _shared import diagnostics

    exceptions = [
        diagnostics.EncryptedFileError("/data/x.xlsx"),
        diagnostics.MalformedFileError(
            "/data/x.csv", row=None, col=None, kind="no_data_rows"
        ),
        diagnostics.MalformedFileError(
            "/data/x.dat", row=None, col=None, kind="unknown_future_kind"
        ),
        diagnostics.ColumnNotFoundError("x", known_columns=("a",)),
        diagnostics.ZeroVarianceTargetError("y"),
        diagnostics.PrivacyBoundaryViolation(token="t", context="c"),
        diagnostics.DependencyError("p", reason="missing"),
        diagnostics.JargonError("term", "loc"),
        diagnostics.ReferentialIntegrityError("ref", kind="k"),
        ValueError("internal"),
    ]
    for exc in exceptions:
        diagnostics.format_diagnostic(exc)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_format_diagnostic_encrypted_file() -> None:
    from _shared import diagnostics

    err = diagnostics.EncryptedFileError("/data/locked.xlsx")
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "/data/locked.xlsx" in text
    assert "encrypt" in text.lower() or "password" in text.lower()


# --- MalformedFileError dispatch by kind -----------------------------------


def test_format_diagnostic_malformed_no_data_rows() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/empty.csv", row=None, col=None, kind="no_data_rows"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "/data/empty.csv" in text
    assert "no data rows" in text.lower() or "no usable" in text.lower()


def test_format_diagnostic_malformed_corrupt_xlsx() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/bad.xlsx", row=None, col=None, kind="corrupt_xlsx"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "/data/bad.xlsx" in text
    assert "corrupt" in text.lower() or "xlsx" in text.lower()
    assert "re-save" in text.lower() or "re-export" in text.lower()


def test_format_diagnostic_malformed_corrupt_xls() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/legacy.xls", row=None, col=None, kind="corrupt_xls"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "/data/legacy.xls" in text
    assert ".xls" in text.lower() or "legacy" in text.lower()


def test_format_diagnostic_malformed_parser_error_with_row_col() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/broken.csv", row=42, col=3, kind="parser_error"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "/data/broken.csv" in text
    assert "42" in text
    assert "3" in text


def test_format_diagnostic_malformed_parser_error_no_row_col() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/broken.csv", row=None, col=None, kind="parser_error"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "/data/broken.csv" in text


def test_format_diagnostic_malformed_xls_engine_missing() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/file.xls", row=None, col=None, kind="xls_engine_missing"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "xlrd" in text.lower() or "engine" in text.lower()
    assert "xlsx" in text.lower() or "convert" in text.lower()


def test_format_diagnostic_malformed_yaml() -> None:
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/project/analysis/preferences.yaml",
        row=5,
        col=2,
        kind="malformed_yaml",
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "preferences.yaml" in text
    assert "yaml" in text.lower()
    assert "5" in text
    assert "2" in text


def test_format_diagnostic_malformed_unknown_kind_fallback() -> None:
    """Unknown kind must not raise — future kinds may be added upstream."""
    from _shared import diagnostics

    err = diagnostics.MalformedFileError(
        "/data/weird.dat", row=None, col=None, kind="new_weird_kind"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "/data/weird.dat" in text


# --- Other exception classes through format_diagnostic ---------------------


def test_format_diagnostic_column_not_found_lists_known() -> None:
    from _shared import diagnostics

    err = diagnostics.ColumnNotFoundError(
        "revenue", known_columns=("id", "name", "cost")
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "revenue" in text
    # Known columns surfaced so user can spot typos.
    for known in ("id", "name", "cost"):
        assert known in text


def test_format_diagnostic_zero_variance_target() -> None:
    from _shared import diagnostics

    err = diagnostics.ZeroVarianceTargetError("revenue")
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "revenue" in text
    assert "variance" in text.lower() or "identical" in text.lower()


def test_format_diagnostic_privacy_boundary_violation() -> None:
    from _shared import diagnostics

    err = diagnostics.PrivacyBoundaryViolation(
        token="ACME Corp", context="headline_findings[0].title"
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    # The context (where the leak happened) must appear so reviewers can
    # locate the offending narrative. The raw token MUST NOT leak into
    # the diagnostic — that would defeat the abort. Assert against the
    # exception's own token field rather than a fixture literal so the
    # ASR-1 guard survives any future fixture refactor.
    assert "headline_findings[0].title" in text
    assert err.token not in text
    assert "privacy" in text.lower() or "boundary" in text.lower()


def test_format_diagnostic_dependency_error_with_versions() -> None:
    from _shared import diagnostics

    err = diagnostics.DependencyError(
        "pymannkendall",
        reason="below version floor",
        required=">=1.4",
        found="1.2",
    )
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "pymannkendall" in text
    assert ">=1.4" in text
    assert "1.2" in text
    assert "pip install" in text.lower() or "install" in text.lower()


def test_format_diagnostic_dependency_error_missing() -> None:
    from _shared import diagnostics

    err = diagnostics.DependencyError("rapidfuzz", reason="missing")
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "rapidfuzz" in text
    assert "missing" in text.lower() or "not installed" in text.lower()


def test_format_diagnostic_jargon_error() -> None:
    from _shared import diagnostics

    err = diagnostics.JargonError("heteroskedasticity", "findings[3].question")
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "heteroskedasticity" in text
    assert "findings[3].question" in text


def test_format_diagnostic_referential_integrity_error() -> None:
    from _shared import diagnostics

    err = diagnostics.ReferentialIntegrityError("col_99", kind="unknown_column")
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "col_99" in text
    assert "unknown_column" in text or "unknown column" in text.lower()


def test_format_diagnostic_column_not_found_empty_known() -> None:
    """Empty known_columns still produces a readable diagnostic."""
    from _shared import diagnostics

    err = diagnostics.ColumnNotFoundError("x", known_columns=())
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "'x'" in text


def test_format_diagnostic_dependency_error_api_mismatch_no_versions() -> None:
    """Non-missing reason without version metadata still renders cleanly.

    Regression guard: previously the formatter emitted ``"required any,
    found not installed"`` for this case, misleading users into searching
    for a constraint that did not exist. The fix only surfaces version
    metadata that was actually provided to the exception.
    """
    from _shared import diagnostics

    err = diagnostics.DependencyError("pymannkendall", reason="api mismatch")
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    assert "pymannkendall" in text
    assert "api mismatch" in text.lower()
    assert "required any" not in text
    assert "not installed" not in text


def test_format_diagnostic_unknown_exception_type_fallback() -> None:
    """An unfamiliar exception must not produce a traceback (NFR-3)."""
    from _shared import diagnostics

    err = ValueError("some internal error")
    text = diagnostics.format_diagnostic(err)
    _assert_canonical_shape(text)
    # The original str(exc) is preserved so we do not drop information.
    assert "some internal error" in text


def test_format_diagnostic_never_raises_for_unknown_type() -> None:
    from _shared import diagnostics

    class WeirdError(Exception):
        pass

    diagnostics.format_diagnostic(WeirdError("x"))
