"""Tests for cmds.cmd_list.ListCmd."""

import argparse
from pathlib import Path

import pytest

from cmds.cmd_list import ListCmd
from cmds.utils import Config, VeryFatalError
from tests.conftest import build_and_run_command


class TestListCmd:

    def test_libs_path_not_exist(self, monkeypatch: pytest.MonkeyPatch):
        p = Path("/nonexistent/path")
        monkeypatch.setattr(Config, "VIX_LIBS_PATH", p)
        monkeypatch.setattr(Config, "local_libs_path", staticmethod(lambda: p))
        with pytest.raises(VeryFatalError):
            build_and_run_command(ListCmd, namespace=argparse.Namespace())

    def test_libs_path_is_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        f = tmp_path / "not_a_dir"
        f.write_text("")
        monkeypatch.setattr(Config, "VIX_LIBS_PATH", f)
        monkeypatch.setattr(Config, "local_libs_path", staticmethod(lambda: f))
        with pytest.raises(VeryFatalError):
            build_and_run_command(ListCmd, namespace=argparse.Namespace())

    def test_empty_libs_path(self, tmp_config: dict, capsys: pytest.CaptureFixture):
        build_and_run_command(ListCmd, namespace=argparse.Namespace())
        captured = capsys.readouterr()
        assert captured.out

    def test_list_with_packages(
        self, libs_with_packages: Path, capsys: pytest.CaptureFixture
    ):
        build_and_run_command(ListCmd, namespace=argparse.Namespace())
        captured = capsys.readouterr()
        assert captured.out

    def test_tree_mode(self, libs_with_packages: Path, capsys: pytest.CaptureFixture):
        build_and_run_command(ListCmd, namespace=argparse.Namespace(tree=True))
        captured = capsys.readouterr()
        assert captured.out

    def test_parser_setup(self):
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ListCmd(subparsers)
        args = cmd.parser.parse_args(["-t"])
        assert args.tree is True
        args2 = cmd.parser.parse_args(["--tree"])
        assert args2.tree is True
        args3 = cmd.parser.parse_args([])
        assert args3.tree is False
