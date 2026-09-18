"""ThreatConnect Webhook Service App"""

# standard library
from typing import Any

# third-party
from tcex import TcEx

# first-party
from app_inputs import AppBaseModel
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.middleware_abc import MiddlewareABC


# pylint: disable=unused-argument
class TcExMiddleware(MiddlewareABC):
    """Standard middleware for all API service apps.

    Injects tcex, args, and logger into resources.
    """

    def __init__(self, args: AppBaseModel, tcex: TcEx):
        """Initialize instance properties."""
        self.args = args
        self.tcex = tcex
        self.log = tcex.log

    def process_resource(
        self, _req: FalconRequest, _resp: FalconResponse, resource: Any, _params: dict
    ):
        """Process resource method."""
        resource.args = self.args
        resource.log = self.log
        resource.tcex = self.tcex
