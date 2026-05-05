"""Contract/collaboration lint — shared helper for gvm-test-cases and gvm-code-review.

Detects two violation classes in test code:

1. **Rainsberger** (J.B. Rainsberger, *Integrated Tests Are A Scam*):
   An HTTP transport library is patched at the consumer level, masquerading
   as a unit test. Such tests do not verify the collaboration protocol; they
   couple the consumer to an implementation detail of the transport.

2. **Metz** (Sandi Metz, POODR Ch. 9):
   A ``[CONTRACT]`` test patches an internal class rather than a true role
   boundary. Contract tests must instantiate real production classes from the
   DI root downward; mocking internal classes hides protocol drift
   (Freeman & Pryce, *GOOS*).

Per-stack detection rules (ADR-503):
  Python    — AST-based.  Patches against ``requests``, ``httpx``, ``urllib``,
              ``aiohttp`` → Rainsberger.  ``[CONTRACT]`` docstring/comment +
              internal-class patch → Metz.
  TypeScript — Text-based regex.  ``(jest|vi).(mock|spyOn)`` against
               ``axios``, ``got``, or ``globalThis.fetch`` → Rainsberger.
  Go        — Line-by-line regex.  External URL literal in a file that imports
               ``net/http`` → Rainsberger; excludes ``localhost``/``127.0.0.1``
               and lines containing ``httptest.New``.

Source-root detection (ADR-504):
  Python    — Walk up from test file looking for ``pyproject.toml`` /
              ``setup.py``; if ``src/`` exists at that level return ``src/``.
  TypeScript — Read ``rootDir`` from nearest ``tsconfig.json``; fall back to
               directory containing ``package.json``.
  Go        — Directory containing ``go.mod``.

``.ebt-boundaries`` (ADR-504):
  One glob pattern per line (``fnmatch.fnmatchcase``-compatible).  ``#``
  introduces comments.  Empty file or ``None`` → use stack defaults only.
  Stack defaults (Python): ``requests.*``, ``httpx.*``, ``psycopg2.*``,
  ``sqlalchemy.engine.*``, ``boto3.*``.

API (ADR-503):
  ``lint(test_file_path, ebt_boundaries_path, source_root, *, stack) → list[LintViolation]``
  ``detect_source_root(test_file_path, stack) → Path | None``

Design note (Brooks): one ``lint()`` entry-point, two callers
(``/gvm-test-cases`` Phase 4 and ``/gvm-code-review`` Panel B).  Do not fork
the logic per caller.
"""

from __future__ import annotations

import ast
import fnmatch
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

KindT = Literal["rainsberger", "metz", "mock-budget"]
SeverityT = Literal["important", "critical"]


@dataclass(frozen=True)
class LintViolation:
    test_id: str  # nearest test-function name or logical test ID
    file_line: str  # "path:line" where the violation lives
    kind: KindT
    detail: str  # one-line human-readable description
    severity: SeverityT = "important"  # v2.1.0: mock-budget escalates to critical on seam hits


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# HTTP transport packages whose request-sending methods trigger Rainsberger.
_HTTP_TRANSPORT_PACKAGES: frozenset[str] = frozenset(
    {"requests", "httpx", "urllib", "aiohttp"}
)

# Suffixes that constitute a "request-method-shaped" name when patching HTTP.
# e.g. requests.get, requests.post, httpx.AsyncClient.send, urllib.request.urlopen
_HTTP_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "request",
        "send",
        "fetch",
        "urlopen",
        "urlretrieve",
    }
)

# Stack defaults for .ebt-boundaries (Python).
#
# These are the eight named external-boundary categories from
# /gvm-build SKILL.md § TDD-2 (items 1–8) plus three commonly-used
# third-party SDKs. When this list changes, the matching change MUST
# be made in /gvm-build SKILL.md § TDD-2 — the SKILL.md text is the
# human-readable specification authority and this tuple is the runtime
# mirror. Pattern matching is glob-style (`fnmatch`) so `pathlib.Path.*`
# covers the real-I/O methods the spec calls out (`read_text`,
# `write_text`, `mkdir`, `iterdir`, ...) without enumerating each one —
# pure path arithmetic (`/`, `parent`, `name`) is a method-style
# attribute, but tests rarely patch those, so the precision/recall
# trade-off favours the broader pattern.
_PYTHON_STACK_DEFAULTS: tuple[str, ...] = (
    # The eight named external-boundary categories (see /gvm-build
    # SKILL.md § TDD-2, items 1–8)
    "requests.*",
    "httpx.*",
    "urllib.*",
    "aiohttp.*",
    "socket.*",
    "pathlib.Path.*",
    "subprocess.*",
    "os.*",
    # Three third-party SDKs commonly used as external-boundary
    # categories. The TDD-2 rule allows any third-party SDK published
    # outside the project's codebase; these are the high-frequency
    # ones we mirror.
    "psycopg2.*",
    "sqlalchemy.engine.*",
    "boto3.*",
)

