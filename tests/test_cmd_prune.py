"""Tests for cmds.cmd_prune.PruneCmd."""

import argparse
from pathlib import Path

import pytest

from cmds.cmd_prune import PruneCmd
from cmds.utils import Config, VeryFatalError
from tests.conftest import build_and_run_command


class TestPruneCmd:

    def test_libs_path_not_exist(self, monkeypatch: pytest.MonkeyPatch):
        p = Path("/nonexistent/path")
        monkeypatch.setattr(Config, "VIX_LIBS_PATH", p)
        monkeypatch.setattr(Config, "local_libs_path", staticmethod(lambda: p))
        with pytest.raises(VeryFatalError):
            build_and_run_command(PruneCmd, namespace=argparse.Namespace())

    def test_libs_path_is_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        f = tmp_path / "not_a_dir"
        f.write_text("")
        monkeypatch.setattr(Config, "VIX_LIBS_PATH", f)
        monkeypatch.setattr(Config, "local_libs_path", staticmethod(lambda: f))
        with pytest.raises(VeryFatalError):
            build_and_run_command(PruneCmd, namespace=argparse.Namespace())

    def test_default_mode(self, libs_with_packages: Path):
        libs = libs_with_packages
        build_and_run_command(PruneCmd, namespace=argparse.Namespace())
        assert not (libs / "github.com" / "fexcode" / "broken").exists()
        assert not (libs / "gitee.com").exists()
        assert (libs / "github.com" / "fexcode" / "vnet").exists()
        assert (libs / "github.com" / "fexcode" / "vnet" / "vindex.toml").exists()

    def test_empty_only_mode(self, libs_with_packages: Path):
        libs = libs_with_packages
        build_and_run_command(PruneCmd, namespace=argparse.Namespace(empty_only=True))
        assert not (libs / "gitee.com").exists()
        assert not (libs / "github.com" / "fexcode" / "broken").exists()
        assert (libs / "github.com" / "fexcode" / "vnet").exists()

    def test_invalid_only_mode(self, libs_with_packages: Path):
        libs = libs_with_packages
        build_and_run_command(PruneCmd, namespace=argparse.Namespace(invalid_only=True))
        assert not (libs / "github.com" / "fexcode" / "broken").exists()
        assert not (libs / "gitee.com" / "user1" / "empty_pkg").exists()
        assert (libs / "gitee.com" / "user1").exists()
        assert (libs / "github.com" / "fexcode" / "vnet").exists()

    def test_summary_output(
        self, libs_with_packages: Path, capsys: pytest.CaptureFixture
    ):
        build_and_run_command(PruneCmd, namespace=argparse.Namespace())
        captured = capsys.readouterr()
        assert captured.out
