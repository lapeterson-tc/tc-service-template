"""On-disk JSON replacement for the tcex v2 DataStore facade.

The TC v2 DataStore (``tcex.api.tc.v2.datastore(...)``) is Elasticsearch
under a per-instance ``organization`` domain index. This module provides a
drop-in, call-signature-compatible stand-in (``DiskStore``) backed by plain
JSON files under ``{tc_out_path}/app-data/``, for environments where the
platform DataStore isn't available or isn't desired.

Layout: ``{root}/{org_key}/{data_type}/{encoded_rid}.json``. ``org_key`` is
derived from the calling user's ThreatConnect organization
(``resolve_org_key``) and is the ONLY access-control boundary — there is no
per-record ACL, so every record lives under its org's directory and nothing
must ever read/write across an ``org_key`` boundary. Resolution therefore
fails CLOSED: any ambiguity or lookup failure returns ``None`` rather than
falling back to a shared or default namespace, and failures are never
cached (a transient outage must not poison a user's namespace for the
cache TTL).

Each record is stored as a small envelope (``{"rid", "updatedAt", "data"}``)
rather than the bare record, so the original rid and a last-write timestamp
survive even though the filename is a lossy/percent-encoded (or hashed)
transform of it.

This app runs as a single long-lived process per container, and writes are
atomic (write-to-temp-file + ``os.replace``), so no additional CRUD locking
is needed: readers only ever see a fully-written file or the previous one,
never a partial write.
"""

# standard library
import hashlib
import json
import os
import string
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# first-party
from api.storage import tc_user
from api.debug_log import debug_print

_SAFE_CHARS = set(string.ascii_letters + string.digits + '_-')
_MAX_ENCODED_LEN = 200

# Cache of resolved org keys: username -> (org_key, expires_at [monotonic]).
_ORG_KEY_CACHE: dict[str, tuple[str, float]] = {}
_ORG_KEY_LOCK = threading.Lock()
ORG_KEY_TTL = 600.0

# Indirection so tests can monkeypatch the time source.
_now = time.monotonic