# TS stack defaults — external-boundary allowlist for mock-budget (ADR-TG-01).
# When this list changes, update the matching ADR in
# specs/methodology-hardening-ts-go-mockbudget.md.
_TS_STACK_DEFAULTS: tuple[str, ...] = (
    # node:-prefixed builtins (modern Node.js import scheme)
    "node:fs.*",
    "node:path.*",
    "node:child_process.*",
    "node:os.*",
    "node:net.*",
    "node:http.*",
    "node:https.*",
    "node:dns.*",
    "node:crypto.*",
    "node:stream.*",
    # Bare-form builtins (CJS / pre-Node-16 imports)
    "fs/*.*",
    "fs.*",
    "path.*",
    "child_process.*",
    "os.*",
    "net.*",
    "http.*",
    "https.*",
    # HTTP client libraries
    "axios.*",
    "node-fetch.*",
    "undici.*",
    "got.*",
    "ky.*",
    # Database drivers
    "pg.*",
    "mysql2.*",
    "mongodb.*",
    "mongoose.*",
    "redis.*",
    "ioredis.*",
    "sqlite3.*",
    # Cloud / SaaS SDKs
    "aws-sdk.*",
    "@aws-sdk/*.*",
    "googleapis.*",
    "stripe.*",
    "@anthropic-ai/sdk.*",
    "openai.*",
)

# TS mock-target detection regexes (ADR-TG-03 — text-line heuristic).
# Each regex captures the mocked target as group(1).
_TS_MOCK_TARGET_PATTERNS: tuple[re.Pattern[str], ...] = (
    # vi.mock("target"), jest.mock("target")
    re.compile(r"""(?:vi|jest)\s*\.\s*mock\s*\(\s*['"]([^'"]+)['"]"""),
    # jest.spyOn(obj, "method") — capture obj symbol
    re.compile(r"""jest\s*\.\s*spyOn\s*\(\s*([A-Za-z_$][\w$]*)"""),
    # vi.spyOn(obj, "method")
    re.compile(r"""vi\s*\.\s*spyOn\s*\(\s*([A-Za-z_$][\w$]*)"""),
    # td.replace("target") / td.replace(obj, ...)
    re.compile(r"""td\s*\.\s*replace\s*\(\s*['"]?([A-Za-z_@./$][\w@./$-]*)['"]?"""),
    # sinon.stub(obj, "method") / sinon.replace(obj, "method", ...)
    re.compile(r"""sinon\s*\.\s*(?:stub|replace)\s*\(\s*([A-Za-z_$][\w$]*)"""),
)

# TypeScript/JS HTTP transport mocks regex
_TS_RAINSBERGER_RE = re.compile(
    r"""(jest|vi)\s*\.\s*(mock|spyOn)\s*\(\s*['"]"""
    r"""(axios|got|node-fetch)['"]\s*""",
    re.MULTILINE,
)
_TS_FETCH_PATCH_RE = re.compile(
    r"""(jest|vi)\s*\.\s*(mock|spyOn)\s*\(\s*['"]"""
    r"""(globalThis\.fetch|global\.fetch|fetch)['"]\s*""",
    re.MULTILINE,
)

# Go external URL regex
_GO_URL_RE = re.compile(r"""https?://[^\s'"]+""")
_GO_LOCALHOST_RE = re.compile(r"""https?://(localhost|127\.0\.0\.1)(:\d+)?""")

# Go stack defaults — external-boundary allowlist for mock-budget (ADR-TG-02).
# Idiomatic Go uses interface substitution; the boundary is the external
# package whose interface is being substituted. Matching is performed on the
# double's TYPE NAME (e.g. `httpClientMock`) — the prefix of the type name
# (case-insensitive) is checked against these patterns. The patterns also
# match raw import paths for completeness.
_GO_STACK_DEFAULTS: tuple[str, ...] = (
    # Standard library boundary categories
    "net/http.*",
    "net/url.*",
    "os.*",
    "os/exec.*",
    "io.*",
    "io/fs.*",
    "database/sql.*",
    "database/sql/driver.*",
    "context.*",
    # Common third-party SDKs
    "github.com/aws/aws-sdk-go-v2/*",
    "cloud.google.com/go/*",
    "github.com/anthropic/*",
    "github.com/openai/*",
    "github.com/redis/go-redis/*",
    "github.com/lib/pq.*",
    "go.mongodb.org/*",
)

