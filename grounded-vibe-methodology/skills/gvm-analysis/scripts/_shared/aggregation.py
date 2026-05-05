"""Multi-sheet xlsx handling and multi-file aggregation (AN-3, P2-C01b).

Split out of ``_shared/io.py`` per cross-cutting ADR-007 (SRP). This module
composes over ``_shared.io.load`` — it never re-implements file loading,
encryption detection, or format dispatch. That keeps the AN-42 refusal
contract a single-sourced concern and makes this module trivially
testable.

Public surface:

* :func:`load_sheets` — enumerate every sheet of a multi-sheet xlsx into a
  ``{sheet_name: DataFrame}`` mapping. The AskUserQuestion prompt that
  chooses which sheet(s) to analyse lives in ``skill-orchestration`` (P5);
  this primitive never silently picks.
* :func:`aggregate` — multi-file aggregation strategies per AN-3. Three
  strategies: ``"concat"`` (inner-join across files), ``"per_file"``
  (one frame per file, native columns preserved), ``"comparative"`` (one
  frame per file, intersection columns only — caller computes deltas).

Every strategy routes paths through :func:`_shared.io.load`, so encrypted
xlsx is refused identically on every aggregation path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from _shared import io

__all__ = ["load_sheets", "aggregate"]

_SUPPORTED_STRATEGIES: tuple[str, ...] = ("concat", "per_file", "comparative")

Strategy = Literal["concat", "per_file", "comparative"]

_SOURCE_FILE_COLUMN = "__source_file__"


def load_sheets(path: Path | str) -> dict[str, pd.DataFrame]:
    """Return ``{sheet_name: DataFrame}`` for every sheet in an xlsx.

    Routes the sheet-name enumeration through :func:`io._open_workbook`
    so the AN-42 encryption-refusal contract applies uniformly — an
    encrypted xlsx handed to this path raises
    :class:`~_shared.diagnostics.EncryptedFileError` identically to
    :func:`io.load`. Each sheet is then loaded via :func:`io.load` so all
    the downstream contracts (empty-sheet detection, multi-sheet
    dispatch) stay single-sourced in ``io.py``.

    The leading underscore on ``io._open_workbook`` is intentionally
    crossed here: it is a semi-public helper shared across ``io.py`` and
    ``aggregation.py`` by design (ADR-007 SRP split — both modules own
    xlsx concerns and must share the encryption guard). Do NOT
    re-implement sheet enumeration in this module; that would fork the
    AN-42 refusal contract.

    Performance note: this is O(N+1) openpyxl opens for an N-sheet
    workbook (one for the name list plus one per sheet inside
    :func:`io.load`). This is deliberate — collapsing to one open would
    bypass ``io.load``'s empty-sheet detection on each sheet. Optimise
    only after a real profiling signal.
    """
    path = Path(path)

    wb = io._open_workbook(path, data_only=True)
    sheet_names = list(wb.sheetnames)

    return {name: io.load(path, sheet=name) for name in sheet_names}


def aggregate(
    paths: list[Path | str], strategy: str
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Combine frames from multiple input files per the chosen strategy.

    Parameters
    ----------
    paths
        Non-empty list of file paths; each is loaded via :func:`io.load`.
        Single-path lists are valid.
    strategy
        One of ``"concat"``, ``"per_file"``, ``"comparative"``. Any other
        value raises :class:`ValueError`.

    Returns
    -------
    ``"concat"``
        A single :class:`pandas.DataFrame` with shared columns plus a
        ``__source_file__`` column recording each row's origin file
        stem.
    ``"per_file"``
        ``{file_stem: DataFrame}`` — each frame keeps its native columns.
    ``"comparative"``
        ``{file_stem: DataFrame}`` — each frame is reduced to the
        intersection columns shared across every input, in the order
        they appeared in the first frame. Caller computes deltas.

    Raises
    ------
    ValueError
        Empty ``paths``; unknown ``strategy``; empty column intersection
        under ``"concat"`` or ``"comparative"``.
    """
    if not paths:
        raise ValueError("no input files: aggregate() requires at least one path")

    if strategy not in _SUPPORTED_STRATEGIES:
        raise ValueError(
            f"unknown aggregation strategy: {strategy!r} "
            f"(supported: {', '.join(_SUPPORTED_STRATEGIES)})"
        )

    resolved = [Path(p) for p in paths]
    frames: list[pd.DataFrame] = [io.load(p) for p in resolved]
    stems: list[str] = [p.stem for p in resolved]

    if strategy == "per_file":
        return dict(zip(stems, frames))

    # concat and comparative both need the shared-column intersection.
    shared = _intersect_columns(frames)
    if not shared:
        per_file_columns = ", ".join(
            f"{stem}={list(frame.columns)}" for stem, frame in zip(stems, frames)
        )
        raise ValueError(f"no common columns across files: {per_file_columns}")

    if strategy == "comparative":
        return {stem: frame.loc[:, shared].copy() for stem, frame in zip(stems, frames)}

    # strategy == "concat"
    tagged = [
        frame.loc[:, shared].assign(**{_SOURCE_FILE_COLUMN: stem})
        for stem, frame in zip(stems, frames)
    ]
    return pd.concat(tagged, ignore_index=True)


def _intersect_columns(frames: list[pd.DataFrame]) -> list[str]:
    """Return the shared columns across every frame, in first-frame order.

    Preserving first-frame order keeps concat/comparative output stable
    against the engine's per-column processing expectations. Using a plain
    :class:`set` intersection would randomise the column order on each
    invocation, which makes downstream diffs unreadable.
    """
    if not frames:
        return []
    common = set(frames[0].columns)
    for frame in frames[1:]:
        common &= set(frame.columns)
    return [col for col in frames[0].columns if col in common]
