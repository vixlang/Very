from dataclasses import dataclass
from pathlib import Path
from git import Repo, remote
import shutil
from .utils import VIndexTool, parse_pack_name, create_git_progress


class GitProgress(remote.RemoteProgress):
    def __init__(self, progress, package_name):
        super().__init__()
        self.progress = progress
        self.package_name = package_name
        self.task_id = None
        self.current_op = ""

    def _get_operation_name(self, op_code):
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
            op_name = self._get_operation_name(op_code)
            self.task_id = self.progress.add_task(
                f"[cyan]克隆 {self.package_name}[/cyan] - {op_name}",
                total=max_count if max_count and max_count > 0 else None,
            )
            self.current_op = op_name
        new_op = self._get_operation_name(op_code)
        if new_op != self.current_op:
            self.current_op = new_op
            self.progress.update(
                self.task_id,
                description=f"[cyan]克隆 {self.package_name}[/cyan] - {new_op}",
            )
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
    @staticmethod
    def install_one(spec: str, parent: Path | None = None) -> InstallResult:
        packinfo = parse_pack_name(spec, parent=parent)
        pack_path = packinfo.pack_path

        if pack_path.exists():
            return InstallResult(spec=spec, success=False, skipped=True, reason="已存在")

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

        content = VIndexTool(pack_path).content()
        if content is None:
            return InstallResult(spec=spec, success=False, reason="缺少 vindex.toml", no_vindex=True)

        return InstallResult(spec=spec, success=True)

    @staticmethod
    def install_transitive_deps(parent: Path, specs: list[str], visited: set[str] | None = None, depth: int = 0):
        import tomllib
        if visited is None:
            visited = set()
        for spec in specs:
            if spec in visited:
                continue
            visited.add(spec)
            info = parse_pack_name(spec, parent=parent)

            if not info.pack_path.exists():
                PackageInstaller.install_one(spec, parent=parent)

            vindex_path = info.pack_path / "vindex.toml"
            if vindex_path.exists():
                with open(vindex_path, "rb") as f:
                    data = tomllib.load(f)
                sub_deps = data.get("project", {}).get("deps", [])
                sub_legacy = list(data.get("dependencies", {}).keys())
                sub = list(dict.fromkeys(sub_deps + sub_legacy))
                if sub:
                    PackageInstaller.install_transitive_deps(parent, sub, visited, depth + 1)
