"""App Config Model"""

# third-party
from pydantic import Extra, Field

# first-party
from core.model.model_base import ModelBase


class UiModel(ModelBase, extra=Extra.allow):
    """UI Model"""

    title: str = Field(..., description='Title of the UI.')
    version: str = Field(..., description='Version of the UI.')


class AppConfigModel(ModelBase, extra=Extra.allow):
    """App Config Model.

    Served by ``GET /api/tc/app-config`` and used by the UI to gate features it
    must not show when the backing capability is unconfigured.

    NOTE: responses serialize with by_alias=False (see
    core/api/validation/models/query_param_model.py), so multi-word fields
    reach the UI as snake_case -- ``schema_version``, not ``schemaVersion``.
    Do NOT "fix" the TypeScript interface to camelCase.
    """

    bedrock: bool = Field(False, description='AWS Bedrock availability (set by boot preflight).')
    schema_version: str = Field(..., description='Schema version of this config.')
    ui: UiModel
