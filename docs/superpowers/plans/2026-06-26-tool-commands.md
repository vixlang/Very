# very tool / very exe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `very tool {add,search}` and `very exe <pkg>` commands for managing and running Vix tools.

**Architecture:** Two new command files (`cmd_tool.py`, `cmd_exe.py`) + utils modifications. Tools are cloned to `$VIX_HOME/tools/{host}/{user}/{repo}/` and compiled binaries go to `$VIX_HOME/tools/{name}{suffix}`. Bare package names use `vtool-` prefix instead of `vlib-`.

**Tech Stack:** Python 3.13+, rich, gitpython, tomllib/tomli-w

## Global Constraints

- `parse_pack_name` gains a `bare_prefix` parameter (default `VLIB_PREFIX`). The bare-name branch uses `bare_prefix` instead of hardcoded `VLIB_PREFIX`.
- `Config.VIX_TOOLS_PATH` = `Path(os.getenv("VIX_HOME", "./.vix")) / "tools"`
- `VTOOL_PREFIX = "vtool-"` constant in `cmds/utils.py`
- Binary name from vindex.toml `project.name` + platform suffix (`.exe` on Windows, else `""`)
- `tool add` default behavior: always global (no `-g`/`-l` flags)
- `tool search` filters `vtool-*` prefix from the same GitHub API as `very search`
- `very exe <name>`: look for `$VIX_HOME/tools/{name}{suffix}`, auto-install if missing, pass extra args to binary

---

### Task 1: utils.py — bare_prefix parameter + parse_tool_name + Config.VIX_TOOLS_PATH

**Files:**
- Modify: `cmds/utils.py:83-87`, `cmds/utils.py:72-81`, `cmds/utils.py:175-287`
- Test: `tests/test_utils.py`

**Interfaces:**
- Consumes: existing `parse_pack_name`, `Config`, `VLIB_PREFIX`
- Produces: `parse_pack_name(package_name, parent, bare_prefix)`, `parse_tool_name(package_name, parent)`, `Config.VIX_TOOLS_PATH`, `VTOOL_PREFIX`

- [ ] **Step 1: Add VTOOL_PREFIX and Config.VIX_TOOLS_PATH**

In `cmds/utils.py`, after `VLIB_PREFIX = "vlib-"` (line 86):

```python
VTOOL_PREFIX = "vtool-"
```

In `Config` class, after `VIX_LIBS_PATH` (line 75):

```python
VIX_TOOLS_PATH: Path = Path(os.getenv("VIX_HOME", "./.vix")) / "tools"
```

- [ ] **Step 2: Add bare_prefix param to parse_pack_name**

Change signature (line 175):
```python
def parse_pack_name(package_name: str, parent: Path | None = None, bare_prefix: str = VLIB_PREFIX) -> PackageNameInfo:
```

Change the bare-name branch (line 277-279):
```python
    else:
        user_name = DEFAULT_ORG
        repo_name = f"{bare_prefix}{package_name}"
```

- [ ] **Step 3: Add parse_tool_name function**

After `parse_pack_name` (before `build_dep_tree`):
```python
def parse_tool_name(package_name: str, parent: Path | None = None) -> PackageNameInfo:
    """Same as parse_pack_name but bare names use vtool- prefix."""
    return parse_pack_name(package_name, parent=parent, bare_prefix=VTOOL_PREFIX)
```

- [ ] **Step 4: Write tests for parse_tool_name**

In `tests/test_utils.py`, add to `TestParsePackName` class:
```python
def test_tool_bare_name(self):
    info = parse_tool_name("game")
    assert info.git_master == "github.com"
    assert info.user_name == "vixlang"
    assert info.repo_name == "vtool-game"

def test_tool_dot_format(self):
    info = parse_tool_name("fexcode.vnet")
    assert info.repo_name == "vnet"
    assert info.user_name == "fexcode"
```

Also import `parse_tool_name` at the top of the test file.

