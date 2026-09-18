"""Unit tests for get_user_org (tc_user.py) and resolve_org_key (disk_store.py).

Pure stdlib + pytest — no tcex import (a SimpleNamespace fake stands in for
``tcex.session.tc``), so these always run.
"""

# standard library
import json
from types import SimpleNamespace

# third-party
import pytest

# first-party
from api.storage import disk_store as ds
from api.storage import tc_user


class _RecordingLog:
    def __init__(self):
        self.warnings = []
        self.infos = []

    def warning(self, msg):
        self.warnings.append(msg)

    def info(self, msg):
        self.infos.append(msg)


class _Resp:
    def __init__(self, ok=True, status_code=200, body=None, text=None):
        self.ok = ok
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = text if text is not None else json.dumps(self._body)

    def json(self):
        return self._body


def _fake_tcex(get_fn):
    return SimpleNamespace(session=SimpleNamespace(tc=SimpleNamespace(get=get_fn)))


@pytest.fixture(autouse=True)
def _clear_org_key_cache():
    ds._ORG_KEY_CACHE.clear()
    yield
    ds._ORG_KEY_CACHE.clear()


# ── get_user_org ──────────────────────────────────────────────────────────


def test_get_user_org_happy_path_picks_organization_row():
    body = {
        'data': {
            'owner': [
                {'id': 1, 'name': 'Some Source', 'type': 'Source'},
                {'id': 42, 'name': 'My Org', 'type': 'Organization'},
            ]
        }
    }

    def get(path):
        assert path == '/v2/owners/mine'
        return _Resp(body=body)

    org = tc_user.get_user_org(_fake_tcex(get), log=_RecordingLog())
    assert org == {'id': 42, 'name': 'My Org'}


def test_get_user_org_single_object_owner_shape():
    # CONFIRMED LIVE 2026-07-31: /v2/owners/mine returns data.owner as a
    # single object, not a list. The old list-only parser silently failed
    # here and disabled all graph storage.
    body = {
        'status': 'Success',
        'data': {'owner': {'id': 3, 'name': 'ThreatConnect', 'type': 'Organization'}},
    }
    org = tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(body=body)), log=_RecordingLog())
    assert org == {'id': 3, 'name': 'ThreatConnect'}


def test_get_user_org_no_match_warn_logs_body():
    body = {'data': {'owner': [{'id': 1, 'name': 'Some Source', 'type': 'Source'}]}}
    log = _RecordingLog()
    org = tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(body=body)), log=log)
    assert org is None
    assert any('no Organization row' in m and 'Some Source' in m for m in log.warnings)


def test_get_user_org_missing_organization_row_returns_none():
    body = {'data': {'owner': [{'id': 1, 'name': 'Some Source', 'type': 'Source'}]}}
    org = tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(body=body)))
    assert org is None


def test_get_user_org_non_ok_response_returns_none():
    org = tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(ok=False, status_code=500)))
    assert org is None


def test_get_user_org_exception_returns_none():
    def get(_path):
        raise RuntimeError('network down')

    org = tc_user.get_user_org(_fake_tcex(get), log=_RecordingLog())
    assert org is None


def test_get_user_org_coerces_id_to_int():
    body = {'data': {'owner': [{'id': '42', 'name': 'My Org', 'type': 'Organization'}]}}
    org = tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(body=body)))
    assert org == {'id': 42, 'name': 'My Org'}
    assert isinstance(org['id'], int)


def test_get_user_org_non_coercible_id_returns_none():
    body = {'data': {'owner': [{'id': 'nope', 'name': 'My Org', 'type': 'Organization'}]}}
    org = tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(body=body)))
    assert org is None


def test_get_user_org_raw_logs_once(monkeypatch):
    monkeypatch.setattr(tc_user, '_org_response_logged', False)
    body = {'data': {'owner': [{'id': 1, 'name': 'Org', 'type': 'Organization'}]}}
    log = _RecordingLog()
    tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(body=body)), log=log)
    tc_user.get_user_org(_fake_tcex(lambda _p: _Resp(body=body)), log=log)
    raw_lines = [m for m in log.infos if 'RAW /v2/owners/mine' in m]
    assert len(raw_lines) == 1


# ── resolve_org_key ───────────────────────────────────────────────────────


