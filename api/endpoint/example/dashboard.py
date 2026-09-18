"""API Endpoint /api/example/dashboard.

EXAMPLE FEATURE — delete this package when you build your own.

A small read-only dashboard over ThreatConnect indicator data, written to
demonstrate every convention this template expects of a real endpoint:

- Query the TIP through ``self.tcex.session.tc`` (the CALLING USER's session),
  so results are automatically scoped to what that user may see. Never use a
  service identity to read user data.
- Declare spectree request/response models and tag the handler so it shows up
  in the OpenAPI page at ``apidoc/swagger``.
- **Never 500.** A failed upstream call returns HTTP 200 with a populated
  ``error`` string and whatever partial data is available, because the UI can
  render a degraded panel but cannot render a stack trace.
- Cache slow, user-agnostic metadata at class level with a TTL *and* a fetch
  cooldown, so a failing upstream endpoint is retried slowly rather than on
  every request.
- Emit ``[APP-DEBUG]`` lines to both stdout and the app log.

SECURITY NOTE on the class-level cache: Falcon resources are singletons shared
by every request, so anything cached on the class is shared across USERS. Only
ever cache instance-wide metadata there (here: the list of indicator type
names). Per-user data — counts, rows, anything scoped by owner or permission —
must be computed per request, or one analyst will be served another's results.
"""

# standard library
import time
from datetime import datetime, timedelta, timezone

# third-party
import falcon
from pydantic import Field
from spectree import Response

# first-party
from api.debug_log import debug_print
from api.endpoint.endpoint_base import EndpointBase
from api.spec_tags import tag_example
from api.tql import tql_quote
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.spec import spec
from core.api.validation.models.query_param_filter_model import QueryParamFilterModel
from core.model.model_base import ModelBase

# Lookback window bounds for the ``days`` query param.
MIN_DAYS = 1
MAX_DAYS = 365
DEFAULT_DAYS = 30

# How many recent indicators to list in the table.
RECENT_LIMIT = 50

# Refresh the /v2/types/indicatorTypes cache after this long.
INDICATOR_TYPE_CACHE_TTL_SECONDS = 6 * 60 * 60
# Minimum gap between fetch attempts (throttles a failing upstream endpoint).
INDICATOR_TYPE_FETCH_COOLDOWN_SECONDS = 60

# Standard system indicator types, used when /v2/types/indicatorTypes is
# unavailable. An instance may add custom types on top of these, which is why
# the live list is preferred.
FALLBACK_INDICATOR_TYPES = (
    'Address',
    'ASN',
    'CIDR',
    'Email Address',
    'Email Subject',
    'File',
    'Hashtag',
    'Host',
    'Mutex',
    'Registry Key',
    'URL',
    'User Agent',
)


def clamp_days(value: int | None) -> int:
    """Clamp the lookback window into ``[MIN_DAYS, MAX_DAYS]``.

    Pure so it can be unit-tested without tcex; see tests/test_example_dashboard.py.
    """
    if value is None:
        return DEFAULT_DAYS
    try:
        days = int(value)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return max(MIN_DAYS, min(MAX_DAYS, days))


def since_datetime(days: int, now: datetime | None = None) -> str:
    """Return the TQL ``dateAdded`` threshold for a ``days``-day lookback.

    ``now`` is injectable so tests don't depend on the wall clock.
    """
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')


def rows_by_type(rows: list[dict]) -> list[dict]:
    """Group indicator rows into ``[{type, count}]``, largest first.

    Pure. Used as the fallback when per-type counts can't be read from the
    response envelope, and directly unit-tested.
    """
    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get('type') or '').strip() or 'Unknown'
        counts[name] = counts.get(name, 0) + 1
    return sorted(
        ({'type': k, 'count': v} for k, v in counts.items()),
        key=lambda d: (-d['count'], d['type'].lower()),
    )


class QueryParamGet(QueryParamFilterModel):
    """Query parameters for GET /api/example/dashboard."""

    days: int | None = None


