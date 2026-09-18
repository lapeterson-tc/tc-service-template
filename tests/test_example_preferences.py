"""Unit tests for the example preferences endpoint.

Demonstrates the storage-backed test pattern: ``safe_datastore`` is
monkeypatched to return a REAL ``DiskStore`` rooted at pytest's ``tmp_path``,
not a mock. That keeps the on-disk record format itself under test -- a mock
would happily accept a shape the real store cannot round-trip.

Patch ``safe_datastore`` where it is USED (the endpoint module), not where it
is defined; the endpoint imported the name at module load.
"""

# standard library
import sys
from pathlib import Path

# third-party
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

pytest.importorskip('falcon', reason='falcon not importable (run `tcex deps`)')
pytest.importorskip('tcex', reason='tcex not importable (run `tcex deps`)')

# first-party
from _common import FakeResponse, FakeTc, NullLog, make_endpoint  # noqa: E402
from api.endpoint.example import preferences as prefs_mod  # noqa: E402
from api.storage.disk_store import DiskStore  # noqa: E402

# ── pure helper ───────────────────────────────────────────────────────────


class TestNormalizePrefs:
    """normalize_prefs must never let a stored record break the page."""

    def test_defaults_for_empty(self):
        assert prefs_mod.normalize_prefs(None) == prefs_mod.DEFAULT_PREFS

    def test_clamps_days(self):
        assert prefs_mod.normalize_prefs({'days': 10_000})['days'] == 365
        assert prefs_mod.normalize_prefs({'days': 0})['days'] == 1

    def test_rejects_unknown_sort(self):
        assert prefs_mod.normalize_prefs({'sort': 'dropTable'})['sort'] == 'dateAdded'

    def test_drops_unknown_keys(self):
        out = prefs_mod.normalize_prefs({'days': 7, 'rogue': 'x'})
        assert set(out) == {'days', 'sort', 'sortAsc'}

    def test_coerces_garbage_days(self):
        assert prefs_mod.normalize_prefs({'days': 'lots'})['days'] == 30


# ── endpoint ──────────────────────────────────────────────────────────────


@pytest.fixture
def store(tmp_path):
    """A real DiskStore in a temp directory."""
    return DiskStore(tmp_path, 'org-1', prefs_mod.DATASTORE_TYPE, NullLog())


def _endpoint(monkeypatch, store_or_none):
    monkeypatch.setattr(prefs_mod, 'safe_datastore', lambda *_a, **_k: store_or_none)
    monkeypatch.setattr(prefs_mod, 'get_username', lambda _tcex: 'analyst')
    return make_endpoint(prefs_mod.ExamplePreferences, session_tc=FakeTc())


def _get(ep):
    resp = FakeResponse()
    ep.on_get.__wrapped__(ep, object(), resp, object())
    return resp


def _put(ep, **fields):
    resp = FakeResponse()
    body = prefs_mod.PreferencesModel(**fields)
    ep.on_put.__wrapped__(ep, object(), resp, body, object())
    return resp


def test_get_returns_defaults_when_nothing_saved(monkeypatch, store):
    body = _get(_endpoint(monkeypatch, store)).media
    assert body == prefs_mod.DEFAULT_PREFS


def test_put_then_get_round_trips_through_real_disk(monkeypatch, store):
    ep = _endpoint(monkeypatch, store)
    _put(ep, days=7, sort='summary', sortAsc=True)
    body = _get(ep).media
    assert body == {'days': 7, 'sort': 'summary', 'sortAsc': True}


def test_put_normalizes_before_storing(monkeypatch, store):
    ep = _endpoint(monkeypatch, store)
    resp = _put(ep, days=99999, sort='nope', sortAsc=False)
    assert resp.media == {'days': 365, 'sort': 'dateAdded', 'sortAsc': False}
    stored = store.get(rid='user-analyst')['_source']
    assert stored['days'] == 365


def test_get_degrades_to_defaults_when_storage_is_unavailable(monkeypatch):
    body = _get(_endpoint(monkeypatch, None)).media
    assert body == prefs_mod.DEFAULT_PREFS


def test_put_refuses_rather_than_pretending_to_save(monkeypatch):
    # A write with no storage must be visibly refused -- silently dropping a
    # user's setting is the failure mode this guards against.
    resp = _put(_endpoint(monkeypatch, None), days=7)
    assert resp.status.startswith('503')
    assert 'error' in resp.media


def test_records_are_keyed_per_user(monkeypatch, store):
    ep = _endpoint(monkeypatch, store)
    _put(ep, days=7)
    monkeypatch.setattr(prefs_mod, 'get_username', lambda _tcex: 'someone-else')
    assert _get(ep).media == prefs_mod.DEFAULT_PREFS
