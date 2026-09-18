"""Class for /api/tc/app-config endpoint"""

# third-party
from spectree import Response

# first-party
from app_config_model import AppConfigModel
from core.api.endpoint.endpoint_base import EndpointBase
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.spec import spec, tag_setting
from core.api.validation.models.query_param_filter_model import QueryParamFilterModel


# pylint: disable=unused-argument
class TcAppConfig(EndpointBase):
    """Class for /api/tc/app-config endpoint"""

    @spec.validate(
        query=QueryParamFilterModel,
        resp=Response(HTTP_200=AppConfigModel),
        skip_validation=True,
        tags=[tag_setting],
    )
    def on_get(
        self, _req: FalconRequest, resp: FalconResponse, query_params: QueryParamFilterModel
    ):
        """Returns the configuration for the App."""
        resp.media = resp.response_model(self.app_config.dict(), AppConfigModel, query_params)
