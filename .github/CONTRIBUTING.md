Contributing
============

Thank you for your interest in the Map Machine project. Since the primary goal of the project is to cover as many tags as possible, the project is crucially depend on contributions as OpenStreetMap itself.

Suggest a tag to support
------------------------

Please, create an issue with `icon` label.

Report a bug
------------

Please, create an issue with `bug` label.

Fix a typo in documentation
---------------------------

This action is not that easy as it supposed to be. We use [Moire](http://github.com/enzet/Moire) markup and converter to automatically generate documentation for GitHub, website, and [OpenStreetMap wiki](http://wiki.openstreetmap.org/). That's why editing Markdown files is not allowed. To fix a typo, open corresponding Moire file in `doc` directory (e.g. `doc/readme.moi` for `README.md`), modify it, and run `python map_machine/moire_manager.py`.

Modify the code
---------------

### First configure your workspace ###

Make sure you have Python 3.9 development tools. E.g., for Ubuntu, run `apt install python3.9-dev python3.9-venv`.

Activate virtual environment. E.g. for fish shell, run `source venv/bin/activate.fish`.

Install the project in editable mode:

```shell
pip install -e .
```

Install formatter, linter and test system: `pip install black flake8 mypy pytest pytest-cov`.

Be sure to enable Git hooks:

```shell
git config --local core.hooksPath data/githooks
```

If you are using PyCharm, you may want to set up user dictionary as well:


  * `cp data/dictionary.xml .idea/dictionaries/<user name>.xml`
  * in `.idea/dictionaries/<user name>.xml` change `%USERNAME%` to your username,
  * restart PyCharm if it is launched.

### Code style ###

We use [Black](http://github.com/psf/black) code formatter with maximum 80 characters line length for all Python files within the project. Reformat a file is as simple as `black -l 80 <file name>`. Reformat everything with `black -l 80 map_machine tests`.

If you create new Python file, make sure you add `__author__ = "<first name> <second name>"` and `__email__ = "<author e-mail>"` string variables.