def _org_tcex(username='layne@example.com', org_id=42, org_name='My Org'):
    # resolve_org_key calls get_username() on every invocation regardless of
    # cache state (per spec: unknown usernames must never be cached), so
    # tests care specifically about the number of owners/mine lookups.
    calls = {'whoami': 0, 'owners': 0}

    def get(path):
        if path == '/v2/whoami':
            calls['whoami'] += 1
            return _Resp(body={'data': {'user': {'userName': username}}})
        if path == '/v2/owners/mine':
            calls['owners'] += 1
            return _Resp(
                body={'data': {'owner': [{'id': org_id, 'name': org_name, 'type': 'Organization'}]}}
            )
        raise AssertionError(f'unexpected path {path}')

    return _fake_tcex(get), calls


def test_resolve_org_key_happy_path():
    tcex, _calls = _org_tcex(org_id=42)
    log = _RecordingLog()
    assert ds.resolve_org_key(tcex, log) == 'org-42'


def test_resolve_org_key_unknown_username_not_cached():
    def get(path):
        if path == '/v2/whoami':
            return _Resp(body={'data': {'user': {'userName': 'unknown'}}})
        raise AssertionError('should not fetch owners for an unknown user')

    log = _RecordingLog()
    assert ds.resolve_org_key(_fake_tcex(get), log) is None
    assert ds._ORG_KEY_CACHE == {}


def test_resolve_org_key_lookup_failure_not_cached_then_recovers():
    state = {'fail': True}

    def get(path):
        if path == '/v2/whoami':
            return _Resp(body={'data': {'user': {'userName': 'layne@example.com'}}})
        if path == '/v2/owners/mine':
            if state['fail']:
                return _Resp(ok=False, status_code=500)
            return _Resp(body={'data': {'owner': [{'id': 7, 'name': 'Org', 'type': 'Organization'}]}})
        raise AssertionError(path)

    tcex = _fake_tcex(get)
    log = _RecordingLog()

    assert ds.resolve_org_key(tcex, log) is None
    assert ds._ORG_KEY_CACHE == {}

    state['fail'] = False
    assert ds.resolve_org_key(tcex, log) == 'org-7'


def test_resolve_org_key_uses_cache_without_second_lookup():
    tcex, calls = _org_tcex(org_id=42)
    log = _RecordingLog()

    assert ds.resolve_org_key(tcex, log) == 'org-42'
    assert calls['owners'] == 1

    assert ds.resolve_org_key(tcex, log) == 'org-42'
    assert calls['owners'] == 1  # no new owners/mine lookup: served from cache


def test_resolve_org_key_ttl_expiry_refetches(monkeypatch):
    tcex, calls = _org_tcex(org_id=42)
    log = _RecordingLog()

    fake_time = {'t': 0.0}
    monkeypatch.setattr(ds, '_now', lambda: fake_time['t'])

    assert ds.resolve_org_key(tcex, log) == 'org-42'
    assert calls['owners'] == 1

    fake_time['t'] += ds.ORG_KEY_TTL + 1
    assert ds.resolve_org_key(tcex, log) == 'org-42'
    assert calls['owners'] == 2  # TTL expired: re-fetched


# ── org.json marker ───────────────────────────────────────────────────────


def test_resolve_org_key_writes_org_marker(tmp_path):
    tcex, _calls = _org_tcex(org_id=42, org_name='My Org')
    log = _RecordingLog()

    ds.resolve_org_key(tcex, log, root=tmp_path)

    marker = tmp_path / 'org-42' / 'org.json'
    assert marker.is_file()
    payload = json.loads(marker.read_text(encoding='utf-8'))
    assert payload['id'] == 42
    assert payload['name'] == 'My Org'
    assert 'firstSeenAt' in payload


def test_resolve_org_key_marker_not_clobbered_on_later_resolution(tmp_path):
    tcex, _calls = _org_tcex(org_id=42, org_name='My Org')
    log = _RecordingLog()

    ds.resolve_org_key(tcex, log, root=tmp_path)
    marker = tmp_path / 'org-42' / 'org.json'
    original = marker.read_text(encoding='utf-8')

    ds._ORG_KEY_CACHE.clear()  # force a second real resolution
    ds.resolve_org_key(tcex, log, root=tmp_path)
    assert marker.read_text(encoding='utf-8') == original


def test_resolve_org_key_marker_write_failure_does_not_break_resolution(tmp_path):
    # `root` points at a file, not a directory, so mkdir() inside the
    # marker-write helper fails; resolution must still succeed.
    bogus_root = tmp_path / 'not-a-dir'
    bogus_root.write_text('x', encoding='utf-8')

    tcex, _calls = _org_tcex(org_id=42)
    log = _RecordingLog()

    assert ds.resolve_org_key(tcex, log, root=bogus_root) == 'org-42'
