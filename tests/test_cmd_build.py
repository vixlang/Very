"""Tests for BuildCmd."""

import argparse
import sys


from cmds.cmd_build import BuildCmd


class TestBuildCmdExtractOutputName:
    @staticmethod
    def test_no_flag():
        output, rest = BuildCmd._extract_output_name(["--target=wasm32"])
        assert output is None
        assert rest == ["--target=wasm32"]

    @staticmethod
    def test_with_flag():
        output, rest = BuildCmd._extract_output_name(["-o", "hello.exe", "--target=wasm32"])
        assert output == "hello.exe"
        assert rest == ["--target=wasm32"]

    @staticmethod
    def test_flag_at_end():
        output, rest = BuildCmd._extract_output_name(["-o"])
        assert output is None
        assert rest == ["-o"]

    @staticmethod
    def test_multiple_o():
        output, rest = BuildCmd._extract_output_name(["-o", "first.exe", "main.vix", "-o", "second.exe"])
        assert output == "second.exe"
        assert rest == ["main.vix"]


class TestBuildCmdExtractInputFile:
    @staticmethod
    def test_no_vix():
        input_file, rest = BuildCmd._extract_input_file(["--target=wasm32"])
        assert input_file is None
        assert rest == ["--target=wasm32"]

    @staticmethod
    def test_with_vix():
        input_file, rest = BuildCmd._extract_input_file(["src/main.vix", "--target=wasm32"])
        assert input_file is not None
        assert input_file.name == "main.vix"
        assert rest == ["--target=wasm32"]

    @staticmethod
    def test_first_vix_wins():
        input_file, rest = BuildCmd._extract_input_file(["a.vix", "b.vix"])
        assert input_file is not None
        assert input_file.name == "a.vix"
        assert rest == ["b.vix"]


class TestBuildCmdDefaultOutputName:
    @staticmethod
    def test_with_vindex(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "myapp"\n')
        name = BuildCmd._default_output_name()
        expected = "myapp.exe" if sys.platform == "win32" else "myapp"
        assert name == expected

    @staticmethod
    def test_without_vindex(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        name = BuildCmd._default_output_name()
        expected = "main.exe" if sys.platform == "win32" else "main"
        assert name == expected

    @staticmethod
    def test_vindex_without_name(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nversion = "1.0"\n')
        name = BuildCmd._default_output_name()
        expected = "main.exe" if sys.platform == "win32" else "main"
        assert name == expected


class TestBuildCmdHasGcc:
    @staticmethod
    def test_gcc_found(monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/gcc" if x == "gcc" else None)
        assert BuildCmd._has_gcc() is True

    @staticmethod
    def test_gcc_not_found(monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: None)
        assert BuildCmd._has_gcc() is False


class TestBuildCmdCreateForSubcommand:
    @staticmethod
    def test_creates_instance():
        ns = argparse.Namespace()
        cmd = BuildCmd.create_for_subcommand(ns, ["--verbose"], silent=True)
        assert cmd.namespace is ns
        assert cmd.extra_args == ["--verbose"]
        assert cmd.silent is True
        assert cmd.parser is None


class TestBuildCmdExecute:
    @staticmethod
    def test_no_vindex(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd = _make_cmd()
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_no_input_no_main_vix(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        cmd = _make_cmd()
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_direct_compile_success(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "main.vix").write_text("// test")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))
        monkeypatch.setattr(BuildCmd, "_has_gcc", lambda self: False)

        cmd = _make_cmd()
        result = cmd.execute()
        assert result == 0

    @staticmethod
    def test_direct_compile_failure(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "main.vix").write_text("// test")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(1))
        monkeypatch.setattr(BuildCmd, "_has_gcc", lambda self: False)

        cmd = _make_cmd()
        result = cmd.execute()
        assert result == 1

    @staticmethod
    def test_gcc_path_success(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        vix_file = tmp_path / "app.vix"
        vix_file.write_text("// test")

        call_count = 0

        def mock_subprocess(*a, **kw):
            nonlocal call_count
            call_count += 1
            return _result(0)

        monkeypatch.setattr("subprocess.run", mock_subprocess)
        monkeypatch.setattr(BuildCmd, "_has_gcc", lambda self: True)

        cmd = _make_cmd([str(vix_file)])
        result = cmd.execute()
        assert result == 0
        assert call_count == 2  # compile + link

    @staticmethod
    def test_gcc_path_compile_fails(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        vix_file = tmp_path / "app.vix"
        vix_file.write_text("// test")

        call_count = 0

        def mock_subprocess(*a, **kw):
            nonlocal call_count
            call_count += 1
            return _result(1)

        monkeypatch.setattr("subprocess.run", mock_subprocess)
        monkeypatch.setattr(BuildCmd, "_has_gcc", lambda self: True)

        cmd = _make_cmd([str(vix_file)])
        result = cmd.execute()
        assert result == 1
        assert call_count == 1  # only compile, link skipped

    @staticmethod
    def test_custom_output_name(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "main.vix").write_text("// test")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))
        monkeypatch.setattr(BuildCmd, "_has_gcc", lambda self: False)

        cmd = _make_cmd(["-o", "custom_app.exe"])
        result = cmd.execute()
        assert result == 0

    @staticmethod
    def test_silent_mode(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        (tmp_path / "main.vix").write_text("// test")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))
        monkeypatch.setattr(BuildCmd, "_has_gcc", lambda self: False)

        cmd = BuildCmd.create_for_subcommand(argparse.Namespace(), [], silent=True)
        cmd.extra_args = []
        result = cmd.execute()
        assert result == 0


# -----------------------------------------------------------------------
#  helpers
# -----------------------------------------------------------------------

def _make_cmd(extra_args: list[str] | None = None) -> BuildCmd:
    parser = argparse.ArgumentParser(prog="very")
    subparsers = parser.add_subparsers(dest="subcommand")
    cmd = BuildCmd(subparsers)
    cmd.namespace = argparse.Namespace()
    cmd.extra_args = extra_args or []
    return cmd


def _result(returncode: int):
    return type("R", (), {"returncode": returncode})()
