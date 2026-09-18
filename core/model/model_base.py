"""Model Definition"""

# standard library
import logging

# third-party
from pydantic import BaseModel, Extra
from pydantic.generics import GenericModel

# logger
logger = logging.getLogger('tcex')


def snake_to_camel(snake_string: str) -> str:
    """Convert snake_case to camelCase

    Args:
        snake_string: The snake case input string.
    """
    components = snake_string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class GenericModelBase(GenericModel):
    """Generic Model Definition"""

    class Config:
        """Model Configuration"""

        alias_generator = snake_to_camel
        allow_population_by_field_name = True
        extra = Extra.forbid
        validate_all = True
        validate_assignment = True


class ModelBase(BaseModel):
    """Model Definition"""

    class Config:
        """Model Configuration"""

        alias_generator = snake_to_camel
        allow_population_by_field_name = True
        extra = Extra.forbid
        validate_all = True
        validate_assignment = True
