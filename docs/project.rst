Project files
=============

A project needs four kinds of file. Hexapla reads the config, then for each manuscript its TEI transcription and
CoNLL-U parse, then for each alignment its links file::

    bicross-navigator/
      bicross-navigator-config.yaml
      theme/                         logo, variables.scss, about.md
      bezae/
        Bezae-Greek.xml              TEI transcriptions
        Bezae-Latin.xml
        Bezae-Greek-John20.conllu    CoNLL-U parses
        Bezae-Latin-John20.conllu
        Bezae-John20-aligned.jsonl   word links between the two parses

The folder layout is up to you: every path in the config is relative to the config file.

The config file
---------------

The config has three sections. Manuscripts and alignments are keyed by an id, which is used in the site's URLs
(``manuscripts/<id>/`` and ``alignments/<id>/``), so it may only use letters, digits, ``.``, ``_`` and ``-``.
Misspelt or unknown keys are reported as errors.

``theme``
    All optional. See :doc:`theming`.

    =============  ==========================================================================================
    ``name``       The site's name, shown in the title bar and on the home page (default ``Hexapla``).
    ``logo``       An image for the sidebar and the home page (default: the Hexapla logo).
    ``variables``  A ``.scss`` file of Bootstrap and Hexapla variables, or a ``.css`` file added to the styles.
    ``about``      A Markdown file for an About page.
    ``licence``    The licence of the site, as an SPDX id such as ``CC-BY-NC-SA-4.0``. It covers the parses, the
                   links, and any transcription whose TEI header gives no licence.
    =============  ==========================================================================================

``manuscripts``
    One entry per text: a TEI transcription and its parse.

    ===================  ====================================================================================
    ``tei``              The TEI transcription (required).
    ``parsing``          The CoNLL-U parse of its text (required).
    ``parsing_licence``  The licence of the parse, if it differs from the site's.
    ===================  ====================================================================================

``alignments``
    One entry per pair of texts. A manuscript can be in several alignments, for example the Latin of one codex
    aligned with its Greek and with the Arabic of another.

    ===============  ========================================================================================
    ``manuscripts``  The two manuscript ids, in the order of the links file: its ``source`` side first, then its
                     ``target`` side (required).
    ``links``        The links file (required).
    ``name``         The alignment's title. By default it is the manuscript's name from the TEI header.
    ``licence``      The licence of the links, if it differs from the site's.
    ===============  ========================================================================================

    Alignments of more than two texts are planned. The config already takes a list of manuscripts, but for now
    it must have exactly two.

The TEI transcriptions
----------------------

Everything the site says about a manuscript comes from the TEI header of its transcription, following the
`TEI guidelines for manuscript description <https://www.tei-c.org/release/doc/tei-p5-doc/en/html/MS.html>`_.
Nothing about a manuscript goes in the config.

.. code-block:: xml

    <teiHeader>
      <fileDesc>
        <titleStmt>
          <title>A Transcription of Codex Bezae (Greek side)</title>
          <respStmt><resp>Transcribed by</resp><name>A. Scribe</name></respStmt>
        </titleStmt>
        <publicationStmt>
          <availability>
            <licence target="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</licence>
          </availability>
        </publicationStmt>
        <sourceDesc>
          <msDesc>
            <msIdentifier>
              <settlement>Cambridge</settlement>
              <repository>University Library</repository>
              <idno>Nn.2.41</idno>
              <msName>Codex Bezae</msName>
              <altIdentifier type="GA"><idno>05</idno></altIdentifier>
              <altIdentifier type="VL"><idno>5</idno></altIdentifier>
              <altIdentifier type="TM"><idno>61777</idno></altIdentifier>
            </msIdentifier>
            <msContents><summary>Greek-Latin bilingual of the Gospels and Acts.</summary></msContents>
            <history><origin><origDate notBefore="0400" notAfter="0499">5th century</origDate></origin></history>
          </msDesc>
        </sourceDesc>
      </fileDesc>
    </teiHeader>
    <text xml:lang="grc"> ... </text>

=====================================  ==========================================================================
``<text xml:lang>``                    The language of the text (required): an ISO 639 code such as ``grc``,
                                       ``lat``, ``ar``, ``cop``, ``got`` or ``syc``. It names the language on the
                                       site and sets right-to-left display.
``msName``                             The manuscript's common name. Without one, the GA number is used
                                       ("GA 0278"), then the title.
``settlement``, ``repository``,        The shelfmark. A manuscript in several places can have several
``idno``                               ``msDesc`` elements.
``altIdentifier``                      Numbers in catalogues: ``GA`` (Gregory-Aland), ``VL`` (Vetus Latina) and
                                       ``TM`` (Trismegistos, linked to its record). ``Gregory-Aland``,
                                       ``VetusLatina`` and ``Trismegistos`` are accepted as type names too.
``origDate``                           The date of the manuscript.
``msContents/summary``                 A sentence describing the manuscript.
``respStmt``, ``publisher``            Who made the transcription, credited in the footer of every page.
``availability``                       The transcription's licence, which overrides the site's.
=====================================  ==========================================================================

The body is read for each verse's ``<ab n="...">``: the folios or pages its words are on (``<pb>``) and its
corrections (``<app>``), lacunae, unclear and supplied text, and editorial notes. Verse references can be written
``John.20.1`` or ``B04K20V1``. A verse split across a page break is several ``<ab>`` elements marked
``part="I"``, ``part="M"`` ... ``part="F"``; an ``<ab>`` holding only a note (such as "Luke 6:5 is found after
Luke 6:10") is ignored.

The CoNLL-U parses
------------------

Each manuscript's text is parsed into `CoNLL-U <https://universaldependencies.org/format.html>`_, one sentence per
verse. The sentences of two parses are paired by ``sent_id``, so both parses of an alignment must use the same ids:

.. code-block:: text

    # sent_id = John.20.1
    # text = τη δε μια των σαββατων μαρια η μαγδαληνη ερχετε πρωι
    1	τη	ὁ	DET	S-	Case=Dat|Gender=Fem|Number=Sing	3	det	_	Conf=lemma:0.97,upos:0.95
    2	δε	δέ	ADV	Df	_	6	discourse	_	_
    ...

- A sentence becomes a verse page when its ``sent_id`` (or a ``# verse =`` comment, or ``Ref=`` in the first word's
  MISC column) is a Bible reference such as ``John.20.1``, ``John 20:1`` or ``B04K20V01``. Other sentences, such as
  an ``inscriptio``, keep their ``sent_id`` as their label.
- Multiword tokens (``2-3``) mark words written together, and empty nodes (``5.1``) are skipped.
- Confidences in the MISC column (``Conf=lemma:0.97,...``, as MCParser writes them) are optional. With them, the
  site underlines uncertain words and lists them in the review queue.

The links
---------

A links file pairs the words of two parses, by their CoNLL-U ids, sentence by sentence. JSON Lines, as MCAligner
writes it, has one sentence per line:

.. code-block:: json

    {"sent_id": "John.20.1", "links": [{"source": "1", "target": "1", "sure": true, "confidence": 0.95, "agent": "aligner"}]}

``source`` is a word of the first manuscript in the alignment's ``manuscripts`` list, and ``target`` a word of the
second. ``sure``, ``confidence`` and ``agent`` are optional. A YAML file of Ugarit-style links also works, with
``S`` for sure and ``P`` for probable links:

.. code-block:: yaml

    John.20.1: 1-1S 2-3S 4-5P
