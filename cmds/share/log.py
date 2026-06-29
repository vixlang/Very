import sys
from random import choice

from rich.console import Console

_console = Console()
_err_console = Console(file=sys.stderr)


class _Logger:
    def debug(self, msg: str) -> None:
        _console.print(f"[white on grey]DEBUG[/]\t[dim]{msg}[/dim]")

    def ok(self, msg: str) -> None:
        happy_word = choice(["NICE", "GOOD", "GREAT", "WON", "YEAH"])
        _console.print(f"[white on green]{happy_word}![/]\t[green]{msg}[/green]")

    def info(self, msg: str) -> None:
        _console.print(f"[white on cyan]INFO[/]\t[cyan]{msg}[/cyan]")

    def warn(self, msg: str) -> None:
        _console.print(f"[white on yellow]WARN![/]\t[yellow]{msg}[/yellow]")

    def error(self, msg: str) -> None:
        happy_word = choice(["FUCK", "SHIT", "OHNO"])
        _err_console.print(f"[white on red]{happy_word}![/]\t[red]{msg}[/red]")


log = _Logger()
