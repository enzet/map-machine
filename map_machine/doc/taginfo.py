"""
Creating Taginfo project file.

See https://wiki.openstreetmap.org/wiki/Taginfo/Projects
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from map_machine import (
    __author__,
    __description__,
    __doc_url__,
    __email__,
    __project__,
    __url__,
)
from map_machine.scheme import Scheme
from map_machine.workspace import workspace


class TaginfoProjectFile:
    """JSON structure with OpenStreetMap tag usage."""

    def __init__(self, path: Path, scheme: Scheme) -> None:
        self.path: Path = path

        self.structure = {
            "data_format": 1,
            "data_url": __url__ + "/" + str(path),
            "data_updated": datetime.now().strftime("%Y%m%dT%H%M%SZ"),
            "project": {
                "name": __project__,
                "description": __description__,
                "project_url": __url__,
                "doc_url": __doc_url__,
                "icon_url": "http://enzet.ru/map-machine/image/logo.png",
                "contact_name": __author__,
                "contact_email": __email__,
            },
            "tags": [],
        }
        tags = self.structure["tags"]

        for matcher in scheme.node_matchers:
            if (
                not matcher.location_restrictions
                and matcher.shapes
                and len(matcher.tags) == 1
                and not matcher.add_shapes
            ):
                key: str = list(matcher.tags.keys())[0]
                value: str = matcher.tags[key]
                ids: list[str] = [
                    (shape if isinstance(shape, str) else shape["shape"])
                    for shape in matcher.shapes
                ]
                icon_id: str = "___".join(ids)
                if value == "*":
                    continue
                tag = {
                    "key": key,
                    "value": value,
                    "object_types": ["node", "area"],
                    "description": "Rendered",
                    "icon_url": "http://enzet.ru/map-machine/"
                    f"roentgen_icons_mapcss/{icon_id}.svg",
                }
                tags.append(tag)

    def write(self) -> None:
        """Write Taginfo JSON file."""
        with self.path.open("w+", encoding="utf-8") as output_file:
            json.dump(self.structure, output_file, indent=4, sort_keys=True)


def write_taginfo_project_file(scheme: Scheme) -> None:
    """Write Taginfo JSON file."""
    out_file: Path = workspace.get_taginfo_file_path()
    logging.info(f"Write Map Machine project file for Taginfo to {out_file}...")
    taginfo_project_file: TaginfoProjectFile = TaginfoProjectFile(
        out_file, scheme
    )
    taginfo_project_file.write()