# Test-double naming-convention regex (ADR-TG-02). Captures struct types whose
# names end with Mock|Fake|Stub|Spy. Word boundary on both sides so
# `realFakeBuilder` is NOT captured (the suffix is `Builder`, not a sentinel).
_GO_DOUBLE_NAME_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*?(Mock|Fake|Stub|Spy))\b")
_GO_GOMOCK_CONTROLLER_RE = re.compile(r"\bgomock\s*\.\s*NewController\s*\(")
_GO_TESTIFY_MOCK_RE = re.compile(r"\bmock\s*\.\s*Mock\b")
_GO_TEST_FUNC_RE = re.compile(
    r"^func\s+(Test\w+)\s*\(\s*\w+\s+\*testing\.T\s*\)\s*\{", re.MULTILINE
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lint(
    test_file_path: Path | str,
    ebt_boundaries_path: Path | str | None,
    source_root: Path | str | None,
    *,
    stack: Literal["python", "typescript", "go"] = "python",
    seam_allowlist_path: Path | str | None = None,
) -> list[LintViolation]:
    """Return all lint violations found in ``test_file_path``.

    Parameters
    ----------
    test_file_path:
        Path to the test file to analyse.
    ebt_boundaries_path:
        Path to the project's ``.ebt-boundaries`` file, or ``None`` to use
        stack defaults only.
    source_root:
        The project source root as detected by :func:`detect_source_root`, or
        ``None`` if detection failed.  When ``None``, all imports not matched
        by the allowlist are treated as internal (fail-closed, per ADR-503).
    stack:
        One of ``"python"``, ``"typescript"``, ``"go"``.
    seam_allowlist_path:
        Path to the project's ``.cross-chunk-seams`` file, or ``None`` (the
        default — opt-in, per ADR-MH-03).  When supplied, mock-budget
        violations whose target matches a seam pattern escalate to
        severity ``"critical"``.

        **Per-stack qualifier (v2.2.0).** Severity escalation is wired
        in all three stacks (Python, TypeScript, Go).  Targets matching
        the seam allowlist escalate Important → Critical via the same
        helper (``_matches_allowlist`` for Python/TS,
        ``_go_target_on_allowlist`` for Go) per ADR-MH-03.
    """
    path = Path(test_file_path)
    src_root = Path(source_root) if source_root is not None else None
    allowlist = _load_allowlist(ebt_boundaries_path, stack=stack)
    seam_allowlist = _load_seam_allowlist(seam_allowlist_path)

    if stack == "python":
        return _lint_python(path, allowlist, src_root, seam_allowlist)
    elif stack == "typescript":
        return _lint_typescript(path, allowlist, src_root, seam_allowlist)
    elif stack == "go":
        return _lint_go(path, allowlist, src_root, seam_allowlist)
    else:
        # Reaching here means the caller supplied a stack outside the typed
        # Literal — a programming error, not a runtime condition. Return-empty
        # would be a silent failure: callers couldn't tell "clean file" from
        # "detection skipped" (Martin: no silent failures).
        raise ValueError(
            f"Unknown stack {stack!r} — must be 'python', 'typescript', or 'go'"
        )


def detect_source_root(test_file_path: Path | str, stack: str) -> Path | None:
    """Detect the project source root for the given stack.

    Parameters
    ----------
    test_file_path:
        Path to the test file being analysed.
    stack:
        One of ``"python"``, ``"typescript"``, ``"go"``.

    Returns
    -------
    Path | None
        The detected source root, or ``None`` if detection fails.
    """
    path = Path(test_file_path).resolve()
    if stack == "python":
        return _detect_python_source_root(path)
    elif stack in ("typescript", "javascript"):
        return _detect_ts_source_root(path)
    elif stack == "go":
        return _detect_go_source_root(path)
    log.warning("detect_source_root: unknown stack %r", stack)
    return None


# ---------------------------------------------------------------------------
# Allowlist loading
# ---------------------------------------------------------------------------


def _load_allowlist(
    ebt_boundaries_path: Path | str | None,
    *,
    stack: str,
) -> list[str]:
    """Return the project allowlist patterns merged with stack defaults.

    Python defaults are merged here. TypeScript and Go defaults are NOT
    merged here — they are prepended inside their per-stack detector
    (`_detect_mock_budget_ts`, `_detect_mock_budget_go`) via
    ``full_allowlist = list(_<STACK>_STACK_DEFAULTS) + list(allowlist)``.
    A new-stack implementer should follow that pattern, not add to this
    function's `defaults` branch.
    """
    defaults: list[str] = []
    if stack == "python":
        defaults = list(_PYTHON_STACK_DEFAULTS)

    if ebt_boundaries_path is None:
        return defaults

    try:
        file_patterns = _parse_boundaries_file(Path(ebt_boundaries_path))
    except OSError as exc:
        log.warning(
            "Cannot read .ebt-boundaries %s: %s — using stack defaults only",
            ebt_boundaries_path,
            exc,
        )
        return defaults
    # Stack defaults first so project can override or extend
    return defaults + file_patterns


def _parse_boundaries_file(path: Path) -> list[str]:
    """Parse an ``.ebt-boundaries`` file and return non-comment patterns.

    Reads with ``errors="replace"`` so a non-UTF-8 byte in a project's
    boundary or seam file (rare but observed on Windows-authored files
    sharing a repo with Linux CI) does NOT raise ``UnicodeDecodeError``
    and silently kill the entire lint run. Pattern matching is
    ASCII-substring-based downstream, so replaced bytes only affect lines
    that already contain non-ASCII data — those lines simply fail to
    match a real pattern, which is the correct degraded behaviour.
    """
    if not path.exists():
        return []
    patterns: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)
    return patterns


def _load_seam_allowlist(path: Path | str | None) -> list[str]:
    """Load the project's ``.cross-chunk-seams`` patterns (ADR-MH-03).

    Opt-in.  Absent file or ``None`` path → empty list (no escalation).
    Unreadable file (OSError on read) → log warning, return empty list —
    matches the convention `_lint_python` / `_lint_typescript` use for
    unreadable test files (Martin: no silent failures, but degrade
    gracefully on transient IO errors rather than crashing the lint
    invocation that surfaced the seam).
    Same comment / blank-line semantics as ``.ebt-boundaries``.
    """
    if path is None:
        return []
    p = Path(path)
    if not p.exists():
        return []
    try:
        return _parse_boundaries_file(p)
    except OSError as exc:
        log.warning("Cannot read seam allowlist %s: %s", p, exc)
        return []


def _matches_allowlist(symbol_path: str, allowlist: list[str]) -> bool:
    """Return True if ``symbol_path`` matches any pattern in ``allowlist``."""
    for pattern in allowlist:
        if fnmatch.fnmatchcase(symbol_path, pattern):
            return True
        # Also allow prefix matches: if pattern is "requests.*" and symbol
        # is "requests.get", fnmatchcase handles it.  But also handle the
        # case where the symbol starts with a package that the pattern covers.
    return False


# ---------------------------------------------------------------------------
# Source-root detection
# ---------------------------------------------------------------------------


