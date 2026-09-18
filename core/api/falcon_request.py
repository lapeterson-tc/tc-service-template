"""Falcon Request Class"""

# third-party
import falcon
from pydantic import BaseModel, Field


class ContextModel(BaseModel):
    """Context model."""

    class Config:
        """Model configuration."""

        extra = 'allow'
        validate_default = True

    # falcon initializes the context object, which should
    # be empty by default, but not with None values???
    body: BaseModel | list[BaseModel] = Field({}, description='Request body data.')  # type: ignore
    form_data: BaseModel = Field({}, description='Form data.')  # type: ignore
    headers: BaseModel = Field({}, description='Request header model.')  # type: ignore
    params: BaseModel = Field({}, description='Query param model.')  # type: ignore


class FalconRequest(falcon.Request):
    """New Falcon Request class."""

    context: ContextModel
    context_type = ContextModel
    method: str
