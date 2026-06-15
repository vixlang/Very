from .base import Command
import argparse
from pathlib import Path
from .utils import log, parse_pack_name, VIndexTool, ask_confirm, console
from .cmd_add import GitProgress
from git import Repo
import shutil
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.panel import Panel


class InstallCmd(Command):
    NAME = "install"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(self.NAME, help="安装 vix.toml 中声明的所有依赖")
        return parser

    def execute(self):
        vix_toml_path = Path("vix.toml")
        if not vix_toml_path.exists():
            log.error("未找到 vix.toml，请确保在项目根目录运行此命令")
            return

        import tomllib

        with open(vix_toml_path, "rb") as f:
            data = tomllib.load(f)

        deps = data.get("deps", [])
        if not deps:
            log.info("vix.toml 中没有声明依赖")
            return

        log.section("安装依赖")
        success = []
        skipped = []
        failed = []

        for spec in deps:
            packinfo = parse_pack_name(spec)
            PACK_PATH = packinfo.pack_path

            if PACK_PATH.exists():
                skipped.append(spec)
                continue

            log.info(f"正在安装 [cyan]{spec}[/cyan] ...")
            with Progress(
                TextColumn("[cyan]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                git_progress = GitProgress(progress, packinfo.full_name)
                try:
                    Repo.clone_from(
                        packinfo.git_url,
                        PACK_PATH,
                        branch=packinfo.branch_name,
                        progress=git_progress,
                    )
                except Exception as e:
                    if PACK_PATH.exists():
                        shutil.rmtree(PACK_PATH, ignore_errors=True)
                    failed.append((spec, str(e)))
                    continue

            content = VIndexTool(PACK_PATH).content()
            if content is None:
                console.print()
                console.print(
                    Panel(
                        f"[bold yellow]包缺少 vindex.toml: [white]{packinfo.full_name}[/white][/bold yellow]\n\n"
                        f"[dim]该包已下载但缺少必要的 vindex.toml 文件[/dim]",
                        title="[bold]⚠ 警告[/bold]",
                        border_style="yellow",
                        padding=(1, 2),
                    )
                )
                if ask_confirm("是否删除此不完整的包?", default=True):
                    shutil.rmtree(PACK_PATH)
                    failed.append((spec, "缺少 vindex.toml"))
                else:
                    success.append(spec)
            else:
                success.append(spec)

        console.print()
        log.section("安装结果")
        if success:
            log.success(f"成功: {', '.join(success)}")
        if skipped:
            log.info(f"跳过(已存在): {', '.join(skipped)}")
        if failed:
            for spec, reason in failed:
                log.error(f"{spec}: {reason}")
