"""P11-C12 cross-suite isolation tests.

Two skills (gvm-walking-skeleton, gvm-impact-map) each ship a `_validator.py`.
Under pytest's default `prepend` import mode, the first-imported module wins
the bare name `_validator`, and the second skill's tests resolve to the wrong
module — surfacing as the wrong error code (e.g. `IM-2` firing in
walking-skeleton tests).

These tests prove that aggregate pytest runs both suites without bare-name
shadowing: each test sees its own scripts/ directory's `_validator`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module(name: str, file: Path):
    spec = importlib.util.spec_from_file_location(name, file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SKILLS = Path(__file__).resolve().parents[2]
WS_VALIDATOR = SKILLS / "gvm-walking-skeleton/scripts/_validator.py"
IM_VALIDATOR = SKILLS / "gvm-impact-map/scripts/_validator.py"


def test_walking_skeleton_validator_resolves_to_correct_file():
    """The bare-name `_validator` import inside walking-skeleton tests
    must resolve to walking-skeleton/scripts/_validator.py — not the
    impact-map one. The conftest's sys.path prepend + module eviction
    is what makes this true under aggregate pytest runs."""
    from _validator import ValidationError, full_check  # noqa: F401

    cached = sys.modules["_validator"]
    cached_file = Path(getattr(cached, "__file__", "")).resolve()
    expected = WS_VALIDATOR.resolve()
    assert cached_file == expected, (
        f"_validator resolved to {cached_file}, expected {expected}. "
        "Conftest module-eviction is not working — the impact-map "
        "_validator is being seen by walking-skeleton tests."
    )


def test_walking_skeleton_validator_has_walking_skeleton_api():
    """Sanity: the resolved module exposes walking-skeleton's `full_check`,
    not impact-map's. Their full_check signatures differ — walking-skeleton
    accepts a path keyword, impact-map's takes only the file."""
    from _validator import full_check

    import inspect

    sig = inspect.signature(full_check)
    params = list(sig.parameters)
    assert "boundaries_path" in params, (
        f"full_check params {params} look wrong for walking-skeleton's "
        "validator. Impact-map's full_check uses (path), not "
        "(boundaries_path, ...) — finding 'path' here would be a false "
        "positive on the wrong module."
    )


def test_both_validator_files_exist_and_differ():
    """Pre-condition: this collision is real — both files exist, and
    their content differs (otherwise the test is meaningless)."""
    assert WS_VALIDATOR.exists()
    assert IM_VALIDATOR.exists()
    assert WS_VALIDATOR.read_text() != IM_VALIDATOR.read_text()


def test_direct_load_of_both_validators_succeeds():
    """If we bypass sys.path entirely and load each file by absolute path,
    both must work. This is the floor — if this fails, the files
    themselves are broken, not just the import wiring."""
    ws = _load_module("_ws_validator_direct", WS_VALIDATOR)
    im = _load_module("_im_validator_direct", IM_VALIDATOR)
    assert hasattr(ws, "full_check")
    assert hasattr(im, "full_check")
    assert ws is not im
