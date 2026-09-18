"""API Endpoint /api/tc/proxy-local.

Localhost-dev shim: the UI's http-interceptor rewrites ``//``-prefixed API
calls through here only when the UI is served from ``localhost`` (in
production the UI is served from inside TC and never calls this route).

Security: the request is issued with the caller's own TC session
(``tcex.session.tc``), so it can never exceed the caller's permissions. It
GETs only, restricts the relayed path to the TC ``/v2``/``/v3`` API surface,
and does NOT forward the inbound request headers to the backend (the session
already carries auth — relaying arbitrary client headers would be a
header-injection vector). Only the query-string params are passed through.
"""

# third-party
import falcon
from spectree import Response

# first-party
from api.endpoint.endpoint_base import EndpointBase
from api.spec_tags import tag_util
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.spec import spec

# Only these TC API prefixes may be relayed (defense-in-depth; the call is
# already scoped to the caller's session).
_ALLOWED_PREFIXES = ('/v2/', '/v3/')


class TcProxyLocal(EndpointBase):
    """API Endpoint /api/tc/proxy-local."""

    @spec.validate(
        resp=Response('HTTP_200'),
        skip_validation=True,
        tags=[tag_util],
    )
    def on_get(self, req: FalconRequest, resp: FalconResponse):
        """Relay a GET to the local TC API using the caller's session."""
        original = req.get_header('X-ORIGINAL-PATH')
        if not original:
            resp.status = falcon.HTTP_400
            resp.media = {'error': 'Missing X-ORIGINAL-PATH header.'}
            return

        # Normalize a leading 'api/' segment to the session's '/'-rooted form.
        path = '/' + original.lstrip('/')
        if path.startswith('/api/'):
            path = path[len('/api'):]

        if not path.startswith(_ALLOWED_PREFIXES):
            resp.status = falcon.HTTP_400
            resp.media = {'error': 'Only /v2 and /v3 TC API paths may be proxied.'}
            return

        # Deliberately do NOT forward req.headers — the session carries auth.
        response = self.tcex.session.tc.get(path, params=req.params)
        resp.media = response.json()

    @property
    def _tc_api_url(self):
        """Return the TC API URL."""
        return self.tcex.inputs.model.tc_api_path.replace('/api', '/')
