## 0.1.7

_17 August 2022_

- __Add icons__ for:
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
