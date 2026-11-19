import tomllib
from pathlib import Path

import hexapla

ROOT = Path(__file__).parent.parent


def test_version_matches_pyproject():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert hexapla.__version__ == pyproject["project"]["version"]


def test_changelog_has_this_version():
    assert f"\n{hexapla.__version__} " in (ROOT / "CHANGELOG.rst").read_text(encoding="utf-8")
