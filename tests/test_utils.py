"""Tests for cmds/utils.py"""

from pathlib import Path

import pytest

from cmds.utils import (
    Config,
    Logger,
    PackageNameInfo,
    VeryFatalError,
    VIndexTool,
    iter_empty_dirs,
    iter_package_dirs,
    parse_pack_name,
)


class TestVeryFatalError:
    def test_is_subclass_of_exception(self):
        assert issubclass(VeryFatalError, Exception)


class TestConfig:
    def test_defaults_are_path_objects(self):
        assert isinstance(Config.VIX_HOME, Path)
        assert isinstance(Config.VIX_LIBS_PATH, Path)

    def test_libs_path_is_home_libs(self):
        assert Config.VIX_LIBS_PATH.name == "libs"
        assert Config.VIX_LIBS_PATH.parent == Config.VIX_HOME


class TestLogger:
    def test_critical_raises_very_fatal_error(self):
        logger = Logger()
        with pytest.raises(VeryFatalError, match="fatal msg"):
            logger.critical("fatal msg")


class TestParsePackName:
    def test_dot_format(self):
        info = parse_pack_name("fexcode.vnet")
        assert info.git_master == "github.com"
        assert info.user_name == "fexcode"
        assert info.repo_name == "vnet"
        assert info.branch_name is None

    def test_dot_format_with_branch(self):
        info = parse_pack_name("fexcode.vnet@master")
        assert info.git_master == "github.com"
        assert info.user_name == "fexcode"
        assert info.repo_name == "vnet"
        assert info.branch_name == "master"

    def test_colon_format_full_host(self):
        info = parse_pack_name("gitee.com:fexcode.vnet")
        assert info.git_master == "gitee.com"
        assert info.user_name == "fexcode"
        assert info.repo_name == "vnet"
        assert info.branch_name is None

    def test_colon_format_short_host(self):
        info = parse_pack_name("gitee:fexcode.vnet")
        assert info.git_master == "gitee.com"
        assert info.user_name == "fexcode"
        assert info.repo_name == "vnet"
        assert info.branch_name is None

    def test_at_prefix_gitee(self):
        info = parse_pack_name("@fexcode.vnet")
        assert info.git_master == "gitee.com"
        assert info.user_name == "fexcode"
        assert info.repo_name == "vnet"
        assert info.branch_name is None

    def test_bare_name(self):
        info = parse_pack_name("vnet")
        assert info.git_master == "github.com"
        assert info.user_name == "vixlang"
        assert info.repo_name == "vlib-vnet"
        assert info.branch_name is None

    def test_at_prefix_with_branch(self):
        info = parse_pack_name("@fexcode.vnet@dev")
        assert info.git_master == "gitee.com"
        assert info.user_name == "fexcode"
        assert info.repo_name == "vnet"
        assert info.branch_name == "dev"

    def test_url_format(self):
        info = parse_pack_name("https://github.com/user/repo.git")
        assert info.git_master == "github.com"
        assert info.user_name == "user"
        assert info.repo_name == "repo"
        assert info.branch_name is None

    def test_scp_format(self):
        info = parse_pack_name("git@github.com:user/repo.git")
        assert info.git_master == "github.com"
        assert info.user_name == "user"
        assert info.repo_name == "repo"
        assert info.branch_name is None

    def test_slash_format(self):
        info = parse_pack_name("user/repo")
        assert info.git_master == "github.com"
        assert info.user_name == "user"
        assert info.repo_name == "repo"
        assert info.branch_name is None

    def test_colon_with_slash_path(self):
        info = parse_pack_name("gitlab.com:myorg/myproject")
        assert info.git_master == "gitlab.com"
        assert info.user_name == "myorg"
        assert info.repo_name == "myproject"
        assert info.branch_name is None

    def test_colon_short_with_bare_path(self):
        info = parse_pack_name("gitlab:myproject")
        assert info.git_master == "gitlab.com"
        assert info.user_name == "vixlang"
        assert info.repo_name == "vlib-myproject"
        assert info.branch_name is None