def _detect_python_source_root(test_file: Path) -> Path | None:
    """Walk up from test_file to find pyproject.toml or setup.py."""
    candidate = test_file.parent
    while True:
        if (candidate / "pyproject.toml").exists() or (candidate / "setup.py").exists():
            # src-layout detection
            src_dir = candidate / "src"
            if src_dir.is_dir():
                return src_dir
            return candidate
        parent = candidate.parent
        if parent == candidate:
            # Reached filesystem root without finding a project marker
            return None
        candidate = parent


def _detect_ts_source_root(test_file: Path) -> Path | None:
    """Walk up from test_file to find tsconfig.json or package.json."""
    candidate = test_file.parent
    while True:
        tsconfig = candidate / "tsconfig.json"
        if tsconfig.exists():
            try:
                data = json.loads(tsconfig.read_text())
                root_dir = data.get("compilerOptions", {}).get("rootDir")
                if root_dir:
                    resolved = (candidate / root_dir).resolve()
                    return resolved
            except (json.JSONDecodeError, KeyError):
                pass
            return candidate

        pkg = candidate / "package.json"
        if pkg.exists():
            return candidate

        parent = candidate.parent
        if parent == candidate:
            return None
        candidate = parent


def _detect_go_source_root(test_file: Path) -> Path | None:
    """Walk up from test_file to find go.mod."""
    candidate = test_file.parent
    while True:
        if (candidate / "go.mod").exists():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            return None
        candidate = parent


# ---------------------------------------------------------------------------
# Python lint
# ---------------------------------------------------------------------------


class _PatchCollector(ast.NodeVisitor):
    """Collect patch() calls and their enclosing function names + line numbers."""

    def __init__(self, file_path: Path, src_lines: list[str]) -> None:
        self._file_path = file_path
        self._src_lines = src_lines
        # list of (test_function_name, patch_target_string, lineno, is_contract)
        self.patches: list[tuple[str, str, int, bool]] = []
        self._current_func: str = "<module>"
        self._current_is_contract: bool = False
        self._func_stack: list[tuple[str, bool]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._enter_func(node)
        self.generic_visit(node)
        self._exit_func()

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815  (same logic)

    def _enter_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        is_contract = _function_has_contract_tag(node, self._src_lines)
        self._func_stack.append((self._current_func, self._current_is_contract))
        self._current_func = node.name
        self._current_is_contract = is_contract

    def _exit_func(self) -> None:
        self._current_func, self._current_is_contract = self._func_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        target = _extract_patch_target(node)
        if target is not None:
            self.patches.append(
                (self._current_func, target, node.lineno, self._current_is_contract)
            )
        self.generic_visit(node)


def _function_has_contract_tag(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    src_lines: list[str],
) -> bool:
    """Return True if the function has [CONTRACT] in docstring or preceding comments.

    Checks both:
    - The function's docstring (first statement if it is a string literal).
    - The block of ``#``-comment lines immediately preceding the ``def`` line.
    """
    # Check docstring
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
        and "[CONTRACT]" in node.body[0].value.value
    ):
        return True

    # Check preceding comment block (lines immediately above the def, 1-indexed)
    def_line_idx = node.lineno - 1  # convert to 0-indexed
    for idx in range(def_line_idx - 1, -1, -1):
        stripped = src_lines[idx].strip()
        if stripped.startswith("#"):
            if "[CONTRACT]" in stripped:
                return True
        elif stripped:
            # Non-empty, non-comment line — stop scanning
            break
    return False


def _extract_patch_target(node: ast.Call) -> str | None:
    """Return the first string argument to patch() / patch.object(), or None."""
    # Match: patch("X.Y"), mock.patch("X.Y"), unittest.mock.patch("X.Y")
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "patch":
        pass  # patch.object etc — fall through to arg extraction
    elif isinstance(func, ast.Name) and func.id == "patch":
        pass
    else:
        return None

    # First positional argument should be the target string
    if node.args and isinstance(node.args[0], ast.Constant):
        val = node.args[0].value
        if isinstance(val, str):
            return val
    return None


def _is_http_transport_patch(target: str) -> bool:
    """Return True if the patch target is a request-method on an HTTP transport."""
    parts = target.split(".")
    if not parts:
        return False
    top = parts[0]
    if top not in _HTTP_TRANSPORT_PACKAGES:
        return False
    # The last segment must look like a request-method name
    last = parts[-1]
    # Also allow patching sub-classes like AsyncClient directly (len >= 2)
    if last in _HTTP_METHOD_NAMES:
        return True
    # Allow patching things like httpx.Client, httpx.AsyncClient (the class itself)
    # which are transport-level objects regardless of method suffix
    if top == "httpx" and len(parts) >= 2:
        return True
    if top == "urllib" and len(parts) >= 2:
        return True
    # For aiohttp, patching ClientSession or request-level calls
    if top == "aiohttp" and len(parts) >= 2:
        return True
    return False


def _is_internal_path(
    target: str,
    source_root: Path | None,
    allowlist: list[str],
) -> bool:
    """Return True if target is an internal module path (Metz).

    Logic:
    - If matched by allowlist → False (allowed boundary mock, not internal).
    - If source_root is None → True (fail-closed per ADR-503).
    - If top-level package is a known stdlib/third-party → False.
    - Otherwise → True.
    """
    if _matches_allowlist(target, allowlist):
        return False
    if source_root is None:
        # Fail-closed: treat as internal
        return True
    # Heuristic per ADR-503: anything not on the allowlist is internal.
    # The allowlist is the practitioner's declaration of permitted seams;
    # stdlib / third-party packages that should be mockable are listed there.
    return True


