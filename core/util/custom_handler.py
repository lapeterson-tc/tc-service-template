"""DatetimeEncoder class."""

# standard library
import json
from datetime import date, datetime

# third-party
import arrow


class CustomHandler(json.JSONEncoder):
    """Json Encoder that supports datetime objects."""

    def default(self, o):  # type: ignore
        """Implement custom JSON Encoder."""
        handlers = {
            arrow.Arrow: lambda x: x.isoformat(),
            callable: lambda x: x.__name__,
            date: lambda x: x.isoformat(),
            datetime: lambda x: x.isoformat(),
            set: lambda x: list(x),  # pylint: disable=unnecessary-lambda
        }

        handler = handlers.get(type(o), lambda x: super().default(x))
        return handler(o)
