**Röntgen** (or **Roentgen** when ASCII is preferred) project consists of

  * simple Python [OpenStreetMap](http://openstreetmap.org) renderer (see [usage](#usage), [renderer documentation](#map-generation)),
  * [set of CC-BY 4.0 icons](#icon-set) that can be used outside the project.

The idea behind the Röntgen project is to **show all the richness of the OpenStreetMap data**: to have a possibility to *display any map feature* represented by OpenStreetMap data tags by means of colors, shapes, and icons. Röntgen is created for OpenStreetMap contributors: to display all changes one made on the map even if they are small, and for users: to dig down into the map and find every detail that was mapped.

Unlike standard OpenStreetMap layers, **Röntgen is a playground for experiments** where one can easily try to support proposed tags, tags with little or even single usage, deprecated tags.

Röntgen is intended to be highly configurable, so it can generate precise but messy maps for OSM contributors as well as pretty and clean maps for OSM users, can use slow algorithms for some experimental features.

Usage
-----

To get SVG map, just run

```bash
python roentgen.py render -b <lon1>,<lat1>,<lon2>,<lat2>
```

(e.g. `python roentgen.py render -b 2.284,48.86,2.29,48.865`). It will automatically download OSM data and write output map to `out/map.svg`. For more options see [Map generation](#map-generation).

Map features
------------

Röntgen features:

  * detailed icons to display subtypes like [power tower design](#power-tower-design),
  * can display multiple icons for one entity to cover more features,
  * use color to visualize [`colour`](https://wiki.openstreetmap.org/wiki/Key:colour) and other features like plant types,
  * display [primitive 3D shapes](#levels) for buildings,
  * display [directions](#direction) with gradient sectors,
  * use width to display roads.

### Simple building shapes ###

Simple shapes for walls and shade in proportion to [`building:levels`](https://wiki.openstreetmap.org/wiki/Key:building:levels), [`building:min_level`](https://wiki.openstreetmap.org/wiki/Key:building:min_level), [`height`](https://wiki.openstreetmap.org/wiki/Key:height) and [`min_height`](https://wiki.openstreetmap.org/wiki/Key:min_height) values.

![3D buildings](doc/buildings.png)

### Trees ###

Visualization of tree leaf types (broadleaved or needleleaved) and genus or taxon by means of icon shapes and leaf cycles (deciduous or evergreen) by means of color.

![Trees](doc/trees.png)

### Viewpoint and camera direction ###

Visualize [`direction`](https://wiki.openstreetmap.org/wiki/Key:direction) tag for [`tourism`](https://wiki.openstreetmap.org/wiki/Key:tourism)=[`viewpoint`](https://wiki.openstreetmap.org/wiki/Tag:tourism=viewpoint) and [`camera:direction`](https://wiki.openstreetmap.org/wiki/Key:camera:direction) for [`man_made`](https://wiki.openstreetmap.org/wiki/Key:man_made)=[`surveillance`](https://wiki.openstreetmap.org/wiki/Tag:man_made=surveillance).

![Surveillance](doc/surveillance.png)

### Power tower design ###

Visualize [`design`](https://wiki.openstreetmap.org/wiki/Key:design) values used with [`power`](https://wiki.openstreetmap.org/wiki/Key:power)=[`tower`](https://wiki.openstreetmap.org/wiki/Tag:power=tower) tag.

![Power tower design](doc/power_tower_design.png)

![Power tower design](doc/power.png)

### Emergency ###

![Emergency](doc/emergency.png)

### Japanese map symbols ###

There are [special symbols](https://en.wikipedia.org/wiki/List_of_Japanese_map_symbols) appearing on Japanese maps.

![Japanese map symbols](doc/japanese.png)

Icon set
--------

If tag is drawable it is displayed using icon combination and colors. All icons are under [CC BY](http://creativecommons.org/licenses/by/4.0/) license. So, do whatever you want but give appropriate credit. Icon set is heavily inspired by [Maki](https://github.com/mapbox/maki), [Osmic](https://github.com/gmgeo/osmic), and [Temaki](https://github.com/ideditor/temaki) icon sets.

![Icons](doc/grid.png)

Feel free to request new icons via issues for whatever you want to see on the map. No matter how frequently the tag is used in OpenStreetMap since final goal is to cover all tags. However, common used tags have priority, other things being equal.

Generate icon grid and sets of individual icons with `python roentgen.py icons`. It will create `out/icon_grid.svg` file, and SVG files in `out/icons_by_id` directory where files are named using shape identifiers (e.g. `power_tower_portal_2_level.svg`) and in `icons_by_name` directory where files are named using shape names (e.g. `Röntgen portal two-level transmission tower.svg`). Files from the last directory are used in OpenStreetMap wiki (e.g. [`File:Röntgen_portal_two-level_transmission_tower.svg`](https://wiki.openstreetmap.org/wiki/File:R%C3%B6ntgen_portal_two-level_transmission_tower.svg)).

### Icon combination ###

Some icons can be combined into new icons.

![Bus stop icon combination](doc/bus_stop.png)

Map styles
----------

### All tags style ###

Options: `--show-missing-tags --overlap 0`.

Display as many OpenStreetMap data tags on the map as possible.

### Pretty style ###

Options: `--draw-captions main --level overground`.

Display only not overlapping icons and main captions.

### Creation time mode ###

Visualize element creation time with `--mode time`.

![Creation time mode](doc/time.png)

### Author mode ###

Every way and node displayed with the random color picked for each author with `--mode user-coloring`.

![Author mode](doc/user.png)

Installation
------------

Requirements: Python (at least 3.9).

To install all packages, run:

```bash
pip install -r requirements.txt
```

Map generation
--------------

Command: `render`.

There are simple Python renderer that generates SVG map from OpenStreetMap data. You can run it using:

```bash
python roentgen.py render \
    -b ${LONGITUDE_1},${LATITUDE_1},${LONGITUDE_2},${LATITUDE_2} \
    -o ${OUTPUT_FILE_NAME} \
    -s ${OSM_ZOOM_LEVEL}
```

Example:

```bash
python roentgen.py render -b 2.284,48.86,2.29,48.865
```

### Arguments ###

| Option | Description |
|---|---|
| `-i`, `--input` | input XML file name or names (if not specified, file will be downloaded using OpenStreetMap API) |
| `-o`, `--output` | output SVG file name, default value: `out/map.svg` |
| `-b`, `--boundary-box` | geo boundary box, use space before "-" if the first value is negative |
| `-s`, `--scale` | OSM zoom level (may not be integer), default value: 18 |
| `--cache` | path for temporary OSM files, default value: `cache` |
| `--labels` | label drawing mode: `no`, `main`, or `all`, default value: `main` |
| `--overlap` | how many pixels should be left around icons and text, default value: 12 |
| `--mode` | map drawing mode, default value: `normal` |
| `--seed` | seed for random |
| `--level` | display only this floor level |

Tile generation
---------------

Command: `tile`.

| Option | Description |
|---|---|
| `-c`, `--coordinates` | coordinates of any location inside the tile |
| `-s`, `--scale` | OSM zoom level, default value: 18 |
| `-t`, `--tile` | tile specification |
| `--cache` | path for temporary OSM files, default value: `cache` |
| `-b`, `--boundary-box` | construct the minimum amount of tiles that cover requested boundary box |

### Generate one tile ###

Specify tile coordinates:

```bash
python roentgen.py tile --tile ${OSM_ZOOM_LEVEL}/${X}/${Y}
```

or specify any geographical coordinates inside a tile:

```bash
python roentgen.py tile \
    --coordinates ${LATITUDE},${LONGITUDE} \
    --scale ${OSM_ZOOM_LEVEL}
```

Tile will be stored as SVG file `out/tiles/tile_<zoom level>_<x>_<y>.svg` and PNG file `out/tiles/tile_<zoom level>_<x>_<y>.svg`, where `x` and `y` are tile coordinates. `--scale` option will be ignored if it is used with `--tile` option.

Example:

```bash
python roentgen.py tile -c 55.7510637,37.6270761 -s 18
```

will generate SVG file `out/tiles/tile_18_158471_81953.svg` and PNG file `out/tiles/tile_18_158471_81953.png`.

### Generate a set of tiles ###

Specify boundary box to get the minimal set of tiles that covers the area:

```bash
python roentgen.py tile \
    --boundary-box ${LONGITUDE_1},${LATITUDE_1},${LONGITUDE_2},${LATITUDE_2} \
    --scale ${OSM_ZOOM_LEVEL}
```

Boundary box will be extended to the boundaries of the minimal tile set that covers the area, then it will be extended a bit more to avoid some artifacts on the edges rounded to 3 digits after the decimal point. Map with new boundary box coordinates will be written to the cache directory as SVG and PNG files. All tiles will be stored as SVG files `out/tiles/tile_<zoom level>_<x>_<y>.svg` and PNG files `out/tiles/tile_<zoom level>_<x>_<y>.svg`, where `x` and `y` are tile coordinates.

Example:

```bash
roentgen.py tile -b 2.361,48.871,2.368,48.875
```

will generate 36 PNG tiles at scale 18 from tile 18/132791/90164 all the way to 18/132796/90169 and two cached files `cache/2.360,48.869,2.370,48.877.svg` and `cache/2.360,48.869,2.370,48.877.png`.

MapCSS 0.2 generation
---------------------

Command: `mapcss`.

`python roentgen.py mapcss` will create `out/roentgen_mapcss` directory with simple MapCSS 0.2 scheme adding icons from Röntgen icon set to nodes and areas: `.mapcss` file and directory with icons.

To create MapCSS with only Röntgen icons run `python roentgen.py mapcss --no-ways`.

| Option | Description |
|---|---|
| `--icons` | add icons for nodes and areas, set by default |
| `--ways` | add style for ways and relations, set by default |
| `--lifecycle` | add icons for lifecycle tags; be careful: this will increase the number of node and area selectors by 9 times, set by default |

### Use Röntgen as JOSM map paint style ###

  * Open [JOSM](https://josm.openstreetmap.de/).
  * Go to <kbd>Preferences</kbd> → Third tab on the left → <kbd>Map Paint Styles</kbd>.
  * Active styles: press <kbd>+</kbd>.
  * URL / File: set path to `out/roentgen_mapcss/roentgen.mapcss`.
  * <kbd>Ok</kbd> → <kbd>OK</kbd>.

To enable / disable Röntgen map paint style go to <kbd>View</kbd> → <kbd>Map Paint Styles</kbd> → <kbd>Röntgen</kbd>.

