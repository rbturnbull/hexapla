.. image:: _static/hexapla-banner.svg
   :alt: Hexapla: read between the columns
   :width: 560px
   :align: center

.. include:: ../README.rst
   :start-after: start-summary
   :end-before: end-summary

A Hexapla *project* is a folder with a YAML config file, the TEI transcriptions of its manuscripts, a CoNLL-U parse
of each text, and the word links between pairs of texts. ``hexapla build`` turns it into a site you can put on any
web server, or publish on GitHub Pages with the Hexapla GitHub Action.

Start with :doc:`installation` and :doc:`quickstart`, then see :doc:`project` for what each file needs and
:doc:`generating` for making the parses and links with MCParser and MCAligner.

.. toctree::
   :maxdepth: 2
   :caption: Guide
   :hidden:

   installation
   quickstart
   project
   generating
   theming
   site
   github-pages

.. toctree::
   :maxdepth: 1
   :caption: Reference
   :hidden:

   _generated/cli
   api
   development
