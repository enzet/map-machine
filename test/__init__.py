from pathlib import Path

from roentgen.icon import ShapeExtractor
from roentgen.scheme import Scheme

SCHEME: Scheme = Scheme(Path("scheme/default.yml"))
SCHEME_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    Path("icons/icons.svg"), Path("icons/config.json")
)


