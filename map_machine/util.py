"""Utility file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, cast

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class ComparableAndArithmetic(Protocol):
    """Protocol for types that support comparison and arithmetic operations."""

    def __lt__(self, other: object) -> bool: ...
    def __gt__(self, other: object) -> bool: ...
    def __sub__(self, other: object) -> object: ...
    def __add__(self, other: object) -> object: ...
    def __truediv__(self, other: object) -> object: ...


T = TypeVar("T", bound=ComparableAndArithmetic)


@dataclass
class MinMax(Generic[T]):
    """Minimum and maximum."""

    min_: T | None = None
    max_: T | None = None

    def update(self, value: T | None) -> None:
        """Update minimum and maximum with new value."""
        if value is None:
            return
        self.min_ = value if not self.min_ or value < self.min_ else self.min_
        self.max_ = value if not self.max_ or value > self.max_ else self.max_

    def delta(self) -> T:
        """Difference between maximum and minimum."""
        if self.min_ is None or self.max_ is None:
            message: str = "Cannot calculate delta of empty bounds."
            raise ValueError(message)
        return cast("T", self.max_ - self.min_)

    def center(self) -> T:
        """Get middle point between minimum and maximum."""
        if self.min_ is None or self.max_ is None:
            message: str = "Cannot calculate center of empty bounds."
            raise ValueError(message)
        sum_result = cast("T", self.min_ + self.max_)
        return cast("T", sum_result / 2.0)

    def is_empty(self) -> bool:
        """Check if interval is empty."""
        return self.min_ == self.max_

    def __repr__(self) -> str:
        return f"{self.min_}:{self.max_}"
