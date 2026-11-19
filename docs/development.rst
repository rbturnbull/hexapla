.. include:: ../README.rst
   :start-after: start-development
   :end-before: end-development

Principles
----------

- **Tests first, and 100% coverage.** ``pytest`` fails below 100%. ``tests/data/project/`` is a small complete
  project that the end-to-end tests build.
- **The TEI is the source of truth for manuscripts**, and the config stays minimal: a field is only added to the
  config when the information cannot live in the TEI, CoNLL-U or links files.
- **No workarounds for broken data.** Validation names the file to fix.
- **Elegant terminal output** with `rich <https://rich.readthedocs.io/>`_: tables, a panel for errors, and a summary
  line.

Layout
------

=============================  ==================================================================================
``hexapla/config.py``          The config file, read into pydantic models.
``hexapla/transcription.py``   Reading TEI headers and bodies.
``hexapla/conllu.py``          Reading CoNLL-U.
``hexapla/links.py``           Reading links (JSON Lines and Ugarit YAML).
``hexapla/corpus.py``          Loading a project: witnesses and aligned pairs.
``hexapla/analysis.py``        Statistics, lexicon, insights and the review queue.
``hexapla/theme.py``           Compiling the SCSS.
``hexapla/build.py``           Writing the pages.
``hexapla/main.py``            The command line.
``hexapla/templates/``         Jinja2 templates.
``hexapla/static/``            JavaScript, the logo, and the SCSS (with Bootstrap's).
``action.yml``                 The GitHub Action.
=============================  ==================================================================================
