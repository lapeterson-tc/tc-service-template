"""Model Definition"""

# standard library
import logging

# third-party
from pydantic import BaseModel, Extra

# first-party
from core.api.validation.models.query_param_model import value_to_camel

# logger
logger = logging.getLogger('tcex')


class ModelBase(BaseModel):
    """Model Definition"""

    class Config:
        """Model Configuration"""

        alias_generator = value_to_camel
        extra = Extra.forbid
        validate_assignment = True
        validate_all = True
