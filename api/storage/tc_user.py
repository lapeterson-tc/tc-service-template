"""Shared helpers for resolving the calling user's identity and home owner."""

# first-party
from api.tql import tql_quote

# Raw-log the /v2/owners/mine response body once per process, for live
# shape verification (mirrors the "RAW ..." tracing convention used
# elsewhere, e.g. api/endpoint/example/dashboard.py).
_org_response_logged = False


def get_username(tcex) -> str:
    """Return the calling user's username from the TC session."""
    r = tcex.session.tc.get('/v2/whoami')
    if r.ok:
        data = r.json().get('data', {}).get('user', {})
        return data.get('userName', 'unknown')
    return 'unknown'


def get_default_owner(tcex, log=None) -> dict | None:
    """Resolve the calling user's home/default owner, or None if unknown.

    RUNTIME-VERIFY CANDIDATE: the ``/v3/security/users`` response shape for
    the ``owner`` field is not independently confirmed against a live
    instance. Defensively accepts either an owner object (``{id, name,
    ...}``) or a bare owner-name string; any other shape, or any failure
    along the way, returns None so callers degrade gracefully (e.g. the
    import-to-TC owner selector falls back to its existing alphabetical-first
    default) rather than breaking.
    """
    username = get_username(tcex)
    if username == 'unknown':
        return None
    escaped = tql_quote(username)
    try:
        r = tcex.session.tc.get(
            '/v3/security/users',
            params={'tql': f'username = "{escaped}"', 'resultLimit': 1},
        )
    except Exception as ex:
        if log:
            log.warning(f'[APP-DEBUG] get_default_owner FAILED: user={username!r}, error={ex}')
        return None
    if not r.ok:
        if log:
            log.warning(
                f'[APP-DEBUG] get_default_owner: /v3/security/users status={r.status_code}'
            )
        return None
    rows = r.json().get('data') or []
    if not rows:
        return None
    owner = rows[0].get('owner')
    if isinstance(owner, dict):
        return {'id': owner.get('id'), 'name': owner.get('name')}
    if isinstance(owner, str) and owner.strip():
        return {'id': None, 'name': owner.strip()}
    return None


def get_user_org(tcex, log=None) -> dict | None:
    """Resolve the calling user's ThreatConnect organization, or None.

    CONFIRMED LIVE 2026-07-31: ``/v2/owners/mine`` returns ``data.owner`` as
    a SINGLE object — ``{"status": "Success", "data": {"owner": {"id": 3,
    "name": "ThreatConnect", "type": "Organization"}}}`` — not the list the
    general v2 owners endpoints use (the original list-only parser silently
    failed and disabled all app storage). Both shapes are accepted: a dict
    is wrapped into a one-element list, then the first row whose ``type`` is
    ``'Organization'`` (case-insensitive) wins. Any failure along the way —
    request exception, non-ok response, malformed body, no Organization row,
    or an id that won't coerce to ``int`` — warn-logs (with the response
    body, since the one-shot RAW info line is filtered at WARNING-level
    deployments) and returns None so callers (notably disk-store
    org-namespace resolution) can fail closed.
    """
    global _org_response_logged
    try:
        r = tcex.session.tc.get('/v2/owners/mine')
    except Exception as ex:
        if log:
            log.warning(f'[APP-DEBUG] get_user_org FAILED: error={ex}')
        return None

    if log and not _org_response_logged:
        _org_response_logged = True
        log.info(f'[APP-DEBUG] RAW /v2/owners/mine body={r.text[:2000]}')

    if not r.ok:
        if log:
            log.warning(f'[APP-DEBUG] get_user_org: /v2/owners/mine status={r.status_code}')
        return None

    try:
        rows = r.json().get('data', {}).get('owner', [])
    except Exception as ex:
        if log:
            log.warning(f'[APP-DEBUG] get_user_org: unparseable body error={ex}')
        return None
    # Some response shapes return a single owner object rather than a list.
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        if log:
            log.warning(
                f'[APP-DEBUG] get_user_org: data.owner is {type(rows).__name__}, '
                f'body={r.text[:2000]}'
            )
        return None

    for row in rows:
        if isinstance(row, dict) and str(row.get('type', '')).lower() == 'organization':
            try:
                return {'id': int(row['id']), 'name': row.get('name', '')}
            except (KeyError, TypeError, ValueError) as ex:
                if log:
                    log.warning(
                        f'[APP-DEBUG] get_user_org: Organization row unusable '
                        f'error={ex} row={row!r}'
                    )
                return None
    if log:
        log.warning(
            f'[APP-DEBUG] get_user_org: no Organization row in response, '
            f'body={r.text[:2000]}'
        )
    return None