And test Config:
```python
def test_tools_path_is_home_tools(self):
    assert Config.VIX_TOOLS_PATH.name == "tools"
    assert Config.VIX_TOOLS_PATH.parent == Config.VIX_HOME
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `uv run pytest tests/test_utils.py -v -k "tool" 2>&1`
Expected: FAIL with "parse_tool_name is not defined" or attribute errors.

- [ ] **Step 6: Run full test to verify they pass**

Run: `uv run pytest tests/test_utils.py -v 2>&1`
Expected: All existing + new tests PASS.

- [ ] **Step 7: Commit**

```bash
git add cmds/utils.py tests/test_utils.py
git commit -m "feat: add parse_tool_name, bare_prefix param, Config.VIX_TOOLS_PATH"
```

---

### Task 2: cmd_tool.py — ToolCmd with `add` and `search` subcommands

**Files:**
- Create: `cmds/cmd_tool.py`
- Dependencies: Task 1 (utils changes)

**Interfaces:**
- Consumes: `parse_tool_name`, `Config.VIX_TOOLS_PATH`, `VIndexTool`, `BuildCmd`, `log`, `console`, `parse_pack_name`
- Produces: `ToolCmd` class (NAME="tool"), `install_tool(packname) -> Path | None` module-level function

- [ ] **Step 1: Create cmd_tool.py scaffold**

```python
"""very tool — manage Vix tools (add, search)."""

from .base import Command
from .cmd_build import BuildCmd
from .utils import (
    VTOOL_PREFIX,
    VIndexTool,
    Config,
    log,
    console,
    err_console,
    parse_tool_name,
    parse_pack_name,
    create_git_progress,
)
from .installer import GitProgress, InstallResult
from git import Repo
from pathlib import Path
import argparse
import sys
import os
import json
import time
import urllib.request
import ssl
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner

_SSL_CTX = ssl.create_default_context()
```

- [ ] **Step 2: Implement install_tool() function**

```python
def install_tool(packname: str, parent: Path | None = None) -> Path | None:
    """Install and build a Vix tool. Returns the compiled binary path or None."""
    if parent is None:
        parent = Config.VIX_TOOLS_PATH

    info = parse_tool_name(packname, parent=parent)
    PACK_PATH = info.pack_path

    # Clone if not already present
    if not PACK_PATH.exists():
        log.section(f"安装工具: {info.full_name}")
        log.info(f"源: [link={info.git_url}]{info.git_url}[/link]")
        if info.branch_name:
            log.info(f"分支: {info.branch_name}")

        with create_git_progress(info.full_name) as progress:
            git_progress = GitProgress(progress, info.full_name)
            try:
                Repo.clone_from(
                    info.git_url,
                    PACK_PATH,
                    branch=info.branch_name,
                    progress=git_progress,
                )
            except Exception as e:
                import shutil
                if PACK_PATH.exists():
                    shutil.rmtree(PACK_PATH, ignore_errors=True)
                log.error(f"克隆失败: {e}")
                return None
    else:
        log.info(f"工具 {info.full_name} 已存在，重新编译")

    # Validate vindex.toml
    content = VIndexTool(PACK_PATH).content()
    if content is None:
        log.error(f"{info.full_name} 缺少 vindex.toml")
        return None

    # Read project name from vindex.toml
    project_name = content.get("project", {}).get("name", info.repo_name)
    suffix = ".exe" if sys.platform == "win32" else ""
    binary_name = f"{project_name}{suffix}"
    binary_path = (parent / binary_name).resolve()

    # Build
    log.info(f"正在编译 [cyan]{project_name}[/cyan] ...")
    binary_path.parent.mkdir(parents=True, exist_ok=True)

    old_cwd = Path.cwd()
    os.chdir(str(PACK_PATH))
    try:
        ns = argparse.Namespace()
        build_cmd = BuildCmd.create_for_subcommand(ns, ["-o", str(binary_path)])
        code = build_cmd.execute()
        if code is not None and code != 0:
            log.error(f"编译 {info.full_name} 失败")
            return None
    finally:
        os.chdir(str(old_cwd))

    if not binary_path.exists():
        log.error(f"编译产物 {binary_name} 未生成")
        return None

    log.success(f"工具 {project_name} 已安装: {binary_path}")
    return binary_path
