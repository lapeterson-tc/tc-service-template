"""Integration Nexus Module"""

# standard library
import logging
import re
from typing import Any

# third-party
from pydantic import BaseModel, Extra, Field

# get primary API logger
logger = logging.getLogger('tcex')


def param_to_list(values) -> list:
    """Convert multiple or single params to a list."""
    if isinstance(values, list):
        return [v for raw_value in values for v in raw_value.split(',')]

    if isinstance(values, str):
        return values.split(',')

    return values


def value_to_camel(snake_string: str) -> str:
    """Convert snake_case to camelCase

    Args:
        snake_string: The snake case input string.
    """
    components = snake_string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def value_to_snake(value: str | None) -> str | None:
    """Convert string value from snake_case to camelCase."""
    if value is not None:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', value).lower()
    return value


def values_to_snake(values: list[str] | None) -> list[str] | None:
    """Convert string value from snake_case to camelCase."""

    if values is None:
        return None

    snake_strings = []
    for camel_case_string in values:
        snake_strings.append(value_to_snake(camel_case_string))
    return snake_strings


class QueryParamModel(BaseModel):
    """Model Definition"""

    class Config:
        """Model Configuration"""

        alias_generator = value_to_camel
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        extra = Extra.forbid

    _not_unset_capable = ['by_alias']

    by_alias: bool = Field(False, description='If True, convert response to camelCase.')

    @property
    def filter_values(self) -> dict[str, Any]:
        """Return filter parameters"""
        return {
            'by_alias': self.by_alias,
        }
