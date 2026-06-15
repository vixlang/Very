"""Shared fixtures and helpers for all tests."""

import argparse
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from cmds.base import Command
from cmds.utils import Config

# ---------------------------------------------------------------------------
#  Fixtures: patch Config paths to tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config(tmp_path: Path, monkeypatch: MonkeyPatch) -> dict[str, Path]:
    """Point Config.VIX_HOME and Config.VIX_LIBS_PATH to temp directories.

    Returns ``{"vix_home": …, "libs_path": …}`` for reference.
    """
    libs = tmp_path / "libs"
    libs.mkdir()
    monkeypatch.setattr(Config, "VIX_HOME", tmp_path)
    monkeypatch.setattr(Config, "VIX_LIBS_PATH", libs)
    return {"vix_home": tmp_path, "libs_path": libs}


# ---------------------------------------------------------------------------
#  Fixtures: helpers for creating mock package structures
# ---------------------------------------------------------------------------


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def libs_with_packages(tmp_config: dict[str, Path]) -> Path:
    """Create a ``libs/`` directory with a few packages.

    Structure::

        libs/
          github.com/
            fexcode/
              vnet/          ← valid (has vindex.toml)
              broken/        ← invalid (no vindex.toml)
          gitee.com/
            user1/
              empty_pkg/     ← empty directory

    Returns the path to ``libs/``.
    """
    libs = tmp_config["libs_path"]
    # Valid package
    pkg_dir = _ensure_dir(libs / "github.com" / "fexcode" / "vnet")
    (pkg_dir / "vindex.toml").write_text(
        '[package]\nname = "vnet"\nversion = "1.0.0"\n'
    )
    # Invalid package (no vindex.toml)
    _ensure_dir(libs / "github.com" / "fexcode" / "broken")
    # Empty directory
    _ensure_dir(libs / "gitee.com" / "user1" / "empty_pkg")
    return libs


# ---------------------------------------------------------------------------
#  Helper: build & run a Command without going through ``main.py``
# ---------------------------------------------------------------------------


def build_and_run_command(
    cmd_cls: type[Command],
    argv: list[str] | None = None,
    namespace: argparse.Namespace | None = None,
) -> Command:
    """Instantiate *cmd_cls*, attach parsed args, and call ``.execute()``.

    Provide *argv* to parse real arguments, or pass a pre-built *namespace*.
    If neither is provided an empty namespace is used.
    """
    parser = argparse.ArgumentParser(prog="very")
    subparsers = parser.add_subparsers(dest="subcommand")
    cmd = cmd_cls(subparsers)
    if namespace is not None:
        cmd.namespace = namespace
    elif argv is not None:
        cmd.namespace = parser.parse_args(argv)
    else:
        cmd.namespace = argparse.Namespace()
    cmd.execute()
    return cmd
