"""API Endpoint /api/example/preferences.

EXAMPLE FEATURE — delete this package when you build your own.

Per-user preferences persisted through the app's on-disk storage. This is the
reference implementation for every storage-backed endpoint in the template:

- Go through ``safe_datastore(tcex, log, data_type)`` — never construct a
  ``DiskStore`` directly. It resolves the caller's org namespace, which is the
  ONLY access-control boundary this storage has.
- Degrade, don't crash. A read with unavailable storage returns defaults so the
  page still renders; a write returns 503 with ``STORAGE_UNAVAILABLE_MSG`` so
  the user is told their change was not saved rather than silently losing it.
- Key records by username so one user's settings can never be served to
  another. (Org-wide settings use a fixed rid instead — e.g. ``'org-settings'``
  — and should be gated on a permission check if not everyone may change them.)
- Declare the ``data_type`` in ``api/storage/registry.DATA_TYPES`` or it will
  be missing from every backup.
"""

# third-party
import falcon
from spectree import Response

# first-party
from api.debug_log import debug_print
from api.endpoint.endpoint_base import EndpointBase
from api.spec_tags import tag_example
from api.storage.datastore_util import STORAGE_UNAVAILABLE_MSG, safe_datastore
from api.storage.tc_user import get_username
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.spec import spec
from core.api.validation.models.query_param_filter_model import QueryParamFilterModel
from core.model.model_base import ModelBase

DATASTORE_TYPE = 'example-preferences'

VALID_SORTS = ('dateAdded', 'summary', 'type', 'ownerName', 'threatAssessScore')
DEFAULT_PREFS = {'days': 30, 'sort': 'dateAdded', 'sortAsc': False}


def normalize_prefs(raw: dict | None) -> dict:
    """Coerce a stored/submitted prefs blob into a known-good shape.

    Pure, so it can be unit-tested without tcex. Unknown keys are dropped and
    out-of-range values fall back to the default: a record written by an older
    (or newer) version of the app must never be able to break the page.
    """
    raw = raw if isinstance(raw, dict) else {}
    try:
        days = int(raw.get('days', DEFAULT_PREFS['days']))
    except (TypeError, ValueError):
        days = DEFAULT_PREFS['days']
    days = max(1, min(365, days))

    sort = raw.get('sort')
    if sort not in VALID_SORTS:
        sort = DEFAULT_PREFS['sort']

    return {'days': days, 'sort': sort, 'sortAsc': bool(raw.get('sortAsc', False))}


class QueryParams(QueryParamFilterModel):
    """Query parameters for the preferences endpoints."""


class PreferencesModel(ModelBase):
    """Request/response body for user preferences."""

    days: int = DEFAULT_PREFS['days']
    sort: str = DEFAULT_PREFS['sort']
    sortAsc: bool = False
    error: str | None = None


class ExamplePreferences(EndpointBase):
    """API Endpoint /api/example/preferences."""

    def _debug(self, msg: str):
        line = f'[APP-DEBUG] preferences: {msg}'
        debug_print(line)
        self.log.info(line)

    def _rid(self) -> str:
        """Return the record id for the calling user."""
        return f'user-{get_username(self.tcex)}'

    @spec.validate(
        query=QueryParams,
        resp=Response(HTTP_200=PreferencesModel),
        skip_validation=True,
        tags=[tag_example],
    )
    def on_get(self, _req: FalconRequest, resp: FalconResponse, query_params: QueryParams):
        """Return the calling user's saved preferences, or the defaults."""
        try:
            store = safe_datastore(self.tcex, self.log, DATASTORE_TYPE)
            if store is None:
                # Read path degrades silently to defaults: the page must render.
                resp.media = resp.response_model(
                    dict(DEFAULT_PREFS), PreferencesModel, query_params
                )
                resp.status = falcon.HTTP_200
                return

            rid = self._rid()
            record = store.get(rid=rid, raise_on_error=False) or {}
            prefs = normalize_prefs(record.get('_source') if record.get('found') else None)
            self._debug(f'loaded rid={rid!r} found={bool(record.get("found"))}')
            resp.media = resp.response_model(prefs, PreferencesModel, query_params)
            resp.status = falcon.HTTP_200
        except Exception as ex:  # noqa: BLE001 - never-500
            self.log.exception('preferences read failed')
            resp.media = {**DEFAULT_PREFS, 'error': str(ex)}
            resp.status = falcon.HTTP_200

    @spec.validate(
        query=QueryParams,
        json=PreferencesModel,
        resp=Response(HTTP_200=PreferencesModel),
        skip_validation=True,
        tags=[tag_example],
    )
    def on_put(
        self,
        _req: FalconRequest,
        resp: FalconResponse,
        body: PreferencesModel,
        query_params: QueryParams,
    ):
        """Persist the calling user's preferences."""
        try:
            store = safe_datastore(self.tcex, self.log, DATASTORE_TYPE)
            if store is None:
                # Write path must NOT pretend to succeed.
                resp.status = falcon.HTTP_503
                resp.media = {'error': STORAGE_UNAVAILABLE_MSG}
                return

            prefs = normalize_prefs(body.dict())
            rid = self._rid()
            store.put(rid, prefs, raise_on_error=True)
            self._debug(f'saved rid={rid!r} prefs={prefs}')
            resp.media = resp.response_model(prefs, PreferencesModel, query_params)
            resp.status = falcon.HTTP_200
        except Exception as ex:  # noqa: BLE001 - never-500
            self.log.exception('preferences write failed')
            resp.status = falcon.HTTP_503
            resp.media = {'error': str(ex)}
