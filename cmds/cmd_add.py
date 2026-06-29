import shutil
from pathlib import Path

import typer

from apis._event import Log, Progress
from apis.pkg import install_package
from apis.types import Config, parse_pack_name
from apis.vindex import add_dep_to_vindex
from pyrsult import Failure, Success

from .share import _remove_readonly, log
from .utils import ask_confirm, console


def _run(gen):
    with console.status("") as status:
        for event in gen:
            match event:
                case Progress(msg, _):
                    status.update(f"[cyan]{msg}[/cyan]")
                case Log(level, msg):
                    status.stop()
                    getattr(log, level)(msg)
                    status.start()
    try:
        gen.send(None)
    except StopIteration as e:
        return e.value


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
    if not global_:
        vindex_path = Path.cwd() / "vindex.toml"
        if not vindex_path.exists():
            log.error("未找到 vindex.toml\n请在项目根目录下运行此命令")
            raise typer.Exit(code=1)

    info = parse_pack_name(package, parent=Config.local_libs_path())
    dest = info.pack_path
    if dest.exists():
        log.warn(f"包已存在: [white]{info.full_name}[/white]")
        if not ask_confirm("是否覆盖现有包?", default=False):
            log.warn("已取消操作")
            return
        shutil.rmtree(dest, onexc=_remove_readonly)
        log.ok("已删除旧版本的包")

    gen = install_package(package, force_local=local)
    result = _run(gen)

    match result:
        case Success(pkg_info):
            if not global_:
                added = add_dep_to_vindex(package)
                if added:
                    log.ok(f"已添加 {package} 到 deps")
            log.ok(f"包 [bold]{pkg_info.full_name}[/bold] 添加成功")
        case Failure(err):
            log.error(f"安装失败: {err}")
            raise typer.Exit(code=1)
