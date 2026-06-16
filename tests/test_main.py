"""Tests for main module: Very class, show_version, print_banner, main()."""

import argparse
import sys

import pytest

from main import Very, show_version, print_banner, main
from cmds.utils import VeryFatalError


class TestVery:
    """Tests for the Very class (parser/runner)."""

    # -----------------------------------------------------------------------
    #  helpers — mock command classes
    # -----------------------------------------------------------------------

    class _MockCmd:
        NAME = "mockcmd"
        executed = False
        captured_ns = None

        def __init__(self, subparsers=None):
            self.executed = False
            self.captured_ns = None

        def execute(self):
            self.executed = True
            self.captured_ns = self.namespace

    class _FatalCmd:
        NAME = "fatal"

        def execute(self):
            raise VeryFatalError()

    class _InterruptCmd:
        NAME = "int"

        def execute(self):
            raise KeyboardInterrupt()

    class _ErrorCmd:
        NAME = "err"

        def execute(self):
            raise Exception("test error")

    # -----------------------------------------------------------------------
    #  run — unknown command
    # -----------------------------------------------------------------------

    def test_run_unknown_command(self):
        parser = argparse.ArgumentParser(prog="very")
        v = Very(parser)
        with pytest.raises(SystemExit) as exc:
            v.run("nonexistent", argparse.Namespace())
        assert exc.value.code == 1

    # -----------------------------------------------------------------------
    #  run — known command
    # -----------------------------------------------------------------------

    def test_run_known_command(self):
        parser = argparse.ArgumentParser(prog="very")
        v = Very(parser)
        mock = self._MockCmd()
        v.commands["mockcmd"] = mock
        ns = argparse.Namespace(keyword="test")
        v.run("mockcmd", ns)
        assert mock.executed
        assert mock.captured_ns is ns

    # -----------------------------------------------------------------------
    #  run — VeryFatalError  -> exit(1)
    # -----------------------------------------------------------------------

    def test_run_very_fatal_error(self):
        parser = argparse.ArgumentParser(prog="very")
        v = Very(parser)
        v.commands["fatal"] = self._FatalCmd()
        with pytest.raises(SystemExit) as exc:
            v.run("fatal", argparse.Namespace())
        assert exc.value.code == 1

    # -----------------------------------------------------------------------
    #  run — KeyboardInterrupt  -> exit(0)
    # -----------------------------------------------------------------------

    def test_run_keyboard_interrupt(self):
        parser = argparse.ArgumentParser(prog="very")
        v = Very(parser)
        v.commands["int"] = self._InterruptCmd()
        with pytest.raises(SystemExit) as exc:
            v.run("int", argparse.Namespace())
        assert exc.value.code == 0

    # -----------------------------------------------------------------------
    #  run — generic Exception  -> exit(1)
    # -----------------------------------------------------------------------

    def test_run_generic_exception(self):
        parser = argparse.ArgumentParser(prog="very")
        v = Very(parser)
        v.commands["err"] = self._ErrorCmd()
        with pytest.raises(SystemExit) as exc:
            v.run("err", argparse.Namespace())
        assert exc.value.code == 1

    # -----------------------------------------------------------------------
    #  register
    # -----------------------------------------------------------------------

    def test_register(self, monkeypatch):
        from cmds import cmds as cmd_classes

        parser = argparse.ArgumentParser(prog="very")
        sub = parser.add_subparsers(dest="subcommand")
        monkeypatch.setattr("main.subparsers", sub)

        v = Very(parser)
        v.register(cmd_classes)
        assert len(v.commands) == 9
        assert set(v.commands.keys()) == {
            "add",
            "build",
            "del",
            "list",
            "prune",
            "init",
            "search",
            "install",
            "update",
        }


class TestMainFunctions:
    """Tests for module-level functions in main.py."""

    # -----------------------------------------------------------------------
    #  show_version
    # -----------------------------------------------------------------------

    def test_show_version(self, capsys):
        show_version()
        out, _err = capsys.readouterr()
        assert "Very" in out

    # -----------------------------------------------------------------------
    #  print_banner
    # -----------------------------------------------------------------------

    def test_print_banner(self, capsys):
        print_banner()
        out, _err = capsys.readouterr()
        assert "VERY" in out or "可用命令" in out

    # -----------------------------------------------------------------------
    #  main() — --version flag  -> exit(0)
    # -----------------------------------------------------------------------

    def test_main_with_version(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["very", "--version"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out, _err = capsys.readouterr()
        assert "Very" in out

    # -----------------------------------------------------------------------
    #  main() — no subcommand  -> exit(1)
    # -----------------------------------------------------------------------

    def test_main_no_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["very"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
