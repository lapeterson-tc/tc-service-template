"""Unit tests for the example dashboard endpoint.

Two patterns worth copying:

1. **Pure helpers are tested without any gating.** ``clamp_days``,
   ``since_datetime`` and ``rows_by_type`` live at module level precisely so
   these tests run on a fresh checkout with no ``deps/`` and no tcex.
2. **Endpoint tests bare-instantiate the class and inject a fake session.**
   They are gated behind ``pytest.importorskip`` because importing the module
   pulls in falcon/spectree/tcex from ``deps/``. The handler is reached via
   ``on_get.__wrapped__`` -- spectree's decorator tries to validate the
   response against a real Falcon response object, which a fake is not.
"""

# standard library
import sys
from datetime import datetime, timezone
from pathlib import Path

# third-party
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

pytest.importorskip('falcon', reason='falcon not importable (run `tcex deps`)')
pytest.importorskip('tcex', reason='tcex not importable (run `tcex deps`)')

# first-party
from _common import FakeResp, FakeResponse, FakeTc, make_endpoint  # noqa: E402
from api.endpoint.example import dashboard as dash  # noqa: E402

# ── pure helpers ──────────────────────────────────────────────────────────


class TestClampDays:
    """clamp_days keeps the lookback window inside sane bounds."""

    def test_default_for_none(self):
        assert dash.clamp_days(None) == dash.DEFAULT_DAYS

    def test_default_for_garbage(self):
        assert dash.clamp_days('not-a-number') == dash.DEFAULT_DAYS

    def test_clamps_low_and_high(self):
        assert dash.clamp_days(0) == dash.MIN_DAYS
        assert dash.clamp_days(-5) == dash.MIN_DAYS
        assert dash.clamp_days(99999) == dash.MAX_DAYS

    def test_passes_through_valid(self):
        assert dash.clamp_days(45) == 45


def test_since_datetime_is_days_back_and_tql_shaped():
    now = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert dash.since_datetime(10, now=now) == '2026-03-05 12:00:00'


class TestRowsByType:
    """rows_by_type groups and orders the sample fallback."""

    def test_groups_and_sorts_descending(self):
        rows = [{'type': 'Host'}, {'type': 'Address'}, {'type': 'Host'}]
        assert dash.rows_by_type(rows) == [
            {'type': 'Host', 'count': 2},
            {'type': 'Address', 'count': 1},
        ]

    def test_missing_type_becomes_unknown(self):
        assert dash.rows_by_type([{'summary': 'x'}]) == [{'type': 'Unknown', 'count': 1}]

    def test_ignores_non_dict_rows(self):
        assert dash.rows_by_type(['nope', None, {'type': 'URL'}]) == [
            {'type': 'URL', 'count': 1}
        ]

    def test_empty_input(self):
        assert dash.rows_by_type([]) == []


# ── endpoint ──────────────────────────────────────────────────────────────


def _endpoint(responder=None):
    """Return a bare dashboard endpoint with a fake TC session."""
    # Reset the class-level type cache so tests don't leak into each other.
    dash.ExampleDashboard._type_cache = []
    dash.ExampleDashboard._type_cache_at = 0.0
    dash.ExampleDashboard._type_fetch_at = 0.0
    return make_endpoint(dash.ExampleDashboard, session_tc=FakeTc(responder))


def _get(ep, days=None):
    """Call the handler past spectree's response-validating wrapper."""
    resp = FakeResponse()
    query = type('Q', (), {'days': days})()
    ep.on_get.__wrapped__(ep, object(), resp, query)
    return resp.media


def test_happy_path_uses_exact_counts():
    def responder(_method, path, params, _json):
        if path == '/v2/types/indicatorTypes':
            return FakeResp(200, {'data': {'indicatorType': [{'name': 'Address'}]}})
        if path == '/v3/indicators' and params.get('resultLimit') == 1:
            return FakeResp(200, {'count': 7, 'data': []})
        return FakeResp(
            200,
            {
                'data': [
                    {
                        'summary': '1.2.3.4',
                        'type': 'Address',
                        'ownerName': 'Org',
                        'dateAdded': '2026-03-01',
                        'threatAssessScore': 250,
                    }
                ]
            },
        )

    body = _get(_endpoint(responder), days=30)
    assert body['error'] is None
    assert body['countSource'] == 'live'
    assert body['typeSource'] == 'live'
    assert body['byType'] == [{'type': 'Address', 'count': 7}]
    assert body['totalCount'] == 7
    assert body['recent'][0]['threatAssessScore'] == 250


def test_falls_back_to_sample_counts_when_envelope_has_no_count():
    def responder(_method, path, params, _json):
        if path == '/v2/types/indicatorTypes':
            return FakeResp(200, {'data': {'indicatorType': [{'name': 'Host'}]}})
        if path == '/v3/indicators' and params.get('resultLimit') == 1:
            return FakeResp(200, {'data': []})  # no 'count' key
        return FakeResp(200, {'data': [{'type': 'Host', 'summary': 'a.example'}]})

    body = _get(_endpoint(responder), days=7)
    assert body['countSource'] == 'sample'
    assert body['byType'] == [{'type': 'Host', 'count': 1}]


def test_unreachable_indicator_query_soft_errors_and_never_raises():
    def responder(_method, path, _params, _json):
        if path == '/v2/types/indicatorTypes':
            return FakeResp(500, None, text='boom')
        return FakeResp(503, None, text='upstream down')

    body = _get(_endpoint(responder), days=30)
    # 200-shaped payload with a soft error, not an exception.
    assert body['error']
    assert body['recent'] == []
    assert body['typeSource'] == 'fallback'


def test_days_param_is_clamped_into_the_response():
    body = _get(_endpoint(), days=100000)
    assert body['days'] == dash.MAX_DAYS


def test_type_list_falls_back_when_instance_lookup_fails():
    def responder(_method, path, _params, _json):
        if path == '/v2/types/indicatorTypes':
            return FakeResp(404, None, text='not found')
        return FakeResp(200, {'count': 0, 'data': []})

    body = _get(_endpoint(responder))
    assert body['typeSource'] == 'fallback'
