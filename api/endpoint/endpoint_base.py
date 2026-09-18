"""Endpoint Base Class (app level).

Extends the framework's ``EndpointBase`` with the objects THIS app injects via
``InjectableMiddleware``. Add an annotation here for every kwarg passed to
``InjectableMiddleware(...)`` in ``app.py:App.middleware`` — the middleware sets
attributes by kwarg name, so the two lists are one contract.
"""

# first-party
from bedrock import Bedrock
from core.api.endpoint.endpoint_base import EndpointBase as CoreEndpointBase


class EndpointBase(CoreEndpointBase):
    """Endpoint Base Class"""

    bedrock: Bedrock
