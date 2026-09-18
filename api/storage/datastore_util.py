"""Crash-safe access to the app's on-disk storage.

Persistent data lives as JSON files under
``{tc_out_path}/app-data/{org_key}/{data_type}/`` (see ``disk_store``). The
org key is resolved from the *calling user's* session (``/v2/owners/mine``)
and is the access-control boundary: storage is namespaced per org, exactly as
TC's v2 DataStore ``organization`` domain was.

Resolution fails CLOSED — when the caller's org can't be determined,
``safe_datastore`` returns ``None`` and every storage-backed endpoint must
degrade gracefully (defaults on read, a clear 503 on write). Never fall back
to a shared or default namespace: the org namespace IS the access control.

Two caveats inherited from the on-disk design, worth stating in any app's
docs: storage is per-container, so it is not shared between multiple
instances of the same service, and it lives on the container's volume rather
than in the platform — which is why the backup/restore endpoints exist.
"""

# first-party
from api.debug_log import debug_print
from api.storage.disk_store import DiskStore, resolve_org_key

# User-facing message for write endpoints when the caller's org storage
# is unavailable (org unresolvable or storage root unwritable).
STORAGE_UNAVAILABLE_MSG = (
    'Storage is unavailable for your organization. '
    'Contact your ThreatConnect administrator.'
)

# Directory name under tc_out_path that holds every org's data.
STORAGE_ROOT_DIR = 'app-data'


def storage_root(tcex):
    """Return the storage root path for this deployment."""
    return tcex.inputs.model.tc_out_path / STORAGE_ROOT_DIR


def safe_datastore(tcex, log, data_type: str):
    """Return a DiskStore for ``data_type`` in the caller's org, or None.

    Returns None (after logging) when the caller's org can't be resolved or
    the storage directory can't be created, instead of letting an exception
    bubble up as an opaque 500. The DataStore-shaped method surface
    (``get``/``post``/``put``/``delete``) is kept so tests can substitute a
    fake, and a real ``tmp_path``-backed DiskStore can stand in unchanged.

    ``data_type`` must be listed in ``api/storage/registry.DATA_TYPES``.
    """
    try:
        root = storage_root(tcex)
        org_key = resolve_org_key(tcex, log, root=root)
        if org_key is None:
            msg = (
                f'[APP-DEBUG] storage unavailable: data_type={data_type}, '
                'caller org could not be resolved (failing closed)'
            )
            debug_print(msg)
            log.warning(msg)
            return None
        return DiskStore(root, org_key, data_type, log)
    except Exception as ex:
        msg = f'[APP-DEBUG] storage unavailable: data_type={data_type}, error="{ex}"'
        debug_print(msg)
        log.warning(msg)
        return None
