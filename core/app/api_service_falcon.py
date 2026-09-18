"""ThreatConnect API Service Falcon API"""

# standard library
import logging
import time
from functools import cached_property

# third-party
from tcex.api.tc.v3.tql.tql_operator import TqlOperator
from tcex.exit import ExitCode

# first-party
from app_inputs import AppBaseModel
from core.api.endpoint.tc_app_config import TcAppConfig
from core.api.error.middleware import ErrorMiddleware
from core.api.falcon_app import FalconApp
from core.api.spec import spec
from core.api.tcex.middleware import TcExMiddleware
from core.api.validation.middleware import ValidationMiddleware
from core.app.api_service_app import ApiServiceApp
from core.service.preflight_check_service import PreflightCheckService
from model.settings_model import SettingModel

logger = logging.getLogger('tcex')


class ApiServiceFalcon(ApiServiceApp):
    """ThreatConnect API Service Falcon API"""

    def __init__(self, *args, **kwargs):
        """Initialize class properties."""
        super().__init__(*args, **kwargs)

        self.log = logger  # type: ignore
        self.model: AppBaseModel = self.inputs.model  # type: ignore

        # properties
        self.app = FalconApp(
            middleware=self._middleware,
            sink_before_static_route=True,
            spa_route_prefixes=self.spa_route_prefixes,
            spa_entry_redirects=self.spa_entry_redirects,
        )
        self.preflight_checks = PreflightCheckService(self.tcex, self.log)

        if not self.app.ui_files.exists():
            self.tcex.exit.exit(1, 'UI files not found. Ensure they are built.')

        # configure routes
        self._inject_routes()

    @property
    def _routes(self) -> dict:
        """Return the Default Falcon Routes"""
        return {
            '/api/tc/app-config': TcAppConfig(),
        }

    @property
    def routes(self) -> dict:
        """Return the Custom Falcon Routes."""
        return {}

    @property
    def spa_route_prefixes(self) -> tuple[str, ...]:
        """Return the SPA top-level route segments that need deep-link sinks.

        Every top-level client route must be listed here (without a leading
        slash). A path-style link to an unlisted route falls through to the
        '/' static route's index.html fallback, which then answers the page's
        RELATIVE asset requests with HTML and the app never boots (white page).
        See ``core/api/falcon_app.py:_add_routing_sinks``.
        """
        return ()

    @property
    def spa_entry_redirects(self) -> tuple[tuple[str, str], ...]:
        """Return ``(url_prefix, spa_hash_route)`` external entry points.

        Use for links handed to systems outside this app, e.g.
        ``(('open_item', '/items/new'),)`` so ``/open_item?id=7`` opens
        ``./#/items/new?id=7``.
        """
        return ()

    def _inject_routes(self):
        """Inject routes into Falcon App."""
        routes = self._routes.copy()
        routes.update(self.routes)
        for route, resource in routes.items():
            self.app.add_route(route, resource)
        spec.register(self.app)

    @property
    def _middleware(self) -> list:
        """Return the Falcon middleware."""
        middleware = self.middleware
        middleware.extend(
            [
                TcExMiddleware(self.model, self.tcex),
                ErrorMiddleware(),
                ValidationMiddleware(),
                # InjectableMiddleware(),
            ]
        )
        return middleware

    @property
    def middleware(self) -> list:
        """Return the Custom Falcon Middleware."""
        return []

    @cached_property
    def settings(self) -> SettingModel:
        """Setting Model."""
        ex_msg = 'settings property must be implemented in child class.'
        raise NotImplementedError(ex_msg)

    def api_event_callback(self, environ, response_handler):
        """Create the API"""
        if not environ['PATH_INFO'].startswith('/'):
            environ['PATH_INFO'] = '/' + environ['PATH_INFO']

        return self.app(environ, response_handler)

    def owner_id(self, owner_name: str) -> int | None:
        """Return the owner id."""
        owners = self.tcex.api.tc.v3.security.owners()
        owners.filter.owner_name(TqlOperator.EQ, owner_name)

        # there should only be one owner
        for owner in owners:
            self.log.debug(f'event=found-owner, owner-id={owner.model.id}, owner-name={owner_name}')
            return owner.model.id

        ex_msg = f'Can not find owner {owner_name} in ThreatConnect instance.'
        raise RuntimeError(ex_msg)

    def loop_forever(self):
        """Loop forever running scheduled task as appropriate."""
        self.preflight_checks.perform_checks()

        while True:
            time.sleep(1)
            if self.tcex.app.service.message_broker.shutdown is True:
                self.log.trace('action=loop-forever, shutdown=True')
                break

        self.tcex.exit.exit(ExitCode.SUCCESS, 'App has been successfully stopped')
