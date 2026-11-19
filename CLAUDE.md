# Hexapla

Hexapla builds a static website for reading and exploring word-aligned manuscript texts.
It is only the software: each project (for example `../bicross-navigator`) has its own
repository with a YAML config file, TEI transcriptions, CoNLL-U parses and alignment links.

```
hexapla build path/to/project-config.yaml --output path/to/site
hexapla validate path/to/project-config.yaml
```

## Priorities

1. **Tests first.** Write or update the tests before the code that makes them pass.
2. **100% test coverage.** `uv run pytest` must report 100% (coverage is configured in `pyproject.toml`).
   Untested code is removed or tested, not excluded. Use `# pragma: no cover` only for lines
   that cannot run under test, and say why in a comment.
3. **The TEI is the source of truth for manuscripts.** Language (`<text xml:lang>`), names, shelfmarks,
   identifiers (GA, VL, Trismegistos), dates, descriptions, credits and licences come from the TEI
   header (TEI P5 ch. 10, Manuscript Description). Do not add manuscript metadata to the config.
4. **Keep the config minimal.** Only add a config field when the information cannot live in the
   TEI, CoNLL-U or links files.
5. **No workarounds for broken data.** If a file is wrong (a missing language, verse numbers that
   restart), validation reports it with the file name and the user fixes the file.
6. **Elegant terminal output with rich.** Everything the CLI prints goes through a rich `Console`
   (`main.py`): tables for anything with rows (manuscripts, alignments, statistics), a red panel
   for errors, `⚠` lines for warnings, a `✓` summary line at the end, and paths shown relative to
   the project folder. No bare `print`/`typer.echo`. Tests run the CLI with `COLUMNS=200`.

## Layout

- `hexapla/`: the package. `config.py` (pydantic `Config`, `Theme`, `Manuscript`, `Alignment`),
  `transcription.py` (TEI), `conllu.py`, `links.py`, `corpus.py` (loads witnesses and aligned pairs),
  `analysis.py`, `theme.py` (SCSS compile), `about.py` (about page Markdown and its asset links),
  `build.py` (pages), `main.py` (CLI).
- `hexapla/templates/`: Jinja2 templates. `hexapla/static/`: JS, images, SCSS (incl. vendored Bootstrap).
- `docs/`: Sphinx docs (furo). They include sections of `README.rst` between `.. start-<name>` /
  `.. end-<name>` markers, so edit shared text in the README. Build with `sphinx-build -W docs docs/_build/html`;
  update the docs whenever behaviour or the config changes.
- `docs/_static/`: the Hexapla banner, logo and small logo. Sites use copies in `hexapla/static/img/`: the logo as the
  default theme logo, and the small logo (background made transparent) in every page's "Built with" footer link.
- `action.yml`: the GitHub Action (installs Hexapla from its own checkout, builds, deploys to Pages).
- `tests/`: pytest; `tests/data/project/` is a small complete project used by the end-to-end tests.

## Conventions

- The project uses uv: `uv sync --all-groups` once, then `uv run pytest`, `uv run hexapla ...` and
  `uv run sphinx-build -W docs docs/_build/html`. Add dependencies with `uv add` (or `uv add --group dev`), which
  updates `uv.lock`; commit the lock file. Build the package with `uv build`.
- Paths in a config file are relative to the config file.
- Config `licence` fields take SPDX ids (`CC-BY-NC-SA-4.0`). A TEI licence overrides the site licence
  for that transcription; `parsing_licence` and an alignment's `licence` override it for those files.
- Alignments pair exactly two manuscripts for now; the config format allows more for later.

## Releasing

1. Set the version in both `pyproject.toml` and `hexapla/__init__.py` (a test checks they match), and in `CITATION.cff`.
2. Give the version a section in `CHANGELOG.rst` (a test checks it is there) with its date.
3. Commit, then tag and push: `git tag v0.1.0 && git push origin v0.1.0`. `.github/workflows/publish.yml` tests,
   builds (`uv build`) and publishes (`uv publish`) to PyPI with the `PYPI_TOKEN` secret.
4. Move the action's major tag: `git tag -f v1 && git push -f origin v1`.
