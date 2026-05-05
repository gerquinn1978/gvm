"""Defect-intake helpers for `/gvm-explore-test` (P11-C07).

Implements ADR-203 (defect intake), ADR-205 (severity-is-practitioner-call),
and ADR-206 (severity-enum split: defects carry Critical/Important/Minor;
observations carry no severity).

The skill's runtime issues `AskUserQuestion` prompts during a session and
calls `IntakeSession.record(...)` with the collected values. This module
classifies the entry (DefectEntry vs ObservationEntry, applying the
no-reproduction → Observation re-filing rule) and accumulates the in-memory
list. After every intake the runtime calls `write_partial_handover(...)`
for crash-recovery (ADR-204).

Practitioner-supplied strings are OPAQUE PAYLOAD here. No `.strip()`,
no `html.escape()`, no normalisation. The HTML escape is P11-C08's job;
mangling the payload at intake would silently mask renderer bugs.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Severity = Literal["Critical", "Important", "Minor", "Observation"]
DefectSeverity = Literal["Critical", "Important", "Minor"]

_ALLOWED_SEVERITIES: tuple[str, ...] = ("Critical", "Important", "Minor", "Observation")
_SESSION_NNN_PATTERN = re.compile(r"^\d{3}$")


class IntakeError(Exception):
    """Validation failure during defect intake. Carries the offending field
    and a human-readable reason — same contract as `CharterError`."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"intake field {field!r}: {reason}")
        self.field = field
        self.reason = reason


@dataclass(frozen=True)
class DefectEntry:
    """A practitioner-classified defect with a reproduction path. ADR-206
    splits these from observations: severity is one of Critical/Important/
    Minor (NEVER Observation — those use ObservationEntry)."""

    id: str
    severity: DefectSeverity
    given: str
    when: str
    then: str
    reproduction: str
    stub_path: str | None


@dataclass(frozen=True)
class ObservationEntry:
    """A non-blocking observation. No severity field per ADR-206 — produced
    by the practitioner choosing severity=Observation, or by the re-filing
    rule (severity ≥ Minor with blank reproduction)."""

    id: str
    given: str
    when: str
    then: str
    stub_path: str | None


class IntakeSession:
    """In-memory accumulator for one charter. Created when the skill enters
    Phase 2 (Session) and discarded after Phase 3 (Debrief) writes the
    artefact. The session_nnn (three-digit, zero-padded) ties this session
    to its charter file."""

    def __init__(self, session_nnn: str) -> None:
        if not isinstance(session_nnn, str) or not _SESSION_NNN_PATTERN.fullmatch(
            session_nnn
        ):
            raise IntakeError(
                "session_nnn",
                f"must be a three-digit zero-padded string; got {session_nnn!r}",
            )
        self._session_nnn = session_nnn
        self._defects: list[DefectEntry] = []
        self._observations: list[ObservationEntry] = []

    @property
    def session_nnn(self) -> str:
        return self._session_nnn

    @property
    def defects(self) -> tuple[DefectEntry, ...]:
        return tuple(self._defects)

    @property
    def observations(self) -> tuple[ObservationEntry, ...]:
        return tuple(self._observations)

    def record(
        self,
        severity: Severity,
        given: str,
        when: str,
        then: str,
        reproduction: str = "",
        stub_path: str | None = None,
    ) -> DefectEntry | ObservationEntry:
        """Classify and store one intake. Per ADR-203, severity ≥ Minor with
        a blank-or-whitespace reproduction is re-filed as Observation."""
        _validate_severity(severity)
        _validate_gwt("given", given)
        _validate_gwt("when", when)
        _validate_gwt("then", then)

        # Re-filing rule (ADR-203 + ET-3). Severity == Observation is
        # always an observation; defect severities with blank reproduction
        # are re-filed.
        if severity == "Observation" or not reproduction.strip():
            entry: DefectEntry | ObservationEntry = ObservationEntry(
                id=f"O-{len(self._observations) + 1:03d}",
                given=given,
                when=when,
                then=then,
                stub_path=stub_path,
            )
            self._observations.append(entry)
            return entry

        defect = DefectEntry(
            id=f"D-{len(self._defects) + 1:03d}",
            severity=severity,  # type: ignore[arg-type]  # narrowed by branch above
            given=given,
            when=when,
            then=then,
            reproduction=reproduction,
            stub_path=stub_path,
        )
        self._defects.append(defect)
        return defect


