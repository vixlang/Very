from .base import Command
import argparse
from pathlib import Path
from .utils import log, parse_pack_name, VIndexTool, ask_confirm, console, Config, create_git_progress
from .installer import GitProgress
from git import Repo
import shutil
from rich.panel import Panel


class InstallCmd(Command):
    NAME = "install"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(self.NAME, help="安装 vindex.toml 中声明的所有依赖")
        parser.add_argument(
            "-l", "--local",
            dest="local_force",
            action="store_true",
            help="强制在项目 .vix 目录下载（即使全局已存在）",
        )
        return parser

    def execute(self):
        if getattr(self, "extra_args", None):
            pkg = self.extra_args[0]
            log.info(f"收到包名 '{pkg}'，也许你是想用 [bold cyan]very add {pkg}[/bold cyan] ？")
            return

        local_force = getattr(self.namespace, "local_force", False)

        vindex_toml_path = Path("vindex.toml")
        if not vindex_toml_path.exists():
            log.error("未找到 vindex.toml，请确保在项目根目录运行此命令")
            return

        import tomllib

        with open(vindex_toml_path, "rb") as f:
            data = tomllib.load(f)

        deps = data.get("project", {}).get("deps", [])
        legacy_deps = list(data.get("dependencies", {}).keys())
        all_deps = list(dict.fromkeys(deps + legacy_deps))
        if not all_deps:
            log.info("vindex.toml 中没有声明依赖")
            return

        local_parent = Config.local_libs_path()

        log.section("安装依赖")
        success = []
        skipped = []
        global_skipped = []
        failed = []

        for spec in all_deps:
            # ── 先查本地 ──
            local_packinfo = parse_pack_name(spec, parent=local_parent)
            if local_packinfo.pack_path.exists():
                skipped.append(spec)
                continue

            # ── 非强制本地模式：查全局 ──
            if not local_force:
                global_packinfo = parse_pack_name(spec, parent=Config.VIX_LIBS_PATH)
                if global_packinfo.pack_path.exists():
                    global_skipped.append(spec)
                    continue

            # ── 执行安装 ──
            PACK_PATH = local_packinfo.pack_path
            log.info(f"正在安装 [cyan]{spec}[/cyan] ...")
            with create_git_progress(local_packinfo.full_name) as progress:
                git_progress = GitProgress(progress, local_packinfo.full_name)
                try:
                    Repo.clone_from(
                        local_packinfo.git_url,
                        PACK_PATH,
                        branch=local_packinfo.branch_name,
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
                        f"[bold yellow]包缺少 vindex.toml: [white]{local_packinfo.full_name}[/white][/bold yellow]\n\n"
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
            log.info(f"跳过(本地已存在): {', '.join(skipped)}")
        if global_skipped:
            log.info(f"跳过(使用全局副本): {', '.join(global_skipped)}")
        if failed:
            for spec, reason in failed:
                log.error(f"{spec}: {reason}")
