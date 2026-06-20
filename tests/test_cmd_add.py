import argparse
from io import StringIO
from pathlib import Path
from itertools import chain, repeat

from git.remote import RemoteProgress
from rich.console import Console

from cmds.cmd_add import AddCmd
from cmds.installer import GitProgress
from cmds.utils import PackageNameInfo, Config

from .conftest import build_and_run_command

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _fix_pack_path_default(monkeypatch, libs_path: Path) -> None:
    """Point ``PackageNameInfo.pack_path`` default parent to *libs_path*."""
    monkeypatch.setattr(PackageNameInfo, "_default_parent", libs_path)
    monkeypatch.setattr(Config, "VIX_LIBS_PATH", libs_path)


def _patch_stderr(monkeypatch) -> StringIO:
    """Replace ``err_console`` with a ``StringIO``-backed one so tests can
    inspect stderr output (e.g. error panels from ``log.error``)."""
    buf = StringIO()
    monkeypatch.setattr("cmds.utils.err_console", Console(file=buf))
    return buf


def _make_clone_mock(*, create_vindex: bool = True, fail: bool = False):
    """Return a callable that stands in for ``Repo.clone_from``."""

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


# ======================================================================
#  GitProgress unit tests
# ======================================================================


class TestGitProgress:
    """Chinese operation-name mapping and BEGIN/END flag masking."""

    def setup_method(self) -> None:
        self.gp = GitProgress(None, "pkg")

    def test_counting(self):
        assert self.gp._get_operation_name(RemoteProgress.COUNTING) == "统计对象"

    def test_compressing(self):
        assert self.gp._get_operation_name(RemoteProgress.COMPRESSING) == "压缩对象"

    def test_writing(self):
        assert self.gp._get_operation_name(RemoteProgress.WRITING) == "写入对象"

    def test_unknown_op_code(self):
        assert self.gp._get_operation_name(999) == "处理中"

    def test_masking_begin(self):
        op = RemoteProgress.COUNTING | RemoteProgress.BEGIN
        assert self.gp._get_operation_name(op) == "统计对象"

    def test_masking_end(self):
        op = RemoteProgress.COUNTING | RemoteProgress.END
        assert self.gp._get_operation_name(op) == "统计对象"


# ======================================================================
#  AddCmd integration scenarios
# ======================================================================


class TestAddCmd:

    # -- 1. Fresh install -----------------------------------------------

    def test_fresh_install(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        monkeypatch.setattr(
            "cmds.installer.Repo.clone_from",
            _make_clone_mock(create_vindex=True),
        )

        build_and_run_command(
            AddCmd, namespace=argparse.Namespace(package="fexcode.vnet", global_install=True)
        )

        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        assert pkg.is_dir()
        assert (pkg / "vindex.toml").is_file()

    # -- 2. Dir exists → overwrite confirmed → clone OK -----------------

    def test_overwrite_confirmed(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        pkg.mkdir(parents=True, exist_ok=True)
        old_file = pkg / "old_file.txt"
        old_file.write_text("old")

        monkeypatch.setattr(
            "cmds.installer.Repo.clone_from",
            _make_clone_mock(create_vindex=True),
        )
        monkeypatch.setattr(
            "cmds.cmd_add.ask_confirm",
            lambda prompt, default=False: True,
        )

        build_and_run_command(
            AddCmd, namespace=argparse.Namespace(package="fexcode.vnet", global_install=True)
        )

        assert not old_file.exists()
        assert (pkg / "vindex.toml").is_file()

    # -- 3. Dir exists → overwrite cancelled ----------------------------

    def test_overwrite_cancelled(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        pkg.mkdir(parents=True, exist_ok=True)
        old_file = pkg / "old_file.txt"
        old_file.write_text("old")

        monkeypatch.setattr(
            "cmds.cmd_add.ask_confirm",
            lambda prompt, default=False: False,
        )

        build_and_run_command(
            AddCmd, namespace=argparse.Namespace(package="fexcode.vnet", global_install=True)
        )

        assert old_file.exists()

    # -- 4. Clone fails → cleanup → error logged ------------------------

    def test_clone_failure(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        err = _patch_stderr(monkeypatch)
        monkeypatch.setattr(
            "cmds.installer.Repo.clone_from",
            _make_clone_mock(fail=True),
        )

        build_and_run_command(
            AddCmd, namespace=argparse.Namespace(package="fexcode.vnet", global_install=True)
        )

        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        assert not pkg.exists()
        assert "下载失败" in err.getvalue()

    # -- 5. Clone succeeds → no vindex → user confirms delete -----------

    def test_no_vindex_delete(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        monkeypatch.setattr(
            "cmds.installer.Repo.clone_from",
            _make_clone_mock(create_vindex=False),
        )
        monkeypatch.setattr(
            "cmds.cmd_add.ask_confirm",
            lambda prompt, default=False: True,
        )

        build_and_run_command(
            AddCmd, namespace=argparse.Namespace(package="fexcode.vnet", global_install=True)
        )

        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        assert not pkg.exists()

    # -- 6. Clone succeeds → no vindex → user keeps it ------------------

    def test_no_vindex_keep(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        monkeypatch.setattr(
            "cmds.installer.Repo.clone_from",
            _make_clone_mock(create_vindex=False),
        )
        monkeypatch.setattr(
            "cmds.cmd_add.ask_confirm",
            lambda prompt, default=False: False,
        )

        build_and_run_command(
            AddCmd, namespace=argparse.Namespace(package="fexcode.vnet", global_install=True)
        )

        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        assert pkg.is_dir()
        assert not (pkg / "vindex.toml").is_file()

    # -- 7. Dir exists → overwrite → no vindex → user confirms delete ---
    #     (two ask_confirm calls: overwrite + delete-incomplete)

    def test_pre_existing_no_vindex_delete(self, tmp_config, monkeypatch):
        _fix_pack_path_default(monkeypatch, tmp_config["libs_path"])
        pkg = tmp_config["libs_path"] / "github.com" / "fexcode" / "vnet"
        pkg.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(
            "cmds.installer.Repo.clone_from",
            _make_clone_mock(create_vindex=False),
        )
        answers = chain([True, True], repeat(True))
        monkeypatch.setattr(
            "cmds.cmd_add.ask_confirm",
            lambda prompt, default=False: next(answers),
        )

        build_and_run_command(
            AddCmd, namespace=argparse.Namespace(package="fexcode.vnet", global_install=True)
        )

        assert not pkg.exists()
