"""P11-C03 unit tests for `_skeleton_gen.py`.

Spec ref: walking-skeleton ADR-404 (real-call validation), ADR-405
(single-flow constraint), ADR-407 (deferred -> STUBS.md).

Test cases: TC-WS-4-01 (one end-to-end flow exercised), TC-WS-4-02
(generator emits exactly one test function so the lint passes).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Bring `_boundaries_parser` in the same way the production module does.
_DS_SCRIPTS = Path(__file__).resolve().parents[2] / "gvm-design-system" / "scripts"
if str(_DS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DS_SCRIPTS))

from _boundaries_parser import Boundaries, Boundary  # noqa: E402

from _single_flow_check import lint  # noqa: E402
from _skeleton_gen import SkeletonResult, generate  # noqa: E402


# ----------------------------------------------------------------- helpers


def _b(
    name: str,
    *,
    type_: str = "http_api",
    provider: str = "Stripe",
    status: str = "wired",
    creds: str = "STRIPE_TEST_KEY",
    cost: str = "$0 sandbox",
    sla: str = "99.9%",
    divergence: str = "n/a",
) -> Boundary:
    return Boundary(
        name=name,
        type=type_,
        chosen_provider=provider,
        real_call_status=status,
        test_credentials_location=creds,
        cost_model=cost,
        sla_notes=sla,
        production_sandbox_divergence=divergence,
    )


def _registry(*rows: Boundary) -> Boundaries:
    return Boundaries(schema_version=1, rows=tuple(rows), changelog=())


# ----------------------------------------------------------------- python emission


def test_one_wired_row_generates_python_test_file(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"))
    result = generate(boundaries, tmp_path, primary_language="python")
    assert isinstance(result, SkeletonResult)
    assert result.primary_language == "python"
    assert result.test_file == tmp_path / "test_skeleton.py"
    assert result.test_file.exists()
    body = result.test_file.read_text(encoding="utf-8")
    assert "def test_walking_skeleton_flow" in body
    assert "payments-api" in body or "payments_api" in body


def test_generated_python_test_passes_single_flow_lint(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"), _b("email", type_="email"))
    result = generate(boundaries, tmp_path, primary_language="python")
    # Generator emits exactly ONE test function regardless of row count.
    assert lint(result.test_file, language="python") == []


def test_one_wired_row_generates_client_file(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"))
    result = generate(boundaries, tmp_path, primary_language="python")
    assert len(result.client_files) == 1
    client = result.client_files[0]
    assert client == tmp_path / "clients" / "payments_api.py"
    assert client.exists()
    text = client.read_text(encoding="utf-8")
    assert "NotImplementedError" in text
    assert "Stripe" in text
    assert "STRIPE_TEST_KEY" in text


def test_deferred_row_emits_no_op_assertion(tmp_path: Path) -> None:
    boundaries = _registry(
        _b(
            "email",
            type_="email",
            provider="SendGrid",
            status="deferred_stub",
            creds="n/a",
            cost="n/a",
            sla="n/a",
        )
    )
    result = generate(boundaries, tmp_path, primary_language="python")
    body = result.test_file.read_text(encoding="utf-8")
    assert "deferred" in body.lower()
    assert "ADR-407" in body
    assert "walking-skeleton/stubs/email.py" in body
    # Deferred rows must not emit a real call — there should be no
    # `clients.email.<...>()` invocation pattern.
    assert "raise NotImplementedError" not in body  # the call is elided


def test_sandbox_divergence_appears_in_client_docstring(tmp_path: Path) -> None:
    note = "Test cards only; no Apple Pay"
    boundaries = _registry(_b("payments-api", status="wired_sandbox", divergence=note))
    result = generate(boundaries, tmp_path, primary_language="python")
    client_text = result.client_files[0].read_text(encoding="utf-8")
    assert note in client_text


def test_mixed_statuses_all_present_in_one_test_function(tmp_path: Path) -> None:
    boundaries = _registry(
        _b("payments-api"),
        _b("inventory", status="wired_sandbox", divergence="Sandbox SKUs only"),
        _b(
            "email",
            type_="email",
            provider="SendGrid",
            status="deferred_stub",
            creds="n/a",
            cost="n/a",
            sla="n/a",
        ),
    )
    result = generate(boundaries, tmp_path, primary_language="python")
    body = result.test_file.read_text(encoding="utf-8")
    # exactly one test function
    assert body.count("def test_walking_skeleton_flow") == 1
    # all three boundaries referenced by name
    assert "payments-api" in body
    assert "inventory" in body
    assert "email" in body
    # three client files emitted
    assert len(result.client_files) == 3


def test_empty_boundaries_emits_placeholder_test(tmp_path: Path) -> None:
    boundaries = _registry()
    result = generate(boundaries, tmp_path, primary_language="python")
    body = result.test_file.read_text(encoding="utf-8")
    assert "def test_walking_skeleton_flow" in body
    assert "no boundaries" in body.lower()
    assert result.client_files == ()


# ----------------------------------------------------------------- typescript / go


def test_typescript_emits_ts_files(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"))
    result = generate(boundaries, tmp_path, primary_language="typescript")
    assert result.test_file == tmp_path / "test_skeleton.ts"
    body = result.test_file.read_text(encoding="utf-8")
    assert (
        "test('walking skeleton flow'" in body or 'test("walking skeleton flow"' in body
    )
    assert result.client_files[0].suffix == ".ts"


def test_go_emits_go_files(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"))
    result = generate(boundaries, tmp_path, primary_language="go")
    assert result.test_file == tmp_path / "skeleton_test.go"
    body = result.test_file.read_text(encoding="utf-8")
    assert "func TestWalkingSkeletonFlow" in body
    assert result.client_files[0].suffix == ".go"


def test_go_client_files_use_test_suffix(tmp_path: Path) -> None:
    """Go client files MUST end in `_test.go` so `go test` links the
    `exercise<Name>(t *testing.T)` helpers into the test binary."""
    boundaries = _registry(_b("payments-api"))
    result = generate(boundaries, tmp_path, primary_language="go")
    assert result.client_files[0].name == "payments_api_test.go"


def test_existing_init_py_raises_file_exists(tmp_path: Path) -> None:
    """If clients/__init__.py exists with practitioner content, refuse."""
    (tmp_path / "clients").mkdir()
    (tmp_path / "clients" / "__init__.py").write_text(
        "# practitioner re-exports\n", encoding="utf-8"
    )
    boundaries = _registry(_b("payments-api"))
    with pytest.raises(FileExistsError):
        generate(boundaries, tmp_path, primary_language="python")


# ----------------------------------------------------------------- error paths


def test_unknown_language_raises(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"))
    with pytest.raises(ValueError, match="ruby"):
        generate(boundaries, tmp_path, primary_language="ruby")


def test_existing_client_file_raises_file_exists(tmp_path: Path) -> None:
    """Practitioner edits to clients/<name>.py must not be silently overwritten."""
    boundaries = _registry(_b("payments-api"))
    (tmp_path / "clients").mkdir()
    (tmp_path / "clients" / "payments_api.py").write_text(
        "# practitioner-wired real call\n", encoding="utf-8"
    )
    with pytest.raises(FileExistsError):
        generate(boundaries, tmp_path, primary_language="python")


def test_leading_digit_boundary_name_yields_legal_python_identifier(
    tmp_path: Path,
) -> None:
    boundaries = _registry(_b("3rdparty-api"))
    result = generate(boundaries, tmp_path, primary_language="python")
    assert result.client_files[0] == tmp_path / "clients" / "_3rdparty_api.py"
    body = result.test_file.read_text(encoding="utf-8")
    assert "_3rdparty_api" in body  # used in import + call


def test_python_emits_clients_init_py(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"))
    generate(boundaries, tmp_path, primary_language="python")
    init = tmp_path / "clients" / "__init__.py"
    assert init.exists()
    assert init.read_text() == ""


def test_existing_test_file_raises_file_exists(tmp_path: Path) -> None:
    (tmp_path / "test_skeleton.py").write_text("# already here\n", encoding="utf-8")
    boundaries = _registry(_b("payments-api"))
    with pytest.raises(FileExistsError):
        generate(boundaries, tmp_path, primary_language="python")


def test_skeleton_result_is_frozen(tmp_path: Path) -> None:
    boundaries = _registry(_b("payments-api"))
    result = generate(boundaries, tmp_path, primary_language="python")
    with pytest.raises(Exception):
        result.test_file = tmp_path / "other.py"  # type: ignore[misc]


# ----------------------------------------------------------------- integration with lint


def test_generated_test_file_at_or_below_max_tests(tmp_path: Path) -> None:
    """Generator emits exactly 1 test function; the lint's max=3 default
    must always pass on generator output (TC-WS-4-01)."""
    boundaries = _registry(*[_b(f"b{i}", type_="http_api") for i in range(10)])
    result = generate(boundaries, tmp_path, primary_language="python")
    assert lint(result.test_file, language="python", max_tests=3) == []
