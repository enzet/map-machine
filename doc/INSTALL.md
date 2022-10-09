<!--
    This is generated file.
    Do not edit it manually, edit the Moire source file instead.
-->

Install
-------

Map Machine requires [Python](https://www.python.org) 3.9, [pip](https://pip.pypa.io/en/stable/installation/), and two libraries:


  * [cairo 2D graphic library](https://www.cairographics.org/download/),
  * [GEOS library](https://libgeos.org).

### Python 3.8 support ###

If you want to use Python 3.8, there is a special branch `python3.8`. It has support for all features, but is likely to be updated less frequently than the `main`. Installation command is

```shell
pip install git+https://github.com/enzet/map-machine@python3.8
```

### Without cairo ###

If you have any problems installing cairo library or cairo-related Python dependencies, but do not plan to generate PNG tiles (only SVG images), you may try special Map Machine branch `no-cairo` without cairo dependency. Installation command is

```shell
pip install git+https://github.com/enzet/map-machine@no-cairo
```

Installation examples
---------------------

### Ubuntu ###

```shell
apt install libcairo2-dev libgeos-dev
pip install git+https://github.com/enzet/map-machine
```

### macOS ###

```shell
brew install cairo geos
pip install git+https://github.com/enzet/map-machine
```

