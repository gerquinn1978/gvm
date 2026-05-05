"""P11-C04 unit tests for `_ci_writer.py`.

Spec ref: walking-skeleton ADR-406 (multi-provider CI integration).

Test cases: TC-WS-5-01 (skeleton test runs in CI on every push) — exercised
across all four provider paths (github_actions, gitlab, circleci, generic).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # test-only — production module does not import yaml

from _ci_writer import (
    CIWriteResult,
    detect_provider,
    write_ci_job,
)


# ----------------------------------------------------------------- helpers


def _touch(path: Path, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


# ----------------------------------------------------------------- detect_provider


def test_detect_github_actions(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    assert detect_provider(tmp_path) == "github_actions"


def test_detect_gitlab(tmp_path: Path) -> None:
    _touch(tmp_path / ".gitlab-ci.yml", "stages: [test]\n")
    assert detect_provider(tmp_path) == "gitlab"


def test_detect_circleci(tmp_path: Path) -> None:
    _touch(tmp_path / ".circleci" / "config.yml", "version: 2.1\n")
    assert detect_provider(tmp_path) == "circleci"


def test_detect_generic_when_no_markers(tmp_path: Path) -> None:
    assert detect_provider(tmp_path) == "generic"


def test_detect_github_actions_wins_over_gitlab(tmp_path: Path) -> None:
    """First match wins; multiple markers — GitHub Actions wins."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    _touch(tmp_path / ".gitlab-ci.yml", "stages: [test]\n")
    assert detect_provider(tmp_path) == "github_actions"