def _is_wrapper_as_sut(
    test_file: Path,
    target: str,
    src: str,
) -> bool:
    """Return True if the test is for a wrapper class and ``target`` is its external dep.

    ADR-MH-02 heuristic: if class ``X`` is imported from a sibling module under
    the same package and the test filename matches ``test_x.py`` /
    ``test_X.py``, then ``X`` is treated as the SUT. Mocks of ``target`` are
    permitted only when ``target``'s top-level package is genuinely
    external — i.e. it is NOT a top-level segment of any of the test file's
    own ``from X.Y import Z`` paths. Sharing a top-level segment with a
    project import means the target is sibling-internal, not the wrapper's
    external dep — flagging is correct in that case.

    Ambiguous cases (no matching import, or target shares a project root
    with the SUT's import path) fall through to ``False`` — the lint
    defaults to flagging, and the practitioner adds ``# noqa: mock-budget``
    with rationale (ADR-MH-02 consequence).
    """
    stem = test_file.stem
    if not stem.startswith("test_"):
        return False
    sut_name = stem[len("test_"):]
    if not sut_name:
        return False

    # Convert snake_case to candidate class names (PascalCase).
    candidates = {sut_name, sut_name.replace("_", ""), _snake_to_pascal(sut_name)}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    imported: set[str] = set()
    from_import_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
            if node.module:
                from_import_roots.add(node.module.split(".", 1)[0])
    if not (candidates & imported):
        return False

    # Reject if the target's top segment collides with any from-import
    # root: the target is then a sibling-internal module (e.g. SUT
    # imported from `myapp.billing`, target patched at `myapp.internal.X`)
    # — flagging is the correct behaviour, not exemption.
    top = target.split(".", 1)[0]
    if not top or top.startswith("_"):
        return False
    return top not in from_import_roots


def _snake_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part)


def _detect_mock_budget(
    path: Path,
    patches: list[tuple[str, str, int, bool]],
    src: str,
    allowlist: list[str],
    seam_allowlist: list[str],
) -> list[LintViolation]:
    """Detect mock-budget violations per ADR-MH-02 / ADR-MH-03.

    A mock target is over-budget when:
      1. It is NOT on the external-boundary allowlist (i.e. internal), AND
      2. It is NOT exempt under the wrapper-as-SUT heuristic.

    Severity escalates from Important to Critical when the target matches
    a pattern in the project's ``.cross-chunk-seams`` allowlist.
    """
    violations: list[LintViolation] = []
    for func_name, target, lineno, is_contract in patches:
        # External boundary — allowed mock, not over-budget.
        if _matches_allowlist(target, allowlist):
            continue
        # HTTP transport already flagged Rainsberger upstream; skip here so
        # the same patch does not produce two violations.
        if _is_http_transport_patch(target):
            continue
        # [CONTRACT] tests with internal patches are Metz's domain; skip
        # here so the same patch does not produce both metz AND mock-budget
        # with conflicting remediation guidance ("use real classes" vs
        # "mock at boundaries"). Mock-budget owns NON-contract internal mocks.
        if is_contract:
            continue
        # Wrapper-as-SUT exemption (ADR-MH-02).
        if _is_wrapper_as_sut(path, target, src):
            continue

        severity: SeverityT = (
            "critical" if _matches_allowlist(target, seam_allowlist) else "important"
        )
        violations.append(
            LintViolation(
                test_id=func_name,
                file_line=f"{path}:{lineno}",
                kind="mock-budget",
                detail=(
                    f"Internal mock over budget: {target!r} — "
                    "mock at boundaries (Metz POODR Ch. 9), not at internal collaborators"
                    + (
                        " — target hits cross-chunk seam allowlist (escalated)"
                        if severity == "critical"
                        else ""
                    )
                ),
                severity=severity,
            )
        )
    return violations


def _lint_python(
    path: Path,
    allowlist: list[str],
    source_root: Path | None,
    seam_allowlist: list[str] | None = None,
) -> list[LintViolation]:
    """Run Python AST-based lint on ``path``."""
    try:
        src = path.read_text()
    except OSError as exc:
        log.warning("Cannot read %s: %s", path, exc)
        return []

    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as exc:
        log.warning("Syntax error in %s: %s", path, exc)
        return []

    src_lines = src.splitlines()
    collector = _PatchCollector(path, src_lines)
    collector.visit(tree)

    violations: list[LintViolation] = []
    for func_name, target, lineno, is_contract in collector.patches:
        file_line = f"{path}:{lineno}"

        # Rainsberger check: HTTP transport patch anywhere (not just CONTRACT tests)
        if _is_http_transport_patch(target):
            violations.append(
                LintViolation(
                    test_id=func_name,
                    file_line=file_line,
                    kind="rainsberger",
                    detail=(
                        f"HTTP transport patched in consumer test: {target!r} — "
                        "use a contract test instead (Rainsberger)"
                    ),
                )
            )
            # Don't also emit Metz for the same patch — HTTP transport is
            # on the allowlist by default, so it would never be Metz anyway.
            continue

        # Metz check: internal class patched inside a [CONTRACT] test
        if is_contract and _is_internal_path(target, source_root, allowlist):
            violations.append(
                LintViolation(
                    test_id=func_name,
                    file_line=file_line,
                    kind="metz",
                    detail=(
                        f"Internal class mocked in [CONTRACT] test: {target!r} — "
                        "instantiate real production classes from DI root (Metz)"
                    ),
                )
            )

    # Mock-budget pass — runs on every patch, not just [CONTRACT] tests.
    violations.extend(
        _detect_mock_budget(
            path,
            collector.patches,
            src,
            allowlist,
            seam_allowlist or [],
        )
    )

    return violations


