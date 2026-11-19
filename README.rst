=======
Hexapla
=======

Static websites for reading and exploring word-aligned manuscript texts.

Named after Origen's Hexapla, which set versions of the Old Testament side by side in columns, Hexapla builds a
site from a project's TEI transcriptions, CoNLL-U parses (mcparser) and alignment links (mcaligner): verse-by-verse
reading with dependency trees, an interlinear and an alignment matrix, a bilingual lexicon, translation insights and
a review queue, and a page for each manuscript described from its TEI header.

Installation
============

.. code-block:: bash

    pip install git+https://github.com/rbturnbull/hexapla

Usage
=====

A project is a folder (usually its own repository) with a config file. Paths are relative to the config file:

.. code-block:: yaml

    theme:
      name: BICROSS Navigator
      logo: theme/logo.svg            # optional: the Hexapla logo by default
      variables: theme/variables.scss # optional: Bootstrap variables (.scss) or extra CSS (.css)
      about: theme/about.md           # optional: an about page
      licence: CC-BY-NC-SA-4.0        # SPDX id: the site, parses and links

    manuscripts:
      bezae-greek:
        tei: bezae/Bezae-Greek.xml
        parsing: bezae/Bezae-Greek-John20.conllu
      bezae-latin:
        tei: bezae/Bezae-Latin.xml
        parsing: bezae/Bezae-Latin-John20.conllu
        parsing_licence: CC-BY-4.0    # optional: overrides the site licence for this parse

    alignments:
      bezae:
        name: Codex Bezae             # optional: from the TEI's <msName> by default
        manuscripts: [bezae-greek, bezae-latin]   # the links file's source, then target
        links: bezae/Bezae-John20-aligned.jsonl
        licence: CC-BY-4.0            # optional: overrides the site licence for these links

Everything about a manuscript comes from the TEI header of its transcription (TEI P5, chapter 10):
the language (``<text xml:lang>``, required), ``msName``, the shelfmark, ``altIdentifier`` numbers
(``GA``, ``VL``, ``TM`` for Trismegistos), ``origDate``, the ``msContents/summary``, the transcribers and the licence.
A TEI file's own licence overrides the site's for that transcription.

.. code-block:: bash

    hexapla validate project-config.yaml
    hexapla build project-config.yaml --output site

GitHub Pages
============

Build and deploy a project's site on every push:

.. code-block:: yaml

    name: pages
    on: { push: { branches: [main] }, workflow_dispatch: {} }
    permissions: { contents: read, pages: write, id-token: write }
    concurrency: { group: pages, cancel-in-progress: false }
    jobs:
      deploy:
        runs-on: ubuntu-latest
        environment: { name: github-pages, url: "${{ steps.site.outputs.page_url }}" }
        steps:
          - uses: actions/checkout@v4
          - id: site
            uses: rbturnbull/hexapla@main
            with:
              config: project-config.yaml

Set the repository's Pages source to "GitHub Actions". The action installs Hexapla from its own checkout, builds the
site and deploys it; ``deploy: "false"`` only builds it (e.g. to check a pull request).

Development
===========

.. code-block:: bash

    pip install -e . pytest pytest-cov
    pytest            # 100% coverage is required

Author
======

Robert Turnbull (Melbourne Data Analytics Platform, University of Melbourne)
