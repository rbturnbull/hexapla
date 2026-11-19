.. include:: ../README.rst
   :start-after: start-github-pages
   :end-before: end-github-pages

Inputs
------

==================  ===========  ========================================================================
``config``          (required)   The project's config file, relative to the repository root.
``output``          ``_site``    Where to write the site.
``deploy``          ``"true"``   Deploy to GitHub Pages, or (``"false"``) only build the site.
``python-version``  ``"3.12"``   The Python version to run Hexapla with.
==================  ===========  ========================================================================

The action's ``page_url`` output is the address of the deployed site.

The workflow needs ``pages: write`` and ``id-token: write`` permissions and the ``github-pages`` environment, as in the
example above. An action cannot give itself these permissions, so they belong in your workflow.

Checking pull requests
----------------------

To build the site on every pull request without publishing it:

.. code-block:: yaml

    name: check
    on: pull_request
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: rbturnbull/hexapla@main
            with:
              config: project-config.yaml
              deploy: "false"
