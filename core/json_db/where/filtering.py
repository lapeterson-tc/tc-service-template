"""Helper methods for filtering data with JSON DB DAOs."""

# standard library
from collections.abc import Callable
from typing import Any, TypeAlias, TypeVar

T = TypeVar('T')
WhereDict: TypeAlias = dict[str, Callable[[Any], bool] | None]


def where(filters: dict[str, Callable[[Any], bool] | None]) -> Callable[[Any], bool]:
    """Return a function that filters based on the provided filters."""

    def where_fn(x: Any) -> bool:
        for key, filter_fn in filters.items():
            if '.' in key:
                keys = key.split('.')
                value = x
                for k in keys:
                    value = getattr(value, k)
            else:
                value = getattr(x, key)
            if filter_fn is not None and not filter_fn(value):
                return False
        return True

    return where_fn


def contains(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value is like the provided value."""
    if value is None:
        return None
    if isinstance(value, str):
        return lambda x: value.casefold() in x.casefold()
    return lambda x: value in x


def eq(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value is equal to the provided value."""
    if value is None:
        return None
    return lambda x: x == value


def is_in(value: list | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value is equal to the provided value."""
    if value is None:
        return None
    return lambda x: x in value


def starts_with(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value starts with the provided value."""
    if value is None:
        return None
    return lambda x: x.casefold().startswith(value.casefold())


def ends_with(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value ends with the provided value."""
    if value is None:
        return None
    return lambda x: x.casefold().endswith(value.casefold())


def gt(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value is greater than the provided value."""
    if value is None:
        return None
    return lambda x: x > value


def lt(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value is less than the provided value."""
    if value is None:
        return None
    return lambda x: x < value


def gte(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value is greater than or equal to the provided value."""
    if value is None:
        return None
    return lambda x: x >= value


def lte(value: Any | None) -> Callable[[Any], bool] | None:
    """Return a function that checks if the value is less than or equal to the provided value."""
    if value is None:
        return None
    return lambda x: x <= value


def not_(fn: Callable[[T], bool] | None) -> Callable[[T], bool] | None:
    """Return a function that negates the provided function."""
    if fn is None:
        return None
    return lambda x: not fn(x)
