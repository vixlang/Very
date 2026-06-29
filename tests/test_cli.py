from typer.testing import CliRunner

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
