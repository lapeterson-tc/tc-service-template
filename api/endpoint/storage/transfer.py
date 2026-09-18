"""API Endpoints /api/storage/export and /api/storage/import.

Backup/restore for this app's on-disk storage (see ``api/storage/disk_store.py``),
covering every data type listed in ``api/storage/registry.DATA_TYPES``. Export
dumps every record for the calling user's org namespace as one curl-able JSON
bundle; import replays a bundle's records back into storage.

These exist because on-disk storage lives on the service container's volume
rather than in the platform — it is not backed up with ThreatConnect, and it
is not shared between instances of the same service.

Two rules worth calling out up front:

- **Restore always writes into the CALLER's org namespace.** A bundle's
  ``orgKey`` field is informational only (it documents where the export was
  taken FROM) and is NEVER used to choose where records land on import. Using
  it would let whoever runs an import silently overwrite a *different* org's
  storage just because they happen to have an org key handy — exactly the
  cross-org leak that the store's per-org namespacing
  (``disk_store.resolve_org_key``) exists to prevent. ``safe_datastore``
  always resolves the store for the *current* caller, so this holds
  structurally, not just by convention.
- **Secrets ride along by default.** ``redactSecrets=true`` routes every
  record through ``registry.redact_record``, which is identity until you
  implement it. See that function's docstring for why opt-in is the right
  default.
"""

# standard library
import threading
from datetime import datetime, timezone

# third-party
import falcon
from pydantic import Field
from spectree import Response

# first-party
from api.debug_log import debug_print
from api.endpoint.endpoint_base import EndpointBase
from api.spec_tags import tag_storage
from api.storage import registry
from api.storage.datastore_util import STORAGE_UNAVAILABLE_MSG, safe_datastore
from api.storage.disk_store import resolve_org_key
from api.storage.tc_user import get_username
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.spec import spec
from core.api.validation.models.query_param_filter_model import QueryParamFilterModel
from core.model.model_base import ModelBase

# Identify bundles produced by THIS app. Change it when you fork the template
# so a bundle can't be restored into an unrelated app's storage.
BUNDLE_FORMAT = 'tc-service-template-storage'
BUNDLE_VERSION = 1

# Per-type list_all cap for export. Well above the 500-record default used by
# list views elsewhere — raise it if a data type can hold more than this.
EXPORT_LIMIT = 10000

VALID_MODES = ('merge', 'overwrite')

# Serializes the write loop of concurrent imports so two overlapping restores
# can't interleave writes to the same record.
_IMPORT_LOCK = threading.Lock()


def _debug(log, msg: str) -> None:
    line = f'[APP-DEBUG] {msg}'
    debug_print(line)
    log.info(line)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def _parse_types(raw: str | None) -> tuple[list[str], list[str]]:
    """Parse the ``types`` query param into ``(requested, bad)``.

    Empty/absent means every registered type. ``bad`` holds any entries not in
    ``registry.DATA_TYPES`` (their presence means the caller should get a 400,
    not a silently-narrowed export). Duplicates are folded, order preserved.
    """
    known = registry.DATA_TYPES
    if not raw or not raw.strip():
        return list(known), []

    entries = [t.strip() for t in raw.split(',') if t.strip()]
    bad = [t for t in entries if t not in known]
    if bad:
        return [], bad

    seen: set[str] = set()
    ordered: list[str] = []
    for t in entries:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered, []


def _validate_import_body(mode: str, bundle) -> str | None:
    """Return an error string, or None when the request is well-formed."""
    if mode not in VALID_MODES:
        return f'mode must be one of {VALID_MODES}, got {mode!r}.'
    if not isinstance(bundle, dict):
        return 'bundle must be an object.'
    if bundle.get('format') != BUNDLE_FORMAT:
        return f"bundle.format must be {BUNDLE_FORMAT!r}, got {bundle.get('format')!r}."
    if bundle.get('version') != BUNDLE_VERSION:
        return f"bundle.version must be {BUNDLE_VERSION!r}, got {bundle.get('version')!r}."
    if not isinstance(bundle.get('data'), dict):
        return 'bundle.data must be an object.'
    return None


