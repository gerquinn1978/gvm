"""Tests for `_skeleton_status.py` — WS-5 red-skeleton refusal hook (P11-C05).

Subprocess and time are injected so tests do not touch the network or the wall
clock. The reference test for TC-WS-5-02 is `test_red_ci_blocks_chunk`.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import pytest

# sys.path injection is handled by `scripts/conftest.py` — adding it here
# would create a duplicate, latently-coupled second source of truth (R24 M-1).
from _skeleton_status import (
    FirstRunMissingError,
    SkeletonStatus,
    WS5_REFUSAL_MESSAGE,
    detect_provider,
    is_blocking,
    make_manual_status,
    query_skeleton_status,
    write_status_sidecar,
)


# ---------------------------------------------------------------- fixtures


FIXED_NOW = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)


def _now() -> datetime:
    return FIXED_NOW


def _make_repo(
    tmp_path: Path, *, provider: str = "github_actions", first_run: bool = True
) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "walking-skeleton").mkdir()
    if first_run:
        (repo / "walking-skeleton" / ".first-run.log").write_text(
            "ok\n", encoding="utf-8"
        )
    if provider == "github_actions":
        (repo / ".github" / "workflows").mkdir(parents=True)
    elif provider == "gitlab":
        (repo / ".gitlab-ci.yml").write_text("stages: [test]\n", encoding="utf-8")
    elif provider == "circleci":
        (repo / ".circleci").mkdir()
        (repo / ".circleci" / "config.yml").write_text(
            "version: 2.1\n", encoding="utf-8"
        )
    return repo


def _runner(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
    raise_filenotfound: bool = False,
):
    def run(args, *, capture_output=True, text=True, check=False, **kwargs):
        if raise_filenotfound:
            raise FileNotFoundError(args[0])
        return subprocess.CompletedProcess(
            args=args, returncode=returncode, stdout=stdout, stderr=stderr
        )

    return run


# ---------------------------------------------------------------- first-run.log gate


def test_first_run_log_missing_raises(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, first_run=False)
    with pytest.raises(FirstRunMissingError):
        query_skeleton_status(repo, runner=_runner(), now=_now)


# ---------------------------------------------------------------- detection delegation


def test_detect_provider_delegates_to_ci_writer(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="gitlab")
    assert detect_provider(repo) == "gitlab"


# ---------------------------------------------------------------- GH Actions paths


def test_github_actions_passing(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="github_actions")
    runner = _runner(stdout="walking-skeleton  pass  0s\n", returncode=0)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "ci"
    assert status.result == "passed"
    assert status.ci_provider == "github_actions"
    assert status.timestamp == FIXED_NOW.isoformat()


def test_red_ci_blocks_chunk(tmp_path: Path) -> None:
    """TC-WS-5-02 reference: red CI -> blocking, refusal message cites WS-5."""
    repo = _make_repo(tmp_path, provider="github_actions")
    runner = _runner(stdout="walking-skeleton  fail  12s\n", returncode=1)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "ci"
    assert status.result == "failed"
    assert is_blocking(status) is True
    assert "WS-5" in WS5_REFUSAL_MESSAGE
    assert "make walking-skeleton" in WS5_REFUSAL_MESSAGE


@pytest.mark.parametrize(
    "stderr_msg",
    [
        "no pull requests found for branch main\n",
        "could not find any pull request for ref HEAD\n",
    ],
)
def test_github_actions_missing_pr_falls_back_to_manual(
    tmp_path: Path, stderr_msg: str
) -> None:
    """Both `gh` no-PR phrasings fall through to the prompted gate."""
    repo = _make_repo(tmp_path, provider="github_actions")
    runner = _runner(stdout="", stderr=stderr_msg, returncode=1)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "needs_manual"
    assert status.result == "unknown"
    assert status.ci_provider == "github_actions"


def test_gh_cli_missing_falls_back_to_manual(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="github_actions")
    runner = _runner(raise_filenotfound=True)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "needs_manual"
    assert status.result == "unknown"
    assert status.ci_provider == "github_actions"


def test_github_actions_walking_skeleton_check_absent_in_output(tmp_path: Path) -> None:
    """`gh pr checks` succeeds but no walking-skeleton job listed -> needs_manual."""
    repo = _make_repo(tmp_path, provider="github_actions")
    runner = _runner(stdout="lint  pass  3s\nbuild  pass  10s\n", returncode=0)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "needs_manual"
    assert status.result == "unknown"


# ---------------------------------------------------------------- GitLab paths


def test_gitlab_passing(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="gitlab")
    runner = _runner(stdout="walking-skeleton (success)  2m\n", returncode=0)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "ci"
    assert status.result == "passed"
    assert status.ci_provider == "gitlab"


def test_gitlab_failing(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="gitlab")
    runner = _runner(stdout="walking-skeleton (failed)  3m\n", returncode=1)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "ci"
    assert status.result == "failed"
    assert is_blocking(status) is True


def test_gitlab_pipeline_success_does_not_mask_failed_skeleton_job(
    tmp_path: Path,
) -> None:
    """Regression: pipeline-level 'success' must NOT mask a failed
    walking-skeleton job. The parser scopes status tokens to the
    walking-skeleton line only (mirrors `_parse_gh_result`)."""
    repo = _make_repo(tmp_path, provider="gitlab")
    stdout = (
        "Status: success\nlint (success)\nwalking-skeleton (failed)\nbuild (success)\n"
    )
    runner = _runner(stdout=stdout, returncode=0)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "ci"
    assert status.result == "failed"
    assert is_blocking(status) is True


def test_glab_missing_falls_back_to_manual(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="gitlab")
    runner = _runner(raise_filenotfound=True)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "needs_manual"


def test_glab_unknown_subcommand_falls_back_to_manual(tmp_path: Path) -> None:
    """If glab is installed but the subcommand drifts (e.g. between glab
    versions), stdout will be empty and we must fall back to manual rather
    than silently never querying CI."""
    repo = _make_repo(tmp_path, provider="gitlab")
    runner = _runner(stdout="", stderr="unknown command\n", returncode=2)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "needs_manual"
    assert status.ci_provider == "gitlab"


def test_glab_invocation_uses_ci_status_subcommand(tmp_path: Path) -> None:
    """The canonical glab subcommand is `glab ci status` (NOT `glab pipeline
    status` — that is not a real subcommand). Pin the args to prevent silent
    regression to the wrong command."""
    repo = _make_repo(tmp_path, provider="gitlab")
    captured = {}

    def runner(args, *, capture_output=True, text=True, check=False, **kwargs):
        captured["args"] = list(args)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    query_skeleton_status(repo, runner=runner, now=_now)
    assert captured["args"] == ["glab", "ci", "status"]


# ---------------------------------------------------------------- CircleCI / generic


def test_circleci_returns_needs_manual(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="circleci")
    status = query_skeleton_status(repo, runner=_runner(), now=_now)
    assert status.method == "needs_manual"
    assert status.ci_provider == "circleci"


def test_generic_provider_returns_needs_manual(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="generic")
    status = query_skeleton_status(repo, runner=_runner(), now=_now)
    assert status.method == "needs_manual"
    assert status.ci_provider == "generic"


# ---------------------------------------------------------------- is_blocking truth table


@pytest.mark.parametrize(
    ("result", "expected"),
    [("failed", True), ("passed", False), ("unknown", False)],
)
def test_is_blocking_truth_table(result: str, expected: bool) -> None:
    status = SkeletonStatus(
        method="ci",
        result=result,
        timestamp=FIXED_NOW.isoformat(),
        ci_provider="github_actions",
    )
    assert is_blocking(status) is expected


# ---------------------------------------------------------------- make_manual_status


def test_make_manual_status_records_user_answer() -> None:
    status = make_manual_status(result="passed", ci_provider="circleci", now=_now)
    assert status.method == "manual"
    assert status.result == "passed"
    assert status.ci_provider == "circleci"
    assert status.timestamp == FIXED_NOW.isoformat()


def test_make_manual_status_invalid_result_raises() -> None:
    with pytest.raises(ValueError):
        make_manual_status(result="bogus", ci_provider=None, now=_now)


# ---------------------------------------------------------------- sidecar


def test_write_status_sidecar_writes_well_formed_json(tmp_path: Path) -> None:
    handover = tmp_path / "P11-C05.md"
    handover.write_text("# handover\n", encoding="utf-8")
    status = SkeletonStatus(
        method="ci",
        result="passed",
        timestamp=FIXED_NOW.isoformat(),
        ci_provider="github_actions",
    )
    sidecar = write_status_sidecar(handover, status)
    assert sidecar == tmp_path / "P11-C05.skeleton-status.json"
    parsed = json.loads(sidecar.read_text(encoding="utf-8"))
    assert parsed == {
        "method": "ci",
        "result": "passed",
        "timestamp": FIXED_NOW.isoformat(),
        "ci_provider": "github_actions",
    }


def test_write_status_sidecar_idempotent_on_identical_content(tmp_path: Path) -> None:
    handover = tmp_path / "P11-C05.md"
    status = SkeletonStatus(
        method="manual",
        result="failed",
        timestamp=FIXED_NOW.isoformat(),
        ci_provider=None,
    )
    p1 = write_status_sidecar(handover, status)
    p2 = write_status_sidecar(handover, status)
    assert p2 == p1
    assert json.loads(p2.read_text(encoding="utf-8"))["ci_provider"] is None


def test_write_status_sidecar_temp_file_pid_suffixed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Atomic write uses a process-unique temp name (mirrors _ci_writer._atomic_write)."""
    handover = tmp_path / "P3-C01.md"
    captured = {}

    real_replace = os.replace

    def spy_replace(src, dst):
        captured["src"] = str(src)
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy_replace)
    status = SkeletonStatus(
        method="ci",
        result="passed",
        timestamp=FIXED_NOW.isoformat(),
        ci_provider="gitlab",
    )
    write_status_sidecar(handover, status)
    assert f".{os.getpid()}.tmp" in captured["src"]


