"""Unit tests for api/storage/disk_store.py.

Pure stdlib + pytest + tmp_path — no tcex import, so these always run.
"""

# standard library
import json
import os

# third-party
import pytest

# first-party
from api.storage import disk_store as ds


class _RecordingLog:
    """A tiny recorder standing in for the app logger."""

    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        self.warnings.append(msg)


def make_log():
    return _RecordingLog()


def make_store(tmp_path, org_key='org-1', data_type='things'):
    return ds.DiskStore(root=tmp_path, org_key=org_key, data_type=data_type, log=make_log())


# ── CRUD round-trip ──────────────────────────────────────────────────────


def test_post_then_get_round_trip(tmp_path):
    store = make_store(tmp_path)
    result = store.post('rid-1', {'a': 1, 'b': 'two'})
    assert result == {'_id': 'rid-1'}

    got = store.get(rid='rid-1')
    assert got == {'found': True, '_id': 'rid-1', '_source': {'a': 1, 'b': 'two'}}


def test_get_missing_rid_returns_not_found(tmp_path):
    store = make_store(tmp_path)
    assert store.get(rid='does-not-exist') == {'found': False}


def test_put_replaces_existing(tmp_path):
    store = make_store(tmp_path)
    store.post('rid-1', {'v': 1})
    store.put('rid-1', {'v': 2})
    assert store.get(rid='rid-1')['_source'] == {'v': 2}


def test_delete_removes_record(tmp_path):
    store = make_store(tmp_path)
    store.post('rid-1', {'v': 1})
    result = store.delete('rid-1')
    assert result == {'_id': 'rid-1'}
    assert store.get(rid='rid-1') == {'found': False}


def test_delete_missing_rid_is_idempotent(tmp_path):
    store = make_store(tmp_path)
    assert store.delete('ghost', raise_on_error=True) == {'_id': 'ghost'}
    assert store.delete('ghost', raise_on_error=False) == {'_id': 'ghost'}


def test_get_query_form_raises(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(RuntimeError):
        store.get(rid=None)
    with pytest.raises(RuntimeError):
        store.get()


# ── raise_on_error semantics on forced failures ──────────────────────────


def test_write_failure_raises_when_flag_true(tmp_path, monkeypatch):
    store = make_store(tmp_path)

    def _boom(path, payload):
        raise OSError('disk full')

    monkeypatch.setattr(ds, '_atomic_write_json', _boom)
    with pytest.raises(RuntimeError):
        store.post('rid-1', {'v': 1}, raise_on_error=True)


def test_write_failure_returns_none_when_flag_false(tmp_path, monkeypatch):
    store = make_store(tmp_path)

    def _boom(path, payload):
        raise OSError('disk full')

    monkeypatch.setattr(ds, '_atomic_write_json', _boom)
    assert store.post('rid-1', {'v': 1}, raise_on_error=False) is None


@pytest.mark.skipif(os.name == 'nt', reason='POSIX permission bits only')
@pytest.mark.skipif(hasattr(os, 'geteuid') and os.geteuid() == 0, reason='root ignores perms')
def test_get_os_error_raises_or_returns_none(tmp_path):
    store = make_store(tmp_path)
    store.post('rid-1', {'v': 1})
    path = store._path('rid-1')
    path.chmod(0o000)
    try:
        with pytest.raises(RuntimeError):
            store.get(rid='rid-1', raise_on_error=True)
        assert store.get(rid='rid-1', raise_on_error=False) is None
    finally:
        path.chmod(0o644)


# ── encode_rid / decode_rid ───────────────────────────────────────────────


@pytest.mark.parametrize(
    'rid',
    [
        'user-icons-layne.pet@gmail.com',
        '..',
        'a%b',
        'unicode-é中文',
    ],
)
def test_encode_decode_round_trip(rid):
    encoded = ds.encode_rid(rid)
    assert '.' not in encoded
    assert '/' not in encoded
    assert ds.decode_rid(encoded) == rid


def test_encode_rid_long_name_uses_hash_fallback():
    rid = 'x' * 300
    encoded = ds.encode_rid(rid)
    assert encoded.startswith('_h')
    assert len(encoded) < 300


def test_long_rid_round_trips_through_store_envelope(tmp_path):
    store = make_store(tmp_path)
    rid = 'y' * 300
    store.post(rid, {'ok': True})
    got = store.get(rid=rid)
    assert got == {'found': True, '_id': rid, '_source': {'ok': True}}

    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0]['_id'] == rid
    assert listed[0]['_source'] == {'ok': True}


# ── list_all ──────────────────────────────────────────────────────────────


def test_list_all_shape_and_limit(tmp_path):
    store = make_store(tmp_path)
    for i in range(5):
        store.post(f'rid-{i}', {'i': i})

    all_rows = store.list_all()
    assert len(all_rows) == 5
    assert all({'_id', '_source'} <= set(row) for row in all_rows)

    limited = store.list_all(limit=2)
    assert len(limited) == 2


def test_list_all_skips_corrupt_and_tmp_files(tmp_path):
    store = make_store(tmp_path)
    store.post('good', {'v': 1})

    (store.dir / 'corrupt.json').write_text('not valid json{{{', encoding='utf-8')
    (store.dir / '.tmp-leftover').write_text('{}', encoding='utf-8')

    rows = store.list_all()
    assert len(rows) == 1
    assert rows[0]['_id'] == 'good'


def test_list_all_missing_dir_returns_empty(tmp_path):
    store = make_store(tmp_path)
    store.dir.rmdir()
    assert store.list_all() == []


def test_get_corrupt_envelope_missing_data_key(tmp_path):
    store = make_store(tmp_path)
    path = store._path('rid-1')
    path.write_text(json.dumps({'rid': 'rid-1', 'updatedAt': 'x'}), encoding='utf-8')
    assert store.get(rid='rid-1') == {'found': False}


def test_get_corrupt_json(tmp_path):
    store = make_store(tmp_path)
    path = store._path('rid-1')
    path.write_text('{not json', encoding='utf-8')
    assert store.get(rid='rid-1') == {'found': False}


# ── org isolation ─────────────────────────────────────────────────────────


def test_org_isolation_no_bleed(tmp_path):
    store_a = ds.DiskStore(root=tmp_path, org_key='org-1', data_type='things', log=make_log())
    store_b = ds.DiskStore(root=tmp_path, org_key='org-2', data_type='things', log=make_log())

    store_a.post('same-rid', {'owner': 'a'})
    store_b.post('same-rid', {'owner': 'b'})

    assert store_a.get(rid='same-rid')['_source'] == {'owner': 'a'}
    assert store_b.get(rid='same-rid')['_source'] == {'owner': 'b'}
    assert store_a.dir != store_b.dir
    assert (tmp_path / 'org-1' / 'things').is_dir()
    assert (tmp_path / 'org-2' / 'things').is_dir()


# ── atomic-write cleanliness ──────────────────────────────────────────────


def test_no_tmp_files_remain_after_writes(tmp_path):
    store = make_store(tmp_path)
    for i in range(10):
        store.post(f'rid-{i}', {'i': i})
    leftovers = [p for p in store.dir.iterdir() if p.name.startswith('.tmp-')]
    assert leftovers == []
