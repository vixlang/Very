from apis.types import parse_pack_name, parse_tool_name


def test_bare_name():
    info = parse_pack_name("vnet")
    assert info.full_name == "github.com:vixlang.vlib-vnet"


def test_dotted_name():
    info = parse_pack_name("fexcode.vnet")
    assert info.full_name == "github.com:fexcode.vnet"


def test_dotted_with_branch():
    info = parse_pack_name("fexcode.vnet@master")
    assert info.full_name == "github.com:fexcode.vnet"
    assert info.branch_name == "master"


def test_gitee_colon():
    info = parse_pack_name("gitee.com:fexcode.vnet")
    assert info.full_name == "gitee.com:fexcode.vnet"


def test_gitee_shorthand():
    info = parse_pack_name("gitee:fexcode.vnet")
    assert info.full_name == "gitee.com:fexcode.vnet"


def test_at_prefix_gitee():
    info = parse_pack_name("@fexcode.vnet")
    assert info.full_name == "gitee.com:fexcode.vnet"


def test_url():
    info = parse_pack_name("https://github.com/vixlang/vlib-vnet.git")
    assert info.full_name == "github.com:vixlang.vlib-vnet"


def test_url_no_git():
    info = parse_pack_name("https://github.com/vixlang/vlib-vnet")
    assert info.full_name == "github.com:vixlang.vlib-vnet"


def test_slash_format():
    info = parse_pack_name("vixlang/vlib-vnet")
    assert info.full_name == "github.com:vixlang.vlib-vnet"


def test_scp_format():
    info = parse_pack_name("git@github.com:vixlang/vlib-vnet.git")
    assert info.full_name == "github.com:vixlang.vlib-vnet"


def test_tool_bare():
    info = parse_tool_name("fmt")
    assert info.full_name == "github.com:vixlang.vtool-fmt"


def test_tool_with_user():
    info = parse_tool_name("fexcode.vfmt")
    assert info.full_name == "github.com:fexcode.vfmt"
