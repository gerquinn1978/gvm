"""Walking-skeleton status query for the WS-5 red-skeleton refusal hook (P11-C05).

`/gvm-build` invokes `query_skeleton_status(repo_root)` before each chunk's TDD
loop. Red CI blocks the chunk; missing CLI / missing PR falls back to a
prompted gate that the SKILL.md flow drives via `AskUserQuestion`. Every
invocation writes a chunk-scoped sidecar
`build/handovers/P{X}-C{XX}.skeleton-status.json` so `/gvm-test` can audit
honour-system gates against the WS-5 contract and cap the verdict at
Demo-ready when no CI re-confirmation followed a manual gate (resolves
R3 I-R3-28). The sidecar feeds the WS-5 audit, not VV-3 (which is the
sandbox-divergence criterion family) — naming corrected per R24 M-5.

Pure module — no AskUserQuestion, no real subprocess calls in tests. The CI
provider classifier is reused from `gvm-walking-skeleton._ci_writer` per
P11-C04's "Notes for Downstream Chunks": that module is the single source of
truth for filesystem-marker provider detection.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Optional

# Reuse the canonical CI provider classifier from P11-C04 (Brooks conceptual
# integrity — one concept, one implementation).
_HERE = Path(__file__).resolve().parent
_WALKING_SKELETON_SCRIPTS = _HERE.parents[1] / "gvm-walking-skeleton" / "scripts"
if str(_WALKING_SKELETON_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_WALKING_SKELETON_SCRIPTS))

from _ci_writer import detect_provider as _detect_provider  # noqa: E402


# ----------------------------------------------------------------- types


Method = Literal["ci", "manual", "needs_manual"]
Result = Literal["passed", "failed", "unknown"]
Provider = Literal["github_actions", "gitlab", "circleci", "generic"]

_VALID_RESULTS: tuple[str, ...] = ("passed", "failed", "unknown")


@dataclass(frozen=True)
class SkeletonStatus:
    """Field names lock the JSON sidecar shape consumed by the
    /gvm-test WS-5 honour-system audit."""

    method: Method
    result: Result
    timestamp: str
    ci_provider: Optional[str]


class FirstRunMissingError(Exception):
    """Raised when `walking-skeleton/.first-run.log` is absent. The skill flow
    refuses the chunk and tells the practitioner to run /gvm-walking-skeleton
    first."""


# ----------------------------------------------------------------- constants


WS5_REFUSAL_MESSAGE = (
    "Walking skeleton is red — fix integration before continuing (WS-5). "
    "Run skeleton locally: `make walking-skeleton`"
)


# ----------------------------------------------------------------- detection


def detect_provider(repo_root: Path) -> Provider:
    """Re-export of `_ci_writer.detect_provider`. Single source of truth."""
    return _detect_provider(repo_root)  # type: ignore[return-value]


# ----------------------------------------------------------------- query


_DEFAULT_RUNNER = subprocess.run


def _now_default() -> datetime:
    return datetime.now(timezone.utc)


def query_skeleton_status(
    repo_root: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = _DEFAULT_RUNNER,
    now: Callable[[], datetime] = _now_default,
) -> SkeletonStatus:
    """Determine WS-5 status for `repo_root`.

    Raises:
        FirstRunMissingError: walking-skeleton/.first-run.log is absent. The
            caller should refuse the chunk and direct the practitioner to
            /gvm-walking-skeleton.

    Returns a `SkeletonStatus`. When `method == "needs_manual"` the caller
    must drive an `AskUserQuestion` and then call `make_manual_status` with
    the user's answer.
    """
    first_run = repo_root / "walking-skeleton" / ".first-run.log"
    if not first_run.exists():
        raise FirstRunMissingError(str(first_run))

    provider = detect_provider(repo_root)
    timestamp = now().isoformat()

    if provider == "github_actions":
        return _query_github_actions(runner, timestamp)
    if provider == "gitlab":
        return _query_gitlab(runner, timestamp)
    # CircleCI and generic have no first-class CLI here — fall back to manual.
    return SkeletonStatus(
        method="needs_manual",
        result="unknown",
        timestamp=timestamp,
        ci_provider=provider,
    )


def _query_github_actions(runner, timestamp: str) -> SkeletonStatus:
    needs_manual = SkeletonStatus(
        method="needs_manual",
        result="unknown",
        timestamp=timestamp,
        ci_provider="github_actions",
    )
    try:
        completed = runner(
            ["gh", "pr", "checks"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return needs_manual

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    # Solo-developer / pre-PR fallback (R3 I-R3-9). `gh` writes both
    # "no pull requests found" and "could not find" depending on context.
    lower_stderr = stderr.lower()
    if "no pull requests found" in lower_stderr or "could not find" in lower_stderr:
        return needs_manual

    # `gh pr checks` exits non-zero (typically 8) when at least one check has
    # failed — that is the EXPECTED red-CI path. We trust stdout content
    # (the walking-skeleton row with a recognised pass/fail keyword) rather
    # than gating on returncode. If the walking-skeleton row is absent we
    # fall back to manual below — that branch covers auth/rate-limit errors
    # where stdout is empty.
    if "walking-skeleton" not in stdout.lower():
        return needs_manual

    parsed = _parse_gh_result(stdout)
    # In-progress / queued / pending CI runs surface as "unknown" tokens.
    # Treating that as ci/unknown silently allows the chunk through (WS-5
    # blocks only on "failed"). Defer to the practitioner instead — the
    # WS-5 gate exists precisely to refuse builds against unverified
    # skeletons (R24 CR-4).
    if parsed == "unknown":
        return needs_manual

    return SkeletonStatus(
        method="ci",
        result=parsed,
        timestamp=timestamp,
        ci_provider="github_actions",
    )


def _parse_gh_result(stdout: str) -> Result:
    """`gh pr checks` lists one job per line: `<name>  <status>  <duration>`.
    Look at the line containing 'walking-skeleton'."""
    for raw in stdout.splitlines():
        if "walking-skeleton" in raw.lower():
            tokens = raw.lower().split()
            if any(tok in {"pass", "passed", "success", "completed"} for tok in tokens):
                return "passed"
            if any(tok in {"fail", "failed", "failure", "error"} for tok in tokens):
                return "failed"
    return "unknown"


def _query_gitlab(runner, timestamp: str) -> SkeletonStatus:
    needs_manual = SkeletonStatus(
        method="needs_manual",
        result="unknown",
        timestamp=timestamp,
        ci_provider="gitlab",
    )
    # `glab ci status` is the canonical subcommand. The walking-skeleton spec
    # row originally listed `glab pipeline status` which is not a real
    # subcommand — see chunk handover "Deviations from Spec". `glab ci view`
    # is the alternative; `status` is sufficient for our pass/fail check.
    try:
        completed = runner(
            ["glab", "ci", "status"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return needs_manual

    stdout = completed.stdout or ""
    if "walking-skeleton" not in stdout.lower():
        return needs_manual

    parsed = _parse_glab_result(stdout)
    # See _query_github_actions for the rationale (R24 CR-4): in-progress
    # pipelines must not silently allow chunks through.
    if parsed == "unknown":
        return needs_manual

    return SkeletonStatus(
        method="ci",
        result=parsed,
        timestamp=timestamp,
        ci_provider="gitlab",
    )


def _parse_glab_result(stdout: str) -> Result:
    """Walking-skeleton-scoped parser — pipeline-level status must NOT mask a
    failed `walking-skeleton` job. Mirror `_parse_gh_result`: read tokens only
    from the line that names the job."""
    for raw in stdout.splitlines():
        if "walking-skeleton" in raw.lower():
            tokens = raw.lower().replace("(", " ").replace(")", " ").split()
            if any(tok in {"success", "passed", "pass", "ok"} for tok in tokens):
                return "passed"
            if any(
                tok in {"failed", "failure", "fail", "error", "broken"}
                for tok in tokens
            ):
                return "failed"
    return "unknown"


# ----------------------------------------------------------------- manual gate


def make_manual_status(
    *,
    result: str,
    ci_provider: Optional[str] = None,
    now: Callable[[], datetime] = _now_default,
) -> SkeletonStatus:
    """Build a SkeletonStatus from the practitioner's AskUserQuestion answer."""
    if result not in _VALID_RESULTS:
        raise ValueError(f"result must be one of {_VALID_RESULTS}; got {result!r}")
    return SkeletonStatus(
        method="manual",
        result=result,  # type: ignore[arg-type]
        timestamp=now().isoformat(),
        ci_provider=ci_provider,
    )


# ----------------------------------------------------------------- gate


def is_blocking(status: SkeletonStatus) -> bool:
    """True when the chunk must be refused. Only `result == "failed"` blocks;
    `unknown` does not block (the gate has not yet been evaluated)."""
    return status.result == "failed"


# ----------------------------------------------------------------- sidecar


def write_status_sidecar(handover_path: Path, status: SkeletonStatus) -> Path:
    """Write `{handover_path_no_md_suffix}.skeleton-status.json` atomically.

    The sidecar shape (`method`, `result`, `timestamp`, `ci_provider`) is the
    contract consumed by the /gvm-test WS-5 honour-system audit — field names
    are locked.
    """
    sidecar = handover_path.with_suffix(".skeleton-status.json")
    body = json.dumps(asdict(status), sort_keys=True, indent=2) + "\n"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    tmp = sidecar.parent / f"{sidecar.name}.{os.getpid()}.tmp"
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, sidecar)
    return sidecar
