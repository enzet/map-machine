"""OSM utility."""

from map_machine.osm.osm_reader import OSMNode, OSMWay


def is_cycle(nodes: list[OSMNode]) -> bool:
    """Check whether the way is a cycle or an area boundary."""
    return nodes[0] == nodes[-1]


def try_to_glue(
    nodes: list[OSMNode], other: list[OSMNode]
) -> list[OSMNode] | None:
    """Create new combined way if ways share endpoints."""
    if nodes[0] == other[0]:
        return list(reversed(other[1:])) + nodes
    if nodes[0] == other[-1]:
        return other[:-1] + nodes
    if nodes[-1] == other[-1]:
        return nodes + list(reversed(other[:-1]))
    if nodes[-1] == other[0]:
        return nodes + other[1:]
    return None


def glue(ways: list[OSMWay]) -> list[list[OSMNode]]:
    """Try to glue ways that share nodes.

    :param ways: ways to glue
    """
    result: list[list[OSMNode]] = []
    to_process: set[tuple[OSMNode, ...]] = set()

    for way in ways:
        if way.is_cycle():
            result.append(way.nodes)
        else:
            to_process.add(tuple(way.nodes))

    while to_process:
        nodes: list[OSMNode] = list(to_process.pop())
        glued: list[OSMNode] | None = None
        other_nodes: tuple[OSMNode, ...] | None = None

        for other_nodes in to_process:
            glued = try_to_glue(nodes, list(other_nodes))
            if glued is not None:
                break

        if glued is not None:
            if other_nodes is not None:
                to_process.remove(other_nodes)
            if is_cycle(glued):
                result.append(glued)
            else:
                to_process.add(tuple(glued))
        else:
            result.append(nodes)

    return result
