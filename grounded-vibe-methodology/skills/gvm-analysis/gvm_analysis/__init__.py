"""gvm_analysis — the /gvm-analysis GVM skill.

This package exists so `import gvm_analysis` succeeds, satisfying the TC-INFRA-01
smoke assertion and giving downstream tooling a canonical import target. Per
cross-cutting ADR-007, actual analysis code lives under ``scripts/_shared/``;
this package is an intentional thin marker, not a re-export layer.
"""

from __future__ import annotations

__version__ = "0.1.0"
