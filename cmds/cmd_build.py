"""very build — 编译 Vix 项目"""

import shutil
import subprocess
import sys
from pathlib import Path

import typer

from .utils import _get_entrypoint, console

app = typer.Typer()


def _extract_output_name(args: list[str]) -> tuple[str | None, list[str]]:
    output = None
    rest: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "-o" and i + 1 < len(args):
            output = args[i + 1]
            i += 2
            continue
        rest.append(args[i])
        i += 1
    return output, rest


def _extract_input_file(args: list[str]) -> tuple[Path | None, list[str]]:
    rest: list[str] = []
    input_file = None
    for a in args:
        if a.endswith(".vix") and input_file is None:
            input_file = Path(a).resolve()
        else:
            rest.append(a)
    return input_file, rest


def _default_output_name() -> str:
    import tomllib

    try:
        with open("vindex.toml", "rb") as f:
            data = tomllib.load(f)
        name = data.get("project", {}).get("name", "main")
    except Exception:
        name = "main"
    return f"{name}.exe" if sys.platform == "win32" else name


def _has_gcc() -> bool:
    return shutil.which("gcc") is not None


def _compile_to_obj(
    input_file: Path,
    vixc_flags: list[str],
    root_dir: Path,
    temp_dir: Path,
    silent: bool = False,
) -> tuple[int, Path]:
    obj_path = temp_dir / f"{input_file.stem}.o"
    cmd = ["vixc", str(input_file), "-obj", str(obj_path)] + vixc_flags
    if not silent:
        console.print(f"  [cyan]ℹ[/cyan]  编译: [dim]{' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, cwd=root_dir)
    return result.returncode, obj_path


def _link_with_gcc(obj_path: Path, output_name: str, silent: bool = False) -> int:
    output_path = Path(output_name)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    cmd = ["gcc", str(obj_path), "-o", str(output_path)]
    if not silent:
        console.print(f"  [cyan]ℹ[/cyan]  链接: [dim]{' '.join(cmd)}[/dim]")
    return subprocess.run(cmd).returncode


def _compile_direct(
    input_file: Path, vixc_flags: list[str], root_dir: Path, silent: bool = False
) -> int:
    cmd = ["vixc", str(input_file)] + vixc_flags
    if not silent:
        console.print(f"  [cyan]ℹ[/cyan]  执行: [dim]{' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd, cwd=root_dir)
    return result.returncode


@app.callback(invoke_without_command=True)
def build(
    ctx: typer.Context,
):
    """编译 Vix 项目"""
    args_list = ctx.args

    if not Path("vindex.toml").exists():
        console.print("[red]未找到 vindex.toml，请确保在项目根目录运行此命令[/red]")
        raise typer.Exit(code=1)

    output_name, args_list = _extract_output_name(args_list)
    if output_name is None:
        output_name = _default_output_name()

    input_file, vixc_flags = _extract_input_file(args_list)
    if input_file is None:
        entrypoint = _get_entrypoint()
        candidate = Path(entrypoint).resolve()
        if not candidate.exists():
            console.print(
                f"[red]未找到入口文件 {entrypoint}，请指定输入文件或确保项目根目录有该文件[/red]"
            )
            raise typer.Exit(code=1)
        input_file = candidate

    root_dir = Path(".").resolve()
    temp_dir = Path(".vix/temp").resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)

    has_gcc = _has_gcc()
    if has_gcc:
        code, obj_path = _compile_to_obj(input_file, vixc_flags, root_dir, temp_dir)
        if code != 0:
            raise typer.Exit(code=code)
        code = _link_with_gcc(obj_path, output_name)
        raise typer.Exit(code=code)
    else:
        code = _compile_direct(input_file, vixc_flags, root_dir)
        raise typer.Exit(code=code)
