from dataclasses import dataclass
from pathlib import Path
from git import Repo, remote
import shutil
from .utils import VIndexTool, parse_pack_name, create_git_progress


class GitProgress(remote.RemoteProgress):
    """Git 进度处理器，在克隆时显示 Rich 进度条。"""

    def __init__(self, progress, package_name):
        super().__init__()
        self.progress = progress
        self.package_name = package_name
        self.task_id = None
        self.current_op = ""

    def _get_operation_name(self, op_code):
        """获取操作名称（op_code 含 BEGIN/END 标志位，需先屏蔽）"""
        # OP_MASK 清除 BEGIN(1)/END(2) 标志位，只保留操作阶段值
        op_map = {
            remote.RemoteProgress.COUNTING: "统计对象",
            remote.RemoteProgress.COMPRESSING: "压缩对象",
            remote.RemoteProgress.WRITING: "写入对象",
            remote.RemoteProgress.RECEIVING: "接收对象",
            remote.RemoteProgress.RESOLVING: "解析差异",
            remote.RemoteProgress.FINDING_SOURCES: "查找源",
            remote.RemoteProgress.CHECKING_OUT: "检出文件",
        }
        return op_map.get(op_code & remote.RemoteProgress.OP_MASK, "处理中")

    def update(self, op_code, cur_count, max_count=None, message=""):
        if self.task_id is None:
            # 第一次调用时创建任务
            op_name = self._get_operation_name(op_code)
            self.task_id = self.progress.add_task(
                f"[cyan]克隆 {self.package_name}[/cyan] - {op_name}",
                total=max_count if max_count and max_count > 0 else None,
            )
            self.current_op = op_name

        # 检查操作是否变化
        new_op = self._get_operation_name(op_code)
        if new_op != self.current_op:
            self.current_op = new_op
            self.progress.update(
                self.task_id,
                description=f"[cyan]克隆 {self.package_name}[/cyan] - {new_op}",
            )

        # 更新进度
        if max_count and max_count > 0:
            self.progress.update(self.task_id, total=max_count, completed=cur_count)


@dataclass
class InstallResult:
    spec: str
    success: bool
    skipped: bool = False
    reason: str = ""
    no_vindex: bool = False


class PackageInstaller:
    """包安装器，统一处理 clone + 校验 + 清理逻辑。

    调用方负责交互式确认（覆盖确认、no_vindex 保留/删除决策）。
    """

    @staticmethod
    def install_one(spec: str, parent: Path | None = None) -> InstallResult:
        """安装单个包。

        Args:
            spec: 包名规范 (如 "fexcode.vnet")
            parent: 安装根目录 (如 .vix/libs 或 $VIX_HOME/libs)

        Returns:
            InstallResult
        """
        packinfo = parse_pack_name(spec, parent=parent)
        pack_path = packinfo.pack_path

        if pack_path.exists():
            return InstallResult(
                spec=spec, success=False, skipped=True, reason="已存在"
            )

        # clone
        with create_git_progress(packinfo.full_name) as progress:
            git_progress = GitProgress(progress, packinfo.full_name)
            try:
                Repo.clone_from(
                    packinfo.git_url,
                    pack_path,
                    branch=packinfo.branch_name,
                    progress=git_progress,
                )
            except Exception as e:
                if pack_path.exists():
                    shutil.rmtree(pack_path, ignore_errors=True)
                return InstallResult(spec=spec, success=False, reason=str(e))

        # 校验 vindex.toml
        content = VIndexTool(pack_path).content()
        if content is None:
            return InstallResult(
                spec=spec, success=False, reason="缺少 vindex.toml", no_vindex=True
            )

        return InstallResult(spec=spec, success=True)

    @staticmethod
    def install_transitive_deps(parent: Path, specs: list[str], visited: set[str] | None = None, depth: int = 0):
        """递归安装传递依赖。"""
        import tomllib
        from .utils import log

        indent = "  " * depth
        if visited is None:
            visited = set()
        for spec in specs:
            if spec in visited:
                continue
            visited.add(spec)
            info = parse_pack_name(spec, parent=parent)

            if info.pack_path.exists():
                log.info(f"{indent}⊳ {spec} [dim]已存在, 检查其依赖[/dim]")
            else:
                log.info(f"{indent}⊳ {spec} [cyan]正在安装...[/cyan]")
                result = PackageInstaller.install_one(spec, parent=parent)
                if result.success:
                    log.success(f"{indent}  ✔ {spec}")
            log.info(f"{indent}  └ 检查 {spec} 的依赖...")
            vindex_path = info.pack_path / "vindex.toml"
            if vindex_path.exists():
                with open(vindex_path, "rb") as f:
                    data = tomllib.load(f)
                sub_deps = data.get("project", {}).get("deps", [])
                sub_legacy = list(data.get("dependencies", {}).keys())
                sub = list(dict.fromkeys(sub_deps + sub_legacy))
                if sub:
                    PackageInstaller.install_transitive_deps(parent, sub, visited, depth + 1)
                else:
                    log.info(f"{indent}    [dim]无更多依赖[/dim]")
