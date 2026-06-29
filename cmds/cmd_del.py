import shutil

import typer
from rich.panel import Panel

from .utils import Config, _remove_readonly, ask_confirm, console, parse_pack_name

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
            console.print(
                Panel(
                    f"[bold red]包不存在: [white]{pack_info.full_name}[/white][/bold red]\n\n"
                    "[yellow]可能的原因:[/yellow]\n"
                    "  • 包名拼写错误\n"
                    "  • 该包尚未安装\n"
                    "  • 包路径不正确\n\n"
                    "[dim]使用以下命令查看已安装的包:[/dim]\n"
                    "  [green]very list[/green]\n\n"
                    "[dim]或使用以下命令安装包:[/dim]\n"
                    f"  [green]very add {package_name}[/green]",
                    title="[bold red]✘ 错误[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            raise typer.Exit(code=1)

    console.print(f"[bold cyan]删除包: {pack_info.full_name}[/bold cyan]")

    if not ask_confirm("确认删除?", default=False):
        typer.secho("已取消操作", fg="yellow")
        return

    try:
        shutil.rmtree(PACK_PATH, onexc=_remove_readonly)
        console.print(f"[green]包 [bold]{pack_info.full_name}[/bold] 已删除[/green]")
    except Exception as e:
        console.print(Panel(f"[red]删除失败: {e}[/red]", border_style="red"))
