## 0.1.9

- Fix a problem with a mutable field (Philipp, [#153](https://github.com/enzet/map-machine/issues/153)).
- Add icon for `natural=human`.
- Add `--hide-credit` option.
- Make colors more configurable.

## 0.1.8

- Improve colors for indoor features ([#139](https://github.com/enzet/map-machine/issues/139)).
- Support empty scheme file ([#140](https://github.com/enzet/map-machine/issues/140)).
- Add icons for:
  - flags,
  - camp, fire, `tourism=camp_pitch` ([#144](https://github.com/enzet/map-machine/issues/144)).
- Support `tourism=artwork` for ways.
- Enhance argument processing ([#100](https://github.com/enzet/map-machine/issues/100)).
- Reuse icon for:
  - `traffic_sign=*`,
  - `parking=yes`,
  - `drinking_water=yes`,
  - `dog=yes`,
  - `shower=yes`,
  - `washing_machine=yes`.
- Fix style for golf features.
- Fix leading `-` issue in argument parsing.

## 0.1.7

_17 August 2022_

- Add icons for:
  - `shop=car_parts`, `shop=variety_store` ([#48](https://github.com/enzet/map-machine/issues/48)),
  - `natural=spring` ([#55](https://github.com/enzet/map-machine/issues/55)),
  - `tomb=pyramid`.
- Reuse icon for `shop=department_store` ([#48](https://github.com/enzet/map-machine/issues/48)).
- Fix style for `indoor=room` ([#139](https://github.com/enzet/map-machine/issues/139)).
- Redraw diving tower and fountain icons.
- Add `--scheme` option ([#140](https://github.com/enzet/map-machine/issues/140)).
- Rename `element` command to `draw` and change format.

## 0.1.6

_4 July 2022_

- Support `attraction=water_slide` ([#137](https://github.com/enzet/map-machine/issues/137)).
- Fix diving tower priority ([#138](https://github.com/enzet/map-machine/issues/138)); test `test_icons/test_diving_tower`.
- Add icon for `amenity=dressing_room` ([#135](https://github.com/enzet/map-machine/issues/135)).

## 0.1.5

_6 June 2022_

- Support `/` as a delimiter for coordinates.
- Fix `placement` tag processing ([#128](https://github.com/enzet/map-machine/issues/128)).
- Split way priority ([#125](https://github.com/enzet/map-machine/issues/125)).
- Fix typo in `motorcar=yes` ([#133](https://github.com/enzet/map-machine/issues/133)).

## 0.1.4

- Fix vending machine priority ([#132](https://github.com/enzet/map-machine/issues/132)).
- Allow duplicate ids in OSM data (Andrew Klofas, [#131](https://github.com/enzet/map-machine/issues/131)).

## 0.1.3

_2022.4_

- Add style for
  - `greenhouse_horticulture`,
  - `recreation_ground`,
  - `landuse=village_green` ([#129](https://github.com/enzet/map-machine/issues/129)).
- Add style for `railway=construction` ([#125](https://github.com/enzet/map-machine/issues/125)).
- Fix electricity shape.
- Support color for default icon.
- Fix waterways priority ([#126](https://github.com/enzet/map-machine/issues/126)).
- Show small dot for overlapped icons ([#121](https://github.com/enzet/map-machine/issues/121)).

## 0.1.2

_2022.2.3_

- Add icons for:
  - `highway=traffic_mirror`.
  - Japanese symbol for health center.
  - Japanese symbol for police station.
- Fix beach shape.
- Copy license file to icon collection ([#98](https://github.com/enzet/map-machine/issues/98)).
- Wrap temporarily matrix creation ([#114](https://github.com/enzet/map-machine/issues/114)).

## 0.1.1

_2022.2.2_

- Add icon for `playground=sandpit`.
- Fix probe, lunokhod shape, solar panel.
- Reuse icon for `shop=antiques`.
- Add `--building-colors` option.
- More precise area detection.
- Support `area=yes` for roads.

## 0.1.0

_2022.2.1_

- Add icons for:
  - `tourism=apartment`,
  - `tourism=guest_house`,
  - `amenity=courthouse`,
  - `barrier=chain`,
  - mazes,
  - `leisure=escape_game`.
- Reuse icon for `craft=jeweller`.
- Redraw icon for swimming area.
- Add support for Docker (Sven Fischer).
- Fix bed shape.
- Remove wildcard matching for `tourism=*`.
- For buildings:
  - Support roof and walls colors.
  - Fix walls order.

## 0.0.35

_2022.1.2_

- Add icons for:
  - `advertising=column`,
  - `building=houseboat`,
  - `building=container`,
  - `building=construction`.
- Enhance style for `man_made=embankment`, `natural=cliff` ([#107](https://github.com/enzet/map-machine/issues/107)).
- Reuse icon for `amenity=gym`.
- Fix placement offset ([#83](https://github.com/enzet/map-machine/issues/83)).
- Add color for grass.
- Support roof drawing.
- Change bus shape.
- Fix outers and inners computing for areas.
- Add credits to the map ([#103](https://github.com/enzet/map-machine/issues/103)).
- For buildings under construction: fix detection and representation ([#105](https://github.com/enzet/map-machine/issues/105)).

## 0.0.34

_2022.1.1_

- Add icons for normal, gabled, and skillion roof for one-story, two-story, three-story, four-story, and five-story apartments,
  - circles.
- Reuse icons for
  - `office=yes`,
  - `railway=railway_crossing`,
  - `shop=medical_supply`,
  - `craft=shoemaker`,
  - `amenity=social_facility`,
  - `diplomatic=embassy`,
  - `shop=farm`, portals.
  - deprecated `building=entrance`.
- Fix shapes for anchor, building, apartments, fix shape positions, charging station.
- Support wall colors.

## 0.0.33

_2021.12.2_

- Add icons for:
  - `shop=travel_agency`,
  - `shop=optician`,
  - `tank_trap=dragon_teeth`,
  - `tank_trap=czech_hedgehog`,
  - washing machine ([#48](https://github.com/enzet/map-machine/issues/48)),
  - bench with sculpture.
- Reuse icon for:
  - cupcake ([#48](https://github.com/enzet/map-machine/issues/48)),
  - `tank_trap=toblerone`,
  - `artwork_type=stone`,
  - `shop=photography`.
- Fix tyre, wind turbine, buoy, diving tower shape.
- Fix icon positions.

## 0.0.32

_2021.12.1_

- Add icons for:
  - `memorial=bench`,
  - `shop=`: `florist`, `furniture`,
  - `amenity=marketplace`,
  - `tower:type=minaret`,
  - `historic=`: `fort`, `wayside_shrine`, `archeological_site` ([#50](https://github.com/enzet/map-machine/issues/50)),
  - `natural=saddle`,
  - dome wall CCTV and dome ceiling CCTV.
- Reuse icons for:
  - `tower:type=watchtower` ([#57](https://github.com/enzet/map-machine/issues/57)),
  - dish towers ([#57](https://github.com/enzet/map-machine/issues/57)).
- Redraw CCTV, diving platform, Pac-Man, rocking horse shape.
- Add style for `landuse=farmyard`.

## 0.0.31

_2021.11.3_

- Reuse icons for
  - `shop=bag`, `shop=tyres` ([#48](https://github.com/enzet/map-machine/issues/48)).
  - `barrier=log` ([#54](https://github.com/enzet/map-machine/issues/54)).
- Add icons for
  - `historic=monument` ([#50](https://github.com/enzet/map-machine/issues/50)).
  - `man_made=stupa`.
  - `man_made=tower` + `tower:type=diving`, and for + `tower:platforms=`: `2`, `3`, `4`.
- Fix icon shape for eruption, recycling container.
- Fix icon vertical positions.

## 0.0.30

_2021.11.2_

- Add icons for:
  - `historic=wayside_cross` ([#57](https://github.com/enzet/map-machine/issues/57)).
  - `man_made=obelisk` ([#50](https://github.com/enzet/map-machine/issues/50)).
  - `crane:type=travel_lift`.
  - `crane:type=portal_crane`.
  - `crane:type=gantry_crane`.
  - communication tower ([#57](https://github.com/enzet/map-machine/issues/57)).
  - `tower:type=`: `siren`, `monitoring`.
- Reuse icons for
  - `power=heliostat`,
  - `recycling:`:
    - `green_waste`, `books`, `wood`, `organic`, `tyres`, `toys`, `glass`, `glass_bottles:colour`,
    - `cartons`, `beverage_cartons`, `tetrapak`, `verre`,
    - `clothes`, `shoes`, `bags`, `paper`, `paper_packaging`, `newspaper`, `magazines`.
  - `shop=`: `cosmetics`, `greengrocer`, `newsagent`, `toys`.
  - `man_made=crane` + `crane:type=floor-mounted_crane`, `tower_crane`.
- Add white and black modes.

## 0.0.29

_2021.11.1_

- Add icons for:
  - `telescope:type=optical` ([#57](https://github.com/enzet/map-machine/issues/57)).
  - `man_made=crane` ([#57](https://github.com/enzet/map-machine/issues/57)).
- Fix waste shapes.
- Split exchange icon.
- Support `placement` tag ([#83](https://github.com/enzet/map-machine/issues/83)):
  - add initial support,
  - display transition as connection,
- Fix address processing ([#67](https://github.com/enzet/map-machine/issues/67)).
