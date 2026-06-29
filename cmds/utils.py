import sys

from rich.console import Console
from rich.prompt import Confirm

console = Console()
err_console = Console(file=sys.stderr)


def ask_confirm(prompt: str, default: bool = False) -> bool:
    return Confirm.ask(prompt, default=default)


def create_git_progress(package_name: str):
    from rich.progress import (
        BarColumn,
        Progress,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )

    return Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
    )
