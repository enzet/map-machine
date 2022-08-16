import sys
from pathlib import Path

from map_machine.element.grid import Grid
from map_machine.osm.osm_reader import Tags, OSMNode


def draw_node():
    pass


def draw_way():
    pass


def draw_area(tags: Tags, path: Path):
    grid: Grid = Grid(x_step=0.0003, show_credit=False, margin=0.5)
    node: OSMNode = grid.add_node({}, 0, 0)
    nodes: list[OSMNode] = [
        node,
        grid.add_node({}, 0, 1),
        grid.add_node({}, 1, 1),
        grid.add_node({}, 1, 0),
        node,
    ]
    grid.add_way(tags, nodes)

    grid.draw(path)


if __name__ == "__main__":
    tags: str = sys.argv[1]
    path: str = sys.argv[2]
    draw_area(
        {x.split("=")[0]: x.split("=")[1] for x in tags.split(",")}, Path(path)
    )