class TestPackageNameInfo:
    def test_git_url(self):
        info = PackageNameInfo(
            repo_name="vnet", user_name="fexcode", git_master="github.com"
        )
        assert info.git_url == "https://github.com/fexcode/vnet"

    def test_full_name(self):
        info = PackageNameInfo(
            repo_name="vnet", user_name="fexcode", git_master="github.com"
        )
        assert info.full_name == "github.com:fexcode.vnet"

    def test_pack_path_uses_expected_structure(self):
        info = PackageNameInfo(
            repo_name="vnet", user_name="fexcode", git_master="github.com"
        )
        assert (
            info.pack_path == Config.VIX_LIBS_PATH / "github.com" / "fexcode" / "vnet"
        )

    def test_pack_path_raises_on_traversal(self):
        info = PackageNameInfo(repo_name="..", user_name="..", git_master="github.com")
        with pytest.raises(ValueError, match="路径穿越检测"):
            _ = info.pack_path

    def test_default_user_name(self):
        info = PackageNameInfo(repo_name="test")
        assert info.user_name == "vixlang"

    def test_default_git_master(self):
        info = PackageNameInfo(repo_name="test")
        assert info.git_master == "github.com"

    def test_branch_name_default_none(self):
        info = PackageNameInfo(repo_name="test")
        assert info.branch_name is None


class TestVIndexTool:
    def test_content_returns_dict_when_exists(self, tmp_path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "vindex.toml").write_text(
            '[package]\nname = "vnet"\nversion = "1.0.0"\n'
        )
        tool = VIndexTool(pkg)
        assert tool.content() == {"package": {"name": "vnet", "version": "1.0.0"}}

    def test_content_returns_none_when_missing(self, tmp_path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        tool = VIndexTool(pkg)
        assert tool.content() is None

    def test_path_attribute(self, tmp_path):
        pkg = tmp_path / "pkg"
        tool = VIndexTool(pkg)
        assert tool.path == pkg / "vindex.toml"


class TestIterPackageDirs:
    def test_yields_packages(self, tmp_path):
        libs = tmp_path / "libs"
        (libs / "github.com" / "user1" / "repo1").mkdir(parents=True)
        (libs / "github.com" / "user1" / "repo2").mkdir(parents=True)
        result = list(iter_package_dirs(libs))
        assert len(result) == 2
        labels = {r[3] for r in result}
        assert "github.com:user1.repo1" in labels
        assert "github.com:user1.repo2" in labels

    def test_skips_non_directory_entries(self, tmp_path):
        libs = tmp_path / "libs"
        libs.mkdir()
        (libs / "file.txt").write_text("")
        (libs / "host" / "user" / "pkg").mkdir(parents=True)
        result = list(iter_package_dirs(libs))
        assert len(result) == 1

    def test_empty_libs_yields_nothing(self, tmp_path):
        libs = tmp_path / "libs"
        libs.mkdir()
        assert list(iter_package_dirs(libs)) == []

    def test_yields_correct_tuple(self, tmp_path):
        libs = tmp_path / "libs"
        (libs / "example.com" / "author" / "mypkg").mkdir(parents=True)
        result = list(iter_package_dirs(libs))
        assert len(result) == 1
        m, u, r, label = result[0]
        assert m.name == "example.com"
        assert u.name == "author"
        assert r.name == "mypkg"
        assert label == "example.com:author.mypkg"


class TestIterEmptyDirs:
    def test_yields_empty_repo_dir(self, tmp_path):
        libs = tmp_path / "libs"
        empty = libs / "host" / "user" / "empty"
        empty.mkdir(parents=True)
        result = list(iter_empty_dirs(libs))
        assert empty in result

    def test_yields_empty_user_dir(self, tmp_path):
        libs = tmp_path / "libs"
        empty = libs / "host" / "empty_user"
        empty.mkdir(parents=True)
        result = list(iter_empty_dirs(libs))
        assert empty in result

    def test_yields_empty_host_dir(self, tmp_path):
        libs = tmp_path / "libs"
        empty = libs / "empty_host"
        empty.mkdir(parents=True)
        result = list(iter_empty_dirs(libs))
        assert empty in result

    def test_does_not_yield_non_empty_dirs(self, tmp_path):
        libs = tmp_path / "libs"
        (libs / "host" / "user" / "pkg").mkdir(parents=True)
        (libs / "host" / "user" / "pkg" / "file.txt").write_text("data")
        result = list(iter_empty_dirs(libs))
        assert result == []

    def test_partially_empty_does_not_yield_parent(self, tmp_path):
        libs = tmp_path / "libs"
        (libs / "host" / "user" / "pkg1").mkdir(parents=True)
        (libs / "host" / "user" / "pkg1" / "file.txt").write_text("data")
        (libs / "host" / "user" / "empty_pkg").mkdir(parents=True)
        result = list(iter_empty_dirs(libs))
        assert libs / "host" / "user" / "empty_pkg" in result
        assert libs / "host" / "user" not in result
        assert libs / "host" not in result

    def test_empty_libs_yields_nothing(self, tmp_path):
        libs = tmp_path / "libs"
        libs.mkdir()
        assert list(iter_empty_dirs(libs)) == []