def test_detect_github_actions_wins_over_circleci(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    _touch(tmp_path / ".circleci" / "config.yml", "version: 2.1\n")
    assert detect_provider(tmp_path) == "github_actions"


# ----------------------------------------------------------------- github_actions


def test_github_actions_writes_workflow_file(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    result = write_ci_job(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "walking-skeleton.yml"
    assert workflow.exists()
    body = workflow.read_text(encoding="utf-8")
    assert "name: Walking Skeleton" in body
    assert "make walking-skeleton" in body
    parsed = yaml.safe_load(body)
    assert parsed["name"] == "Walking Skeleton"
    # GitHub Actions `on:` collides with YAML 1.1 boolean — we quote the key.
    triggers = parsed.get("on", parsed.get(True))
    assert triggers == ["push", "pull_request"]
    assert "walking-skeleton" in parsed["jobs"]
    assert isinstance(result, CIWriteResult)
    assert result.provider == "github_actions"
    assert workflow in result.files_created


def test_github_actions_idempotent_on_identical_content(tmp_path: Path) -> None:
    """Re-running on a repo with byte-identical existing content is a no-op
    (review I-2)."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    write_ci_job(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "walking-skeleton.yml"
    body_before = workflow.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_after = workflow.read_text(encoding="utf-8")
    assert body_before == body_after
    assert result2.files_created == ()
    assert result2.files_modified == ()


def test_github_actions_refuses_overwrite(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    existing = tmp_path / ".github" / "workflows" / "walking-skeleton.yml"
    existing.write_text("# practitioner-edited\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_ci_job(tmp_path)


def test_github_actions_creates_workflows_dir_if_only_dotgithub_exists(
    tmp_path: Path,
) -> None:
    # `.github` alone is not a marker; the `workflows` subdir is. Create it now.
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "workflows").mkdir()
    result = write_ci_job(tmp_path)
    assert (tmp_path / ".github" / "workflows" / "walking-skeleton.yml").exists()
    assert result.provider == "github_actions"


def test_github_actions_uses_custom_skeleton_command(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    write_ci_job(tmp_path, skeleton_command="npm run test:skeleton")
    body = (tmp_path / ".github" / "workflows" / "walking-skeleton.yml").read_text()
    assert "npm run test:skeleton" in body


# ----------------------------------------------------------------- gitlab


def test_gitlab_appends_job(tmp_path: Path) -> None:
    gitlab = tmp_path / ".gitlab-ci.yml"
    gitlab.write_text("stages:\n  - test\n", encoding="utf-8")
    result = write_ci_job(tmp_path)
    body = gitlab.read_text(encoding="utf-8")
    assert "walking-skeleton:" in body
    assert "stage: test" in body
    assert "make walking-skeleton" in body
    parsed = yaml.safe_load(body)
    assert "walking-skeleton" in parsed
    job = parsed["walking-skeleton"]
    assert job["stage"] == "test"
    # `rules` ensures push + MR trigger; both clauses present
    rules = job["rules"]
    sources = [r.get("if", "") for r in rules]
    assert any("push" in s for s in sources)
    assert any("merge_request_event" in s for s in sources)
    assert result.provider == "gitlab"
    assert gitlab in result.files_modified


def test_gitlab_idempotent(tmp_path: Path) -> None:
    gitlab = tmp_path / ".gitlab-ci.yml"
    gitlab.write_text("stages:\n  - test\n", encoding="utf-8")
    write_ci_job(tmp_path)
    body_before = gitlab.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_after = gitlab.read_text(encoding="utf-8")
    assert body_before == body_after
    assert result2.files_modified == ()
    assert result2.files_created == ()
    # Job appears exactly once
    assert body_after.count("\nwalking-skeleton:\n") == 1 or body_after.startswith(
        "walking-skeleton:\n"
    )


# ----------------------------------------------------------------- circleci


def test_circleci_inserts_job_and_workflow(tmp_path: Path) -> None:
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    circle.write_text(
        "version: 2.1\njobs:\n  hello:\n    docker:\n      - image: cimg/base:stable\n    steps:\n      - checkout\n",
        encoding="utf-8",
    )
    result = write_ci_job(tmp_path)
    body = circle.read_text(encoding="utf-8")
    assert "walking-skeleton:" in body
    assert "walking-skeleton-on-push:" in body
    parsed = yaml.safe_load(body)
    assert "walking-skeleton" in parsed["jobs"]
    assert (
        parsed["jobs"]["walking-skeleton"]["docker"][0]["image"] == "cimg/base:stable"
    )
    assert "walking-skeleton-on-push" in parsed["workflows"]
    assert parsed["workflows"]["walking-skeleton-on-push"]["jobs"] == [
        "walking-skeleton"
    ]
    assert result.provider == "circleci"
    assert circle in result.files_modified


def test_circleci_prepends_version_when_missing(tmp_path: Path) -> None:
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    circle.write_text(
        "jobs:\n  hello:\n    docker:\n      - image: cimg/base:stable\n    steps:\n      - checkout\n",
        encoding="utf-8",
    )
    write_ci_job(tmp_path)
    body = circle.read_text(encoding="utf-8")
    assert body.startswith("version: 2.1")


def test_circleci_keeps_existing_version(tmp_path: Path) -> None:
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    circle.write_text(
        "version: 2.1\njobs:\n  hello:\n    docker:\n      - image: cimg/base:stable\n    steps:\n      - checkout\n",
        encoding="utf-8",
    )
    write_ci_job(tmp_path)
    body = circle.read_text(encoding="utf-8")
    # Only one version line
    assert body.count("\nversion:") + (1 if body.startswith("version:") else 0) == 1


def test_circleci_idempotent(tmp_path: Path) -> None:
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    circle.write_text(
        "version: 2.1\njobs:\n  hello:\n    docker:\n      - image: cimg/base:stable\n    steps:\n      - checkout\n",
        encoding="utf-8",
    )
    write_ci_job(tmp_path)
    body_before = circle.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_after = circle.read_text(encoding="utf-8")
    assert body_before == body_after
    assert result2.files_modified == ()
    assert result2.files_created == ()


def test_circleci_idempotent_with_blank_lines_in_jobs(tmp_path: Path) -> None:
    """Re-run idempotency must hold even when the existing config has a
    blank line between `jobs:` and the first job (review I-3)."""
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    circle.write_text(
        "version: 2.1\njobs:\n\n  hello:\n    docker:\n      - image: cimg/base:stable\n    steps:\n      - checkout\n",
        encoding="utf-8",
    )
    write_ci_job(tmp_path)
    body_first = circle.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_second = circle.read_text(encoding="utf-8")
    assert body_first == body_second
    assert result2.files_modified == ()
    # Job appears exactly once
    assert body_second.count("walking-skeleton:\n") == 1


def test_circleci_idempotent_with_crlf_line_endings(tmp_path: Path) -> None:
    """Re-run idempotency holds even with CRLF line endings (review M-1/M-2)."""
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    # Write with CRLF.
    crlf_body = "version: 2.1\r\njobs:\r\n  hello:\r\n    docker:\r\n      - image: cimg/base:stable\r\n    steps:\r\n      - checkout\r\n"
    circle.write_bytes(crlf_body.encode("utf-8"))
    write_ci_job(tmp_path)
    body_first = circle.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_second = circle.read_text(encoding="utf-8")
    assert body_first == body_second
    assert result2.files_modified == ()


def test_gitlab_idempotent_with_crlf(tmp_path: Path) -> None:
    gitlab = tmp_path / ".gitlab-ci.yml"
    gitlab.write_bytes(b"stages:\r\n  - test\r\n")
    write_ci_job(tmp_path)
    body_first = gitlab.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_second = gitlab.read_text(encoding="utf-8")
    assert body_first == body_second
    assert result2.files_modified == ()


def test_circleci_creates_jobs_block_when_missing(tmp_path: Path) -> None:
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    circle.write_text("version: 2.1\n", encoding="utf-8")
    write_ci_job(tmp_path)
    body = circle.read_text(encoding="utf-8")
    parsed = yaml.safe_load(body)
    assert "walking-skeleton" in parsed["jobs"]
    assert "walking-skeleton-on-push" in parsed["workflows"]


# ----------------------------------------------------------------- generic


def test_generic_creates_makefile_and_runbook(tmp_path: Path) -> None:
    result = write_ci_job(tmp_path)
    makefile = tmp_path / "Makefile"
    runbook = tmp_path / "RUNBOOK.md"
    assert makefile.exists()
    assert runbook.exists()
    mk_body = makefile.read_text(encoding="utf-8")
    assert ".PHONY: walking-skeleton" in mk_body
    assert "walking-skeleton:" in mk_body
    # Recipe line MUST start with a tab (Make syntax)
    lines = mk_body.splitlines()
    recipe_idx = lines.index("walking-skeleton:") + 1
    assert lines[recipe_idx].startswith("\t")
    assert lines[recipe_idx].lstrip("\t") == "make walking-skeleton"
    rb_body = runbook.read_text(encoding="utf-8")
    assert "## Walking skeleton CI" in rb_body
    assert "make walking-skeleton" in rb_body
    assert result.provider == "generic"
    assert makefile in result.files_created
    assert runbook in result.files_created


def test_generic_appends_to_existing_makefile(tmp_path: Path) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text(".PHONY: build\nbuild:\n\techo build\n", encoding="utf-8")
    result = write_ci_job(tmp_path)
    body = makefile.read_text(encoding="utf-8")
    assert "build:" in body  # original target preserved
    assert "walking-skeleton:" in body
    assert makefile in result.files_modified
    assert makefile not in result.files_created


def test_generic_idempotent_makefile(tmp_path: Path) -> None:
    write_ci_job(tmp_path)
    makefile = tmp_path / "Makefile"
    body_before = makefile.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_after = makefile.read_text(encoding="utf-8")
    assert body_before == body_after
    assert makefile not in result2.files_modified
    assert makefile not in result2.files_created


def test_generic_appends_runbook_section(tmp_path: Path) -> None:
    runbook = tmp_path / "RUNBOOK.md"
    runbook.write_text("# Existing runbook\n\nSomething else.\n", encoding="utf-8")
    write_ci_job(tmp_path)
    body = runbook.read_text(encoding="utf-8")
    assert "# Existing runbook" in body
    assert "## Walking skeleton CI" in body


def test_generic_idempotent_runbook(tmp_path: Path) -> None:
    write_ci_job(tmp_path)
    runbook = tmp_path / "RUNBOOK.md"
    body_before = runbook.read_text(encoding="utf-8")
    result2 = write_ci_job(tmp_path)
    body_after = runbook.read_text(encoding="utf-8")
    assert body_before == body_after
    assert runbook not in result2.files_modified


# ----------------------------------------------------------------- error paths


def test_skeleton_command_with_newline_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="newline"):
        write_ci_job(tmp_path, skeleton_command="line1\nline2")


def test_repo_root_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_ci_job(tmp_path / "does-not-exist")


def test_ci_write_result_is_frozen(tmp_path: Path) -> None:
    result = write_ci_job(tmp_path)
    with pytest.raises(Exception):
        result.provider = "other"  # type: ignore[misc]


# ----------------------------------------------------------------- TC-WS-5-01 reference


def test_tc_ws_5_01_github_actions_runs_on_push(tmp_path: Path) -> None:
    """TC-WS-5-01: skeleton test job triggered on push."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    write_ci_job(tmp_path)
    body = (tmp_path / ".github" / "workflows" / "walking-skeleton.yml").read_text()
    parsed = yaml.safe_load(body)
    on_value = parsed.get("on", parsed.get(True))
    triggers = on_value if isinstance(on_value, list) else [on_value]
    assert "push" in triggers


def test_tc_ws_5_01_gitlab_runs_on_push(tmp_path: Path) -> None:
    gitlab = tmp_path / ".gitlab-ci.yml"
    gitlab.write_text("stages: [test]\n", encoding="utf-8")
    write_ci_job(tmp_path)
    parsed = yaml.safe_load(gitlab.read_text(encoding="utf-8"))
    rules = parsed["walking-skeleton"]["rules"]
    assert any("push" in r.get("if", "") for r in rules)


def test_tc_ws_5_01_circleci_runs_on_push(tmp_path: Path) -> None:
    """CircleCI workflow runs on every commit by default; the workflow MUST
    reference the walking-skeleton job."""
    circle = tmp_path / ".circleci" / "config.yml"
    circle.parent.mkdir()
    circle.write_text("version: 2.1\n", encoding="utf-8")
    write_ci_job(tmp_path)
    parsed = yaml.safe_load(circle.read_text(encoding="utf-8"))
    assert "walking-skeleton" in parsed["jobs"]
    assert parsed["workflows"]["walking-skeleton-on-push"]["jobs"] == [
        "walking-skeleton"
    ]
