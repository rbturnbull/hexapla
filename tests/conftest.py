import shutil
from pathlib import Path

import pytest
import yaml

PROJECT = Path(__file__).parent / "data" / "project"
CONFIG_NAME = "project.yaml"


@pytest.fixture
def project_dir(tmp_path) -> Path:
    """ A writable copy of the test project. """
    target = tmp_path / "project"
    shutil.copytree(PROJECT, target)
    return target


def read_config(project: Path) -> dict:
    return yaml.safe_load((project / CONFIG_NAME).read_text(encoding="utf-8"))


def write_config(project: Path, data: dict) -> Path:
    path = project / CONFIG_NAME
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
