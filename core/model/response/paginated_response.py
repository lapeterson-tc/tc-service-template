"""Model Definition"""

# standard library
from typing import Generic, TypeVar

# first-party
from core.model.response.response_model import ResponseModel

T = TypeVar('T')


class PaginatedResponseModel(ResponseModel[list[T]], Generic[T]):
    """Paginated Collection Response Model"""

    count: int
    data: list[T]
    next: str | None
    prev: str | None
    status: str | None
    total_count: int
