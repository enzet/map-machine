<!--
    This is generated file.
    Do not edit it manually, edit the Moire source file instead.
-->

Contributing
============

Thank you for your interest in the Map Machine project. Since the primary goal of the project is to cover as many tags as possible, the project is crucially depend on contributions as OpenStreetMap itself.

Modify the code
---------------

❗ **IMPORTANT** ❗ Before committing please enable Git hooks:

```shell
git config --local core.hooksPath data/githooks
```

This will allow you to automatically check your commit message and code before committing and pushing changes. This will crucially speed up pull request merging and make Git history neat and uniform.

### First configure your workspace ###

Make sure you have Python 3.9 development tools. E.g., for Ubuntu, run `apt install python3.9-dev python3.9-venv`.

Activate virtual environment. E.g. for fish shell, run `source venv/bin/activate.fish`.

Install the project in editable mode:

```shell
pip install -e .
```

Install formatter, linter and test system: `pip install black flake8 mypy pytest pytest-cov`.

If you are using PyCharm, you may want to set up user dictionary as well:


  * `cp data/dictionary.xml .idea/dictionaries/<user name>.xml`
  * in `.idea/dictionaries/<user name>.xml` change `%USERNAME%` to your username,
  * restart PyCharm if it is launched.

### Code style ###

We use [Black](http://github.com/psf/black) code formatter with maximum 80 characters line length for all Python files within the project. Reformat a file is as simple as `black -l 80 <file name>`. Reformat everything with `black -l 80 map_machine tests`.

If you create new Python file, make sure you add `__author__ = "<first name> <second name>"` and `__email__ = "<author e-mail>"` string variables.

### Commit message format ###

The project uses commit messages that starts with a verb in infinitive form with first letter in uppercase, ends with a dot, and is not longer than 50 characters. E.g. `Add new icon.` or `Fix labels.`

If some issues or pull requests are referenced, commit message should starts with prefix such as `PR #123: `, `Issue #42: `, or `Fix #13: ` with the next letter in lowercase. E.g. `PR #123: refactor elements.` or `Issue #42: add icon for natural=tree.`

Suggest a tag to support
------------------------

Please, create an issue describing how you would like the feature to be visualized.

Report a bug
------------

Please, create an issue describing the current behavior, expected behavior, and environment (most importantly, the OS version and Python version if it was not the recommended one).

Fix a typo in documentation
---------------------------

This action is not that easy as it supposed to be. We use [Moire](http://github.com/enzet/Moire) markup and converter to automatically generate documentation for GitHub, website, and [OpenStreetMap wiki](http://wiki.openstreetmap.org/). That's why editing Markdown files is not allowed. To fix a typo, open corresponding Moire file in `doc` directory (e.g. `doc/readme.moi` for `README.md`), modify it, and run `python map_machine/moire_manager.py`.

