from .base import Command
import argparse
from .utils import log, parse_pack_name, ask_confirm
import shutil


命令格式说明 = """
[bold]vpm del 命令格式说明[/bold]

[green]格式:[/green]
    vpm del <包名>

[green]注意:[/green]
    • 默认仓库为 github.com
    • 支持简写语法

[green]示例:[/green]
    vpm del fexcode.vnet                # 删除 github.com/fexcode/vnet
    vpm del gitee.com:fexcode.vnet      # 删除 gitee.com/fexcode.vnet
    vpm del gitee:fexcode.vnet          # .com 可以省略
    vpm del @fexcode.vnet               # @ 符号开头默认为 gitee.com
"""


class DelCmd(Command):
    NAME = "del"

    def execute(self):
        package_name = getattr(self.namespace, "package", "unknown")
        pack_info = parse_pack_name(package_name)
        PACK_PATH = pack_info.pack_path

        if not PACK_PATH.exists():
            from rich.panel import Panel
            from cmds.utils import err_console
            
            err_console.print()
            err_console.print(
                Panel(
                    f"[bold red]包不存在: [white]{pack_info.full_name}[/white][/bold red]\n\n"
                    f"[yellow]可能的原因:[/yellow]\n"
                    f"  • 包名拼写错误\n"
                    f"  • 该包尚未安装\n"
                    f"  • 包路径不正确\n\n"
                    f"[dim]使用以下命令查看已安装的包:[/dim]\n"
                    f"  [green]vpm list[/green]\n\n"
                    f"[dim]或使用以下命令安装包:[/dim]\n"
                    f"  [green]vpm add {package_name}[/green]",
                    title="[bold red]✘ 错误[/bold red]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            err_console.print()
            return

        log.section(f"删除包: {pack_info.full_name}")
        
        if not ask_confirm("确认删除?", default=False):
            log.warning("已取消操作")
            return

        try:
            shutil.rmtree(PACK_PATH)
            log.success(f"包 [bold]{pack_info.full_name}[/bold] 已删除")
        except Exception as e:
            log.error(f"删除失败: {e}")

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        del_parser = p.add_parser(
            "del",
            help="删除包",
            description="从本地环境中删除已安装的 vix 包",
            epilog=命令格式说明,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        del_parser.add_argument(
            "package",
            help="需要删除的包名（支持简写语法）",
        )
        return del_parser
