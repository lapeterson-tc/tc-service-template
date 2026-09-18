"""Where ABC module."""

# standard library
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class ToWhere(ABC):
    """An abstract class that defines a method to convert an object to a where dictionary."""

    @abstractmethod
    def to_where(self) -> dict[str, Callable[[Any], bool] | None]:
        """Convert the object to a where dictionary that can be passed to DAO objects."""
