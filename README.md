

❗ This is special version of Map Machine without cairo dependency. ❗

This means, there is no PNG tile generation in this version of Map Machine (no `tile` and `server` commands are supported).

**Map Machine** project consists of


  * Python [OpenStreetMap](http://openstreetmap.org) renderer: SVG [map generation](#map-generation),
  * [Röntgen](#röntgen-icon-set) icon set: unique CC-BY 4.0 map icons.

The idea behind the Map Machine project is to **show all the richness of the OpenStreetMap data**: to have a possibility to display any map feature represented by OpenStreetMap data tags by means of colors, shapes, and icons. Map Machine is created both for map contributors: to display all changes one made on the map even if they are small, and for map users: to dig down into the map and find every detail that was mapped.

Unlike standard OpenStreetMap layers, **Map Machine is a playground for experiments** where one can easily try to support any unsupported tag, proposed tagging scheme, tags with little or even single usage, deprecated ones that are still in use.

Map Machine is intended to be highly configurable, so it can generate precise but messy maps for OSM contributors as well as pretty and clean maps for OSM users. It can also use some slow algorithms for experimental features.

See

  * [installation instructions](#installation),
  * [map features](#map-features),
  * [using Röntgen as JOSM style](#use-röntgen-as-josm-map-paint-style).

Usage example
-------------

```shell
map-machine render -b=2.284,48.860,2.290,48.865
```

will automatically download OSM data and write output SVG map of the specified area to `out/map.svg`. See [Map generation](#map-generation).

Röntgen icon set
----------------

The central feature of the project is Röntgen icon set. It is a set of monochrome 14 × 14 px pixel-aligned icons specially created for Map Machine project. Unlike the Map Machine source code, which is under MIT license, all icons are under [CC BY](http://creativecommons.org/licenses/by/4.0/) license. So, with the appropriate credit icon set can be used outside the project. Some icons can be used as emoji symbols.

All icons tend to support a common design style, which is heavily inspired by [Maki](https://github.com/mapbox/maki), [Osmic](https://github.com/gmgeo/osmic), and [Temaki](https://github.com/ideditor/temaki).

![Icons](doc/grid.svg)

Feel free to request new icons via issues for whatever you want to see on the map. No matter how frequently the tag is used in OpenStreetMap since the final goal is to cover all tags. However, commonly used tags have priority, other things being equal.

Generate icon grid and sets of individual icons with `map-machine icons`. It will update `doc/grid.svg` file, and create SVG files in `out/icons_by_id` directory where files are named using shape identifiers (e.g. `power_tower_portal_2_level.svg`) and in `icons_by_name` directory where files are named using shape names (e.g. `Röntgen portal two-level transmission tower.svg`). Files from the last directory are used in OpenStreetMap wiki (e.g. [`File:Röntgen_portal_two-level_transmission_tower.svg`](https://wiki.openstreetmap.org/wiki/File:R%C3%B6ntgen_portal_two-level_transmission_tower.svg)).

Map features
------------

### Extra icons ###

Map Machine uses icons to visualize tags for nodes and areas. But unlike other renderers, Map Machine can use more than one icon to visualize an entity and use colors to visualize [`colour`](https://wiki.openstreetmap.org/wiki/Key:colour) value or other entity properties (like [`material`](https://wiki.openstreetmap.org/wiki/Key:material) or [`genus`](https://wiki.openstreetmap.org/wiki/Key:genus)).

### Isometric building shapes ###

With `--buildings isometric` or `--buildings isometric-no-parts` (not set by default), buildings are drawn using isometric shapes for walls and shade in proportion to [`building:levels`](https://wiki.openstreetmap.org/wiki/Key:building:levels), [`building:min_level`](https://wiki.openstreetmap.org/wiki/Key:building:min_level), [`height`](https://wiki.openstreetmap.org/wiki/Key:height), and [`min_height`](https://wiki.openstreetmap.org/wiki/Key:min_height) values.

![3D buildings](doc/buildings.svg)

### Road lanes ###

To determine road width Map Machine uses the [`width`](https://wiki.openstreetmap.org/wiki/Key:width) tag value or estimates it based on the [`lanes`](https://wiki.openstreetmap.org/wiki/Key:lanes) value. If lane value is specified, it also draws lane separators. This map style is highly inspired by Christoph Hormann's post [Navigating the Maze](http://blog.imagico.de/navigating-the-maze-part-2/).

![Road lanes](doc/lanes.svg)

### Trees ###

Visualization of tree leaf types (broadleaved or needle-leaved) and genus or taxon by means of icon shapes and leaf cycles (deciduous or evergreen) by means of color.

![Trees](doc/trees.svg)

### Viewpoint and camera direction ###

[`direction`](https://wiki.openstreetmap.org/wiki/Key:direction) tag values for [`tourism`](https://wiki.openstreetmap.org/wiki/Key:tourism) = [`viewpoint`](https://wiki.openstreetmap.org/wiki/Tag:tourism=viewpoint) and [`camera:direction`](https://wiki.openstreetmap.org/wiki/Key:camera:direction) for [`man_made`](https://wiki.openstreetmap.org/wiki/Key:man_made) = [`surveillance`](https://wiki.openstreetmap.org/wiki/Tag:man_made=surveillance) are rendered with sectors displaying the direction and angle (15º if angle is not specified) or the whole circle for panorama view. Radial gradient is used for surveillance and inverted radial gradient is used for viewpoints.

![Surveillance](doc/surveillance.svg)

![Viewpoints](doc/viewpoints.svg)

### Power tower design ###

Visualize [`design`](https://wiki.openstreetmap.org/wiki/Key:design) values used with [`power`](https://wiki.openstreetmap.org/wiki/Key:power) = [`tower`](https://wiki.openstreetmap.org/wiki/Tag:power=tower) tag.

![Power tower design](doc/icons_power.svg)

![Power tower design](doc/power.svg)

### Colors ###

Map icons have [`colour`](https://wiki.openstreetmap.org/wiki/Key:colour) tag value if it is present, otherwise, icons are displayed with dark grey color by default, purple color for shop nodes, red color for emergency features, and special colors for natural features. Map Machine also takes into account [`building:colour`](https://wiki.openstreetmap.org/wiki/Key:building:colour), [`roof:colour`](https://wiki.openstreetmap.org/wiki/Key:roof:colour) and other `*:colour` tags, and uses [`colour`](https://wiki.openstreetmap.org/wiki/Key:colour) tag value to paint subway lines.

![Building colors](doc/colors.svg)

### Emergency ###

![Emergency](doc/icons_emergency.svg)

### Japanese map symbols ###

Japanese maps usually use [special symbols](https://en.wikipedia.org/wiki/List_of_Japanese_map_symbols) called *chizukigou* (地図記号) which are different from standard map symbols used in other countries. They can be enabled with `--country jp` option.

![Japanese map symbols](doc/icons_japanese.svg)

### Shape combination ###

One of the key features of Map Machine is constructing icons from the several shapes.

#### Masts ####

For [`man_made`](https://wiki.openstreetmap.org/wiki/Key:man_made) = [`mast`](https://wiki.openstreetmap.org/wiki/Tag:man_made=mast) distinguish types (communication, lighting, monitoring, and siren) and construction (freestanding or lattice, and using of guys) are rendered by combining 7 unique icon shapes.

![Mast types](doc/mast.svg)

#### Volcanoes ####

For [`natural`](https://wiki.openstreetmap.org/wiki/Key:natural) = [`volcano`](https://wiki.openstreetmap.org/wiki/Tag:natural=volcano) status (active, dormant, extinct, or unspecified) and type (stratovolcano, shield, or scoria) are rendered by combining 7 unique icon shapes.

![Volcano types](doc/volcano.svg)

Wireframe view
--------------

### Creation time mode ###

Visualize element creation time with `--mode time`.

![Creation time mode](doc/time.svg)

### Author mode ###

Every way and node displayed with the random color picked for each author with `--mode author`.

![Author mode](doc/author.svg)

Installation
------------

Requirements: Python 3.9.


  * Install [cairo 2D graphic library](https://www.cairographics.org/download/),
  * install [GEOS library](https://libgeos.org),
  * install Python packages with the command:

```shell
pip install git+https://github.com/enzet/map-machine@no-cairo
```

For more detailed instructions, see [instructions](doc/INSTALL.md).

Map generation
--------------

Command `render` is used to generate SVG map from OpenStreetMap data. You can run it using:

```shell
map-machine render \
    -b=<min longitude>,<min latitude>,<max longitude>,<max latitude> \
    -o=<output file name> \
    -z=<OSM zoom level> \
    <other arguments>
```

### Example ###

```shell
map-machine render \
    --boundary-box=2.284,48.860,2.290,48.865 \
    --output=out/esplanade_du_trocadéro.svg
```

will download OSM data to `cache/2.284,48.860,2.290,48.865.osm` and write an output SVG map of the specified area to `out/esplanade_du_trocadéro.svg`.

### Arguments ###

| Option | Description |
|---|---|
| <span style="white-space: nowrap;">`-i`</span>, <span style="white-space: nowrap;">`--input`</span> `<path>` | input XML file name or names (if not specified, file will be downloaded using OpenStreetMap API) |
| <span style="white-space: nowrap;">`-o`</span>, <span style="white-space: nowrap;">`--output`</span> `<path>` | output SVG file name, default value: `out/map.svg` |
| <span style="white-space: nowrap;">`-b`</span>, <span style="white-space: nowrap;">`--boundary-box`</span> `<lon1>,<lat1>,<lon2>,<lat2>` | geo boundary box; if the first value is negative, use `=` sign or enclose the value with quotes and use space before `-`, e.g. `-b=-84.752,39.504,-84.749,39.508` or `-b " -84.752,39.504,-84.749,39.508"` |
| <span style="white-space: nowrap;">`--cache`</span> `<path>` | path for temporary OSM files, default value: `cache` |
| <span style="white-space: nowrap;">`-z`</span>, <span style="white-space: nowrap;">`--zoom`</span> `<float>` | OSM zoom level, default value: 18.0 |
| <span style="white-space: nowrap;">`-c`</span>, <span style="white-space: nowrap;">`--coordinates`</span> `<latitude>,<longitude>` | coordinates of any location inside the tile; if the first value is negative, use `=` sign or enclose the value with quotes and use space before `-`, e.g. `-c=-84.752,39.504` or `-c " -84.752,39.504"` |
| <span style="white-space: nowrap;">`-s`</span>, <span style="white-space: nowrap;">`--size`</span> `<width>,<height>` | resulted image size |

plus [map configuration options](#map-options)

Map options
-----------

Map configuration options used by `render`:

| Option | Description |
|---|---|
| <span style="white-space: nowrap;">`--scheme`</span> `<id> or <path>` | scheme identifier (look for `<id>.yml` file) or path to a YAML scheme file, default value: `default` |
| <span style="white-space: nowrap;">`--buildings`</span> `<mode>` | building drawing mode: no, flat, isometric, isometric-no-parts, default value: `flat` |
| <span style="white-space: nowrap;">`--mode`</span> `<string>` | map drawing mode: normal, author, time, white, black, default value: `normal` |
| <span style="white-space: nowrap;">`--overlap`</span> `<integer>` | how many pixels should be left around icons and text, default value: 12 |
| <span style="white-space: nowrap;">`--labels`</span> `<string>` | label drawing mode: no, main, all, address, default value: `main` |
| <span style="white-space: nowrap;">`--level`</span> | display only this floor level, default value: `overground` |
| <span style="white-space: nowrap;">`--seed`</span> `<string>` | seed for random |
| <span style="white-space: nowrap;">`--tooltips`</span> | add tooltips with tags for icons in SVG files |
| <span style="white-space: nowrap;">`--country`</span> | two-letter code (ISO 3166-1 alpha-2) of country, that should be used for location restrictions, default value: `world` |
| <span style="white-space: nowrap;">`--ignore-level-matching`</span> | draw all map features ignoring the current level |
| <span style="white-space: nowrap;">`--roofs`</span> | draw building roofs, set by default |
| <span style="white-space: nowrap;">`--building-colors`</span> | paint walls (if isometric mode is enabled) and roofs with specified colors |
| <span style="white-space: nowrap;">`--show-overlapped`</span> | show hidden nodes with a dot |

MapCSS 0.2 generation
---------------------

Command `mapcss` is used to generate MapCSS scheme. `map-machine mapcss` will create `out/map_machine_mapcss` directory with simple MapCSS 0.2 scheme adding icons from Röntgen icon set to nodes and areas: `.mapcss` file and directory with icons.

To create MapCSS with Map Machine style also for ways and relations, run `map-machine mapcss --ways`.

| Option | Description |
|---|---|
| <span style="white-space: nowrap;">`--icons`</span> | add icons for nodes and areas, set by default |
| <span style="white-space: nowrap;">`--ways`</span> | add style for ways and relations |
| <span style="white-space: nowrap;">`--lifecycle`</span> | add icons for lifecycle tags; be careful: this will increase the number of node and area selectors by 9 times, set by default |

### Use Röntgen as JOSM map paint style ###


  * Run `map-machine mapcss`.
  * Open [JOSM](https://josm.openstreetmap.de/).
  * Go to <kbd>Preferences</kbd> → Third tab on the left → <kbd>Map Paint Styles</kbd>.
  * Active styles: press <kbd>+</kbd>.
  * URL / File: set path to `out/map_machine_mapcss/map_machine.mapcss`.

To enable/disable Map Machine map paint style go to <kbd>View</kbd> → <kbd>Map Paint Styles</kbd> → <kbd>Map Machine</kbd>.

#### Example ####

![JOSM example](doc/josm.png)

Example of using Röntgen icons on top of Mapnik style in JOSM. Map Paint Styles look like this:

  * ✓ Mapnik (true)
  * ✓ Map Machine

