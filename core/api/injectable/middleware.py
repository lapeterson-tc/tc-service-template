"""Injectable middleware module."""

# standard library
from typing import Any

# first-party
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.middleware_abc import MiddlewareABC


# pylint: disable=unused-argument
class InjectableMiddleware(MiddlewareABC):
    """Injectable middleware module."""

    def __init__(self, **kwargs):
        """Initialize.

        Args:
            kwargs: k,v pair where each will be injected into each resource such that
                resource.k = v
        """
        self.injectable = kwargs

    def process_resource(
        self, _req: FalconRequest, _resp: FalconResponse, resource: Any, _params: dict
    ):
        """."""
        for k, v in self.injectable.items():
            setattr(resource, k, v)
