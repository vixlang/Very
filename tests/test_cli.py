from types import SimpleNamespace

from pyrsult import Success
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


def test_tool_prune_help():
    result = runner.invoke(app, ["tool", "prune", "--help"])
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


def test_exe_uses_installed_binary_path_after_auto_install(tmp_path, monkeypatch):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True)
    installed_binary = tools_dir / "vtool-pnum.exe"
    installed_binary.write_text("", encoding="utf-8")

    monkeypatch.setattr(cmd_exe.Config, "VIX_TOOLS_PATH", tools_dir)

    def fake_install_tool(_tool):
        yield cmd_exe.Log("info", "安装工具: pnum")
        return Success(SimpleNamespace(full_name="github.com:vixlang.vtool-pnum", binary_path=installed_binary))

    monkeypatch.setattr(cmd_exe, "install_tool", fake_install_tool)

    Called = {}

    def fake_run(args):
        Called["args"] = args
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cmd_exe.subprocess, "run", fake_run)

    result = runner.invoke(app, ["exe", "pnum", "114"])

    assert result.exit_code == 0
    assert Called["args"] == [str(installed_binary), "114"]
