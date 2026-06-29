import tomllib
from pathlib import Path


def test_pyproject_declares_main_module_for_packaging():
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    assert data["tool"]["setuptools"]["py-modules"] == ["main"]
