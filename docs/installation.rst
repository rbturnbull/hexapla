.. include:: ../README.rst
   :start-after: start-installation
   :end-before: end-installation

To upgrade to the latest release, run ``pip install --upgrade hexapla``.

To build a site on GitHub instead of your own computer, you do not need to install anything: the
:doc:`GitHub Action <github-pages>` installs Hexapla itself.

Hexapla's dependencies are installed with it. The SCSS compiler (libsass) comes as a wheel for Linux, macOS and
Windows, so nothing needs to be compiled.

The tools that make the parses and alignments, :doc:`MCParser and MCAligner <generating>`, are installed separately
and are optional.
