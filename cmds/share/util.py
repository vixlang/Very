import os
import stat


def _remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _get_entrypoint(vindex_path: str = "vindex.toml") -> str:
    import tomllib

    try:
        with open(vindex_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("entrypoint", "main.vix")
    except Exception:
        return "main.vix"
