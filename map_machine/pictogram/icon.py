"""Extract icons from SVG file."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roentgen import IconSpecification

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)

DEFAULT_SHAPE_ID: str = "default"
DEFAULT_SMALL_SHAPE_ID: str = "default_small"


@dataclass
class IconSet:
    """Node representation: icons and color."""

    main_icon: IconSpecification
    extra_icons: list[IconSpecification]

    # Icon to use if the point is hidden by overlapped icons but still need to
    # be shown.
    default_icon: IconSpecification | None

    # Tag keys that were processed to create icon set (other tag keys should be
    # displayed by text or ignored)
    processed: set[str]
