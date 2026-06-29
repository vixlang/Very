from pathlib import Path

import typer
from git import Repo

from .installer import PackageInstaller
from .share import log
from .utils import Config, iter_package_dirs, parse_pack_name

app = typer.Typer()


def _update_one(
    display_name: str, repo_path: Path, libs_parent: Path, visited: set[str]
):
    if repo_path.exists() and display_name in visited:
        return
    visited.add(display_name)
    if not repo_path.exists():
        log.error(f"包 {display_name} 未安装")
        return
    log.info(f"正在更新 {display_name} ...")
    try:
        repo = Repo(repo_path)
        origin = repo.remotes.origin
        pull_info = origin.pull()
        if pull_info:
            log.ok(f"{display_name} 已更新到最新")
        else:
            log.info(f"{display_name} 已经是最新")
    except Exception as e:
        log.error(f"更新 {display_name} 失败: {e}")
        return

    vindex_path = repo_path / "vindex.toml"
    if vindex_path.exists():
        import tomllib

        with open(vindex_path, "rb") as f:
            data = tomllib.load(f)
        deps = data.get("project", {}).get("deps", [])
        legacy = list(data.get("dependencies", {}).keys())
        transitive = list(dict.fromkeys(deps + legacy))
        if transitive:
            log.info(
                f"检测到 {len(transitive)} 个传递依赖: [dim]{', '.join(transitive)}[/dim]"
            )
            for dep_spec in transitive:
                if dep_spec in visited:
                    continue
                dep_info = parse_pack_name(dep_spec, parent=libs_parent)
                if dep_info.pack_path.exists():
                    _update_one(dep_spec, dep_info.pack_path, libs_parent, visited)
                else:
                    log.info(f"⊳ {dep_spec} 尚未安装, 正在安装...")
                    result = PackageInstaller.install_one(dep_spec, parent=libs_parent)
                    if result.success:
                        log.ok(f"✔ {dep_spec}")
                        dep_path = parse_pack_name(
                            dep_spec, parent=libs_parent
                        ).pack_path
                        _update_one(dep_spec, dep_path, libs_parent, visited)


@app.callback(invoke_without_command=True)
def update(
    package: str = typer.Argument(
        None, help="要更新的包名（不指定则更新所有已安装的包）"
    ),
):
    """更新已安装的包"""
    packname = package
    local_libs = Config.local_libs_path()

    if packname:
        packinfo = parse_pack_name(packname, parent=local_libs)
        _update_one(packinfo.full_name, packinfo.pack_path, local_libs, set())
    else:
        if not local_libs.exists():
            log.info("没有已安装的包")
            return
        packages = list(iter_package_dirs(local_libs))
        if not packages:
            log.info("没有已安装的包")
            return
        log.info("更新所有包")
        visited: set[str] = set()
        for _md, _ud, rd, full_name in packages:
            _update_one(full_name, rd, local_libs, visited)
