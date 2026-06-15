import argparse
from pathlib import Path

from cmds.cmd_update import UpdateCmd
from cmds.utils import PackageNameInfo

from .conftest import build_and_run_command


def _fix_pack_path_default(monkeypatch, libs_path: Path) -> None:
    monkeypatch.setattr(
        PackageNameInfo.pack_path.fget,
        "__defaults__",
        (libs_path,),
    )


def _make_mock_repo(exists: bool = True):
    class MockOrigin:
        def pull(self):
            return ["updated"]

    class MockRepo:
        def __init__(self, path):
            if not exists:
                raise Exception("not a git repository")
            self.remotes = type("remotes", (), {"origin": MockOrigin()})()

    return MockRepo


class TestUpdateCmd:
    def test_update_specific_package(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        pkg.mkdir(parents=True)
        (pkg / "vindex.toml").write_text(
            '[package]\nname = "vnet"\nversion = "1.0.0"\n'
        )

        monkeypatch.setattr("cmds.cmd_update.Repo", _make_mock_repo(exists=True))

        build_and_run_command(
            UpdateCmd, namespace=argparse.Namespace(package="fexcode.vnet")
        )

    def test_update_nonexistent_package(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])

        build_and_run_command(
            UpdateCmd, namespace=argparse.Namespace(package="fexcode.vnet")
        )

    def test_update_all_no_packages(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])

        build_and_run_command(
            UpdateCmd, namespace=argparse.Namespace(package=None)
        )

    def test_update_all_with_packages(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        pkg.mkdir(parents=True)
        (pkg / "vindex.toml").write_text(
            '[package]\nname = "vnet"\nversion = "1.0.0"\n'
        )

        monkeypatch.setattr("cmds.cmd_update.Repo", _make_mock_repo(exists=True))

        build_and_run_command(
            UpdateCmd, namespace=argparse.Namespace(package=None)
        )
