import argparse
from io import StringIO
from pathlib import Path

from rich.console import Console

from cmds.cmd_init import InitCmd

from .conftest import build_and_run_command


def _patch_stderr(monkeypatch) -> StringIO:
    """Replace err_console with one backed by a StringIO, return the buffer."""
    buf = StringIO()
    monkeypatch.setattr("cmds.utils.err_console", Console(file=buf))
    return buf


class TestInitCmd:
    def test_no_project_name(self, monkeypatch):
        err = _patch_stderr(monkeypatch)
        build_and_run_command(InitCmd, namespace=argparse.Namespace(name=None))
        assert "请提供项目名称" in err.getvalue()

    def test_project_dir_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing_proj").mkdir()
        err = _patch_stderr(monkeypatch)
        build_and_run_command(
            InitCmd, namespace=argparse.Namespace(name="existing_proj")
        )
        assert "目录" in err.getvalue() and "已存在" in err.getvalue()

    def test_successful_creation(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        build_and_run_command(InitCmd, namespace=argparse.Namespace(name="myproject"))
        out, _err = capsys.readouterr()
        assert "成功创建项目" in out
        proj = tmp_path / "myproject"
        assert proj.is_dir()
        assert (proj / "vindex.toml").is_file()
        assert 'name = "myproject"' in (proj / "vindex.toml").read_text("utf-8")
        assert (proj / "main.vix").is_file()
        assert "Hello, Vix!" in (proj / "main.vix").read_text("utf-8")
        assert (proj / ".gitignore").is_file()
        assert (proj / "README.md").is_file()

    def test_filesystem_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        orig_mkdir = Path.mkdir

        def _failing_mkdir(self, *args, **kwargs):
            if self.name == "failproj":
                raise PermissionError("Access denied")
            return orig_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", _failing_mkdir)
        err = _patch_stderr(monkeypatch)
        build_and_run_command(InitCmd, namespace=argparse.Namespace(name="failproj"))
        assert "创建项目失败" in err.getvalue()
