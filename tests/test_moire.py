"""
Test Moire extension for Map Machine.
"""
from map_machine.doc.moire_manager import MapMachineHTML


def test_osm() -> None:
    convertor: MapMachineHTML = MapMachineHTML()

    assert convertor.convert("\\osm {natural}", wrap=False) == (
        '<a href="https://wiki.openstreetmap.org/wiki/Key:natural">'
        "<tt>natural</tt></a>"
    )

    assert convertor.convert("\\osm {natural=tree}", wrap=False) == (
        '<a href="https://wiki.openstreetmap.org/wiki/Key:natural">'
        "<tt>natural</tt></a>="
        '<a href="https://wiki.openstreetmap.org/wiki/Tag:natural=tree">'
        "<tt>tree</tt></a>"
    )