# ---------------------------------------------------------------------------
# TypeScript lint (text-based, no full TS parser)
# ---------------------------------------------------------------------------


def _lint_typescript(
    path: Path,
    allowlist: list[str],
    source_root: Path | None,
    seam_allowlist: list[str] | None = None,
) -> list[LintViolation]:
    """Text-based TypeScript/JavaScript lint.

    Emits ``rainsberger`` for HTTP-transport mocks and ``mock-budget`` for
    internal mocks (via ``_detect_mock_budget_ts``). Severity escalation via
    ``seam_allowlist`` mirrors ``_lint_python`` per ADR-MH-03: targets matching
    the cross-chunk seam allowlist escalate Important → Critical.
    """
    try:
        src = path.read_text()
    except OSError as exc:
        log.warning("Cannot read %s: %s", path, exc)
        return []

    violations: list[LintViolation] = []
    for i, line in enumerate(src.splitlines(), start=1):
        file_line = f"{path}:{i}"
        if _TS_RAINSBERGER_RE.search(line) or _TS_FETCH_PATCH_RE.search(line):
            violations.append(
                LintViolation(
                    test_id=_ts_nearest_test_name(src, i),
                    file_line=file_line,
                    kind="rainsberger",
                    detail=(
                        "HTTP transport mocked in consumer test (TS) — "
                        "use a contract test instead (Rainsberger)"
                    ),
                )
            )

    violations.extend(
        _detect_mock_budget_ts(path, src, allowlist, seam_allowlist or [])
    )
    return violations


def _detect_mock_budget_ts(
    path: Path,
    src: str,
    allowlist: list[str],
    seam_allowlist: list[str],
) -> list[LintViolation]:
    """Detect TS mock-budget violations per ADR-MH-02 / ADR-TG-01 / ADR-TG-03.

    Iterates lines, captures each mocked target via the TS pattern set,
    classifies internal vs external against ``_TS_STACK_DEFAULTS + allowlist``.
    Internal targets emit ``mock-budget`` Important; targets matching
    ``seam_allowlist`` escalate to Critical.

    Wrapper-as-SUT exemption: when the test file's basename (stripping
    ``.test.ts`` / ``.spec.ts`` / ``.test.tsx``) appears in the mocked-target
    string, the file is treated as a wrapper around that module and the
    mock counts as a boundary, not an internal collaborator.
    """
    full_allowlist = list(_TS_STACK_DEFAULTS) + list(allowlist)
    sut_stem = _ts_sut_stem(path)
    seen_targets: set[tuple[int, str]] = set()
    violations: list[LintViolation] = []
    for i, line in enumerate(src.splitlines(), start=1):
        for pattern in _TS_MOCK_TARGET_PATTERNS:
            for match in pattern.finditer(line):
                target = match.group(1)
                key = (i, target)
                if key in seen_targets:
                    continue
                seen_targets.add(key)

                if _ts_target_on_allowlist(target, full_allowlist):
                    # Note: this check subsumes rainsberger-overlap dedup
                    # because every transport in `_TS_RAINSBERGER_RE` /
                    # `_TS_FETCH_PATCH_RE` (axios, got, node-fetch, fetch)
                    # is also in `_TS_STACK_DEFAULTS`. A target that
                    # would emit `rainsberger` is therefore filtered here.
                    continue
                # Wrapper-as-SUT (ADR-MH-02 parity): exempt only when the
                # test file's stem equals the mocked target's basename. A
                # substring check is too loose ("user" in "../userservice").
                if sut_stem and _ts_target_basename(target) == sut_stem:
                    continue

                severity: SeverityT = (
                    "critical"
                    if _matches_allowlist(target, seam_allowlist)
                    else "important"
                )
                violations.append(
                    LintViolation(
                        test_id=_ts_nearest_test_name(src, i),
                        file_line=f"{path}:{i}",
                        kind="mock-budget",
                        detail=(
                            f"Internal mock over budget (TS): {target!r} — "
                            "mock at boundaries (Metz POODR Ch. 9), not at "
                            "internal collaborators"
                            + (
                                " — target hits cross-chunk seam allowlist (escalated)"
                                if severity == "critical"
                                else ""
                            )
                        ),
                        severity=severity,
                    )
                )
    return violations


def _ts_target_on_allowlist(target: str, allowlist: list[str]) -> bool:
    """Match TS mock targets against the allowlist.

    fnmatch's `axios.*` requires a literal dot; bare module strings like
    `vi.mock("axios")` would otherwise not match. We accept the pattern,
    AND its `pattern.removesuffix(".*")` form, so both `axios` and
    `axios.get` flow through to the allowlist.
    """
    if _matches_allowlist(target, allowlist):
        return True
    bare_forms = [p[:-2] for p in allowlist if p.endswith(".*")]
    return any(fnmatch.fnmatchcase(target, p) for p in bare_forms)


def _ts_target_basename(target: str) -> str:
    """Return the lowercase basename of a TS mock target.

    `../UserService` → `userservice`.  `@anthropic-ai/sdk` → `sdk`.
    `axios` → `axios`.  Used by the wrapper-as-SUT exemption.
    """
    last = target.replace("\\", "/").rstrip("/").split("/")[-1]
    return last.lower()