```

- [ ] **Step 3: Implement ToolCmd class — set_parser with subparsers**

```python
class ToolCmd(Command):
    NAME = "tool"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            "tool",
            help="管理 Vix 工具",
            description="安装、搜索和管理 Vix 工具。",
        )
        sub = parser.add_subparsers(dest="tool_subcommand")

        # tool add
        add_parser = sub.add_parser("add", help="安装 Vix 工具")
        add_parser.add_argument("package", help="工具包名")

        # tool search
        search_parser = sub.add_parser(
            "search",
            help="搜索可用的 Vix 工具",
            description=f"从 GitHub vixlang 组织中搜索可用的 vix 工具。",
        )
        search_parser.add_argument("keyword", nargs="?", default="", help="搜索关键词（可选）")
        search_parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
        search_parser.add_argument("--clear-cache", action="store_true", help="清理缓存")
        search_parser.add_argument("--cache-status", action="store_true", help="查看缓存状态")
        search_parser.add_argument("--sort", choices=["stars", "updated", "name"], default="stars", help="排序方式")
        search_parser.add_argument("--limit", type=int, default=None, help="限制显示数量")

        return parser
```

- [ ] **Step 4: Implement ToolCmd.execute() dispatch**

```python
    def execute(self):
        sub = getattr(self.namespace, "tool_subcommand", None)
        if sub == "add":
            self._cmd_add()
        elif sub == "search":
            self._cmd_search()
        else:
            err_console.print("[red]未知 tool 子命令，使用 'very tool --help' 查看帮助[/red]")

    def _cmd_add(self):
        packname = getattr(self.namespace, "package", "")
        if not packname:
            log.error("请指定工具包名")
            return
        result = install_tool(packname)
        if result is None:
            return

    # ---- Search ----
    CACHE_DIR = Config.VIX_TOOLS_PATH / "cache"
    CACHE_FILE = CACHE_DIR / "tool_search_cache.json"
    CACHE_EXPIRY = 3600
    MAX_RETRIES = 3
    RETRY_DELAY = 2
