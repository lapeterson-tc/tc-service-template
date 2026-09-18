"""ThreatConnect API Service App.

This is the file you edit for every new feature: it declares the route table,
the objects injected onto endpoints, the boot preflight checks, and the SPA
route prefixes that make client-side deep links survive a reload.

Adding a feature is four edits:
  1. write the endpoint class under ``api/endpoint/<feature>/``
  2. import it here and add it to ``routes``
  3. add a Tag in ``api/spec_tags.py`` (once per feature area)
  4. if it has a UI page, add the route's top-level segment to
     ``spa_route_prefixes`` AND to ``ui/src/app/app-routing.module.ts``
"""

# standard library
import json
from datetime import datetime, timezone

# third-party
from tcex.pleb.cached_property import cached_property

# first-party
from api.endpoint.example.ask_ai import ExampleAskAi
from api.endpoint.example.dashboard import ExampleDashboard
from api.endpoint.example.preferences import ExamplePreferences
from api.endpoint.storage.transfer import StorageExport, StorageImport
from api.endpoint.tc.tc_proxy_local import TcProxyLocal
from api.storage.datastore_util import storage_root
from app_config_model import AppConfigModel, UiModel
from bedrock import Bedrock
from core.api.injectable.middleware import InjectableMiddleware
from core.app.api_service_falcon import ApiServiceFalcon

# Bump when the /api/tc/app-config payload shape changes in a way the UI
# must notice.
CONFIG_SCHEMA_VERSION = '1.0.0'


class App(ApiServiceFalcon):
    """API Service App"""

    def __init__(self, _tcex):
        """Initialize class properties."""
        super().__init__(_tcex)

        # Preflight checks run once, from loop_forever(), before the service
        # reports ready. A check must never raise — a failed capability should
        # disable a feature, not stop the app from booting.
        self.preflight_checks.register_preflight_check(self._check_bedrock_api)
        self.preflight_checks.register_preflight_check(self._check_storage)

    # ── preflight checks ─────────────────────────────────────────────────

    def _check_storage(self):
        """Verify the on-disk storage root and track boot persistence.

        Maintains ``app-data/.boot-marker.json`` so operators can confirm the
        container volume actually persists across restarts: a growing
        ``bootCount`` is the proof. Volume loss is indistinguishable from a
        first boot at runtime — a bootCount that fails to grow across known
        restarts is the diagnostic, not anything this check can detect
        directly. Never raises (the framework's own ``_check_filesystem``
        already hard-fails an unwritable ``tc_out_path``).
        """
        try:
            root = storage_root(self.tcex)
            root.mkdir(parents=True, exist_ok=True)
            marker_path = root / '.boot-marker.json'
            now = datetime.now(timezone.utc).isoformat()
            if marker_path.is_file():
                try:
                    marker = json.loads(marker_path.read_text())
                except (ValueError, OSError):
                    marker = {}
                marker['bootCount'] = int(marker.get('bootCount') or 0) + 1
                marker.setdefault('firstSeenAt', now)
                marker['lastBootAt'] = now
                self.log.info(
                    'action=check_storage, message=persistence verified '
                    f'bootCount={marker["bootCount"]} firstSeenAt={marker["firstSeenAt"]}'
                )
            else:
                org_dirs = [p.name for p in root.iterdir() if p.is_dir()]
                if org_dirs:
                    # Data survived but the marker did not — someone deleted it,
                    # or a partial restore happened. Loud, because bootCount
                    # history (the only persistence diagnostic) was just lost.
                    self.log.warning(
                        'action=check_storage, message=boot marker missing but '
                        f'org data exists (orgs={org_dirs}); persistence history lost, '
                        'restarting bootCount'
                    )
                else:
                    self.log.info(
                        f'action=check_storage, message=initialized storage at {root}'
                    )
                marker = {'firstSeenAt': now, 'lastBootAt': now, 'bootCount': 1}
            marker_path.write_text(json.dumps(marker, indent=2))
        except Exception as ex:  # noqa: BLE001 - preflight must never raise
            self.log.warning(f'action=check_storage, message=storage preflight failed: {ex}')

    def _check_bedrock_api(self):
        """Prove the Bedrock credentials/model work, and flip the UI gate.

        On success sets ``app_config.bedrock = True``, which reaches the UI via
        ``/api/tc/app-config``. On failure the app boots normally with every AI
        surface hidden. Delete this (and ``bedrock.py``) if the app has no AI
        features — it costs one model invocation at every service start.
        """
        try:
            body = dict(self.bedrock.anthropic_config)
            body['messages'] = [
                {
                    'role': 'user',
                    'content': [{'text': 'Return the words "MODEL IS WORKING".', 'type': 'text'}],
                }
            ]
            response = self.bedrock.invoke_model(body=json.dumps(body))
            response_body = json.loads(response['body'].read())
            result = response_body['content'][0]['text']
            self.log.info(
                'action=check_bedrock_api, '
                f'message=Preflight check for Bedrock passed, response="{result}"'
            )
            self.app_config.bedrock = True
        except Exception as ex:  # noqa: BLE001 - preflight must never raise
            self.log.warning(
                f'action=check_bedrock_api, message=Preflight check for Bedrock failed: {ex}'
            )

    # ── injected objects ─────────────────────────────────────────────────

    @cached_property
    def app_config(self) -> AppConfigModel:
        """Return the payload served by GET /api/tc/app-config.

        Add a field for every capability the UI must be able to hide. Note
        responses serialize with by_alias=False, so multi-word names arrive in
        the browser as snake_case.
        """
        return AppConfigModel(
            bedrock=False,  # set by the preflight above
            schema_version=CONFIG_SCHEMA_VERSION,
            ui=UiModel(
                title=self.tcex.app.ij.model.display_name,
                version=str(self.tcex.app.ij.model.program_version),
            ),
        )

    @cached_property
    def bedrock(self) -> Bedrock:
        """Return the shared AWS Bedrock client."""
        return Bedrock()

    @property
    def middleware(self) -> list:
        """Return the Custom Falcon Middleware.

        Each kwarg is set on every endpoint instance BY NAME, so these names
        must match the annotations on ``api/endpoint/endpoint_base.py``.
        """
        return [
            InjectableMiddleware(
                app_config=self.app_config,
                bedrock=self.bedrock,
            )
        ]

    # ── routes ───────────────────────────────────────────────────────────

    @property
    def routes(self) -> dict:
        """Return the Falcon Routes.

        Values are singletons constructed once at boot — endpoints must not
        hold per-request state on ``self`` (see EndpointBase).
        """
        return {
            # example feature -- replace with your own
            '/api/example/dashboard': ExampleDashboard(),
            '/api/example/preferences': ExamplePreferences(),
            '/api/example/ask-ai': ExampleAskAi(),
            # backup/restore for on-disk app storage
            '/api/storage/export': StorageExport(),
            '/api/storage/import': StorageImport(),
            # local-dev proxy shim (used by the UI's http interceptor on localhost)
            '/api/tc/proxy-local': TcProxyLocal(),
        }

    @property
    def spa_route_prefixes(self) -> tuple[str, ...]:
        """Top-level Angular routes that need path-style deep-link sinks.

        Must mirror the top-level paths in
        ``ui/src/app/app-routing.module.ts``. Miss one and a bookmarked or
        reloaded link to it renders a white page.
        """
        return ('dashboard',)
