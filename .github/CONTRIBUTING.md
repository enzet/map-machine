Contributing
============

Thank you for your interest in the Röntgen project. Since the primary goal of the project is to cover as many tags as possible, the project is crucially depend on contributions as OpenStreetMap itself.

Suggest a tag to support
------------------------

Please, create an issue with `icon` label.

Report a bug
------------

Please, create an issue with `bug` and `generator` labels.

Modify the code
---------------

First of all, configure your workspace.

  * Install formatter, linter and test system: `pip install black flake8 pytest`.

### Code style ###

We use [Black](http://github.com/psf/black) code formatter with maximum 80 characters line lenght for all Python files within the project. Reformat a file is as simple as `black -l 80 <file name>`.

If you create new Python file, make sure you add `__author__ = "<first name> <second name>"` and `__email__ = "<author e-mail>"` string variables.
