"""Walking-skeleton CI job writer (P11-C04 — ADR-406).

Detects the project's CI provider by filesystem markers and writes (or amends)
a stack-specific CI job that runs the walking-skeleton test on push. Falls
back to a Makefile + RUNBOOK pair when no CI provider is detected.

Pure module — no AskUserQuestion, no network, no shell. The "Add a CI job?"
prompt lives in SKILL.md; this module mechanically writes files when called.

YAML editing strategy is text-level (per spec): no `yaml` import in the
production module. Tests use `yaml.safe_load` to verify the produced YAML
is well-formed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ----------------------------------------------------------------- types


Provider = Literal["github_actions", "gitlab", "circleci", "generic"]


@dataclass(frozen=True)
class CIWriteResult:
    """Outcome of `write_ci_job`. `files_created` and `files_modified` are
    disjoint — a path appears in at most one. Both are empty when the call
    was a no-op (idempotent re-run)."""

    provider: Provider
    files_created: tuple[Path, ...] = field(default_factory=tuple)
    files_modified: tuple[Path, ...] = field(default_factory=tuple)


# ----------------------------------------------------------------- templates

_GITHUB_ACTIONS_TEMPLATE = """\
name: Walking Skeleton
"on": [push, pull_request]
jobs:
  walking-skeleton:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run skeleton
        run: {skeleton_command}
"""

_GITLAB_JOB_TEMPLATE = """\

walking-skeleton:
  stage: test
  script:
    - {skeleton_command}
  rules:
    - if: '$CI_PIPELINE_SOURCE == "push"'
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
"""

_CIRCLECI_JOB_TEMPLATE = """\
  walking-skeleton:
    docker:
      - image: cimg/base:stable
    steps:
      - checkout
      - run: {skeleton_command}
"""

_CIRCLECI_WORKFLOW_TEMPLATE = """\
  walking-skeleton-on-push:
    jobs:
      - walking-skeleton
"""

_MAKEFILE_TEMPLATE = """\
.PHONY: walking-skeleton
walking-skeleton:
\t{skeleton_command}
"""

_RUNBOOK_SECTION = """\

## Walking skeleton CI

Wire `make walking-skeleton` into your CI provider's pipeline as a job that
runs on every push.
"""


# ----------------------------------------------------------------- detection


def detect_provider(repo_root: Path) -> Provider:
    """Return the CI provider for `repo_root`. Markers are checked in order;
    first match wins. GitHub Actions wins when multiple markers are present."""
    if (repo_root / ".github" / "workflows").is_dir():
        return "github_actions"
    if (repo_root / ".gitlab-ci.yml").is_file():
        return "gitlab"
    if (repo_root / ".circleci" / "config.yml").is_file():
        return "circleci"
    return "generic"


# ----------------------------------------------------------------- public API


def write_ci_job(
    repo_root: Path,
    *,
    skeleton_command: str = "make walking-skeleton",
) -> CIWriteResult:
    """Write or amend the walking-skeleton CI job in `repo_root`.

    Detects provider via `detect_provider`, then dispatches to a per-provider
    writer. Each writer is idempotent: re-running on a repo where the job is
    already wired returns a `CIWriteResult` with empty `files_created` and
    `files_modified`.

    Raises:
        FileNotFoundError: `repo_root` does not exist OR (TOCTOU window —
            R24 M-2) `.gitlab-ci.yml` / `.circleci/config.yml` was deleted
            between provider detection and the writer's `read_text` call.
            The window is narrow and acceptable; documented for callers.
        ValueError: `skeleton_command` contains a newline (would corrupt
            YAML/Make output).
        FileExistsError: GitHub Actions path only — the workflow file
            `.github/workflows/walking-skeleton.yml` already exists with
            content the writer did not produce. Practitioner must resolve.
    """
    if not repo_root.exists():
        raise FileNotFoundError(repo_root)
    if "\n" in skeleton_command:
        raise ValueError(
            f"skeleton_command must not contain a newline; got {skeleton_command!r}"
        )

    provider = detect_provider(repo_root)
    if provider == "github_actions":
        return _write_github_actions(repo_root, skeleton_command)
    if provider == "gitlab":
        return _write_gitlab(repo_root, skeleton_command)
    if provider == "circleci":
        return _write_circleci(repo_root, skeleton_command)
    return _write_generic(repo_root, skeleton_command)


# ----------------------------------------------------------------- writers


def _atomic_write(path: Path, body: str) -> None:
    """Write `body` to `path` atomically: write to a process-unique sibling
    file, then `os.replace`. The PID-suffixed temp name avoids two concurrent
    callers clobbering each other's partial output (P11-C04 review I-1).

    Cleans up the .tmp file on any exception so a failed `os.replace` (disk
    full, permission, EXDEV cross-device) does not leave a permanent orphan
    next to the target (R24 CR-3)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.{os.getpid()}.tmp"
    try:
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        # Best-effort cleanup; swallow secondary errors so the original
        # exception propagates with its real cause.
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _write_github_actions(repo_root: Path, skeleton_command: str) -> CIWriteResult:
    workflow = repo_root / ".github" / "workflows" / "walking-skeleton.yml"
    body = _GITHUB_ACTIONS_TEMPLATE.format(skeleton_command=skeleton_command)
    if workflow.exists():
        # Idempotent re-run: byte-for-byte identical content is a no-op.
        # Only raise if the existing file diverges (practitioner edited it).
        existing = workflow.read_text(encoding="utf-8")
        if existing == body:
            return CIWriteResult(provider="github_actions")
        raise FileExistsError(
            f"{workflow} already exists with different content; refusing "
            f"to overwrite practitioner edits"
        )
    _atomic_write(workflow, body)
    return CIWriteResult(provider="github_actions", files_created=(workflow,))


