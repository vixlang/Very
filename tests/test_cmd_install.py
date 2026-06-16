import argparse
from pathlib import Path

from cmds.cmd_install import InstallCmd
from cmds.utils import PackageNameInfo

from .conftest import build_and_run_command


def _fix_pack_path_default(monkeypatch, libs_path: Path) -> None:
    monkeypatch.setattr(
        PackageNameInfo.pack_path.fget,
        "__defaults__",
        (libs_path,),
    )


def _make_clone_mock(*, create_vindex: bool = True, fail: bool = False):
    def clone_from(url, path, branch=None, progress=None):
        if fail:
            raise Exception("network error")
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        if create_vindex:
            (p / "vindex.toml").write_text(
                '[package]\nname = "test"\nversion = "0.1.0"\n'
            )

    return clone_from


class TestInstallCmd:
    def test_no_vix_toml(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        build_and_run_command(InstallCmd, namespace=argparse.Namespace())

    def test_empty_deps(self, tmp_config, monkeypatch, tmp_path):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        (tmp_path / "vix.toml").write_text('[project]\nname = "test"\n\ndeps = []\n')
        monkeypatch.chdir(tmp_path)
        build_and_run_command(InstallCmd, namespace=argparse.Namespace())

    def test_install_single_dep(self, tmp_config, monkeypatch, tmp_path):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        (tmp_path / "vix.toml").write_text('deps = ["fexcode.vnet"]\n')
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "cmds.cmd_add.Repo.clone_from",
            _make_clone_mock(create_vindex=True),
        )

        build_and_run_command(InstallCmd, namespace=argparse.Namespace())

        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        assert pkg.is_dir()
        assert (pkg / "vindex.toml").is_file()

    def test_install_already_exists(self, tmp_config, monkeypatch, tmp_path):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        pkg.mkdir(parents=True)
        (pkg / "vindex.toml").write_text(
            '[package]\nname = "vnet"\nversion = "1.0.0"\n'
        )
        (tmp_path / "vix.toml").write_text('deps = ["fexcode.vnet"]\n')
        monkeypatch.chdir(tmp_path)

        build_and_run_command(InstallCmd, namespace=argparse.Namespace())

    def test_install_clone_failure(self, tmp_config, monkeypatch, tmp_path):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        (tmp_path / "vix.toml").write_text('deps = ["fexcode.vnet"]\n')
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "cmds.cmd_add.Repo.clone_from",
            _make_clone_mock(fail=True),
        )

        build_and_run_command(InstallCmd, namespace=argparse.Namespace())

        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        assert not pkg.exists()

    def test_install_no_vindex(self, tmp_config, monkeypatch, tmp_path):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        (tmp_path / "vix.toml").write_text('deps = ["fexcode.vnet"]\n')
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "cmds.cmd_add.Repo.clone_from",
            _make_clone_mock(create_vindex=False),
        )
        monkeypatch.setattr(
            "cmds.cmd_install.ask_confirm",
            lambda prompt, default=False: True,
        )

        build_and_run_command(InstallCmd, namespace=argparse.Namespace())

        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        assert not pkg.exists()