# ── Models ────────────────────────────────────────────────────────────────


class QueryParamExport(QueryParamFilterModel):
    """Query parameters for GET /api/storage/export."""

    # Optional comma-joined subset of registry.DATA_TYPES; absent/empty = all.
    types: str | None = None
    # Route records through registry.redact_record. Default False (see the
    # module docstring for why keeping secrets is the safer default).
    redactSecrets: bool = False


class QueryParamImport(QueryParamFilterModel):
    """Query parameters for POST /api/storage/import."""


class ExportOut(ModelBase):
    """Response body for a storage export."""

    format: str = BUNDLE_FORMAT
    version: int = BUNDLE_VERSION
    orgKey: str = ''
    exportedAt: str = ''
    exportedBy: str = ''
    counts: dict[str, int] = Field(default_factory=dict)
    data: dict[str, dict] = Field(default_factory=dict)
    error: str | None = None


class ImportBody(ModelBase):
    """Request body for a storage import."""

    mode: str = 'merge'
    bundle: dict = Field(default_factory=dict)


class RecordErrorOut(ModelBase):
    """One record that could not be imported."""

    type: str = ''
    rid: str = ''
    error: str = ''


class TypeCountsOut(ModelBase):
    """Per-type import counters."""

    imported: int = 0
    skipped: int = 0
    replaced: int = 0


class ImportOut(ModelBase):
    """Response body for a storage import."""

    imported: int = 0
    skipped: int = 0
    replaced: int = 0
    skippedTypes: list[str] = Field(default_factory=list)
    errors: list[RecordErrorOut] = Field(default_factory=list)
    byType: dict[str, TypeCountsOut] = Field(default_factory=dict)
    error: str | None = None


# ── /api/storage/export ──────────────────────────────────────────────────


class StorageExport(EndpointBase):
    """Export every record across the requested storage types for the caller's org."""

    @spec.validate(
        query=QueryParamExport,
        resp=Response(HTTP_200=ExportOut),
        skip_validation=True,
        tags=[tag_storage],
    )
    def on_get(self, _req: FalconRequest, resp: FalconResponse, query_params: QueryParamExport):
        """Return a self-contained JSON bundle of the caller's org storage."""
        try:
            requested, bad = _parse_types(query_params.types)
            if bad:
                resp.status = falcon.HTTP_400
                resp.media = {
                    'error': (
                        f'Unknown storage type(s): {", ".join(bad)}. '
                        f'Known types: {", ".join(registry.DATA_TYPES)}.'
                    )
                }
                return

            org_key = resolve_org_key(self.tcex, self.log)
            if org_key is None:
                # An empty/partial bundle must never masquerade as a
                # successful backup.
                resp.status = falcon.HTTP_503
                resp.media = {'error': STORAGE_UNAVAILABLE_MSG}
                return

            data: dict[str, dict] = {}
            counts: dict[str, int] = {}
            for dtype in requested:
                store = safe_datastore(self.tcex, self.log, dtype)
                if store is None:
                    resp.status = falcon.HTTP_503
                    resp.media = {'error': STORAGE_UNAVAILABLE_MSG}
                    return
                rows = store.list_all(limit=EXPORT_LIMIT)
                records = {row['_id']: row['_source'] for row in rows}
                if query_params.redactSecrets:
                    records = {
                        rid: (
                            registry.redact_record(dtype, rec) if isinstance(rec, dict) else rec
                        )
                        for rid, rec in records.items()
                    }
                counts[dtype] = len(records)
                data[dtype] = records

            username = get_username(self.tcex)
            _debug(
                self.log,
                f'storage export: org={org_key} user={username!r} '
                f'types={list(requested)} counts={counts} '
                f'redactSecrets={bool(query_params.redactSecrets)}',
            )

            resp.media = {
                'format': BUNDLE_FORMAT,
                'version': BUNDLE_VERSION,
                'orgKey': org_key,
                'exportedAt': _iso_now(),
                'exportedBy': username,
                'counts': counts,
                'data': data,
            }
        except Exception as ex:  # noqa: BLE001 - never-500
            self.log.exception('storage export failed')
            resp.media = {'error': str(ex)}


