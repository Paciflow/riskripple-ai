"""Shared path configuration.

`Path(__file__).resolve().parents[N]`-style repo-relative paths only work when this
package is imported from its source checkout (backend/src/riskripple/...). In the
deployed Lambda container, pip installs this package flat into /var/task, so that
kind of relative climb resolves to nonsense (confirmed by actually running a handler
inside the built image -- see docs/KNOWN_LIMITATIONS.md). Both FIXTURES_DIR and
REPORTS_DIR must be resolved through environment variables with a local-dev fallback
instead, exactly once, here.
"""
from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT_FALLBACK = Path(__file__).resolve().parents[3]  # backend/src/riskripple/ -> repo root

FIXTURES_DIR = Path(os.environ.get("RISKRIPPLE_FIXTURES_DIR", _REPO_ROOT_FALLBACK / "data" / "fixtures"))
REPORTS_DIR = Path(os.environ.get("RISKRIPPLE_REPORTS_DIR", _REPO_ROOT_FALLBACK / "data" / "analysis" / "reports"))