# ----------------------------------------------------------------- validators


def _validate_severity(value: object) -> None:
    if value not in _ALLOWED_SEVERITIES:
        raise IntakeError(
            "severity",
            f"must be one of {_ALLOWED_SEVERITIES}; got {value!r}",
        )


def _validate_gwt(field: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise IntakeError(field, "must be a non-empty string")


# ----------------------------------------------------------------- partial handover


def write_partial_handover(session: IntakeSession, handovers_dir: Path) -> Path:
    """Write `explore-NNN-partial.md` atomically (write to a sibling .tmp,
    then `os.replace`). Per ADR-204 — recovery point after every intake.
    Creates `handovers_dir` if missing.

    Returns the final path of the written file."""
    handovers_dir.mkdir(parents=True, exist_ok=True)
    final = handovers_dir / f"explore-{session.session_nnn}-partial.md"
    body = _render_partial_handover(session)

    # tempfile.NamedTemporaryFile in the same dir guarantees os.replace is
    # an atomic rename on POSIX and a replace on Windows. delete=False so
    # we manage the tmp lifecycle ourselves.
    fd, tmp_path = tempfile.mkstemp(
        prefix=f"explore-{session.session_nnn}-partial.",
        suffix=".tmp",
        dir=str(handovers_dir),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmp_path, final)
    except Exception:
        # Best-effort cleanup on failure so we don't leave .tmp orphans.
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
    return final


def remove_partial_handover(session: IntakeSession, handovers_dir: Path) -> bool:
    """Delete `explore-NNN-partial.md` after `_report_writer.write_report`
    succeeds. The DEBRIEF flow MUST call this only on a successful write —
    if `write_report` raised, the partial file is the crash-recovery point
    (ADR-204) and removing it would lose state (R24 I-6).

    Returns True if a partial file was removed, False if it did not exist
    or could not be removed (R25 I-1: PermissionError / IsADirectoryError
    must not crash the DEBRIEF flow — the report is already written, so the
    session is functionally complete; an unremovable partial is a
    housekeeping concern, not a correctness one)."""
    final = handovers_dir / f"explore-{session.session_nnn}-partial.md"
    try:
        final.unlink()
        return True
    except OSError:
        return False


def _render_partial_handover(session: IntakeSession) -> str:
    lines = [
        f"# Partial Handover: explore-{session.session_nnn}",
        "",
        "Session resumable — written after every intake (ADR-204).",
        "",
        f"- Defects: {len(session.defects)}",
        f"- Observations: {len(session.observations)}",
        "",
        "## Defects",
        "",
    ]
    if not session.defects:
        lines.append("_None recorded yet._")
    else:
        for d in session.defects:
            lines.extend(
                [
                    f"### {d.id} — {d.severity}",
                    f"- **Given:** {d.given}",
                    f"- **When:** {d.when}",
                    f"- **Then:** {d.then}",
                    f"- **Reproduction:** {d.reproduction}",
                    f"- **Stub-path:** {d.stub_path or '(none)'}",
                    "",
                ]
            )
    lines.extend(["", "## Observations", ""])
    if not session.observations:
        lines.append("_None recorded yet._")
    else:
        for o in session.observations:
            lines.extend(
                [
                    f"### {o.id}",
                    f"- **Given:** {o.given}",
                    f"- **When:** {o.when}",
                    f"- **Then:** {o.then}",
                    f"- **Stub-path:** {o.stub_path or '(none)'}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"
