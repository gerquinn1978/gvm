"""Boundary discovery scanner for `/gvm-walking-skeleton` Phase 2.

Spec ref: walking-skeleton ADR-402.

The scanner walks a project root for source files of a given language and
matches each line against scan tokens loaded from `boundary-discovery.md`.
Matches surface as `BoundaryCandidate` records that the calling skill (later
chunks P11-C02..C05) confirms via `AskUserQuestion`. False positives are
practitioner-rejected at confirmation time.

The scanner is a discovery aid, not a CI gate: it silently skips unreadable
files and binary content rather than aborting (McConnell — defensive
programming at the file boundary).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Map of `boundary-discovery.md` category labels to `BoundaryCandidate.type`
# enum values per walking-skeleton ADR-403.
_CATEGORY_LABELS_TO_TYPE: dict[str, str] = {
    "HTTP outbound": "http_api",
    "Database": "database",
    "Cloud SDK": "cloud_sdk",
    "Filesystem": "filesystem",
    "Subprocess": "subprocess",
    "Email": "email",
    "SMS": "sms",
    "Queue": "queue",
}

# Per-language file extensions to walk.
_LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "typescript": (".ts", ".tsx", ".js", ".jsx"),
    "go": (".go",),
}

# Capture H2 headings (language sections) and bullet category lines.
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^-\s+([^:]+):\s*(.+)$")
_BACKTICK_RE = re.compile(r"`([^`]+)`")


@dataclass(frozen=True)
class BoundaryCandidate:
    """A draft boundary detected by source-scan; pre-confirmation.

    Field meanings:
    - `name`: the matching scan token (e.g. ``"requests."``).
    - `type`: the `boundaries.md` type enum, derived from the heuristic file
      category label (e.g. ``"http_api"``).
    - `file`: source file path, relative to the project root passed to
      :func:`scan`.
    - `line`: 1-based line number where the token was matched.
    """

    name: str
    type: str
    file: Path
    line: int


def _category_to_type(category: str) -> str:
    try:
        return _CATEGORY_LABELS_TO_TYPE[category]
    except KeyError as exc:
        raise KeyError(
            f"unknown boundary-discovery category: {category!r}; "
            f"known categories: {sorted(_CATEGORY_LABELS_TO_TYPE)}"
        ) from exc


def load_heuristics(path: Path, language: str) -> list[tuple[str, str]]:
    """Parse ``boundary-discovery.md`` and return ``[(type, token), ...]``.

    Raises:
        FileNotFoundError: when ``path`` does not exist.
        KeyError: when ``language`` (case-insensitive) is not present in the
            file or has no recognised category bullets.
    """

    if not path.exists():
        raise FileNotFoundError(f"boundary-discovery.md not found: {path}")

    text = path.read_text(encoding="utf-8")
    lang_norm = language.strip().lower()

    headings = list(_H2_RE.finditer(text))
    target_section: str | None = None
    for i, h in enumerate(headings):
        if h.group(1).strip().lower() == lang_norm:
            start = h.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            target_section = text[start:end]
            break

    if target_section is None:
        raise KeyError(
            f"language {language!r} not found in {path}; "
            f"known languages: {[h.group(1).strip() for h in headings]}"
        )

    pairs: list[tuple[str, str]] = []
    for line in target_section.splitlines():
        m = _BULLET_RE.match(line)
        if not m:
            continue
        category = m.group(1).strip()
        try:
            type_value = _category_to_type(category)
        except KeyError:
            # Unknown categories are tolerated — they may be human prose
            # bullets that happen to look like categories. Skip rather than
            # fail (the heuristic file is human-edited).
            continue
        for token_match in _BACKTICK_RE.finditer(m.group(2)):
            pairs.append((type_value, token_match.group(1)))

    if not pairs:
        raise KeyError(
            f"language {language!r} present in {path} but has no recognised "
            f"category bullets"
        )

    return pairs


def _iter_source_files(project_root: Path, extensions: tuple[str, ...]):
    """Yield source files under ``project_root`` matching any of ``extensions``.

    Skips ``.git``, ``__pycache__``, ``node_modules``, ``.venv`` directories
    on the way down — these are virtually never project sources and would
    blow up scan time on real projects.
    """

    skip_dirs = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".tox",
        "dist",
        "build",
    }
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix in extensions:
            yield path


def scan(
    project_root: Path,
    language: str = "python",
    heuristics_path: Path | None = None,
) -> list[BoundaryCandidate]:
    """Walk ``project_root`` and return all boundary candidates for ``language``.

    Args:
        project_root: directory to walk recursively.
        language: lowercase language name (``"python"``, ``"typescript"``,
            ``"go"``). Must match an H2 in the heuristics file.
        heuristics_path: path to ``boundary-discovery.md``. Defaults to the
            shared design-system reference.

    Raises:
        FileNotFoundError: when ``project_root`` does not exist.
        NotADirectoryError: when ``project_root`` is not a directory.
        KeyError: when ``language`` is not present in the heuristics file.
    """

    if not project_root.exists():
        raise FileNotFoundError(f"project_root not found: {project_root}")
    if not project_root.is_dir():
        raise NotADirectoryError(f"project_root must be a directory: {project_root}")

    if heuristics_path is None:
        heuristics_path = (
            Path(__file__).resolve().parents[2]
            / "gvm-design-system"
            / "references"
            / "boundary-discovery.md"
        )

    pairs = load_heuristics(heuristics_path, language)
    extensions = _LANGUAGE_EXTENSIONS.get(language.strip().lower(), ())
    if not extensions:
        # Heuristics exist for this language but no file extensions are
        # registered — still return [] rather than raise; callers can extend
        # _LANGUAGE_EXTENSIONS for new languages.
        return []

    # Pre-compile token matchers — escape so tokens like `open(` are matched
    # literally, not as regex.
    compiled = [
        (type_value, token, re.compile(re.escape(token))) for type_value, token in pairs
    ]

    candidates: list[BoundaryCandidate] = []
    for src in _iter_source_files(project_root, extensions):
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Unreadable file — skip silently per the discovery-aid contract.
            continue
        rel = src.relative_to(project_root)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for type_value, token, matcher in compiled:
                if matcher.search(line):
                    candidates.append(
                        BoundaryCandidate(
                            name=token,
                            type=type_value,
                            file=rel,
                            line=line_no,
                        )
                    )

    candidates.sort(key=lambda c: (str(c.file), c.line, c.name))
    return candidates
