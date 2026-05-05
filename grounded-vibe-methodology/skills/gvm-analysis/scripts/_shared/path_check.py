"""Mapping-path risk validator for ``anonymise.py``.

Anonymisation-pipeline ADR-404 / AN-38 (P14-C01, originally P7-C01 in the
gvm-analysis impl-guide; renumbered to avoid plugin-build clash).

Public API
----------

* :func:`validate(mapping_out, *, accept_risk=False, claude_settings_path=None)`
  — raises :class:`_shared.diagnostics.RiskyMappingPathError` if the path
  lies inside any scope Claude Code can typically read. Returns ``None``
  silently when the path is safe (or when ``accept_risk=True`` short-circuits
  the check).

Scope definition (post-spec interpretation, see handover "Deviations from
Spec"): a path is risky when it falls under

* the current working directory (resolved), OR
* any directory listed in ``permissions.additionalDirectories`` of
  ``claude_settings_path`` (default ``~/.claude/settings.json``).

The spec's ADR-404 prose also names ``Path.home()`` as a warning scope.
That blanket reading contradicts TC-AN-38-02, which fixes
``~/.private/gvm-mappings/<project>/<date>.csv`` as the canonical *safe*
path. We treat home-overlap-alone as not risky; if the same path is also
under cwd or ``additionalDirectories`` the overlap with those scopes
flags it independently. This resolves the spec/test contradiction.
"""

from __future__ import annotations

import json
from pathlib import Path

from _shared.diagnostics import MalformedFileError, RiskyMappingPathError


def _default_settings_path() -> Path:
    """Resolve ``~/.claude/settings.json`` relative to ``HOME`` env at call time.

    Resolved at call time (not import time) so tests that monkeypatch
    ``HOME`` are honoured without restating the path on every call.
    """
    return Path.home() / ".claude" / "settings.json"


def _load_additional_directories(settings_path: Path) -> list[Path]:
    """Read the ``permissions.additionalDirectories`` list.

    Missing file → empty list (defensive: not all users have a settings
    file). Malformed JSON propagates as :class:`MalformedFileError` so
    :func:`format_diagnostic` renders the standard parser-error block.
    Missing or non-list ``additionalDirectories`` key → empty list (the
    user simply has not declared any extra dirs).
    """
    if not settings_path.exists():
        return []
    try:
        raw = settings_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise MalformedFileError(
            settings_path, row=None, col=None, kind="parser_error"
        ) from None

    if not isinstance(data, dict):
        return []
    perms = data.get("permissions")
    if not isinstance(perms, dict):
        return []
    extras = perms.get("additionalDirectories")
    if not isinstance(extras, list):
        return []
    out: list[Path] = []
    for entry in extras:
        if isinstance(entry, str):
            out.append(Path(entry).expanduser().resolve())
    return out


def _is_under(path: Path, scope: Path) -> bool:
    """Return True if ``path`` is ``scope`` or a descendant.

    Both arguments must already be resolved. ``Path.is_relative_to`` (3.9+)
    returns False for unrelated trees and True for self / descendants —
    matches the "inside scope" semantics ADR-404 needs.
    """
    return path == scope or path.is_relative_to(scope)


def validate(
    mapping_out: Path,
    *,
    accept_risk: bool = False,
    claude_settings_path: Path | None = None,
) -> None:
    """Validate that ``mapping_out`` does not lie inside Claude's reachable scope.

    Returns ``None`` silently when the path is safe (or when
    ``accept_risk=True``). Raises :class:`RiskyMappingPathError` with a
    fully-formed ADR-404 diagnostic otherwise.

    Parameters
    ----------
    mapping_out
        The path the user supplied to ``anonymise.py --mapping-out``.
        Resolved internally via :meth:`Path.resolve` before comparison.
    accept_risk
        When True, the function returns silently without checking. This
        is the ``--i-accept-the-risk`` opt-in path; the caller has
        accepted that they have audited their environment.
    claude_settings_path
        The settings file to consult for ``additionalDirectories``.
        ``None`` means use :func:`_default_settings_path`. Tests inject a
        ``tmp_path`` settings file so the real ``~/.claude/settings.json``
        is never touched.
    """
    if accept_risk:
        return

    target = mapping_out.expanduser().resolve()
    cwd = Path.cwd().resolve()
    settings_path = (
        claude_settings_path
        if claude_settings_path is not None
        else _default_settings_path()
    )
    additional = _load_additional_directories(settings_path)

    flagged_scopes: list[str] = []
    if _is_under(target, cwd):
        flagged_scopes.append(f"{cwd} (current working directory)")
    for extra in additional:
        if _is_under(target, extra):
            flagged_scopes.append(f"{extra} (additionalDirectories)")

    if flagged_scopes:
        raise RiskyMappingPathError(target, flagged_scopes)
    return None
