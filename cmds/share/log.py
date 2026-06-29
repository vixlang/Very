import sys

from rich.console import Console

_console = Console()
_err_console = Console(file=sys.stderr)


class _Logger:
    def debug(self, msg: str) -> None:
        _console.print(f"[dim]{msg}[/dim]")

    def ok(self, msg: str) -> None:
        _console.print(f"[green]{msg}[/green]")

    def info(self, msg: str) -> None:
        _console.print(f"[cyan]{msg}[/cyan]")

    def warn(self, msg: str) -> None:
        _console.print(f"[yellow]{msg}[/yellow]")

    def error(self, msg: str) -> None:
        _err_console.print(f"[red]{msg}[/red]")


log = _Logger()
