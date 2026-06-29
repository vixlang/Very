import shutil
from pathlib import Path

import typer

from .installer import PackageInstaller
from .share import _remove_readonly, log
from .utils import (
    Config,
    add_dep_to_vindex,
    ask_confirm,
    parse_pack_name,
)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def add(
    package: str = typer.Argument(..., help="需要添加的包名"),
    global_: bool = typer.Option(
        False, "-g", "--global", help="全局安装到 VIX_HOME 目录"
    ),
    local: bool = typer.Option(
        False, "-l", "--local", help="强制在项目 .vix 目录下载（即使全局已存在）"
    ),
):
    """添加包(需要git)"""
    packname = package
    global_install = global_
    local_force = local

    if not global_install:
        vindex_path = Path.cwd() / "vindex.toml"
        if not vindex_path.exists():
            log.error("未找到 vindex.toml\n" "请在项目根目录下运行此命令")
            raise typer.Exit(code=1)

    if global_install:
        parent = Config.VIX_LIBS_PATH
    else:
        parent = Config.local_libs_path()

    packinfo = parse_pack_name(packname, parent=parent)

    if not global_install and not local_force:
        global_packinfo = parse_pack_name(packname, parent=Config.VIX_LIBS_PATH)
        if global_packinfo.pack_path.exists():
            added = add_dep_to_vindex(packname)
            if added:
                log.ok(f"已添加 {packinfo.full_name} 到 deps (使用全局副本)")
            else:
                log.info(f"deps 中已存在: {packname}")
            return

    pack_path = packinfo.pack_path

    if pack_path.exists():
        log.warn(f"包已存在: [white]{packinfo.full_name}[/white]")
        log.info(f"安装位置: {pack_path}")

        if not ask_confirm("是否覆盖现有包?", default=False):
            log.warn("已取消操作")
            return

        shutil.rmtree(pack_path, onexc=_remove_readonly)
        log.ok(f"已删除旧版本的包 {packinfo.full_name}")

    log.info(f"添加包: {packinfo.full_name}")
    log.info(f"源: {packinfo.git_url}")
    if packinfo.branch_name:
        log.info(f"分支: {packinfo.branch_name}")

    result = PackageInstaller.install_one(packname, parent=parent)

    if not result.success:
        if result.no_vindex:
            log.warn(f"包缺少 vindex.toml: [white]{packinfo.full_name}[/white]")
            if ask_confirm("是否删除此不完整的包?", default=True):
                shutil.rmtree(pack_path, onexc=_remove_readonly)
                log.warn(f"已删除不完整的包 {packinfo.full_name}")
            else:
                log.warn(f"已保留包 {packinfo.full_name}，但它可能无法使用")
        else:
            log.error(
                f"下载失败\n\n{result.reason}\n\n"
                "请检查:\n"
                "  • 网络连接是否正常\n"
                "  • 仓库地址是否正确\n"
                "  • 是否有访问权限"
            )
        return

    if not global_install:
        added = add_dep_to_vindex(packname)
        if added:
            log.ok(f"已添加 {packname} 到 deps")

        vindex_path = pack_path / "vindex.toml"
        if vindex_path.exists():
            import tomllib

            with open(vindex_path, "rb") as f:
                vindex_data = tomllib.load(f)
            pkg_deps = vindex_data.get("project", {}).get("deps", [])
            pkg_legacy = list(vindex_data.get("dependencies", {}).keys())
            transitive = list(dict.fromkeys(pkg_deps + pkg_legacy))
            if transitive:
                log.info(
                    f"检测到 {len(transitive)} 个传递依赖: {', '.join(transitive)}"
                )
                PackageInstaller.install_transitive_deps(parent, transitive)

    log.ok(f"包 {packinfo.full_name} 添加成功")
