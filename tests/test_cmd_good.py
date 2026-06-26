"""Tests for GoodCmd."""

import argparse


from cmds.cmd_good import GoodCmd


class TestGoodCmdResolveFiles:
    @staticmethod
    def test_no_patterns_main_exists(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "main.vix").write_text("// test")
        cmd = _make_cmd()
        files = cmd._resolve_files([])
        assert len(files) == 1
        assert files[0].name == "main.vix"

    @staticmethod
    def test_no_patterns_main_missing(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd = _make_cmd()
        files = cmd._resolve_files([])
        assert files == []

    @staticmethod
    def test_with_directory(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        srcdir = tmp_path / "src"
        srcdir.mkdir()
        (srcdir / "mod.vix").write_text("// test")
        (srcdir / "util.vix").write_text("// test")
        cmd = _make_cmd()
        files = cmd._resolve_files(["src"])
        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"mod.vix", "util.vix"}

    @staticmethod
    def test_with_wildcard(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.vix").write_text("// test")
        (tmp_path / "b.vix").write_text("// test")
        (tmp_path / "c.txt").write_text("text")
        cmd = _make_cmd()
        files = cmd._resolve_files(["*.vix"])
        assert len(files) == 2

    @staticmethod
    def test_with_specific_file(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "custom.vix").write_text("// test")
        cmd = _make_cmd()
        files = cmd._resolve_files(["custom.vix"])
        assert len(files) == 1
        assert files[0].name == "custom.vix"

    @staticmethod
    def test_non_existent_file(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd = _make_cmd()
        files = cmd._resolve_files(["nonexistent.vix"])
        assert len(files) == 0

    @staticmethod
    def test_duplicates_removed(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "same.vix").write_text("// test")
        cmd = _make_cmd()
        files = cmd._resolve_files(["same.vix", "same.vix"])
        assert len(files) == 1


class TestGoodCmdExecute:
    @staticmethod
    def test_no_vindex(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd = _make_cmd(namespace=argparse.Namespace(files=[]))
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_no_matching_files_with_pattern(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        cmd = _make_cmd(namespace=argparse.Namespace(files=["nonexistent.vix"]))
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_no_matching_files_without_pattern(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        cmd = _make_cmd(namespace=argparse.Namespace(files=[]))
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_all_pass(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "main.vix").write_text("// test")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))

        cmd = _make_cmd(namespace=argparse.Namespace(files=[]))
        result = cmd.execute()
        assert result == 0

    @staticmethod
    def test_has_errors(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "main.vix").write_text("// test")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(1))

        cmd = _make_cmd(namespace=argparse.Namespace(files=[]))
        result = cmd.execute()
        assert result == 1

    @staticmethod
    def test_multiple_files(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "a.vix").write_text("// test")
        (tmp_path / "b.vix").write_text("// test")

        call_count = 0

        def mock_subprocess(*a, **kw):
            nonlocal call_count
            call_count += 1
            return _result(0)

        monkeypatch.setattr("subprocess.run", mock_subprocess)

        cmd = _make_cmd(namespace=argparse.Namespace(files=["a.vix", "b.vix"]))
        result = cmd.execute()
        assert result == 0
        assert call_count == 2


# -----------------------------------------------------------------------
#  helpers
# -----------------------------------------------------------------------

def _make_cmd(namespace: argparse.Namespace | None = None) -> GoodCmd:
    parser = argparse.ArgumentParser(prog="very")
    subparsers = parser.add_subparsers(dest="subcommand")
    cmd = GoodCmd(subparsers)
    if namespace is not None:
        cmd.namespace = namespace
    else:
        cmd.namespace = argparse.Namespace()
    return cmd


def _result(returncode: int):
    return type("R", (), {"returncode": returncode})()