class TypeCountModel(ModelBase):
    """One bar of the by-type chart."""

    type: str
    count: int


class RecentIndicatorModel(ModelBase):
    """One row of the recent-indicators table."""

    summary: str = ''
    type: str = ''
    ownerName: str = ''
    dateAdded: str = ''
    threatAssessScore: int | None = None


class ResponseBodyModel(ModelBase):
    """Response body model."""

    days: int
    totalCount: int = 0
    byType: list[TypeCountModel] = Field(default_factory=list)
    recent: list[RecentIndicatorModel] = Field(default_factory=list)
    # 'live' when per-type counts came from the API's count envelope,
    # 'sample' when they were derived from the recent-rows sample.
    countSource: str = 'live'
    # 'live' when the indicator type list came from /v2/types/indicatorTypes.
    typeSource: str = 'live'
    # Soft error: populated instead of raising, so the UI degrades.
    error: str | None = None


class ExampleDashboard(EndpointBase):
    """API Endpoint /api/example/dashboard."""

    # /v2/types/indicatorTypes results, shared across requests for the service
    # lifetime. Instance-wide metadata only — see the module docstring.
    _type_cache: list[str] = []
    _type_cache_at: float = 0.0
    _type_fetch_at: float = 0.0

    def _debug(self, msg: str):
        line = f'[APP-DEBUG] dashboard: {msg}'
        debug_print(line)
        self.log.info(line)

    # ── indicator type list ───────────────────────────────────────────────

    def _fetch_indicator_types(self) -> list[str] | None:
        """Fetch indicator type names, or None on any failure.

        Returning None (rather than an empty list) lets the caller keep a
        previously-good cache instead of replacing it with nothing.
        """
        try:
            r = self.tcex.session.tc.get('/v2/types/indicatorTypes', params={'resultLimit': 500})
        except Exception as ex:  # noqa: BLE001
            self._debug(f'indicatorTypes fetch FAILED: {ex}')
            return None
        if not r.ok:
            self._debug(
                f'indicatorTypes fetch error: status={r.status_code}, '
                f'body[:200]={(r.text or "")[:200]!r}'
            )
            return None
        body = r.json() if r.content else {}
        rows = (body.get('data') or {}).get('indicatorType') or []
        names = sorted(
            {
                (row.get('name') or '').strip()
                for row in rows
                if isinstance(row, dict) and (row.get('name') or '').strip()
            },
            key=str.lower,
        )
        return names or None

    def _indicator_types(self) -> tuple[list[str], str]:
        """Return (indicator type names, source), refreshing the cache as needed."""
        cls = ExampleDashboard
        now = time.time()
        stale = (
            not cls._type_cache
            or (now - cls._type_cache_at) > INDICATOR_TYPE_CACHE_TTL_SECONDS
        )
        if stale and (
            not cls._type_fetch_at
            or (now - cls._type_fetch_at) > INDICATOR_TYPE_FETCH_COOLDOWN_SECONDS
        ):
            cls._type_fetch_at = now
            names = self._fetch_indicator_types()
            if names is not None:
                cls._type_cache = names
                cls._type_cache_at = now
                self._debug(f'indicator-types cache refreshed: {len(names)} types')
        if cls._type_cache:
            return cls._type_cache, 'live'
        return list(FALLBACK_INDICATOR_TYPES), 'fallback'

    # ── indicator queries ────────────────────────────────────────────────

    def _count_for_type(self, type_name: str, since: str) -> int | None:
        """Return the number of indicators of ``type_name`` added since ``since``.

        RUNTIME-VERIFY: this reads the total from the v3 response envelope's
        ``count`` key with ``resultLimit=1``, which is the cheap way to get an
        exact total without paging. If a live instance does not return
        ``count``, this returns None and the caller falls back to deriving
        counts from the recent-rows sample (and says so via ``countSource``).
        """
        tql = f'typeName = "{tql_quote(type_name)}" and dateAdded > "{tql_quote(since)}"'
        try:
            r = self.tcex.session.tc.get(
                '/v3/indicators', params={'tql': tql, 'resultLimit': 1}
            )
        except Exception as ex:  # noqa: BLE001
            self._debug(f'count FAILED type={type_name!r}: {ex}')
            return None
        if not r.ok:
            self._debug(f'count error type={type_name!r} status={r.status_code}')
            return None
        try:
            body = r.json() if r.content else {}
        except ValueError:
            return None
        count = body.get('count')
        if isinstance(count, int):
            return count
        return None

    def _recent(self, since: str, limit: int) -> tuple[list[dict], str | None]:
        """Return the most recently added indicators, newest first."""
        tql = f'dateAdded > "{tql_quote(since)}"'
        params = {
            'tql': tql,
            'resultLimit': limit,
            'sorting': 'dateAdded DESC',
            # ThreatAssess is not in the default field set; ask for it by name.
            'fields': 'threatassess',
        }
        try:
            r = self.tcex.session.tc.get('/v3/indicators', params=params)
        except Exception as ex:  # noqa: BLE001
            return [], f'Could not reach ThreatConnect: {ex}'
        if not r.ok:
            return [], f'ThreatConnect returned {r.status_code} for the indicator query.'
        try:
            body = r.json() if r.content else {}
        except ValueError:
            return [], 'ThreatConnect returned an unreadable response.'

        out: list[dict] = []
        for row in body.get('data') or []:
            if not isinstance(row, dict):
                continue
            score = row.get('threatAssessScore')
            out.append(
                {
                    'summary': row.get('summary') or '',
                    'type': row.get('type') or '',
                    'ownerName': row.get('ownerName') or '',
                    'dateAdded': row.get('dateAdded') or '',
                    'threatAssessScore': score if isinstance(score, int) else None,
                }
            )
        return out, None

    # ── handler ──────────────────────────────────────────────────────────

    @spec.validate(
        query=QueryParamGet,
        resp=Response(HTTP_200=ResponseBodyModel),
        skip_validation=True,
        tags=[tag_example],
    )
    def on_get(self, _req: FalconRequest, resp: FalconResponse, query_params: QueryParamGet):
        """Return indicator counts by type plus a recent-indicators sample."""
        days = clamp_days(query_params.days)
        payload = {
            'days': days,
            'totalCount': 0,
            'byType': [],
            'recent': [],
            'countSource': 'live',
            'typeSource': 'live',
            'error': None,
        }
        try:
            since = since_datetime(days)
            self._debug(f'days={days} since={since!r}')

            recent, error = self._recent(since, RECENT_LIMIT)
            payload['recent'] = recent
            payload['error'] = error

            type_names, type_source = self._indicator_types()
            payload['typeSource'] = type_source

            by_type: list[dict] = []
            exact = True
            for name in type_names:
                count = self._count_for_type(name, since)
                if count is None:
                    exact = False
                    break
                if count:
                    by_type.append({'type': name, 'count': count})

            if exact:
                by_type.sort(key=lambda d: (-d['count'], d['type'].lower()))
            else:
                # Envelope counts unavailable — derive from the sample and say so,
                # rather than showing numbers that quietly under-report.
                self._debug('count envelope unavailable; deriving byType from sample')
                by_type = rows_by_type(recent)
                payload['countSource'] = 'sample'

            payload['byType'] = by_type
            payload['totalCount'] = sum(d['count'] for d in by_type)
            self._debug(
                f'returning types={len(by_type)} total={payload["totalCount"]} '
                f'recent={len(recent)} countSource={payload["countSource"]}'
            )
        except Exception as ex:  # noqa: BLE001 - never-500
            self.log.exception('example dashboard failed')
            payload['error'] = str(ex)

        resp.media = resp.response_model(payload, ResponseBodyModel, query_params)
        resp.status = falcon.HTTP_200
