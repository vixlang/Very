"""Tests for ExeCmd."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock

from cmds.cmd_exe import ExeCmd
from cmds.utils import Config


class TestExeCmd:
    def test_parser_adds_tool_argument(self):
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        ExeCmd(subparsers)
        ns = parser.parse_args(["exe", "mygame"])
        assert ns.tool == "mygame"

    def test_tool_not_found_auto_installs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "VIX_TOOLS_PATH", tmp_path / "tools")
        tool_bin = tmp_path / "tools" / "mygame.exe"
        tool_bin.parent.mkdir(parents=True)

        def fake_install(name):
            tool_bin.write_text("fake binary")
            return tool_bin

        import cmds.cmd_exe as exe_mod
        monkeypatch.setattr(exe_mod, "install_tool", fake_install)

        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ExeCmd(subparsers)
        cmd.namespace = argparse.Namespace(tool="mygame")
        cmd.extra_args = ["--score", "100"]
        cmd.execute()

        assert tool_bin.exists()
        mock_run.assert_called_once_with([str(tool_bin), "--score", "100"])

    def test_tool_already_installed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "VIX_TOOLS_PATH", tmp_path / "tools")
        tool_bin = tmp_path / "tools" / "mygame.exe"
        tool_bin.parent.mkdir(parents=True)
        tool_bin.write_text("fake binary")

        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ExeCmd(subparsers)
        cmd.namespace = argparse.Namespace(tool="mygame")
        cmd.extra_args = []
        cmd.execute()

        mock_run.assert_called_once_with([str(tool_bin)])

    def test_tool_name_empty(self):
        """Empty tool name should exit early without error."""
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ExeCmd(subparsers)
        cmd.namespace = argparse.Namespace(tool="")
        cmd.extra_args = []
        # Should not raise
        cmd.execute()
