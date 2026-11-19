=========
Changelog
=========

0.1.0 (unreleased)
==================

The first release.

- ``hexapla build`` and ``hexapla validate``: build a static website from a project's YAML config, TEI
  transcriptions, CoNLL-U parses and word-alignment links, or check that every file can be read.
- Pages for each alignment (overview, verse pages with dependency trees, an interlinear and an alignment matrix,
  lexicon, translation insights and review queue) and for each manuscript (described from its TEI header).
- Manuscript metadata from the TEI header: language, name, shelfmarks, GA, VL and Trismegistos numbers, date,
  summary, transcribers and licence.
- Themes: a logo, Bootstrap and Hexapla variables in SCSS (or extra CSS), an About page in Markdown with its own
  images and files, and the site licence. Licences of transcriptions, parses and links are shown on every page.
- A GitHub Action that builds a project's site and deploys it to GitHub Pages.
