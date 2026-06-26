"""Tests for RunCmd."""

import argparse


from cmds.cmd_run import RunCmd
from cmds.cmd_build import BuildCmd


class TestRunCmd:
    @staticmethod
    def test_no_vindex(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cmd = _make_cmd()
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_build_failure(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')

        def mock_build_execute(self):
            return 1

        monkeypatch.setattr(BuildCmd, "execute", mock_build_execute)

        cmd = _make_cmd()
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_output_not_generated(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')

        def mock_build_execute(self):
            return 0

        monkeypatch.setattr(BuildCmd, "execute", mock_build_execute)
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))

        cmd = _make_cmd()
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_full_run_with_cleanup(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        output = tmp_path / "test.exe"
        output.write_text("binary data")

        def mock_build_execute(self):
            return 0

        monkeypatch.setattr(BuildCmd, "execute", mock_build_execute)
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))

        cmd = _make_cmd()
        result = cmd.execute()
        assert result is None
        # output should be cleaned up
        assert not output.exists()

    @staticmethod
    def test_full_run_with_keep(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        output = tmp_path / "test.exe"
        output.write_text("binary data")

        def mock_build_execute(self):
            return 0

        monkeypatch.setattr(BuildCmd, "execute", mock_build_execute)
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))

        ns = argparse.Namespace(keep=True, vdebug=False)
        cmd = _make_cmd(namespace=ns)
        result = cmd.execute()
        assert result is None
        assert output.exists()

    @staticmethod
    def test_run_nonzero_exit(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        output = tmp_path / "test.exe"
        output.write_text("binary data")

        def mock_build_execute(self):
            return 0

        monkeypatch.setattr(BuildCmd, "execute", mock_build_execute)
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(1))

        cmd = _make_cmd()
        result = cmd.execute()
        assert result is None

    @staticmethod
    def test_run_with_vdebug(tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "vindex.toml").write_text('[project]\nname = "test"\n')
        output = tmp_path / "test.exe"
        output.write_text("binary data")

        def mock_build_execute(self):
            return 0

        monkeypatch.setattr(BuildCmd, "execute", mock_build_execute)
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _result(0))

        ns = argparse.Namespace(keep=True, vdebug=True)
        cmd = _make_cmd(namespace=ns)
        result = cmd.execute()
        assert result is None


# -----------------------------------------------------------------------
#  helpers
# -----------------------------------------------------------------------

def _make_cmd(namespace: argparse.Namespace | None = None) -> RunCmd:
    parser = argparse.ArgumentParser(prog="very")
    subparsers = parser.add_subparsers(dest="subcommand")
    cmd = RunCmd(subparsers)
    cmd.namespace = namespace or argparse.Namespace(keep=False, vdebug=False)
    cmd.extra_args = []
    return cmd


def _result(returncode: int):
    return type("R", (), {"returncode": returncode})()
