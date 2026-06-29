from pathlib import Path

import pytest

from cmds.utils import PackageNameInfo, parse_pack_name


def test_git_url():
    info = parse_pack_name("vnet")
    assert info.git_url == "https://github.com/vixlang/vlib-vnet"


def test_full_name():
    info = parse_pack_name("fexcode.vnet@dev")
    assert info.full_name == "github.com:fexcode.vnet"


def test_pack_path_default():
    info = parse_pack_name("vnet")
    assert info.pack_path.name == "vlib-vnet"
    assert "vixlang" in str(info.pack_path)
    assert "github.com" in str(info.pack_path)


def test_pack_path_custom_parent():
    info = parse_pack_name("vnet", parent=Path("/tmp/mylibs"))
    assert info.pack_path == Path("/tmp/mylibs/github.com/vixlang/vlib-vnet")


def test_pack_path_traversal():
    info = PackageNameInfo(
        repo_name="evil",
        git_master="..",
        user_name="..",
        parent=Path("/safe"),
    )
    with pytest.raises(ValueError, match="包路径穿越检测"):
        _ = info.pack_path


def test_default_parent_classvar(tmp_path):
    PackageNameInfo._default_parent = tmp_path / "libs"
    info = PackageNameInfo(repo_name="mylib", user_name="me", git_master="example.com")
    assert info.pack_path == tmp_path / "libs" / "example.com" / "me" / "mylib"
