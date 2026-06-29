from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from cmds import cmd_exe
from main import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Very" in result.output


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Commands" in result.output or "命令" in result.output


def test_add_help():
    result = runner.invoke(app, ["add", "--help"])
    assert result.exit_code == 0


def test_del_help():
    result = runner.invoke(app, ["del", "--help"])
    assert result.exit_code == 0


def test_list_help():
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0


def test_search_help():
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0


def test_tool_help():
    result = runner.invoke(app, ["tool", "--help"])
    assert result.exit_code == 0


def test_tool_add_help():
    result = runner.invoke(app, ["tool", "add", "--help"])
    assert result.exit_code == 0


def test_tool_del_help():
    result = runner.invoke(app, ["tool", "del", "--help"])
    assert result.exit_code == 0


def test_tool_update_help():
    result = runner.invoke(app, ["tool", "update", "--help"])
    assert result.exit_code == 0


def test_tool_search_help():
    result = runner.invoke(app, ["tool", "search", "--help"])
    assert result.exit_code == 0


def test_exe_help():
    result = runner.invoke(app, ["exe", "--help"])
    assert result.exit_code == 0


def test_exe_treats_tool_name_as_argument():
    result = runner.invoke(app, ["exe", "pnum"])
    assert "No such command 'pnum'" not in result.output


def test_exe_forwards_extra_args(tmp_path, monkeypatch):
    tool_path = tmp_path / "tools" / "pnum.exe"
    tool_path.parent.mkdir(parents=True)
    tool_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(cmd_exe.Config, "VIX_TOOLS_PATH", tool_path.parent)

    Called = {}

    def fake_run(args):
        Called["args"] = args
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cmd_exe.subprocess, "run", fake_run)

    result = runner.invoke(app, ["exe", "pnum", "114"])

    assert result.exit_code == 0
    assert Called["args"] == [str(tool_path), "114"]


def test_cmd_exe_still_exports_compat_app():
    assert isinstance(cmd_exe.app, cmd_exe.typer.Typer)
