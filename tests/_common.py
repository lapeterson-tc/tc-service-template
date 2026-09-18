"""Shared fakes for endpoint tests.

Endpoint classes are constructed BARE here -- no ``__init__``, no Falcon, no
running service. At runtime the middleware injects ``tcex``/``log``/
``app_config`` onto each resource instance, so a test does the same thing by
hand and then calls the handler directly. Keep everything here network-free.
"""

# standard library
from types import SimpleNamespace


class NullLog:
    """A logger that swallows everything."""

    def info(self, *_a, **_k):
        """No-op."""

    def warning(self, *_a, **_k):
        """No-op."""

    def exception(self, *_a, **_k):
        """No-op."""

    def debug(self, *_a, **_k):
        """No-op."""


class FakeResp:
    """Minimal stand-in for a requests.Response."""

    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload
        self.text = text if text is not None else ''
        self.content = b'x' if payload is not None or text else b''

    def json(self):
        """Return the canned payload."""
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


class FakeTc:
    """Records every TC API call and replays canned responses.

    ``responder(method, path, params, json_body)`` returns a ``FakeResp`` or
    None; None falls through to a generic empty 200. Every call is appended to
    ``self.calls``, so a test can assert on the exact requests made -- which is
    usually more valuable than asserting on the response, especially for
    "this must write NOTHING" cases (``assert fake.calls == []``).
    """

    def __init__(self, responder=None):
        self.calls: list[dict] = []
        self.responder = responder

    def _record(self, method, path, params=None, json_body=None):
        self.calls.append(
            {'method': method, 'path': path, 'params': params or {}, 'json': json_body}
        )
        if self.responder is not None:
            resp = self.responder(method, path, params or {}, json_body)
            if resp is not None:
                return resp
        return FakeResp(200, {'data': []})

    def get(self, path, params=None, **_kwargs):
        """Record and answer a GET."""
        return self._record('GET', path, params)

    def post(self, path, json=None, params=None, **_kwargs):
        """Record and answer a POST."""
        return self._record('POST', path, params, json)

    def put(self, path, json=None, params=None, **_kwargs):
        """Record and answer a PUT."""
        return self._record('PUT', path, params, json)

    def delete(self, path, params=None, **_kwargs):
        """Record and answer a DELETE."""
        return self._record('DELETE', path, params)


class FakeResponse:
    """Minimal Falcon response stand-in.

    ``response_model`` mirrors the real FalconResponse helper closely enough
    for assertions: it returns the payload unchanged.
    """

    def __init__(self):
        self.media = None
        self.status = None

    @staticmethod
    def response_model(payload, _model=None, _query_params=None):
        """Return the payload as-is."""
        return payload


def make_endpoint(endpoint_cls, *, session_tc=None, app_config=None, **attrs):
    """Bare-instantiate ``endpoint_cls`` and inject the usual middleware attrs."""
    ep = endpoint_cls()
    ep.log = NullLog()
    ep.tcex = SimpleNamespace(session=SimpleNamespace(tc=session_tc or FakeTc()))
    ep.app_config = app_config or SimpleNamespace(bedrock=False)
    for key, value in attrs.items():
        setattr(ep, key, value)
    return ep