def _write_gitlab(repo_root: Path, skeleton_command: str) -> CIWriteResult:
    gitlab = repo_root / ".gitlab-ci.yml"
    existing = gitlab.read_text(encoding="utf-8")
    if _has_top_level_key(existing, "walking-skeleton"):
        return CIWriteResult(provider="gitlab")
    job_block = _GITLAB_JOB_TEMPLATE.format(skeleton_command=skeleton_command)
    new_body = existing
    if not new_body.endswith("\n"):
        new_body += "\n"
    new_body += job_block
    _atomic_write(gitlab, new_body)
    return CIWriteResult(provider="gitlab", files_modified=(gitlab,))


def _write_circleci(repo_root: Path, skeleton_command: str) -> CIWriteResult:
    circle = repo_root / ".circleci" / "config.yml"
    existing = circle.read_text(encoding="utf-8")

    has_job = _has_indented_key_under(existing, "jobs:", "walking-skeleton:")
    has_workflow = _has_indented_key_under(
        existing, "workflows:", "walking-skeleton-on-push:"
    )
    if has_job and has_workflow:
        return CIWriteResult(provider="circleci")

    new_body = existing

    # 1) Ensure version: 2.1 is present.
    if not _has_top_level_key(new_body, "version"):
        new_body = "version: 2.1\n" + new_body

    # 2) Insert the job under jobs:.
    if not has_job:
        job_block = _CIRCLECI_JOB_TEMPLATE.format(skeleton_command=skeleton_command)
        new_body = _insert_after_top_level_key(new_body, "jobs:", job_block)

    # 3) Insert the workflow under workflows:.
    if not has_workflow:
        new_body = _insert_after_top_level_key(
            new_body, "workflows:", _CIRCLECI_WORKFLOW_TEMPLATE
        )

    _atomic_write(circle, new_body)
    return CIWriteResult(provider="circleci", files_modified=(circle,))


def _write_generic(repo_root: Path, skeleton_command: str) -> CIWriteResult:
    makefile = repo_root / "Makefile"
    runbook = repo_root / "RUNBOOK.md"

    created: list[Path] = []
    modified: list[Path] = []

    # Makefile
    if makefile.exists():
        mk_body = makefile.read_text(encoding="utf-8")
        if not _has_makefile_target(mk_body, "walking-skeleton"):
            new_mk = mk_body
            if not new_mk.endswith("\n"):
                new_mk += "\n"
            new_mk += "\n" + _MAKEFILE_TEMPLATE.format(
                skeleton_command=skeleton_command
            )
            _atomic_write(makefile, new_mk)
            modified.append(makefile)
    else:
        _atomic_write(
            makefile, _MAKEFILE_TEMPLATE.format(skeleton_command=skeleton_command)
        )
        created.append(makefile)

    # RUNBOOK.md
    if runbook.exists():
        rb_body = runbook.read_text(encoding="utf-8")
        if "## Walking skeleton CI" not in rb_body:
            new_rb = rb_body
            if not new_rb.endswith("\n"):
                new_rb += "\n"
            new_rb += _RUNBOOK_SECTION
            _atomic_write(runbook, new_rb)
            modified.append(runbook)
    else:
        _atomic_write(runbook, _RUNBOOK_SECTION.lstrip("\n"))
        created.append(runbook)

    return CIWriteResult(
        provider="generic",
        files_created=tuple(created),
        files_modified=tuple(modified),
    )


# ----------------------------------------------------------------- text helpers


def _has_top_level_key(text: str, key: str) -> bool:
    """True if `text` contains a line starting with `key:` at column 0.
    CRLF-tolerant (review M-2)."""
    prefix = key + ":"
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if (
            line == prefix
            or line.startswith(prefix + " ")
            or line.startswith(prefix + "\t")
        ):
            return True
    return False


def _has_indented_key_under(text: str, parent: str, child: str) -> bool:
    """True if `parent` (a top-level key like `jobs:`) appears as a line and
    a subsequent indented line starts with `child` (e.g. `walking-skeleton:`)
    before the next top-level key. Blank lines do not reset the parent
    context (review I-3). CRLF-tolerant."""
    in_parent = False
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if line == "":
            # Blank lines do not reset parent context.
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 0:
            in_parent = line == parent or line.startswith(parent + " ")
            continue
        if in_parent and (
            stripped == child
            or stripped.startswith(child + " ")
            or stripped.startswith(child + "\t")
        ):
            return True
    return False


def _insert_after_top_level_key(text: str, parent: str, block: str) -> str:
    """Insert `block` immediately after the first occurrence of a top-level
    line equal to `parent` (e.g. `jobs:`). If the parent line is missing,
    append `\\n{parent}\\n{block}` at end of file. CRLF-tolerant
    (review M-1)."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip("\r\n") == parent:
            return "".join(lines[: i + 1]) + block + "".join(lines[i + 1 :])
    # Parent missing — append at end.
    suffix = text
    if suffix and not suffix.endswith("\n"):
        suffix += "\n"
    return suffix + "\n" + parent + "\n" + block


def _has_makefile_target(text: str, target: str) -> bool:
    """True if `text` contains a Make target line `<target>:` at column 0.
    CRLF-tolerant (review M-2)."""
    needle = target + ":"
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if (
            line == needle
            or line.startswith(needle + " ")
            or line.startswith(needle + "\t")
        ):
            return True
    return False
