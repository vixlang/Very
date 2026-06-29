from pathlib import Path

import typer
from git import Repo

from .installer import PackageInstaller
from .utils import Config, console, iter_package_dirs, parse_pack_name

app = typer.Typer()


def _update_one(
    display_name: str, repo_path: Path, libs_parent: Path, visited: set[str]
):
    if repo_path.exists() and display_name in visited:
        return
    visited.add(display_name)
    if not repo_path.exists():
        console.print(f"[red]包 {display_name} 未安装[/red]")
        return
    console.print(f"[cyan]正在更新 {display_name} ...[/cyan]")
    try:
        repo = Repo(repo_path)
        origin = repo.remotes.origin
        pull_info = origin.pull()
        if pull_info:
            typer.secho(f"{display_name} 已更新到最新", fg="green")
        else:
            typer.secho(f"{display_name} 已经是最新", fg="cyan")
    except Exception as e:
        console.print(f"[red]更新 {display_name} 失败: {e}[/red]")
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
            console.print(
                f"  [cyan]└ 检测到 {len(transitive)} 个传递依赖: [dim]{', '.join(transitive)}[/dim][/cyan]"
            )
            for dep_spec in transitive:
                if dep_spec in visited:
                    continue
                dep_info = parse_pack_name(dep_spec, parent=libs_parent)
                if dep_info.pack_path.exists():
                    _update_one(dep_spec, dep_info.pack_path, libs_parent, visited)
                else:
                    console.print(
                        f"    [cyan]⊳ {dep_spec} 尚未安装, 正在安装...[/cyan]"
                    )
                    result = PackageInstaller.install_one(dep_spec, parent=libs_parent)
                    if result.success:
                        typer.secho(f"    ✔ {dep_spec}", fg="green")
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
            typer.secho("没有已安装的包", fg="cyan")
            return
        packages = list(iter_package_dirs(local_libs))
        if not packages:
            typer.secho("没有已安装的包", fg="cyan")
            return
        console.print("[bold cyan]更新所有包[/bold cyan]")
        visited: set[str] = set()
        for _md, _ud, rd, full_name in packages:
            _update_one(full_name, rd, local_libs, visited)
