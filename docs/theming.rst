Theming
=======

The ``theme`` section of the config sets the site's name, logo, favicon, colours, about page and licence. Everything in it is
optional: without it, the site has Hexapla's look and logo.

.. code-block:: yaml

    theme:
      name: BICROSS Navigator
      logo: theme/logo.svg
      favicon: theme/favicon.svg
      variables: theme/variables.scss
      about: theme/about.md
      assets: theme/assets
      licence: CC-BY-NC-SA-4.0

Colours and fonts
-----------------

The site is styled with `Bootstrap 5.3 <https://getbootstrap.com/docs/5.3/>`_, compiled together with Hexapla's own
styles when the site is built. A ``.scss`` file can set any
`Bootstrap variable <https://getbootstrap.com/docs/5.3/customize/sass/#variable-defaults>`_ and any of Hexapla's:

.. code-block:: scss

    // theme/variables.scss
    $primary: #7b2d26;                                  // links, buttons and the sidebar
    $hexapla-page-bg: #faf8f5;
    $hexapla-serif: "Gentium Plus", Georgia, serif;

The site's brand colour (links and the sidebar) follows ``$primary`` when the theme sets it, and so do the colours made
from it: the highlighted words and arcs, the bars and dots of the charts, the heatmap scale and the light hover
backgrounds. Without a theme, the site keeps Hexapla's blues. Hexapla's variables, which a theme can also set one by
one:

=============================  ======================================================================
``$hexapla-brand``             The brand colour, if it should differ from ``$primary``.
``$hexapla-brand-light``       The top of the sidebar's gradient (a tint of the brand colour by default).
``$hexapla-page-bg``           The page background.
``$hexapla-surface``           The background of panels and cards.
``$hexapla-border``            Borders of panels and cards.
``$hexapla-text``              Text.
``$hexapla-text-secondary``    Secondary text, such as explanations under headings.
``$hexapla-text-muted``        Muted text, such as labels.
``$hexapla-accent``            Highlighted words, arcs and aligned words (a shade of the brand colour).
``$hexapla-series``            The bars, dots and meters of the charts (the brand colour).
``$hexapla-series-soft``       A light version of the series colour.
``$hexapla-tint``              Light backgrounds, such as the language labels (a tint of the brand colour).
``$hexapla-ramp``              The heatmap scale: a list of seven colours, light to dark.
``$hexapla-sidebar-width``     The sidebar's width.
``$hexapla-serif``             The font for manuscript text and headings.
``$hexapla-sans``              The font for everything else.
=============================  ======================================================================

The file is compiled between Bootstrap's functions and the rest of Bootstrap, the order Bootstrap recommends, so it
can use Bootstrap's functions and ``@import`` partials beside it. A mistake in it stops the build with the
compiler's message, and the last build is left as it was.

A ``.css`` file is added after the compiled styles instead, for rules of your own.

Logo
----

``logo`` can be any image (SVG, PNG or JPEG). It is shown at the top of the sidebar and on the home page.

``favicon`` is the icon browsers show in the tab and in bookmarks: a ``.png``, ``.ico`` or ``.svg`` file. Make it
square, and keep it simple enough to read at 16 pixels: a logo's shape without its text works well. Without a
favicon, the logo is used.

About page and assets
---------------------

``about`` is a Markdown file. It becomes an About page, linked from the sidebar and the home page: a good place for
the project, its funders, and how its texts were prepared.

``assets`` is a folder copied into the site as ``assets/``, for the images and files the about page shows or links
to: a funder's logo, a PDF, a diagram. Write their links relative to the Markdown file, as you would for it to
preview on GitHub, and Hexapla points them at the copies in the site::

    theme/
      about.md
      assets/
        erc-logo.jpg
        guidelines.pdf

.. code-block:: markdown

    ## Funding

    ![European Research Council](assets/erc-logo.jpg){width=160 .float-end .ms-4}

    The research leading to this contribution ... Read our [transcription guidelines](assets/guidelines.pdf).

Attributes in braces after an image set its size, or add `Bootstrap classes
<https://getbootstrap.com/docs/5.3/utilities/float/>`_ such as ``.float-end`` (float right) and ``.ms-4`` (a margin
on its left).

A local image or link that is not in the assets folder would be broken on the site, so ``hexapla validate`` reports
it as an error. Links to web pages (``https://...``) and to headings on the page (``#funding``) are left as they are.

Licences
--------

Licences are given as `SPDX ids <https://spdx.org/licenses/>`_. Creative Commons ids (``CC-BY-4.0``,
``CC-BY-NC-SA-4.0``, ``CC0-1.0``...) become a name and a link; a URL or any other text is shown as it is.

- ``theme.licence`` covers the site, the parses and the links.
- A transcription's own licence, from its TEI header, overrides it for that transcription.
- ``parsing_licence`` on a manuscript and ``licence`` on an alignment override it for those files.

Every alignment page credits the transcribers and lists the licences that apply in its footer.
