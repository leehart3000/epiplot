import tomllib
from pathlib import Path

import epiplot


def test_import() -> None:
    assert epiplot is not None


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject.open("rb") as file:
        expected = tomllib.load(file)["project"]["version"]

    assert epiplot.__version__ == expected
