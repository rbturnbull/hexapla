Python API
==========

The command line covers most uses, but a project can also be loaded and built from Python:

.. code-block:: python

    from hexapla.config import load_config
    from hexapla.corpus import load_project
    from hexapla.build import build_site

    project = load_project(load_config("project-config.yaml"))
    for pair in project.pairs:
        print(pair.title, len(pair.verses), pair.problems)
    build_site(project, "site")

Config
------

.. automodule:: hexapla.config
   :members: Config, Theme, Manuscript, Alignment, load_config, ConfigError

Loading a project
-----------------

.. automodule:: hexapla.corpus
   :members: load_project, Project, Witness, AlignedPair, Verse, CorpusError

Building
--------

.. autofunction:: hexapla.build.build_site

.. autoclass:: hexapla.build.OutputDirError

.. autofunction:: hexapla.theme.compile_css

Reading files
-------------

.. autofunction:: hexapla.transcription.read_transcription

.. autofunction:: hexapla.conllu.read_conllu

.. autofunction:: hexapla.links.read_links
