The website
===========

``hexapla build`` writes a static site: plain HTML, CSS and JavaScript that any web server can host. All links are
relative, so it works in a sub-folder too, such as ``https://<user>.github.io/<repository>/``.

Pages
-----

Home
    The alignments, grouped by language pair, with their verses, links and the share of words aligned.

Manuscript (``manuscripts/<id>/``)
    A manuscript as described in its TEI header: shelfmark, date, identifiers, transcribers and licences, with a
    summary of the transcription (folios, words, corrections, lacunae) and a link to download the TEI file.

Alignment overview (``alignments/<id>/``)
    Statistics for the pair, a chart of every verse, how words correspond (1:1, 1:n...), and a sortable table of
    the verses.

Verse (``alignments/<id>/<verse>/``)
    The two texts, then three views of their alignment:

    - **Trees & alignment**: the dependency tree of each text, with the links between them;
    - **Interlinear**: each word with its lemma and the words it is linked to;
    - **Alignment matrix**: a grid of the two texts' words, where reordering shows as links off the diagonal.

    The side panel shows the verse's statistics and what the transcriptions record for it. The arrow keys move
    between verses, and ``1``, ``2`` and ``3`` switch views; the view is kept when you change verse.

Lexicon (``alignments/<id>/lexicon/``)
    Every lemma with its translation equivalents, searchable in both directions. A word linked to several words
    counts once, with those words together ("in Christus"). Each lemma has its own page of examples.

Translation insights (``alignments/<id>/insights/``)
    How parts of speech, case, tense, voice and other features carry over between the languages, and what each
    text leaves out.

Review queue (``alignments/<id>/review/``)
    The least confident links and parses, to check first.

About (``about/``)
    The theme's about page, if it has one.

Every page ends with a footer that credits the transcribers and lists the licences that apply, with a small
"Built with Hexapla" logo linking to Hexapla on GitHub.

Files
-----

.. code-block:: text

    site/
      index.html                                  home page
      about/index.html                            about page
      css/hexapla.css                             styles, compiled with the theme
      js/, img/                                   scripts, the logo and the favicon
      manuscripts/<ms>/index.html                 a manuscript
      manuscripts/<ms>/<file>.xml                 its TEI transcription
      alignments/<id>/index.html                  overview
      alignments/<id>/lexicon/index.html          lexicon
      alignments/<id>/insights/index.html         translation insights
      alignments/<id>/review/index.html           review queue
      alignments/<id>/<verse>/index.html          verse page
      alignments/<id>/<language>/<lemma>/         lemma page

To look at a site on your own computer, serve its folder (opening ``index.html`` directly does not load everything):

.. code-block:: bash

    python -m http.server --directory site 8000