def _iso_now() -> str:
    """Return the current UTC time as an ISO-8601 string with millisecond precision."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def encode_rid(rid: str) -> str:
    """Percent-encode ``rid`` into a filesystem-safe name.

    Hand-rolled rather than ``urllib.parse.quote`` because that helper's
    default "always safe" set includes ``.``, which must be encoded here to
    make ``.``/``..``/dotfiles/``/`` structurally impossible in the output.
    Every byte outside ``[A-Za-z0-9_-]`` becomes an uppercase ``%XX``. If the
    result would exceed ``_MAX_ENCODED_LEN`` characters (long rids, e.g. very
    long emails, chunk ids), fall back to a non-reversible sha256 hash name
    prefixed ``_h`` — the record's envelope still carries the real rid.
    """
    raw = rid.encode('utf-8')
    parts = []
    for byte in raw:
        ch = chr(byte)
        if byte < 128 and ch in _SAFE_CHARS:
            parts.append(ch)
        else:
            parts.append(f'%{byte:02X}')
    encoded = ''.join(parts)
    if len(encoded) > _MAX_ENCODED_LEN:
        return '_h' + hashlib.sha256(raw).hexdigest()
    return encoded


def decode_rid(name: str) -> str:
    """Reverse :func:`encode_rid` for a percent-encoded name.

    Not load-bearing at runtime (the envelope carries the original rid) —
    provided for tests/inspection. Hash-fallback names (``_h...``) are not
    reversible and are not meaningfully decodable by this function.
    """
    out = bytearray()
    i = 0
    n = len(name)
    while i < n:
        ch = name[i]
        if ch == '%' and i + 3 <= n:
            try:
                out.append(int(name[i + 1 : i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out.extend(ch.encode('utf-8'))
        i += 1
    return bytes(out).decode('utf-8')


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write ``payload`` as JSON to ``path`` atomically (temp file + rename)."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix='.tmp-')
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(payload, separators=(',', ':')))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


class DiskStore:
    """Disk-backed stand-in for a single tcex v2 DataStore ``(domain, data_type)``.

    Call-signature-compatible with the subset of the tcex DataStore API this
    app uses (``get``/``post``/``put``/``delete``), plus ``list_all`` for the
    ES-scroll-style listing call sites previously did against the real
    DataStore. ``raise_on_error`` mirrors tcex semantics: ``True`` raises
    ``RuntimeError`` on failure, ``False`` returns ``None``.
    """

    def __init__(self, root: Path, org_key: str, data_type: str, log):
        self.root = root
        self.org_key = org_key
        self.data_type = data_type
        self.log = log
        self.dir = root / org_key / data_type
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, rid: str) -> Path:
        return self.dir / f'{encode_rid(rid)}.json'

    def _warn(self, msg: str) -> None:
        debug_print(msg)
        self.log.warning(msg)

    def get(self, rid=None, data=None, raise_on_error=True):  # noqa: ARG002 - signature parity
        """Look up a record by rid. ``rid=None`` (the ES query form) is unsupported."""
        if rid is None:
            raise RuntimeError(
                '[APP-DEBUG] DiskStore.get: query-based get() (rid=None) is not supported'
            )
        path = self._path(rid)
        try:
            if not path.exists():
                return {'found': False}
            text = path.read_text(encoding='utf-8')
        except OSError as ex:
            msg = (
                f'[APP-DEBUG] DiskStore.get OS error: rid={rid!r} '
                f'data_type={self.data_type} error={ex}'
            )
            self._warn(msg)
            if raise_on_error:
                raise RuntimeError(msg) from ex
            return None
        try:
            envelope = json.loads(text)
            if not isinstance(envelope, dict) or 'data' not in envelope:
                raise ValueError('envelope missing "data" key')
        except (ValueError, TypeError) as ex:
            self._warn(
                f'[APP-DEBUG] DiskStore.get corrupt envelope: rid={rid!r} '
                f'data_type={self.data_type} error={ex}'
            )
            return {'found': False}
        return {'found': True, '_id': rid, '_source': envelope['data']}

    def _upsert(self, rid, data, raise_on_error):
        path = self._path(rid)
        envelope = {'rid': rid, 'updatedAt': _iso_now(), 'data': data}
        try:
            _atomic_write_json(path, envelope)
        except Exception as ex:
            msg = (
                f'[APP-DEBUG] DiskStore write failed: rid={rid!r} '
                f'data_type={self.data_type} error={ex}'
            )
            self._warn(msg)
            if raise_on_error:
                raise RuntimeError(msg) from ex
            return None
        return {'_id': rid}

    def post(self, rid, data, raise_on_error=True):
        """Upsert ``data`` under ``rid`` (tcex ``post`` is also an upsert here)."""
        return self._upsert(rid, data, raise_on_error)

    def put(self, rid, data, raise_on_error=True):
        """Upsert ``data`` under ``rid``."""
        return self._upsert(rid, data, raise_on_error)

    def delete(self, rid, raise_on_error=True):
        """Delete the record for ``rid``. Missing rid is treated as success (idempotent)."""
        path = self._path(rid)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as ex:
            msg = (
                f'[APP-DEBUG] DiskStore.delete failed: rid={rid!r} '
                f'data_type={self.data_type} error={ex}'
            )
            self._warn(msg)
            if raise_on_error:
                raise RuntimeError(msg) from ex
            return None
        return {'_id': rid}

    def list_all(self, limit: int = 500) -> list:
        """Return up to ``limit`` records in this store, filename-sorted.

        Corrupt/unreadable files are skipped (with a logged warning) rather
        than failing the whole listing; ``.``-prefixed names (including
        ``.tmp-*`` leftovers from an interrupted write) are always skipped.
        """
        try:
            if not self.dir.is_dir():
                return []
            names = sorted(p.name for p in self.dir.iterdir())
        except OSError as ex:
            self._warn(
                f'[APP-DEBUG] DiskStore.list_all failed to list dir: '
                f'data_type={self.data_type} error={ex}'
            )
            return []

        out = []
        for name in names:
            if len(out) >= limit:
                break
            if name.startswith('.'):
                continue
            path = self.dir / name
            try:
                envelope = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(envelope, dict) or 'data' not in envelope or 'rid' not in envelope:
                    raise ValueError('bad envelope')
            except Exception as ex:
                self._warn(
                    f'[APP-DEBUG] DiskStore.list_all skipping unreadable file: '
                    f'path={path} error={ex}'
                )
                continue
            out.append({'_id': envelope['rid'], '_source': envelope['data']})
        return out


def _ensure_org_marker(root: Path, org_key: str, org: dict, log) -> None:
    """Best-effort write of a human-readable ``org.json`` marker. Never raises."""
    try:
        org_dir = root / org_key
        org_dir.mkdir(parents=True, exist_ok=True)
        marker = org_dir / 'org.json'
        if marker.exists():
            return
        payload = {'id': org.get('id'), 'name': org.get('name', ''), 'firstSeenAt': _iso_now()}
        _atomic_write_json(marker, payload)
    except Exception as ex:
        msg = f'[APP-DEBUG] resolve_org_key: org.json marker write failed: org_key={org_key} error={ex}'
        debug_print(msg)
        if log:
            log.warning(msg)


def resolve_org_key(tcex, log, root: Path | None = None) -> str | None:
    """Resolve the calling user's ``org-{id}`` namespace key, or None.

    Fails CLOSED: an unknown username or a failed org lookup returns None
    rather than falling back to a shared/default namespace (the org
    namespace is the only access-control boundary this store has). Failures
    are NEVER cached — only a successful resolution is cached, for
    ``ORG_KEY_TTL`` seconds, keyed by username. When ``root`` is given, a
    successful resolution also best-effort ensures a human-readable
    ``{root}/{org_key}/org.json`` marker file exists.
    """
    username = tc_user.get_username(tcex)
    if username == 'unknown':
        msg = '[APP-DEBUG] resolve_org_key: unknown username, cannot resolve org (not cached)'
        debug_print(msg)
        log.warning(msg)
        return None

    now = _now()
    with _ORG_KEY_LOCK:
        cached = _ORG_KEY_CACHE.get(username)
        if cached is not None and cached[1] > now:
            return cached[0]

    org = tc_user.get_user_org(tcex, log)
    if org is None:
        msg = (
            f'[APP-DEBUG] resolve_org_key: org lookup failed for user={username!r} '
            '(not cached, failing closed)'
        )
        debug_print(msg)
        log.warning(msg)
        return None

    org_key = f"org-{org['id']}"
    with _ORG_KEY_LOCK:
        _ORG_KEY_CACHE[username] = (org_key, now + ORG_KEY_TTL)

    if root is not None:
        _ensure_org_marker(root, org_key, org, log)

    return org_key
