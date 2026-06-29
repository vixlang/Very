import tomllib
from pathlib import Path

import tomli_w

from .types import Config, parse_pack_name


class VIndexTool:
    def __init__(self, dir_path: Path):
        self.path = dir_path / "vindex.toml"

    def content(self) -> dict[str, object] | None:
        if not self.path.exists():
            return None
        with open(self.path, "rb") as f:
            return tomllib.load(f)


def build_dep_tree(libs_path: Path, root_deps: list[str]) -> set[str]:
    referenced: set[str] = set()
    queue = list(root_deps)
    while queue:
        spec = queue.pop(0)
        if spec in referenced:
            continue
        info = parse_pack_name(spec, parent=libs_path)
        referenced.add(info.full_name)
        vindex_path = info.pack_path / "vindex.toml"
        if vindex_path.exists():
            with open(vindex_path, "rb") as f:
                data = tomllib.load(f)
            sub_deps = data.get("project", {}).get("deps", [])
            sub_legacy = list(data.get("dependencies", {}).keys())
            for d in dict.fromkeys(sub_deps + sub_legacy):
                if d not in referenced:
                    queue.append(d)
    return referenced


def add_dep_to_vindex(pack_spec: str) -> bool:
    vindex_path = Path.cwd() / "vindex.toml"
    if not vindex_path.exists():
        return False

    with open(vindex_path, "rb") as f:
        data = tomllib.load(f)

    deps: list = data.get("project", {}).get("deps", [])
    if not isinstance(deps, list):
        deps = []
    legacy = list(data.get("dependencies", {}).keys())
    existing = list(dict.fromkeys(deps + legacy))

    if pack_spec in existing:
        return False

    data.setdefault("project", {})["deps"] = existing + [pack_spec]
    data.pop("dependencies", None)

    with open(vindex_path, "wb") as f:
        tomli_w.dump(data, f)

    return True


def get_transitive_deps(pack_path: Path) -> list[str]:
    vindex_path = pack_path / "vindex.toml"
    if not vindex_path.exists():
        return []
    with open(vindex_path, "rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("deps", [])
    legacy = list(data.get("dependencies", {}).keys())
    return list(dict.fromkeys(deps + legacy))
