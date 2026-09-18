"""Model Definition"""

# standard library
from typing import Generic, TypeVar

# first-party
from core.model.model_base import GenericModelBase

T = TypeVar('T')


class ResponseModel(GenericModelBase, Generic[T]):
    """Paginated Collection Response Model"""

    data: T