def test_write_status_sidecar_creates_parent_directory(tmp_path: Path) -> None:
    handover = tmp_path / "deep" / "nested" / "P1-C01.md"
    status = SkeletonStatus(
        method="ci",
        result="passed",
        timestamp=FIXED_NOW.isoformat(),
        ci_provider="github_actions",
    )
    sidecar = write_status_sidecar(handover, status)
    assert sidecar.exists()


# ---------------------------------------------------------------- WS5 refusal message


def test_ws5_refusal_message_content() -> None:
    assert "WS-5" in WS5_REFUSAL_MESSAGE
    assert "make walking-skeleton" in WS5_REFUSAL_MESSAGE
    assert "red" in WS5_REFUSAL_MESSAGE.lower()


# ---------------------------------------------------------------- R24 CR-4: in-progress CI must not silently pass
#
# The defect: when `gh pr checks` lists `walking-skeleton  in_progress  -`,
# `_parse_gh_result` returns `"unknown"` (no recognised pass/fail token).
# Pre-fix: that produced `SkeletonStatus(method="ci", result="unknown")` and
# `is_blocking → False` because only "failed" blocks. WS-5 was silently
# bypassed for any chunk started while a CI run was still pending.
# Post-fix: ci/unknown promotes to needs_manual so the practitioner is
# asked to confirm.


@pytest.mark.parametrize(
    "stdout",
    [
        "walking-skeleton  in_progress  -\n",
        "walking-skeleton  queued  -\n",
        "walking-skeleton  pending  -\n",
    ],
)
def test_gh_in_progress_promotes_to_needs_manual(stdout: str, tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="github_actions")
    runner = _runner(stdout=stdout, returncode=0)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "needs_manual"
    assert status.result == "unknown"
    assert status.ci_provider == "github_actions"


def test_glab_in_progress_promotes_to_needs_manual(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, provider="gitlab")
    runner = _runner(stdout="walking-skeleton (running)  -\n", returncode=0)
    status = query_skeleton_status(repo, runner=runner, now=_now)
    assert status.method == "needs_manual"
    assert status.result == "unknown"
    assert status.ci_provider == "gitlab"
