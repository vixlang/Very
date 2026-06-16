import argparse
from io import StringIO
from pathlib import Path

from rich.console import Console

from cmds.cmd_del import DelCmd
from cmds.utils import PackageNameInfo

from .conftest import build_and_run_command


def _fix_pack_path_default(monkeypatch, libs_path: Path) -> None:
    """Make PackageNameInfo.pack_path use the given parent by default."""
    monkeypatch.setattr(PackageNameInfo, "_default_parent", libs_path)


def _patch_stderr(monkeypatch) -> StringIO:
    """Replace rich consoles writing to stderr with StringIO-backed ones."""
    buf = StringIO()
    new_console = Console(file=buf)
    monkeypatch.setattr("cmds.utils.err_console", new_console)
    return buf


class TestDelCmd:
    def test_package_not_exists(self, monkeypatch):
        err = _patch_stderr(monkeypatch)
        build_and_run_command(
            DelCmd, namespace=argparse.Namespace(package="some.nonexistent")
        )
        assert "包不存在" in err.getvalue()

    def test_package_exists_and_confirm(self, libs_with_packages, monkeypatch, capsys):
        _fix_pack_path_default(monkeypatch, libs_with_packages)
        monkeypatch.setattr(
            "cmds.cmd_del.ask_confirm", lambda prompt, default=True: True
        )
        build_and_run_command(
            DelCmd, namespace=argparse.Namespace(package="fexcode.vnet")
        )
        out, _err = capsys.readouterr()
        assert "已删除" in out
        pkg_dir = libs_with_packages / "github.com" / "fexcode" / "vnet"
        assert not pkg_dir.exists()

    def test_package_exists_and_cancel(self, libs_with_packages, monkeypatch, capsys):
        _fix_pack_path_default(monkeypatch, libs_with_packages)
        monkeypatch.setattr(
            "cmds.cmd_del.ask_confirm", lambda prompt, default=True: False
        )
        build_and_run_command(
            DelCmd, namespace=argparse.Namespace(package="fexcode.vnet")
        )
        out, _err = capsys.readouterr()
        assert "已取消操作" in out
        pkg_dir = libs_with_packages / "github.com" / "fexcode" / "vnet"
        assert pkg_dir.is_dir()

    def test_rmtree_fails(self, libs_with_packages, monkeypatch):
        _fix_pack_path_default(monkeypatch, libs_with_packages)
        monkeypatch.setattr(
            "cmds.cmd_del.ask_confirm", lambda prompt, default=True: True
        )

        def _failing_rmtree(*args, **kwargs):
            raise PermissionError("Access denied")

        monkeypatch.setattr("cmds.cmd_del.shutil.rmtree", _failing_rmtree)
        err = _patch_stderr(monkeypatch)
        build_and_run_command(
            DelCmd, namespace=argparse.Namespace(package="fexcode.vnet")
        )
        assert "删除失败" in err.getvalue()
