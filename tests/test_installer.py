"""Tests for installer.py."""

from pathlib import Path

from cmds.installer import PackageInstaller, InstallResult, GitProgress


class TestInstallResult:
    def test_defaults(self):
        r = InstallResult(spec="test", success=True)
        assert r.skipped is False
        assert r.reason == ""
        assert r.no_vindex is False


class TestPackageInstaller:
    def test_fresh_install(self, tmp_path, monkeypatch):
        def mock_clone_from(url, path, branch=None, progress=None):
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "vindex.toml").write_text('[package]\nname = "vnet"\nversion = "1.0.0"\n')

        monkeypatch.setattr("cmds.installer.Repo.clone_from", mock_clone_from)
        result = PackageInstaller.install_one("fexcode.vnet", parent=tmp_path)
        assert result.success is True
        assert result.skipped is False
        pkg = tmp_path / "github.com" / "fexcode" / "vnet"
        assert pkg.is_dir()

    def test_already_exists(self, tmp_path):
        pkg = tmp_path / "github.com" / "fexcode" / "vnet"
        pkg.mkdir(parents=True)
        result = PackageInstaller.install_one("fexcode.vnet", parent=tmp_path)
        assert result.success is False
        assert result.skipped is True
        assert result.reason == "已存在"

    def test_clone_failure(self, tmp_path, monkeypatch):
        def mock_clone_from(url, path, branch=None, progress=None):
            raise Exception("network error")

        monkeypatch.setattr("cmds.installer.Repo.clone_from", mock_clone_from)
        result = PackageInstaller.install_one("fexcode.vnet", parent=tmp_path)
        assert result.success is False
        assert result.skipped is False
        assert "network error" in result.reason

    def test_no_vindex(self, tmp_path, monkeypatch):
        def mock_clone_from(url, path, branch=None, progress=None):
            Path(path).mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr("cmds.installer.Repo.clone_from", mock_clone_from)
        result = PackageInstaller.install_one("fexcode.vnet", parent=tmp_path)
        assert result.success is False
        assert result.no_vindex is True
        assert result.reason == "缺少 vindex.toml"

    def test_clone_partial_cleanup(self, tmp_path, monkeypatch):
        created_path = None

        def mock_clone_from(url, path, branch=None, progress=None):
            nonlocal created_path
            created_path = Path(path)
            created_path.mkdir(parents=True, exist_ok=True)
            raise Exception("partial failure")

        monkeypatch.setattr("cmds.installer.Repo.clone_from", mock_clone_from)
        result = PackageInstaller.install_one("fexcode.vnet", parent=tmp_path)
        assert result.success is False
        assert created_path is not None
        assert not created_path.exists()


class TestGitProgress:
    def setup_method(self):
        self.gp = GitProgress(None, "pkg")

    def test_counting(self):
        from git.remote import RemoteProgress
        assert self.gp._get_operation_name(RemoteProgress.COUNTING) == "统计对象"

    def test_compressing(self):
        from git.remote import RemoteProgress
        assert self.gp._get_operation_name(RemoteProgress.COMPRESSING) == "压缩对象"

    def test_writing(self):
        from git.remote import RemoteProgress
        assert self.gp._get_operation_name(RemoteProgress.WRITING) == "写入对象"

    def test_receiving(self):
        from git.remote import RemoteProgress
        assert self.gp._get_operation_name(RemoteProgress.RECEIVING) == "接收对象"

    def test_resolving(self):
        from git.remote import RemoteProgress
        assert self.gp._get_operation_name(RemoteProgress.RESOLVING) == "解析差异"

    def test_finding_sources(self):
        from git.remote import RemoteProgress
        assert self.gp._get_operation_name(RemoteProgress.FINDING_SOURCES) == "查找源"

    def test_checking_out(self):
        from git.remote import RemoteProgress
        assert self.gp._get_operation_name(RemoteProgress.CHECKING_OUT) == "检出文件"

    def test_unknown_op_code(self):
        assert self.gp._get_operation_name(999) == "处理中"

    def test_masking_begin(self):
        from git.remote import RemoteProgress
        op = RemoteProgress.COUNTING | RemoteProgress.BEGIN
        assert self.gp._get_operation_name(op) == "统计对象"

    def test_masking_end(self):
        from git.remote import RemoteProgress
        op = RemoteProgress.COUNTING | RemoteProgress.END
        assert self.gp._get_operation_name(op) == "统计对象"