def _ts_sut_stem(path: Path) -> str:
    """Return the lowercase wrapper stem inferred from a TS test filename.

    `axiosWrapper.test.ts` → `axioswrapper`. Used by the wrapper-as-SUT
    exemption — when the stem equals the mocked target's basename the
    mock is treated as a boundary, not an internal collaborator.
    """
    name = path.name.lower()
    for suffix in (".test.tsx", ".test.ts", ".spec.tsx", ".spec.ts", ".test.jsx", ".test.js"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return ""


def _ts_nearest_test_name(src: str, lineno: int) -> str:
    """Best-effort: find the enclosing it/test/describe label above lineno."""
    lines = src.splitlines()
    it_re = re.compile(r"""(?:it|test)\s*\(\s*['"`]([^'"`]+)['"`]""")
    for idx in range(min(lineno - 1, len(lines) - 1), -1, -1):
        m = it_re.search(lines[idx])
        if m:
            return m.group(1)
    return "<unknown>"


# ---------------------------------------------------------------------------
# Go lint (line-by-line, text-based)
# ---------------------------------------------------------------------------


def _lint_go(
    path: Path,
    allowlist: list[str],
    source_root: Path | None,
    seam_allowlist: list[str] | None = None,
) -> list[LintViolation]:
    """Line-by-line Go lint.

    Emits ``rainsberger`` for external HTTP URL literals (when the test
    imports ``net/http``) and ``mock-budget`` for test-double instances over
    budget (per ADR-TG-02). ``seam_allowlist`` matches the Python path:
    targets in the cross-chunk seam allowlist escalate Important → Critical.
    """
    try:
        src = path.read_text()
    except OSError as exc:
        log.warning("Cannot read %s: %s", path, exc)
        return []

    violations: list[LintViolation] = []

    # Rainsberger pass — only meaningful when net/http is imported.
    if re.search(r'"net/http"', src):
        for i, line in enumerate(src.splitlines(), start=1):
            if "httptest.New" in line:
                continue
            for m in _GO_URL_RE.finditer(line):
                url = m.group(0)
                if _GO_LOCALHOST_RE.match(url):
                    continue
                file_line = f"{path}:{i}"
                violations.append(
                    LintViolation(
                        test_id=_go_nearest_func_name(src, i),
                        file_line=file_line,
                        kind="rainsberger",
                        detail=(
                            f"External URL literal {url!r} in Go test with net/http import — "
                            "use a contract/httptest approach (Rainsberger)"
                        ),
                    )
                )

    violations.extend(
        _detect_mock_budget_go(path, src, allowlist, seam_allowlist or [])
    )
    return violations


def _detect_mock_budget_go(
    path: Path,
    src: str,
    allowlist: list[str],
    seam_allowlist: list[str],
) -> list[LintViolation]:
    """Detect Go mock-budget violations per ADR-TG-02.

    Per Test function body, count distinct test-double instances:
      - Type names matching ``*Mock|*Fake|*Stub|*Spy`` (struct literals
        like ``&userRepoFake{}`` or ``UserRepoMock{...}``).
      - ``gomock.NewController(t)`` invocations.
      - Struct definitions embedding ``mock.Mock`` (testify) — surfaced via
        the type name when an instance is created.
    Each unique double is classified internal vs external against
    ``_GO_STACK_DEFAULTS + allowlist`` (matched on the type name prefix,
    case-insensitive). Internal doubles emit ``mock-budget`` Important;
    targets matching ``seam_allowlist`` escalate to Critical.

    Wrapper-as-SUT (ADR-MH-02) is not implemented for Go: the language has
    no test-file naming convention that signals "this file IS the wrapper
    around module X" (Go test files are always `<pkg>_test.go`). A Go
    project that legitimately mocks a boundary not on the allowlist
    extends `.ebt-boundaries` to include the wrapper's mock type name.

    Limitation (ADR-TG-03): brace-depth counting does not parse strings
    or comments. Adversarial inputs (a `}` inside a string literal) could
    misalign function bodies. Real-world Go test code does not exhibit
    this pattern; documented as a known accepted limitation.
    """
    full_allowlist = list(_GO_STACK_DEFAULTS) + list(allowlist)
    testify_types = _collect_testify_types(src)
    violations: list[LintViolation] = []
    for func_name, body, body_lineno in _go_iter_test_bodies(src):
        seen: set[str] = set()
        gomock_controller_count = 0
        for i_offset, line in enumerate(body.splitlines()):
            lineno = body_lineno + i_offset

            # gomock.NewController — each invocation counts as one double.
            # Each match generates a unique target via the counter, so no
            # `seen` guard is needed — the counter itself enforces uniqueness.
            for _ in _GO_GOMOCK_CONTROLLER_RE.finditer(line):
                gomock_controller_count += 1
                target = f"gomock.NewController#{gomock_controller_count}"
                seen.add(target)
                # gomock controllers are by definition "internal" — they
                # mock arbitrary interfaces. Severity escalates only via
                # an explicit seam_allowlist match on `gomock.NewController`.
                severity: SeverityT = (
                    "critical"
                    if _go_target_on_allowlist(
                        "gomock.NewController", seam_allowlist
                    )
                    else "important"
                )
                violations.append(
                    LintViolation(
                        test_id=func_name,
                        file_line=f"{path}:{lineno}",
                        kind="mock-budget",
                        detail=(
                            "gomock controller in test — each NewController "
                            "counts as a mocked collaborator (Metz POODR "
                            "Ch. 9). Substitute the real interface or move "
                            "the boundary into .ebt-boundaries"
                            + (
                                " — target hits cross-chunk seam allowlist (escalated)"
                                if severity == "critical"
                                else ""
                            )
                        ),
                        severity=severity,
                    )
                )

            for m in _GO_DOUBLE_NAME_RE.finditer(line):
                target = m.group(1)
                if target in seen:
                    continue
                # Skip type definitions (`type FooMock struct`) — only count
                # instances. The simplest signal: skip lines starting with
                # `type ` after stripping whitespace.
                if line.lstrip().startswith("type "):
                    continue
                seen.add(target)
                if _go_target_on_allowlist(target, full_allowlist):
                    continue
                severity = (
                    "critical"
                    if _go_target_on_allowlist(target, seam_allowlist)
                    else "important"
                )
                violations.append(
                    LintViolation(
                        test_id=func_name,
                        file_line=f"{path}:{lineno}",
                        kind="mock-budget",
                        detail=(
                            f"Internal mock over budget (Go): {target!r} — "
                            "mock at boundaries (Metz POODR Ch. 9), not at "
                            "internal collaborators"
                            + (
                                " — target hits cross-chunk seam allowlist (escalated)"
                                if severity == "critical"
                                else ""
                            )
                        ),
                        severity=severity,
                    )
                )

            # Testify embed — count instances of types that embed mock.Mock,
            # even when the type name carries no Mock|Fake|Stub|Spy suffix.
            for type_name in testify_types:
                if type_name in seen:
                    continue
                # Look for a literal instance creation: `&TypeName{` or
                # `TypeName{` anywhere in the body line.
                inst_re = re.compile(rf"&?{re.escape(type_name)}\s*\{{")
                if inst_re.search(line) and not line.lstrip().startswith("type "):
                    seen.add(type_name)
                    if _go_target_on_allowlist(type_name, full_allowlist):
                        continue
                    severity = (
                        "critical"
                        if _go_target_on_allowlist(type_name, seam_allowlist)
                        else "important"
                    )
                    violations.append(
                        LintViolation(
                            test_id=func_name,
                            file_line=f"{path}:{lineno}",
                            kind="mock-budget",
                            detail=(
                                f"Internal mock over budget (Go): {type_name!r} "
                                "(testify mock.Mock embed) — mock at boundaries "
                                "(Metz POODR Ch. 9), not at internal collaborators"
                                + (
                                    " — target hits cross-chunk seam allowlist (escalated)"
                                    if severity == "critical"
                                    else ""
                                )
                            ),
                            severity=severity,
                        )
                    )
    return violations


def _collect_testify_types(src: str) -> set[str]:
    """Return the set of struct type names whose definition embeds mock.Mock.

    Recognises:

        type FooSvc struct {
            mock.Mock
            ...
        }

    Detection is brace-balanced over the type's body to handle multi-line
    struct definitions. The returned set lets ``_detect_mock_budget_go``
    count testify-backed types as doubles even when the type name lacks
    the Mock|Fake|Stub|Spy suffix (ADR-TG-02 decision: testify is detected
    by library API, not naming convention).
    """
    types: set[str] = set()
    type_re = re.compile(r"\btype\s+(\w+)\s+struct\s*\{")
    for m in type_re.finditer(src):
        type_name = m.group(1)
        open_brace = m.end() - 1
        depth = 0
        end = open_brace
        for i in range(open_brace, len(src)):
            ch = src[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = src[open_brace + 1 : end]
        if _GO_TESTIFY_MOCK_RE.search(body):
            types.add(type_name)
    return types


def _go_target_on_allowlist(target: str, allowlist: list[str]) -> bool:
    """Match a Go test-double type name (case-insensitive) against allowlist.

    Allowlist patterns are package-style globs (`net/http.*`,
    `httpClient*`). The target is the struct type name (e.g.
    `httpClientMock`). We match the lowercased target against each pattern
    AND its bare prefix (pattern with `.*` or `/*` stripped).
    """
    target_lc = target.lower()
    for pattern in allowlist:
        p_lc = pattern.lower()
        if fnmatch.fnmatchcase(target_lc, p_lc):
            return True
        # Bare prefix forms — strip trailing `.*` or `/*`.
        for suffix in (".*", "/*"):
            if p_lc.endswith(suffix):
                bare = p_lc[: -len(suffix)]
                if fnmatch.fnmatchcase(target_lc, bare + "*"):
                    return True
    return False


def _go_iter_test_bodies(src: str):
    """Yield ``(func_name, body_text, body_start_lineno)`` for each TestXxx.

    Uses brace-depth counting from the opening `{` of the function. Subtests
    (`t.Run`) flow through to the outer body — ADR-TG-02 design.
    """
    for m in _GO_TEST_FUNC_RE.finditer(src):
        func_name = m.group(1)
        open_brace = src.find("{", m.start())
        if open_brace == -1:
            continue
        depth = 0
        end = open_brace
        for i in range(open_brace, len(src)):
            ch = src[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        body = src[open_brace + 1 : end]
        body_lineno = src.count("\n", 0, open_brace + 1) + 1
        yield func_name, body, body_lineno


def _go_nearest_func_name(src: str, lineno: int) -> str:
    """Best-effort: find the nearest Go test function name above lineno."""
    func_re = re.compile(r"^func\s+(Test\w+)\s*\(")
    lines = src.splitlines()
    for idx in range(min(lineno - 1, len(lines) - 1), -1, -1):
        m = func_re.match(lines[idx])
        if m:
            return m.group(1)
    return "<unknown>"
