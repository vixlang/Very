"""very run — 编译并运行 Vix 项目"""

import subprocess
from pathlib import Path

import typer

from . import cmd_build
from .utils import _get_entrypoint, console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    keep: bool = typer.Option(False, "-k", "--keep", help="运行后保留生成的可执行文件"),
    vdebug: bool = typer.Option(False, "-v", "--vdebug", help="显示编译调试信息"),
):
    """编译并运行 Vix 项目"""
    extra = ctx.args

    if not Path("vindex.toml").exists():
        console.print("[red]未找到 vindex.toml，请确保在项目根目录运行此命令[/red]")
        raise typer.Exit(code=1)

    output_name = cmd_build._extract_output_name(extra)[0]
    if output_name is None:
        output_name = cmd_build._default_output_name()
    output_path = Path(output_name).resolve()

    if vdebug:
        console.print("[bold cyan]▶ 编译项目...[/bold cyan]")

    build_code = 1
    has_gcc = cmd_build._has_gcc()
    input_file, vixc_flags = cmd_build._extract_input_file(extra)
    if input_file is None:
        entrypoint = _get_entrypoint()
        candidate = Path(entrypoint).resolve()
        if candidate.exists():
            input_file = candidate
    if input_file:
        root_dir = Path(".").resolve()
        temp_dir = Path(".vix/temp").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        if has_gcc:
            code, obj_path = cmd_build._compile_to_obj(
                input_file, vixc_flags, root_dir, temp_dir, silent=not vdebug
            )
            if code != 0:
                build_code = code
            else:
                build_code = cmd_build._link_with_gcc(
                    obj_path, output_name, silent=not vdebug
                )
        else:
            build_code = cmd_build._compile_direct(
                input_file, vixc_flags, root_dir, silent=not vdebug
            )

    if build_code != 0:
        console.print("[red]编译失败，无法运行[/red]")
        raise typer.Exit(code=build_code)

    if not output_path.exists():
        console.print(f"[red]编译产物 {output_path.name} 未生成[/red]")
        raise typer.Exit(code=1)

    result = subprocess.run([str(output_path)] + extra)

    if result.returncode != 0:
        typer.secho(f"程序以退出码 {result.returncode} 退出", fg="yellow")

    if not keep:
        output_path.unlink()
    elif vdebug:
        console.print(f"[dim]保留 {output_path.name}（--keep）[/dim]")
