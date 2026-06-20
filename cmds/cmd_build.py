"""very build — 编译 Vix 项目

流程（当系统装有 gcc 时）:
  1. vixc <input>.vix -obj <temp>/<stem>.o [flags...]  # .o 输出到 .vix/temp/
  2. gcc   <temp>/<stem>.o   -o <output>                # 链接为可执行文件

流程（无 gcc 时）:
  1. vixc <input>.vix [flags...]          # 全权交给 vixc 处理编译+链接

-o 参数会被截获用于指定输出文件名, 其余参数原样透传 vixc。
vixc 始终从项目根目录运行（使 import 路径正确解析），产物输出到 .vix/temp/。
"""

from .base import Command
import argparse
import subprocess
import sys
import shutil
import tomllib
from pathlib import Path
from .utils import log, console


class BuildCmd(Command):
    NAME = "build"
    silent: bool = False

    @classmethod
    def create_for_subcommand(cls, namespace, extra_args: list[str], silent: bool = False) -> "BuildCmd":
        """Create a BuildCmd instance for use by other commands (e.g., RunCmd).

        This avoids bypassing __init__ with __new__.
        """
        instance = cls.__new__(cls)
        instance.parser = None
        instance.namespace = namespace
        instance.extra_args = extra_args
        instance.silent = silent
        return instance

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            self.NAME,
            help="编译 Vix 项目",
            epilog="所有无法识别的参数将原样透传给 vixc，例如: very build -o hello.exe --target=wasm32",
        )
        # 不在 argparse 注册 passthrough 参数, 避免被 -o / --target 等干扰
        return parser

    # ---------------------------------------------------------------
    # 参数解析
    # ---------------------------------------------------------------
    @staticmethod
    def _extract_output_name(args: list[str]) -> tuple[str | None, list[str]]:
        """从参数列表中提取 -o <file>, 返回 (输出文件名, 剩余参数)."""
        output = None
        rest: list[str] = []
        i = 0
        while i < len(args):
            if args[i] == "-o" and i + 1 < len(args):
                output = args[i + 1]
                i += 2  # 跳过 -o 及其值
                continue
            rest.append(args[i])
            i += 1
        return output, rest

    @staticmethod
    def _extract_input_file(args: list[str]) -> tuple[Path | None, list[str]]:
        """从参数列表中提取 .vix 输入文件, 返回 (文件路径, 剩余参数)."""
        rest: list[str] = []
        input_file = None
        for a in args:
            if a.endswith(".vix") and input_file is None:
                input_file = Path(a).resolve()
            else:
                rest.append(a)
        return input_file, rest

    @staticmethod
    def _default_output_name() -> str:
        """从 vindex.toml 读取项目名作为默认输出文件名."""
        try:
            with open("vindex.toml", "rb") as f:
                data = tomllib.load(f)
            name = data.get("project", {}).get("name", "main")
        except Exception:
            name = "main"
        # Windows 下加 .exe 后缀
        return f"{name}.exe" if sys.platform == "win32" else name

    # ---------------------------------------------------------------
    # 编译与链接
    # ---------------------------------------------------------------
    @staticmethod
    def _has_gcc() -> bool:
        """检测系统是否可用 gcc."""
        return shutil.which("gcc") is not None

    def _compile_to_obj(self, input_file: Path, vixc_flags: list[str], root_dir: Path, temp_dir: Path) -> tuple[int, Path]:
        """第 1 步: vixc 编译到目标文件 (.o).

        Args:
            input_file: 源文件绝对路径
            vixc_flags: 透传 vixc 参数
            root_dir:   项目根目录（作为 vixc 工作目录，使 import 路径正确解析）
            temp_dir:   临时目录，.o 文件输出到此

        Returns:
            (returncode, obj_path) — obj_path 是 .o 文件的绝对路径。
        """
        obj_path = temp_dir / f"{input_file.stem}.o"
        # -obj 可接文件路径: 显式指定输出位置, 避免 vixc 默认放到 <input>.o
        cmd = ["vixc", str(input_file), "-obj", str(obj_path)] + vixc_flags
        if not self.silent:
            console.print(f"  [cyan]ℹ[/cyan]  编译: [dim]{' '.join(cmd)}[/dim]")
        result = subprocess.run(cmd, cwd=root_dir)
        return result.returncode, obj_path

    def _link_with_gcc(self, obj_path: Path, output_name: str) -> int:
        """第 2 步: gcc 链接目标文件为可执行文件."""
        output_path = Path(output_name)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path  # 相对于项目根目录
        cmd = ["gcc", str(obj_path), "-o", str(output_path)]
        if not self.silent:
            console.print(f"  [cyan]ℹ[/cyan]  链接: [dim]{' '.join(cmd)}[/dim]")
        return subprocess.run(cmd).returncode

    def _compile_direct(self, input_file: Path, vixc_flags: list[str], root_dir: Path) -> int:
        """降级方案: 直接由 vixc 处理编译+链接."""
        cmd = ["vixc", str(input_file)] + vixc_flags
        if not self.silent:
            console.print(f"  [cyan]ℹ[/cyan]  执行: [dim]{' '.join(cmd)}[/dim]")
        result = subprocess.run(cmd, cwd=root_dir)
        return result.returncode

    # ---------------------------------------------------------------
    # 主流程
    # ---------------------------------------------------------------
    def execute(self):
        # —— 1. 收集 argparse 未识别的透传参数 ——
        args_list = self.extra_args

        # —— 2. 确认在 vix 项目根目录 ——
        if not Path("vindex.toml").exists():
            log.error("未找到 vindex.toml，请确保在项目根目录运行此命令")
            return

        # —— 3. 提取 -o 输出文件名 ——
        output_name, args_list = self._extract_output_name(args_list)
        # 未指定 -o 时从 vindex.toml 读取项目名
        if output_name is None:
            output_name = self._default_output_name()

        # —— 4. 提取 .vix 输入文件 ——
        input_file, vixc_flags = self._extract_input_file(args_list)
        if input_file is None:
            # 自动补 main.vix
            candidate = Path("main.vix").resolve()
            if not candidate.exists():
                log.error("未找到 main.vix，请指定输入文件或确保项目根目录有 main.vix")
                return
            input_file = candidate
        # vixc_flags 中已不含 -o 和 .vix 文件, 可安全透传

        # —— 5. 准备输出目录 ——
        root_dir = Path(".").resolve()
        temp_dir = Path(".vix/temp").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)

        # —— 6. 根据系统情况选择编译方案 ——
        has_gcc = self._has_gcc()
        if has_gcc:
            # 方案 A: vixc -obj + gcc 链接
            #   vixc 从项目根目录运行（使 import 路径正确解析），.o 输出到 .vix/temp/
            code, obj_path = self._compile_to_obj(input_file, vixc_flags, root_dir, temp_dir)
            if code != 0:
                return code
            return self._link_with_gcc(obj_path, output_name)
        else:
            # 方案 B: vixc 全权处理编译+链接
            return self._compile_direct(input_file, vixc_flags, root_dir)
