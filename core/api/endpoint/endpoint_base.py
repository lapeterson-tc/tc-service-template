"""Endpoint Base Class"""

# third-party
from tcex.logger.trace_logger import TraceLogger
from tcex.tcex import TcEx

# first-party
from app_config_model import AppConfigModel
from app_inputs import AppBaseModel


class EndpointBase:
    """Endpoint Base Class.

    Endpoint resources are Falcon singletons constructed once at boot (see
    ``app.py:App.routes``), so they declare bare class-level annotations and
    the middleware populates real values on the instance per request. That is
    why endpoints have no ``__init__`` — adding one, or setting these in it,
    would fight the middleware.

    Attributes below are grouped by which middleware sets them. Anything the
    app passes to ``InjectableMiddleware(**kwargs)`` is set **by kwarg name**,
    so an app-level subclass (``api/endpoint/endpoint_base.py``) must keep its
    annotations in sync with ``app.py:App.middleware``.
    """

    ##################################################
    # injected by TcEx middleware (core/api/tcex/middleware.py)
    args: AppBaseModel
    log: TraceLogger
    tcex: TcEx
    ##################################################

    ##################################################
    # injected by Injectable middleware (app.py:App.middleware)
    app_config: AppConfigModel
    ##################################################
