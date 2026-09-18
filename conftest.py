"""Pytest bootstrap: resolve imports the way run.py does.

Third-party packages (tcex, falcon, spectree, pydantic, requests, ...) live in
``deps/`` (populated by ``tcex deps``), not site-packages — mirror
``run.py:setup()`` and put it on sys.path before test collection. ``deps/``
may be absent on a fresh checkout; the pure-logic tests still run, and the
endpoint tests skip themselves via ``pytest.importorskip``.
"""

# standard library
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_DEPS = _REPO_ROOT / 'deps'

# repo root first so `api.*`, `more.*`, `cal_client` import from source
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if _DEPS.is_dir() and str(_DEPS) not in sys.path:
    sys.path.insert(0, str(_DEPS))
