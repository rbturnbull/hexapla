.. include:: ../README.rst
   :start-after: start-usage
   :end-before: end-usage

What ``validate`` reports
-------------------------

``hexapla validate`` reads every file the config names and prints a table of the manuscripts and the alignments:

.. code-block:: text

    ──────────────────────── BICROSS Navigator  · Hexapla ────────────────────────
    Manuscripts

     Manuscript     Name          Language   TEI file          Sentences
     ─────────────────────────────────────────────────────────────────────
     bezae-greek    Codex Bezae   Greek      Bezae-Greek.xml          31
     bezae-latin    Codex Bezae   Latin      Bezae-Latin.xml          31

    Alignments

     Alignment   Title         Languages     Verses   Links   Probable   Warnings
     ──────────────────────────────────────────────────────────────────────────────
     bezae       Codex Bezae   Greek–Latin       31     536         14          —

    ✓ All files are valid

There are two kinds of problem:

**Errors** stop the build, because the site could not show the files correctly. They are listed together, each with
the file to fix:

- a config entry that is missing, misspelt, or names a file that does not exist;
- a TEI file without a language (``<text xml:lang="...">``);
- a verse number used by more than one ``<ab>`` in a TEI file (a verse split across pages is fine when its parts are
  marked ``part="I"`` ... ``part="F"``);
- a ``sent_id`` used twice in a CoNLL-U file, or two parses with no ``sent_id`` in common.

**Warnings** (``⚠``) are listed, and the site is still built: a sentence in only one of the two parses, a link to a
word that does not exist, or a ``sent_id`` in the links file that is not in both parses.

Hexapla never works around a mistake in a file: fix the file, and run ``validate`` again.

Building
--------

``hexapla build`` writes the site to the ``--output`` folder (``site`` by default) and ends with a summary:

.. code-block:: text

    ✓ Built 10 alignments and 20 manuscripts (6,653 pages, 93.9 MB, 4.1 s) → site

Each build replaces the output folder completely. To keep you from losing anything, Hexapla only replaces a folder
that is empty or that it built itself (it leaves a ``.hexapla`` file there).
