Making the parses and links
===========================

Hexapla only reads the files: any tool that writes CoNLL-U and word links will do, and you can make or correct them
by hand. For the BICROSS Navigator they were made with two tools that use LLM agents together with a treebank of
trusted examples:

- `MCParser <https://github.com/rbturnbull/llmparser>`_ lemmatises, tags and parses a text into CoNLL-U, recording
  a confidence for each cell;
- `MCAligner <https://github.com/rbturnbull/llmaligner>`_ links the words of two parses, marking each link sure or
  probable.

Both are optional, and installed separately from Hexapla:

.. code-block:: bash

    pip install --pre mcparser
    pip install git+https://github.com/rbturnbull/llmaligner      # mcaligner
    export ANTHROPIC_API_KEY=...                                  # the key for your models' provider

Both tools call a language model, which costs money. Try a few sentences first (``--max-sentences 5``): each run
prints the tokens it used and their estimated cost.

1. Extract the text of each verse
---------------------------------

MCParser starts from plain text. Write one YAML file per text, with the verse reference as the ``sent_id``, and use
the same references on both sides of an alignment:

.. code-block:: yaml

    - sent_id: John.20.1
      text: τη δε μια των σαββατων μαρια η μαγδαληνη ερχετε πρωι σκοτιας ετι ουσης εις το μνημιον
    - sent_id: John.20.2
      text: τρεχει ουν και ερχεται προς σιμωνα πετρον

How to turn a transcription into running text depends on the project: which reading of a correction to take,
whether to expand nomina sacra, what to do with supplied letters. A starting point for an IGNTP-style TEI file,
which takes the words of each ``<ab>``:

.. code-block:: python

    import xml.etree.ElementTree as ET
    import yaml

    TEI = "{http://www.tei-c.org/ns/1.0}"
    root = ET.parse("Bezae-Greek.xml").getroot()
    verses = []
    for ab in root.iter(f"{TEI}ab"):
        words = ["".join(w.itertext()).strip() for w in ab.iter(f"{TEI}w")]
        if ab.get("n", "").startswith("B04K20") and words:   # John 20
            verses.append({"sent_id": ab.get("n"), "text": " ".join(words)})
    with open("bezae-john20-grc.yaml", "w") as f:
        yaml.safe_dump(verses, f, allow_unicode=True, sort_keys=False)

2. Parse each text with MCParser
--------------------------------

``mcparser init`` tokenises the text and fills in what a treebank of the language makes obvious; ``mcparser run``
then has the agents annotate and check the rest. ``-s`` names the trusted examples, for example a
`Universal Dependencies <https://universaldependencies.org/>`_ treebank such as PROIEL:

.. code-block:: bash

    mcparser init bezae-john20-grc.yaml -o Bezae-Greek-John20.conllu -s grc_proiel-ud-train.conllu
    mcparser run Bezae-Greek-John20.conllu -s grc_proiel-ud-train.conllu

    mcparser init bezae-john20-lat.yaml -o Bezae-Latin-John20.conllu -s la_proiel-ud-train.conllu
    mcparser run Bezae-Latin-John20.conllu -s la_proiel-ud-train.conllu

``run`` saves as it goes, and running it again resumes. Each edit is recorded in ``<file>.history.jsonl``, and what
the agents flagged for review in ``<file>.review.json``. The ``# sent_id`` and ``# text`` of each sentence are kept,
so the parse is ready for Hexapla. See the `MCParser documentation <https://github.com/rbturnbull/llmparser>`_ for
models, providers and settings.

3. Align the two parses with MCAligner
--------------------------------------

``mcaligner run`` pairs the sentences of the two parses by ``sent_id``, links the near-certain words with rules,
and has an aligner agent link the rest:

.. code-block:: bash

    mcaligner run \
        -s grc=Bezae-Greek-John20.conllu -s lat=Bezae-Latin-John20.conllu \
        -a pred=grc,lat,Bezae-John20-aligned.jsonl --target pred \
        --guidelines grc-lat --concurrency 4

- ``-s`` names each parse; ``-a pred=grc,lat,FILE`` is the links file to write, with ``grc`` as its source side and
  ``lat`` as its target. List the manuscripts in the same order in the Hexapla config.
- ``--guidelines`` gives the agents rules for the language pair. Bundled guidelines: ``grc-lat``, ``grc-ar``,
  ``grc-cop``, ``got-lat``, ``lat-ar`` and ``bicross``.
- Running it again resumes, and the edits are recorded in ``<file>.history.jsonl``.

4. Add them to the config
-------------------------

.. code-block:: yaml

    manuscripts:
      bezae-greek:
        tei: bezae/Bezae-Greek.xml
        parsing: bezae/Bezae-Greek-John20.conllu
      bezae-latin:
        tei: bezae/Bezae-Latin.xml
        parsing: bezae/Bezae-Latin-John20.conllu

    alignments:
      bezae:
        manuscripts: [bezae-greek, bezae-latin]     # grc (source), then lat (target)
        links: bezae/Bezae-John20-aligned.jsonl

Then ``hexapla validate`` checks that the sentences and links line up.