```

- [ ] **Step 5: Implement tool search methods**

Add to ToolCmd class. Based on SearchCmd but filtering `vtool-*`:

```python
    def _cmd_search(self):
        keyword = getattr(self.namespace, "keyword", "")
        no_cache = getattr(self.namespace, "no_cache", False)
        clear_cache = getattr(self.namespace, "clear_cache", False)
        cache_status = getattr(self.namespace, "cache_status", False)
        sort_by = getattr(self.namespace, "sort", "stars")
        limit = getattr(self.namespace, "limit", None)

        if clear_cache:
            self._clear_cache()
            return
        if cache_status:
            self._show_cache_status()
            return

        log.section(f"搜索工具: {keyword if keyword else '全部'}")

        try:
            if no_cache:
                log.info("正在从 GitHub 获取工具列表...（不使用缓存）")
                packages = self._fetch_with_retry()
                self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
                self._save_cache(packages)
            else:
                packages = self._fetch_packages_with_cache()

            if not packages:
                log.warning("未找到任何工具")
                return

            if keyword:
                filtered = [
                    p for p in packages
                    if keyword.lower() in p["name"].lower()
                    or keyword.lower() in (p.get("description") or "").lower()
                ]
            else:
                filtered = packages

            if not filtered:
                log.warning(f"未找到包含 '{keyword}' 的工具")
                return

            filtered = self._sort_packages(filtered, sort_by)
            if limit and limit > 0:
                filtered = filtered[:limit]

            self._display_results(filtered, sort_by)

        except Exception as e:
            log.error(f"搜索失败\n\n[white]{str(e)}[/white]\n\n[yellow]请检查网络连接[/yellow]")

    def _sort_packages(self, packages, sort_by):
        if sort_by == "stars":
            return sorted(packages, key=lambda x: x["stars"], reverse=True)
        elif sort_by == "updated":
            return sorted(packages, key=lambda x: x["updated"], reverse=True)
        elif sort_by == "name":
            return sorted(packages, key=lambda x: x["name"].lower())
        return sorted(packages, key=lambda x: x["stars"], reverse=True)

    def _fetch_with_retry(self):
        last_exception = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    log.info(f"重试第 {attempt - 1} 次...")
                    time.sleep(self.RETRY_DELAY)
                with Live(Spinner("dots", text="正在从 GitHub 获取数据..."), refresh_per_second=10, transient=True):
                    result = self._fetch_github_packages()
                return result
            except urllib.error.HTTPError as e:
                last_exception = e
                if e.code == 403:
                    if attempt < self.MAX_RETRIES:
                        wait_time = self.RETRY_DELAY * (2 ** (attempt - 1))
                        log.warning(f"GitHub API 速率限制，{wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    raise Exception("GitHub API 速率限制已用完，请稍后再试")
                elif e.code == 404:
                    raise Exception("GitHub API 端点不存在")
                elif e.code >= 500:
                    if attempt < self.MAX_RETRIES:
                        log.warning(f"服务器错误 ({e.code})，将重试...")
                        continue
                    raise Exception(f"GitHub API 服务器错误 ({e.code})")
                else:
                    raise Exception(f"HTTP 错误: {e.code}")
            except urllib.error.URLError as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    log.warning(f"网络错误，将重试...")
                    continue
                raise Exception(f"网络错误，请检查网络连接")
            except Exception as e:
                raise Exception(f"请求失败: {str(e)}")
        if last_exception:
            raise Exception(f"经过 {self.MAX_RETRIES} 次重试后仍然失败")

    def _fetch_packages_with_cache(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached = self._read_cache()
        if cached is not None:
            log.info(f"使用缓存数据（{len(cached)} 个工具）")
            return cached
        log.info("正在从 GitHub 获取工具列表...")
        packages = self._fetch_with_retry()
        self._save_cache(packages)
        return packages

    def _read_cache(self):
        if not self.CACHE_FILE.exists():
            return None
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data["timestamp"] > self.CACHE_EXPIRY:
                return None
            return data["packages"]
        except (json.JSONDecodeError, KeyError):
            return None
        except Exception:
            return None

    def _save_cache(self, packages):
        try:
            data = {"timestamp": time.time(), "packages": packages}
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.debug(f"保存缓存失败: {e}")

    def _fetch_github_packages(self):
        from .utils import DEFAULT_ORG
        packages = []
        page = 1
        per_page = 100
        while True:
            url = f"https://api.github.com/orgs/{DEFAULT_ORG}/repos?per_page={per_page}&page={page}&type=sources"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Very-Project-Manager"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as response:
                data = json.loads(response.read().decode("utf-8"))
                if not data:
                    break
                for repo in data:
                    if repo["name"].startswith(VTOOL_PREFIX):
                        packages.append({
                            "name": repo["name"],
                            "description": repo["description"] or "无描述",
                            "stars": repo["stargazers_count"],
                            "language": repo["language"] or "Unknown",
                            "updated": repo["updated_at"][:10],
                            "url": repo["html_url"],
                        })
                if len(data) < per_page:
                    break
                page += 1
        packages.sort(key=lambda x: x["stars"], reverse=True)
        return packages

    def _display_results(self, packages, sort_by="stars"):
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("工具名", style="green", width=25)
        table.add_column("描述", style="white", width=50)
        table.add_column("星标", justify="right", style="yellow", width=6)
        table.add_column("语言", style="magenta", width=12)
        table.add_column("更新时间", style="dim", width=12)

        for pkg in packages:
            short_name = pkg["name"].replace(VTOOL_PREFIX, "", 1) if pkg["name"].startswith(VTOOL_PREFIX) else pkg["name"]
            desc = pkg.get("description") or ""
            table.add_row(short_name, desc[:47] + "..." if len(desc) > 50 else desc, str(pkg["stars"]), pkg["language"], pkg["updated"])

        console.print()
        console.print(table)
        console.print()

        sort_labels = {"stars": "星标数", "updated": "更新时间", "name": "名称"}
        log.success(f"共找到 {len(packages)} 个工具（按{sort_labels.get(sort_by, '星标数')}排序）")
        console.print()

    def _clear_cache(self):
        log.section("清理缓存")
        if not self.CACHE_FILE.exists():
            log.info("缓存文件不存在，无需清理")
            return
        try:
            size = self.CACHE_FILE.stat().st_size
            self.CACHE_FILE.unlink()
            log.success(f"缓存已清理（释放 {size/1024:.2f} KB）")
        except Exception as e:
            log.error(f"清理缓存失败: {e}")

    def _show_cache_status(self):
        log.section("缓存状态")
        if not self.CACHE_FILE.exists():
            log.info("缓存文件不存在\n运行 [green]very tool search[/green] 将自动创建缓存")
            return
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data["timestamp"]
            count = len(data["packages"])
            age = time.time() - ts
            size = self.CACHE_FILE.stat().st_size
            remaining = self.CACHE_EXPIRY - age
            status = f"[green]有效[/green]（剩余 {int(remaining/60)} 分钟）" if remaining > 0 else "[red]已过期[/red]"
            cache_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            console.print()
            console.print(f"缓存文件: [cyan]{self.CACHE_FILE}[/cyan]")
            console.print(f"创建时间: [white]{cache_time}[/white]")
            console.print(f"缓存大小: [yellow]{size/1024:.2f} KB[/yellow]")
            console.print(f"工具数量: [magenta]{count}[/magenta]")
            console.print(f"状态: {status}")
            console.print()
        except Exception as e:
            log.error(f"读取缓存状态失败: {e}")
```

- [ ] **Step 6: Verify the file parses correctly**

Run: `uv run python -c "from cmds.cmd_tool import ToolCmd, install_tool; print('OK')" 2>&1`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add cmds/cmd_tool.py
git commit -m "feat: add cmd_tool.py with tool add and tool search"
```

---

### Task 3: cmd_exe.py — ExeCmd

**Files:**
- Create: `cmds/cmd_exe.py`
- Dependencies: Task 1, Task 2 (imports `install_tool`)

**Interfaces:**
- Consumes: `install_tool`, `parse_tool_name`, `Config.VIX_TOOLS_PATH`, `log`
- Produces: `ExeCmd` class (NAME="exe")

- [ ] **Step 1: Create cmd_exe.py**

```python
"""very exe — execute compiled Vix tools."""

from .base import Command
from .cmd_tool import install_tool
from .utils import Config, log, err_console, parse_tool_name
import argparse
import sys
import subprocess
from pathlib import Path


class ExeCmd(Command):
    NAME = "exe"

    def set_parser(self, p: argparse._SubParsersAction) -> argparse.ArgumentParser:
        parser = p.add_parser(
            "exe",
            help="执行 Vix 工具",
            description="查找并执行已安装的 Vix 工具，未安装则自动安装。",
        )
        parser.add_argument("tool", help="要执行的工具名")
        return parser

    def execute(self):
        tool_name = getattr(self.namespace, "tool", "")
        extra = self.extra_args

        if not tool_name:
            log.error("请指定要执行的工具名")
            return

        suffix = ".exe" if sys.platform == "win32" else ""
        binary_path = Config.VIX_TOOLS_PATH / f"{tool_name}{suffix}"

        if not binary_path.exists():
            log.info(f"工具 [cyan]{tool_name}[/cyan] 未安装，正在自动安装...")
            result = install_tool(tool_name)
            if result is None:
                log.error(f"无法安装工具 {tool_name}")
                return
            binary_path = result

        if not binary_path.exists():
            log.error(f"工具 {tool_name} 安装后未找到编译产物")
            return

        try:
            log.info(f"执行: [dim]{binary_path} {' '.join(extra)}[/dim]")
            result = subprocess.run([str(binary_path)] + extra)
            if result.returncode != 0:
                log.warning(f"工具以退出码 {result.returncode} 退出")
        except FileNotFoundError:
            log.error(f"找不到可执行文件: {binary_path}")
        except Exception as e:
            log.error(f"执行失败: {e}")
```

- [ ] **Step 2: Verify it loads**

Run: `uv run python -c "from cmds.cmd_exe import ExeCmd; print('OK')" 2>&1`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add cmds/cmd_exe.py
git commit -m "feat: add cmd_exe.py for executing Vix tools"
```

---

### Task 4: Register in __init__.py + bump version

**Files:**
- Modify: `cmds/__init__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Register exe and tool in CMD_REGISTRY**

In `cmds/__init__.py`, add imports:
```python
from . import (
    ...
    cmd_exe,
    cmd_tool,
)
```

Add to `CMD_REGISTRY`:
```python
    "exe": {"cls": cmd_exe.ExeCmd, "color": "yellow", "desc": "执行 Vix 工具"},
    "tool": {"cls": cmd_tool.ToolCmd, "color": "green", "desc": "管理 Vix 工具"},
```

- [ ] **Step 2: Bump version in pyproject.toml**

`0.21.1` → `0.22.0` (minor: new features)

- [ ] **Step 3: Verify registration works**

Run: `uv run python -c "from cmds import CMD_REGISTRY; print('exe' in CMD_REGISTRY, 'tool' in CMD_REGISTRY)" 2>&1`
Expected: `True True`

- [ ] **Step 4: Commit**

```bash
git add cmds/__init__.py pyproject.toml
git commit -m "feat: register exe and tool commands" -m "chore: bump 0.21.1 -> 0.22.0"
```

---

### Task 5: Tests for cmd_tool.py and cmd_exe.py

**Files:**
- Create: `tests/test_cmd_tool.py`
- Create: `tests/test_cmd_exe.py`

- [ ] **Step 1: Create tests/test_cmd_tool.py**

```python
"""Tests for ToolCmd."""

import argparse
import json
import time
from pathlib import Path
from unittest.mock import MagicMock

from cmds.cmd_tool import ToolCmd, install_tool


class TestToolSearchSubcommand:
    """Test suite for tool search cache/sort/fetch logic."""

    def _make_cmd(self, tmp_path) -> ToolCmd:
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ToolCmd(subparsers)
        cmd.CACHE_DIR = tmp_path / "cache"
        cmd.CACHE_FILE = cmd.CACHE_DIR / "tool_search_cache.json"
        return cmd

    @staticmethod
    def _sample_packages():
        return [
            {"name": "vtool-game", "description": "A game", "stars": 50, "updated": "2024-03-01", "language": "Vix", "url": ""},
            {"name": "vtool-score", "description": "Score tool", "stars": 10, "updated": "2024-01-15", "language": "Vix", "url": ""},
        ]

    # ---- sort ----
    def test_sort_by_stars(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd._sort_packages(pkgs, "stars")
        assert [p["stars"] for p in result] == [50, 10]

    def test_sort_by_name(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd._sort_packages(pkgs, "name")
        assert [p["name"] for p in result] == ["vtool-game", "vtool-score"]

    # ---- cache ----
    def test_read_cache_not_exists(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        assert cmd._read_cache() is None

    def test_read_cache_valid(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vtool-test", "stars": 1}]
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "packages": packages}, f)
        assert cmd._read_cache() == packages

    def test_read_cache_expired(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time() - 7200, "packages": []}, f)
        assert cmd._read_cache() is None

    def test_save_and_read(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vtool-test", "stars": 1}]
        cmd._save_cache(packages)
        assert cmd._read_cache() == packages

    def test_clear_cache(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": []}, f)
        assert cmd.CACHE_FILE.exists()
        cmd._clear_cache()
        assert not cmd.CACHE_FILE.exists()

    # ---- fetch_github_packages ----
    @staticmethod
    def _mock_urlopen(data):
        def mock_urlopen(req, timeout=10, context=None):
            resp = MagicMock()
            resp.read.return_value = json.dumps(data).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp
        return mock_urlopen

    def test_fetch_filters_vtool(self, tmp_path, monkeypatch):
        raw = [
            {"name": "vtool-game", "description": "Game", "stargazers_count": 50, "language": "Vix", "updated_at": "2024-01-15T00:00:00Z", "html_url": ""},
            {"name": "vlib-core", "description": "Core lib", "stargazers_count": 99, "language": "Vix", "updated_at": "2024-02-01T00:00:00Z", "html_url": ""},
        ]
        monkeypatch.setattr("urllib.request.urlopen", self._mock_urlopen(raw))
        cmd = self._make_cmd(tmp_path)
        result = cmd._fetch_github_packages()
        assert len(result) == 1
        assert result[0]["name"] == "vtool-game"

    # ---- display_results ----
    def test_display_results(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        packages = [
            {"name": "vtool-game", "description": "A game", "stars": 50, "updated": "2024-03-01", "language": "Vix", "url": ""},
        ]
        cmd._display_results(packages, "stars")
        out, _ = capsys.readouterr()
        assert "game" in out  # short name displayed without vtool- prefix
        assert "A game" in out
```

- [ ] **Step 2: Create tests/test_cmd_exe.py**

```python
"""Tests for ExeCmd."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from cmds.cmd_exe import ExeCmd
from cmds.utils import Config


class TestExeCmd:
    def test_parser_adds_tool_argument(self):
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ExeCmd(subparsers)
        ns = parser.parse_args(["exe", "mygame"])
        assert ns.tool == "mygame"

    def test_tool_not_found_auto_installs(self, tmp_path, monkeypatch):
        """When binary doesn't exist, exe should call install_tool."""
        monkeypatch.setattr(Config, "VIX_TOOLS_PATH", tmp_path / "tools")
        tool_bin = tmp_path / "tools" / "mygame.exe"
        tool_bin.parent.mkdir(parents=True)

        # install_tool should create the binary
        def fake_install(name):
            tool_bin.write_text("fake binary")
            return tool_bin

        import cmds.cmd_exe as exe_mod
        monkeypatch.setattr(exe_mod, "install_tool", fake_install)

        # Mock subprocess.run to avoid actually running
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ExeCmd(subparsers)
        cmd.namespace = argparse.Namespace(tool="mygame")
        cmd.extra_args = ["--score", "100"]
        cmd.execute()

        assert tool_bin.exists()
        mock_run.assert_called_once_with([str(tool_bin), "--score", "100"])

    def test_tool_already_installed(self, tmp_path, monkeypatch):
        """When binary exists, exe should run it directly."""
        monkeypatch.setattr(Config, "VIX_TOOLS_PATH", tmp_path / "tools")
        tool_bin = tmp_path / "tools" / "mygame.exe"
        tool_bin.parent.mkdir(parents=True)
        tool_bin.write_text("fake binary")

        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ExeCmd(subparsers)
        cmd.namespace = argparse.Namespace(tool="mygame")
        cmd.extra_args = []
        cmd.execute()

        mock_run.assert_called_once_with([str(tool_bin)])

    def test_tool_name_empty(self, tmp_path, capsys):
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ExeCmd(subparsers)
        cmd.namespace = argparse.Namespace(tool="")
        cmd.extra_args = []
        cmd.execute()
        out, _ = capsys.readouterr()
        assert "请指定要执行的工具名" in out
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_cmd_tool.py tests/test_cmd_exe.py -v 2>&1`
Expected: All tests PASS.

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v 2>&1`
Expected: All tests PASS (including existing ones).

- [ ] **Step 5: Commit**

```bash
git add tests/test_cmd_tool.py tests/test_cmd_exe.py
git commit -m "test: add tests for tool add/search and exe commands"
```

---

### Task 6: Run linter and finalize

- [ ] **Step 1: Run ruff**

Run: `uv run ruff check . 2>&1 | head -30`
Expected: No errors or only pre-existing ones.

- [ ] **Step 2: Run black**

Run: `uv run black . --check 2>&1`
Expected: No files would be reformatted (or fix with `uv run black .`).

- [ ] **Step 3: Final full test pass**

Run: `uv run pytest tests/ 2>&1`
Expected: All tests PASS.

- [ ] **Step 4: Final commit (if lint fixes)**

```bash
git add -A
git commit -m "style: format with black"
```

