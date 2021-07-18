"""
Icon grid drawing.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import logging
import numpy as np
from colour import Color
from svgwrite import Drawing

from roentgen.icon import Icon, Shape, ShapeExtractor, ShapeSpecification
from roentgen.scheme import NodeMatcher, Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


@dataclass
class IconCollection:
    """
    Collection of icons.
    """

    icons: List[Icon]
    selectors: Dict[str, Icon] = field(default_factory=dict)

    @classmethod
    def from_scheme(
        cls,
        scheme: Scheme,
        extractor: ShapeExtractor,
        background_color: Color = Color("white"),
        color: Color = Color("black"),
        add_unused: bool = False,
    ) -> "IconCollection":
        """
        Collect all possible icon combinations in grid.

        :param scheme: tag specification
        :param extractor: shape extractor for icon creation
        :param background_color: background color
        :param color: icon color
        :param add_unused: create icons from shapes that have no corresponding
            tags
        """
        icons: List[Icon] = []
        selectors: Dict[str, Icon] = {}

        def add() -> Icon:
            """
            Construct icon and add it to the list.
            """
            specifications = [
                ShapeSpecification.from_structure(x, extractor, scheme)
                for x in current_set
            ]
            constructed_icon: Icon = Icon(specifications)
            constructed_icon.recolor(color, white=background_color)
            if constructed_icon not in icons:
                icons.append(constructed_icon)

            return constructed_icon

        for matcher in scheme.node_matchers:
            matcher: NodeMatcher
            if matcher.shapes:
                current_set = matcher.shapes
                icon = add()
                if not matcher.location_restrictions:
                    selectors[matcher.get_mapcss_selector()] = icon
            if matcher.add_shapes:
                current_set = matcher.add_shapes
                add()
            if not matcher.over_icon:
                continue
            if matcher.under_icon:
                for icon_id in matcher.under_icon:
                    current_set = [icon_id] + matcher.over_icon
                    add()
            if not (matcher.under_icon and matcher.with_icon):
                continue
            for icon_id in matcher.under_icon:
                for icon_2_id in matcher.with_icon:
                    current_set: List[str] = (
                        [icon_id] + [icon_2_id] + matcher.over_icon
                    )
                    add()
                for icon_2_id in matcher.with_icon:
                    for icon_3_id in matcher.with_icon:
                        current_set = (
                            [icon_id]
                            + [icon_2_id]
                            + [icon_3_id]
                            + matcher.over_icon
                        )
                        if (
                            icon_2_id != icon_3_id
                            and icon_2_id != icon_id
                            and icon_3_id != icon_id
                        ):
                            add()

        specified_ids: Set[str] = set()

        for icon in icons:
            specified_ids |= set(icon.get_shape_ids())

        if add_unused:
            for shape_id in extractor.shapes.keys() - specified_ids:
                shape: Shape = extractor.get_shape(shape_id)
                if shape.is_part:
                    continue
                icon: Icon = Icon([ShapeSpecification(shape)])
                icon.recolor(color)
                icons.append(icon)

        return cls(icons, selectors)

    def draw_icons(
        self,
        output_directory: Path,
        by_name: bool = False,
        color: Optional[Color] = None,
        outline: bool = False,
    ):
        """
        :param output_directory: path to the directory to store individual SVG
            files for icons
        :param by_name: use names instead of identifiers
        :param color: fill color
        :param outline: if true, draw outline beneath the icon
        """
        if by_name:

            def get_file_name(x) -> str:
                """Generate human-readable file name."""
                return f"Röntgen {' + '.join(x.get_names())}.svg"

        else:

            def get_file_name(x) -> str:
                """Generate file name with unique identifier."""
                return f"{'___'.join(x.get_shape_ids())}.svg"

        for icon in self.icons:
            icon.draw_to_file(
                output_directory / get_file_name(icon),
                color=color,
                outline=outline,
            )

    def draw_grid(
        self,
        file_name: Path,
        columns: int = 16,
        step: float = 24,
        background_color: Color = Color("white"),
    ):
        """
        Draw icons in the form of table.

        :param file_name: output SVG file name
        :param columns: number of columns in grid
        :param step: horizontal and vertical distance between icons in grid
        :param background_color: background color
        """
        point: np.array = np.array((step / 2, step / 2))
        width: float = step * columns

        height: int = int(int(len(self.icons) / (width / step) + 1) * step)
        svg: Drawing = Drawing(str(file_name), (width, height))
        svg.add(svg.rect((0, 0), (width, height), fill=background_color.hex))

        for icon in self.icons:
            icon: Icon
            rectangle = svg.rect(
                point - np.array((10, 10)), (20, 20), fill=background_color.hex
            )
            svg.add(rectangle)
            icon.draw(svg, point)
            point += np.array((step, 0))
            if point[0] > width - 8:
                point[0] = step / 2
                point += np.array((0, step))
                height += step

        with file_name.open("w") as output_file:
            svg.write(output_file)

    def get_mapcss_selectors(self) -> str:
        """
        Construct MapCSS 0.2 style scheme.
        """
        s = ""
        for selector in self.selectors:
            for target in ["node", "area"]:
                s += target + selector + " {\n"
                s += (
                    '    icon-image: "icons/'
                    + "___".join(self.selectors[selector].get_shape_ids())
                    + '.svg";\n'
                )
                s += "    set icon_z17;\n"
                s += "    icon-width: 16;\n"
                s += "}\n"
        return s

    def __len__(self) -> int:
        return len(self.icons)

    def sort(self) -> None:
        """Sort icon list."""
        self.icons = sorted(self.icons)


def draw_icons() -> None:
    """
    Draw all possible icon shapes combinations as grid in one SVG file and as
    individual SVG files.
    """
    out_path: Path = Path("out")
    icons_by_id_path: Path = out_path / "icons_by_id"
    icons_by_name_path: Path = out_path / "icons_by_name"

    for path in (out_path, icons_by_id_path, icons_by_name_path):
        path.mkdir(parents=True, exist_ok=True)

    scheme: Scheme = Scheme(Path("scheme/default.yml"))
    extractor: ShapeExtractor = ShapeExtractor(
        Path("icons/icons.svg"), Path("icons/config.json")
    )
    collection: IconCollection = IconCollection.from_scheme(scheme, extractor)
    icon_grid_path: Path = out_path / "icon_grid.svg"
    collection.draw_grid(icon_grid_path)
    logging.info(f"Icon grid is written to {icon_grid_path}.")
    collection.draw_icons(icons_by_id_path)
    collection.draw_icons(icons_by_name_path, by_name=True)
    logging.info(
        f"Icons are written to {icons_by_name_path} and {icons_by_id_path}."
    )


def write_mapcss() -> None:
    """
    Write MapCSS 0.2 scheme.
    """
    out_path: Path = Path("out")
    directory: Path = out_path / "roentgen_icons_mapcss"
    directory.mkdir(exist_ok=True)
    icons_with_outline_path: Path = directory / "icons"

    icons_with_outline_path.mkdir(parents=True, exist_ok=True)

    scheme: Scheme = Scheme(Path("scheme/default.yml"))
    extractor: ShapeExtractor = ShapeExtractor(
        Path("icons/icons.svg"), Path("icons/config.json")
    )
    collection: IconCollection = IconCollection.from_scheme(scheme, extractor)
    collection.draw_icons(
        icons_with_outline_path, color=Color("black"), outline=True
    )
    with Path("data/roentgen_icons_part.mapcss").open() as input_file:
        with (directory / "roentgen_icons.mapcss").open("w+") as output_file:
            for line in input_file.readlines():
                if line == "%CONTENT%\n":
                    output_file.write(collection.get_mapcss_selectors())
                else:
                    output_file.write(line)

    logging.info(f"MapCSS 0.2 scheme is written to {directory}.")
