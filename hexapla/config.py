"""
A Hexapla project's config file: the theme, the manuscripts (a TEI transcription and its CoNLL-U parse)
and the alignments between them. Paths are relative to the config file::

    theme:
      name: BICROSS Navigator
      logo: theme/logo.svg
      favicon: theme/favicon.svg
      variables: theme/variables.scss
      about: theme/about.md
      assets: theme/assets
      licence: CC-BY-NC-SA-4.0

    manuscripts:
      bezae-greek:
        tei: bezae/Bezae-Greek.xml
        parsing: bezae/Bezae-Greek-John20.conllu

    alignments:
      bezae:
        name: Codex Bezae (GA 05)
        manuscripts: [bezae-greek, bezae-latin]
        links: bezae/Bezae-John20-aligned.jsonl

Everything about a manuscript itself (language, names, identifiers, date, licence) is in its TEI header.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from .about import asset_path, local_links
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, ValidationInfo, field_validator, model_validator

ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"


class ConfigError(Exception):
    def __init__(self, source: Path | str, errors: list[str]):
        self.source = source
        self.errors = errors
        super().__init__(f"{source}:\n" + "\n".join(f"  - {error}" for error in errors))


def _locate(value: Path | None, info: ValidationInfo) -> Path | None:
    """ A path made absolute against the config file's folder; None when not loading a file (paths are kept as given). """
    root = (info.context or {}).get("root")
    if value is None or root is None:
        return None
    path = value.expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def _resolve(value: Path | None, info: ValidationInfo) -> Path | None:
    """ Makes a path absolute against the config file's folder and checks the file exists (only when loading a file). """
    path = _locate(value, info)
    if path is None:
        return value
    if not path.is_file():
        raise ValueError(f"file not found: {path}")
    return path


def _resolve_folder(value: Path | None, info: ValidationInfo) -> Path | None:
    path = _locate(value, info)
    if path is None:
        return value
    if not path.is_dir():
        raise ValueError(f"folder not found: {path}")
    return path


FAVICON_TYPES = {".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml"}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Theme(Model):
    name: str = "Hexapla"
    logo: Path | None = None
    favicon: Path | None = None  # the browser tab icon (.png, .ico or .svg); the logo by default
    variables: Path | None = None  # Bootstrap variables (.scss) or extra CSS (.css)
    assets: Path | None = None  # a folder copied into the site as assets/, for the about page's images and files
    about: Path | None = None  # Markdown for the about page; its links into the assets folder work on the site
    licence: str | None = None  # SPDX id; covers the site, CoNLL-U and links unless overridden

    @field_validator("variables")
    @classmethod
    def _scss_or_css(cls, value: Path | None) -> Path | None:
        if value is not None and value.suffix.lower() not in (".scss", ".css"):
            raise ValueError(f"must be a .scss or .css file, not {value.name}")
        return value

    @field_validator("favicon")
    @classmethod
    def _icon(cls, value: Path | None) -> Path | None:
        if value is not None and value.suffix.lower() not in FAVICON_TYPES:
            raise ValueError(f"must be a .png, .ico or .svg file, not {value.name}")
        return value

    _paths = field_validator("logo", "favicon", "variables")(_resolve)
    _folders = field_validator("assets")(_resolve_folder)

    @field_validator("about")
    @classmethod
    def _about(cls, value: Path | None, info: ValidationInfo) -> Path | None:
        """ The about file, whose local images and links must all be in the assets folder (else broken on the site). """
        value = _resolve(value, info)
        if value is None or (info.context or {}).get("root") is None:
            return value
        assets = info.data.get("assets")
        missing = [link for link in local_links(value.read_text(encoding="utf-8")) if not asset_path(link, value, assets)]
        if missing:
            raise ValueError("; ".join(f"{link} is not in the assets folder" for link in missing))
        return value


class Manuscript(Model):
    id: str = Field(pattern=ID_PATTERN)
    tei: Path
    parsing: Path
    parsing_licence: str | None = None

    _paths = field_validator("tei", "parsing")(_resolve)


class Alignment(Model):
    id: str = Field(pattern=ID_PATTERN)
    name: str | None = None
    manuscripts: list[str] = Field(min_length=2)  # in the order of the links file: source, target
    links: Path
    licence: str | None = None

    _paths = field_validator("links")(_resolve)

    @field_validator("manuscripts")
    @classmethod
    def _distinct(cls, value: list[str]) -> list[str]:
        repeated = sorted({item for item in value if value.count(item) > 1})
        if repeated:
            raise ValueError(f"lists {', '.join(repeated)} more than once")
        return value

    @model_validator(mode="after")
    def _pairs_only(self) -> Alignment:
        if len(self.manuscripts) != 2:
            raise ValueError("an alignment needs exactly two manuscripts for now (n-way alignments are not supported yet)")
        return self


def _keyed(value: Any, section: str) -> Any:
    """ ``{id: {...}}`` → ``[{"id": id, ...}]``. """
    if not isinstance(value, dict):
        raise ValueError(f"'{section}' must be a mapping from id to settings")
    return [{"id": key, **item} if isinstance(item, dict) else item for key, item in value.items()]


class Config(Model):
    theme: Theme = Field(default_factory=Theme)
    manuscripts: list[Manuscript]
    alignments: list[Alignment] = Field(default_factory=list)

    _path: Path | None = PrivateAttr(default=None)

    @model_validator(mode="before")
    @classmethod
    def _from_mappings(cls, data: Any) -> Any:
        """ The file keys manuscripts and alignments by id; in Python they can be given as lists of models. """
        data = dict(data)
        for section in ("manuscripts", "alignments"):
            if section in data and not _is_model_list(data[section]):
                data[section] = _keyed(data[section], section)
        return data

    @model_validator(mode="after")
    def _known_manuscripts(self) -> Config:
        known = {manuscript.id for manuscript in self.manuscripts}
        unknown = [f"alignment '{alignment.id}' lists unknown manuscript '{ms}'"
                   for alignment in self.alignments for ms in alignment.manuscripts if ms not in known]
        if unknown:
            raise ValueError("; ".join(unknown))
        return self

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def root(self) -> Path | None:
        return self._path.parent if self._path else None

    def manuscript(self, manuscript_id: str) -> Manuscript:
        for manuscript in self.manuscripts:
            if manuscript.id == manuscript_id:
                return manuscript
        raise KeyError(manuscript_id)


def _is_model_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, BaseModel) for item in value)


def _describe(error: dict, data: dict) -> str:
    """ A pydantic error as ``manuscripts.claro-greek.tei: file not found: ...`` (list positions shown as ids). """
    loc = list(error["loc"])
    if len(loc) >= 2 and loc[0] in ("manuscripts", "alignments") and isinstance(loc[1], int):
        keys = list((data.get(loc[0]) or {}).keys()) if isinstance(data.get(loc[0]), dict) else []
        if loc[1] < len(keys):
            loc[1] = keys[loc[1]]
    message = error["msg"].removeprefix("Value error, ")
    where = ".".join(str(part) for part in loc)
    return f"{where}: {message}" if where else message


def load_config(path: Path | str) -> Config:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ConfigError(path, ["config file not found"])
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        raise ConfigError(path, [f"not valid YAML: {err}"]) from err
    if not isinstance(data, dict):
        raise ConfigError(path, ["expected a mapping with theme, manuscripts and alignments"])
    try:
        config = Config.model_validate(data, context={"root": path.parent})
    except ValidationError as err:
        raise ConfigError(path, [_describe(error, data) for error in err.errors()]) from err
    config._path = path
    return config
