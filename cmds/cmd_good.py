"""very good — 检查 Vix 语法和类型"""

import subprocess
from pathlib import Path

import typer

from .utils import _get_entrypoint, console

app = typer.Typer()


def _resolve_files(patterns: list[str]) -> list[Path]:
    if not patterns:
        entrypoint = _get_entrypoint()
        main = Path(entrypoint)
        return [main] if main.exists() else []

    files: list[Path] = []
    seen: set[Path] = set()
    for p in patterns:
        path = Path(p)
        if path.is_dir():
            for f in sorted(path.rglob("*.vix")):
                if f not in seen:
                    files.append(f)
                    seen.add(f)
        else:
            expanded = list(Path(".").glob(p)) if ("*" in p or "?" in p) else [path]
            for f in expanded:
                resolved = f.resolve()
                if f.exists() and resolved not in seen:
                    files.append(f)
                    seen.add(resolved)
    return files


@app.callback(invoke_without_command=True)
def good(
    files: list[str] = typer.Argument(
        None, help="要检查的 .vix 文件或目录 (支持通配符, 默认: main.vix)"
    ),
):
    """检查语法和类型"""
    if not Path("vindex.toml").exists():
        console.print("[red]未找到 vindex.toml，请确保在项目根目录运行此命令[/red]")
        raise typer.Exit(code=1)

    patterns = files or []
    resolved = _resolve_files(patterns)

    if not resolved:
        if patterns:
            console.print(f"[red]未找到匹配的文件: {' '.join(patterns)}[/red]")
        else:
            entrypoint = _get_entrypoint()
            console.print(f"[red]未找到入口文件 {entrypoint}，请指定要检查的文件[/red]")
        raise typer.Exit(code=1)

    has_error = False
    for i, f in enumerate(resolved):
        if i > 0:
            console.print()
        console.print(f"  [green]ℹ[/green]  检查: [dim]{f}[/dim]")
        result = subprocess.run(
            ["vixc", str(f), "--check"],
            cwd=Path(".").resolve(),
        )
        if result.returncode != 0:
            has_error = True

    if not has_error:
        console.print("  [green]✔[/green]  全部通过")
    raise typer.Exit(code=1 if has_error else 0)
