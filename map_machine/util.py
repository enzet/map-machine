"""Utility file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


@dataclass
class MinMax:
    """Minimum and maximum."""

    min_: Any | None = None
    max_: Any | None = None

    def update(self, value: Any) -> None:  # noqa: ANN401
        """Update minimum and maximum with new value."""
        if value is None:
            return
        self.min_ = value if not self.min_ or value < self.min_ else self.min_
        self.max_ = value if not self.max_ or value > self.max_ else self.max_

    def delta(self) -> Any:  # noqa: ANN401
        """Difference between maximum and minimum."""
        if self.min_ is None or self.max_ is None:
            message: str = "Cannot calculate delta of empty bounds."
            raise ValueError(message)
        return self.max_ - self.min_

    def center(self) -> Any:  # noqa: ANN401
        """Get middle point between minimum and maximum."""
        if self.min_ is None or self.max_ is None:
            message: str = "Cannot calculate center of empty bounds."
            raise ValueError(message)
        sum_result = self.min_ + self.max_
        return sum_result / 2.0

    def is_empty(self) -> bool:
        """Check if interval is empty."""
        return self.min_ == self.max_

    def __repr__(self) -> str:
        return f"{self.min_}:{self.max_}"
