"""Getting OpenStreetMap data from the web."""

from __future__ import annotations

import gzip
import hashlib
import logging
import time
from dataclasses import dataclass
from textwrap import dedent
from typing import TYPE_CHECKING

import urllib3

if TYPE_CHECKING:
    from pathlib import Path

    from map_machine.geometry.bounding_box import BoundingBox
    from map_machine.osm.osm_reader import OSMData

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)

SLEEP_TIME_BETWEEN_REQUESTS: float = 2.0
MAX_OSM_MESSAGE_LENGTH: int = 500
OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"

DEFAULT_OVERPASS_FILTER: str = dedent(
    """
    (
        way["building"];
        way["highway"];
        way["natural"="water"];
        way["waterway"];
        way["natural"="wood"];
        way["landuse"="forest"];
        relation["natural"="water"];
        relation["landuse"="forest"];
    );
    (._;>;);
    out body;
    """
)


@dataclass
class NetworkError(Exception):
    """Failed network request."""

    message: str


def get_osm(
    bounding_box: BoundingBox, cache_file_path: Path, *, to_update: bool = False
) -> str:
    """Download OSM data from the web or get it from the cache.

    :param bounding_box: borders of the map part to download
    :param cache_file_path: cache file to store downloaded OSM data
    :param to_update: update cache files
    """
    if not to_update and cache_file_path.is_file():
        with cache_file_path.open(encoding="utf-8") as output_file:
            return output_file.read()

    content: bytes = get_data(
        "https://api.openstreetmap.org/api/0.6/map",
        {"bbox": bounding_box.get_format()},
    )

    # Try to decompress gzip content if needed.
    try:
        if content.startswith(b"\x1f\x8b"):  # gzip magic header.
            content = gzip.decompress(content)
    except (gzip.BadGzipFile, OSError) as error:
        logger.warning("Cannot decompress OSM data: %s.", error)

    if not content.startswith(b"<"):
        if len(content) < MAX_OSM_MESSAGE_LENGTH:
            message = "Cannot download data: `" + content.decode("utf-8") + "`."
            raise NetworkError(message)

        message = "Cannot download data."
        raise NetworkError(message)

    with cache_file_path.open("bw+") as output_file:
        output_file.write(content)

    return content.decode("utf-8")


def get_data(address: str, parameters: dict[str, str]) -> bytes:
    """Construct a URL with parameters and fetch its content.

    :param address: URL without parameters
    :param parameters: URL parameters
    :return: connection descriptor
    """
    logger.info("Getting %s...", address)
    headers = {
        "User-Agent": "map-machine/1.0",
        # Disable compression to avoid gzip issues.
        "Accept-Encoding": "identity",
    }
    pool_manager: urllib3.PoolManager = urllib3.PoolManager()
    urllib3.disable_warnings()

    try:
        result = pool_manager.request(
            "GET", address, fields=parameters, headers=headers
        )
    except urllib3.exceptions.MaxRetryError as error:
        message: str = "Cannot download data: too many attempts."
        raise NetworkError(message) from error

    pool_manager.clear()
    time.sleep(SLEEP_TIME_BETWEEN_REQUESTS)
    return result.data


def find_incomplete_relations(osm_data: OSMData) -> list[int]:
    """Find relations that have member ways missing from the data.

    :param osm_data: parsed OSM data
    :return: list of relation IDs with missing member ways
    """
    incomplete: list[int] = []
    for relation in osm_data.relations.values():
        if relation.tags.get("natural") != "water":
            continue
        if relation.members is None:
            continue
        for member in relation.members:
            if member.type_ == "way" and member.ref not in osm_data.ways:
                incomplete.append(relation.id_)
                break
    return incomplete


def get_overpass_relations(
    relation_ids: list[int], cache_path: Path
) -> bytes | None:
    """Download complete relation data from Overpass API.

    Fetches full geometry (ways and nodes) for the given relation IDs.
    Results are cached to avoid repeated downloads.

    :param relation_ids: list of relation IDs to fetch
    :param cache_path: directory for caching responses
    :return: response bytes or None on failure
    """
    ids_str: str = ",".join(str(i) for i in sorted(relation_ids))
    ids_hash: str = hashlib.sha256(ids_str.encode()).hexdigest()[:12]
    cache_file: Path = cache_path / f"overpass_relations_{ids_hash}.json"

    if cache_file.is_file():
        logger.info("Using cached Overpass data from `%s`.", cache_file)
        return cache_file.read_bytes()

    query: str = (
        f"[out:json][timeout:60]; rel(id:{ids_str}); (._;>;); out body;"
    )
    logger.info("Querying Overpass API for %d relations...", len(relation_ids))

    try:
        content: bytes = get_data(OVERPASS_API_URL, {"data": query})
    except NetworkError:
        logger.warning("Failed to download data from Overpass API.")
        return None

    if not content or not content.strip().startswith(b"{"):
        logger.warning("Unexpected Overpass API response.")
        return None

    cache_file.write_bytes(content)
    return content


def get_osm_overpass(
    bounding_box: BoundingBox,
    cache_file_path: Path,
    query: str | None = None,
    *,
    to_update: bool = False,
) -> str:
    """Download OSM data from the Overpass API.

    Uses a simplified filter query to fetch only major map features, which
    avoids failures when the standard OSM API returns too much data.

    :param bounding_box: borders of the map part to download
    :param cache_file_path: cache file to store downloaded OSM data
    :param query: custom Overpass query with ``{{bbox}}`` placeholder; if None,
        the default filter is used
    :param to_update: update cache files
    """
    if not to_update and cache_file_path.is_file():
        with cache_file_path.open(encoding="utf-8") as output_file:
            return output_file.read()

    box: str = bounding_box.get_overpass_format()

    if query is not None:
        full_query = query.replace("{{bbox}}", box)
    else:
        full_query = f"[out:xml][bbox:{box}];\n{DEFAULT_OVERPASS_FILTER}"

    logger.info("Querying Overpass API for bounding box %s...", box)

    try:
        content: bytes = get_data(OVERPASS_API_URL, {"data": full_query})
    except NetworkError:
        logger.warning("Failed to download data from Overpass API.")
        raise

    if not content or not content.strip().startswith(b"<"):
        if len(content) < MAX_OSM_MESSAGE_LENGTH:
            message = (
                "Unexpected Overpass API response: `"
                + content.decode("utf-8")
                + "`."
            )
        else:
            message = "Unexpected Overpass API response."
        raise NetworkError(message)

    with cache_file_path.open("bw+") as output_file:
        output_file.write(content)

    return content.decode("utf-8")
