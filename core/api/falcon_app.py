"""Falcon Response Class"""

# standard library
import json
import logging
import traceback
from functools import partial
from pathlib import Path

# third-party
import falcon
from falcon import media

# first-party
from core.api.error.custom_error_handler import custom_error_handler
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.util.custom_handler import CustomHandler

# logger
logger = logging.getLogger('tcex')


def unhandled_error_handler(
    req: FalconRequest, _resp: FalconResponse, ex: Exception, _params: dict
):
    """Log unhandled (non-HTTP) exceptions to the app log, then return a 500.

    Falcon's built-in Exception handler writes the traceback to wsgi.errors,
    which the TC service runner wires to stderr — it never reaches the app
    log file, so unhandled exceptions surface only as ThreatConnect's generic
    "internal error" message with nothing to debug from. Log the full
    traceback to the tcex logger before composing the 500 response.
    """
    logger.error(f'event=unhandled-exception, path={req.path}, error="{ex}"')
    logger.error(
        ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__)).strip()
    )
    # Return a generic message to the client — the exception text can carry
    # internal detail (paths, upstream errors). The full traceback is in the
    # app log above for debugging.
    raise falcon.HTTPInternalServerError(
        title='Internal Server Error',
        description='An internal error occurred. See the app log for details.',
    ) from ex


class FalconApp(falcon.App):
    """New Falcon Response class.

    Beyond the stock falcon.App this adds: the custom request/response types,
    the app-log error handler above, a JSON media handler that can serialize
    datetimes, and the static route + redirect sinks that make a hash-routed
    Angular SPA survive a page reload under ThreatConnect's per-instance
    service path. See ``_add_routing_sinks`` for why the sinks exist.

    Args:
        spa_route_prefixes: top-level SPA route segments (without a leading
            slash) that must answer path-style deep links, e.g.
            ``('dashboard', 'reports')``. Each gets a 308 to the hash form.
        spa_entry_redirects: ``(prefix, hash_target)`` pairs for external
            entry points that should open a specific SPA route, e.g.
            ``(('open_report', '/reports/new'),)`` turns
            ``/open_report?id=7`` into ``./#/reports/new?id=7``.
    """

    def __init__(
        self,
        *args,
        spa_route_prefixes: tuple[str, ...] = (),
        spa_entry_redirects: tuple[tuple[str, str], ...] = (),
        **kwargs,
    ):
        """Initialize Falcon App."""

        self.spa_route_prefixes = tuple(spa_route_prefixes)
        self.spa_entry_redirects = tuple(spa_entry_redirects)

        super().__init__(*args, **kwargs)

        # update the request and response types
        self._request_type = FalconRequest
        self._response_type = FalconResponse

        # configure app
        self.req_options.auto_parse_qs_csv = True  # auto parse csv parameters
        self.req_options.strip_url_path_trailing_slash = True
        self._add_redirect_and_sink()

        # add custom error handler for api
        self.add_error_handler(falcon.HTTPError, custom_error_handler)

        # replace falcon's default Exception handler (stderr-only) with one
        # that logs to the app log; HTTPError still routes to the handler
        # above via most-specific-type matching.
        self.add_error_handler(Exception, unhandled_error_handler)

        # add media handlers
        self._add_media_handlers()

    def _add_media_handlers(self):
        """Add API handlers."""
        json_handler = media.JSONHandler(dumps=partial(json.dumps, cls=CustomHandler))
        extra_handlers = {'application/json': json_handler}
        self.resp_options.media_handlers.update(extra_handlers)  # pylint: disable=no-member

    def _add_redirect_and_sink(self):
        """Add redirect and sink to angular App."""
        # serve index.html specifically since `/` will not match a file (fallback returned)
        # index.html then calls ng route which will redirect to the SPA's default route
        self.add_static_route('/', self.ui_files, fallback_filename='index.html')

        # add routing sinks for "/ui/*", if this path is hit it indicates that
        # ng was already loaded and someone is trying to reload the page. this is
        # not technically supported, but we will redirect to the SPA root.
        self._add_routing_sinks()

    def _add_routing_sinks(self):
        """Add routing sinks to redirect all request to the UI."""

        def _ng_redirect(req: FalconRequest, _resp: FalconResponse):
            """Redirect to angular index.html file."""
            path_count = req.path.count('/') - 1
            redirect = '/'.join(['..'] * path_count)
            raise falcon.HTTPPermanentRedirect(redirect)

        self.add_sink(_ng_redirect, prefix='/ui')  # type: ignore

        def _spa_hash_redirect(req: FalconRequest, _resp: FalconResponse):
            """Redirect path-style SPA deep links to the hash-routed form.

            The Angular router uses hash routing (the app lives under a
            per-instance service prefix, so path-based routes can't survive a
            reload — the index.html fallback would answer the page's relative
            asset requests with HTML). Old-style links like
            .../v1/dashboard/{id} land here and bounce to
            .../v1/#/dashboard/{id}. The Location is relative because the app
            never knows its own absolute prefix.
            """
            path_count = req.path.count('/') - 1
            rel = '/'.join(['..'] * path_count) or '.'
            query = f'?{req.query_string}' if req.query_string else ''
            raise falcon.HTTPPermanentRedirect(f'{rel}/{query}#{req.path}')

        # sinks are matched before static routes (falcon default), so these
        # win over the '/' static route's index.html fallback. Declare every
        # top-level SPA route here or a bookmarked/reloaded deep link white-pages.
        for prefix in self.spa_route_prefixes:
            self.add_sink(_spa_hash_redirect, prefix=rf'/{prefix}(/|$)')  # type: ignore

        def _make_entry_redirect(hash_target: str):
            """Build an entry-point sink that opens ``hash_target`` in the SPA.

            Lets external callers deep-link into a specific route with query
            params. The query goes INSIDE the hash fragment — the Angular hash
            router only parses params after '#' (raw query_string, not
            req.params, so auto_parse_qs_csv can't mangle comma-containing
            values).
            """

            def _entry_redirect(req: FalconRequest, _resp: FalconResponse):
                path_count = req.path.count('/') - 1
                rel = '/'.join(['..'] * path_count) or '.'
                query = f'?{req.query_string}' if req.query_string else ''
                raise falcon.HTTPPermanentRedirect(f'{rel}/#{hash_target}{query}')

            return _entry_redirect

        for prefix, hash_target in self.spa_entry_redirects:
            self.add_sink(  # type: ignore
                _make_entry_redirect(hash_target), prefix=rf'/{prefix}(/|$)'
            )

    @property
    def ui_files(self):
        """Return the UI files."""
        return Path.cwd() / 'ui_build' / 'browser'
