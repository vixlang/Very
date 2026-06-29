import shutil

import typer

from .share import log
from .share import _remove_readonly
from .utils import Config, ask_confirm, parse_pack_name

app = typer.Typer()


@app.callback(invoke_without_command=True)
def delete(
    package: str = typer.Argument(..., help="需要删除的包名（支持简写语法）"),
):
    """删除包"""
    package_name = package

    pack_info = parse_pack_name(package_name, parent=Config.local_libs_path())
    PACK_PATH = pack_info.pack_path

    if not PACK_PATH.exists():
        global_info = parse_pack_name(package_name, parent=Config.VIX_LIBS_PATH)
        if global_info.pack_path.exists():
            pack_info = global_info
            PACK_PATH = global_info.pack_path
        else:
            log.error(
                f"包不存在: [white]{pack_info.full_name}[/white]\n"
                f"[yellow]可能的原因:[/yellow]\n"
                "  • 包名拼写错误\n"
                "  • 该包尚未安装\n"
                "  • 包路径不正确"
            )
            raise typer.Exit(code=1)

    log.info(f"删除包: {pack_info.full_name}")

    if not ask_confirm("确认删除?", default=False):
        log.warn("已取消操作")
        return

    try:
        shutil.rmtree(PACK_PATH, onexc=_remove_readonly)
        log.ok(f"包 [bold]{pack_info.full_name}[/bold] 已删除")
    except Exception as e:
        log.error(f"删除失败: {e}")
