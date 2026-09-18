"""Middleware module"""

# first-party
from core.api.error.util import error
from core.api.middleware_abc import MiddlewareABC


# pylint: disable=unused-argument
class ErrorMiddleware(MiddlewareABC):
    """Middleware module"""

    def process_resource(self, _req, _resp, resource, _params):
        """Process resource method."""
        resource.error = error