# ── /api/storage/import ──────────────────────────────────────────────────


class StorageImport(EndpointBase):
    """Restore a previously exported bundle's records into the caller's org.

    Always writes into the CALLING user's org namespace — the bundle's own
    ``orgKey`` is never consulted for placement (see the module docstring).
    """

    @spec.validate(
        query=QueryParamImport,
        json=ImportBody,
        resp=Response(HTTP_200=ImportOut),
        skip_validation=True,
        tags=[tag_storage],
    )
    def on_post(
        self,
        _req: FalconRequest,
        resp: FalconResponse,
        body: ImportBody,
        query_params: QueryParamImport,
    ):
        """Merge or overwrite storage records from ``body.bundle`` into this org."""
        try:
            mode = (body.mode or 'merge').strip().lower()
            error = _validate_import_body(mode, body.bundle)
            if error:
                resp.status = falcon.HTTP_400
                resp.media = {'error': error}
                return

            bundle_data: dict = body.bundle['data']
            username = get_username(self.tcex)

            imported = 0
            skipped = 0
            replaced = 0
            skipped_types: list[str] = []
            errors: list[dict] = []
            by_type: dict[str, dict] = {}

            with _IMPORT_LOCK:
                for dtype, records in bundle_data.items():
                    # Unknown types are reported and skipped, never refused —
                    # a bundle from a newer version of the app must still
                    # restore everything this version understands.
                    if dtype not in registry.DATA_TYPES:
                        skipped_types.append(dtype)
                        continue
                    if not isinstance(records, dict):
                        errors.append(
                            {'type': dtype, 'rid': '', 'error': 'records must be an object'}
                        )
                        continue

                    store = safe_datastore(self.tcex, self.log, dtype)
                    if store is None:
                        resp.status = falcon.HTTP_503
                        resp.media = {'error': STORAGE_UNAVAILABLE_MSG}
                        return

                    type_counts = {'imported': 0, 'skipped': 0, 'replaced': 0}
                    for rid, record in records.items():
                        if not isinstance(rid, str) or not rid.strip():
                            errors.append(
                                {
                                    'type': dtype,
                                    'rid': str(rid),
                                    'error': 'rid must be a non-empty string',
                                }
                            )
                            continue
                        if not isinstance(record, dict):
                            errors.append(
                                {'type': dtype, 'rid': rid, 'error': 'record must be an object'}
                            )
                            continue

                        try:
                            existing = store.get(rid=rid, raise_on_error=False)
                        except Exception as ex:  # noqa: BLE001
                            errors.append({'type': dtype, 'rid': rid, 'error': str(ex)})
                            continue
                        existed = bool(existing and existing.get('found'))

                        if mode == 'merge' and existed:
                            skipped += 1
                            type_counts['skipped'] += 1
                            continue

                        try:
                            store.post(rid, record, raise_on_error=True)
                        except Exception as ex:  # noqa: BLE001
                            errors.append({'type': dtype, 'rid': rid, 'error': str(ex)})
                            continue

                        if existed:
                            replaced += 1
                            type_counts['replaced'] += 1
                        else:
                            imported += 1
                            type_counts['imported'] += 1

                    by_type[dtype] = type_counts

            _debug(
                self.log,
                f'storage import: mode={mode} imported={imported} skipped={skipped} '
                f'replaced={replaced} errors={len(errors)} by={username!r}',
            )

            resp.media = {
                'imported': imported,
                'skipped': skipped,
                'replaced': replaced,
                'skippedTypes': skipped_types,
                'errors': errors,
                'byType': by_type,
            }
        except Exception as ex:  # noqa: BLE001 - never-500
            self.log.exception('storage import failed')
            resp.media = {'error': str(ex)}
