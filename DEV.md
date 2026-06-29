# DEV.md — very

## 项目

Vix 语言的项目管理与构建工具。CLI 名：`very`。

- **Python** >=3.13，**uv** 管理，setuptools 构建
- 入口：`main.py` → `main:entry`（`pyproject.toml` `[project.scripts]`）

## 目录结构

```
very/
├── apis/               业务逻辑层，零 UI 依赖
│   ├── __init__.py
│   ├── types.py        Config, PackageNameInfo 等公共 data class
│   ├── _error.py       错误联盟类型
│   ├── _event.py       事件联盟类型（仅 generator 操作使用）
│   ├── pkg.py          包管理：add / del / list / prune / update / install
│   ├── tool.py         工具管理：add / del / update
│   ├── build.py        编译/运行/检查：build / run / good（长操作 → generator）
│   ├── search.py       搜索：libs + tools 统一后端
│   ├── scaffold.py     项目脚手架
│   └── vindex.py       vindex.toml 读写、依赖树
├── cmds/               CLI 层，仅做参数解析 + 调用 apis + 渲染输出
│   ├── cmd_add.py
│   ├── cmd_del.py
│   ├── cmd_list.py
│   ├── cmd_prune.py
│   ├── cmd_init.py
│   ├── cmd_search.py
│   ├── cmd_install.py
│   ├── cmd_update.py
│   ├── cmd_build.py
│   ├── cmd_run.py
│   ├── cmd_good.py
│   ├── cmd_exe.py
│   ├── cmd_tool/          工具子命令
│   │   ├── __init__.py
│   │   ├── install.py
│   │   ├── delete.py
│   │   ├── update.py
│   │   └── search.py
│   ├── share/             仅 CLI 渲染用
│   │   ├── __init__.py
│   │   └── log.py         全局 logger（5 级：debug/ok/info/warn/error）
│   ├── installer.py       Git 克隆进度回调（仅用于 CLI 渲染）
│   └── utils.py           残留公共工具（逐步迁移到 apis/）
├── tests/
│   ├── __init__.py
│   ├── test_parse.py
│   ├── test_info.py
│   └── test_cli.py
├── main.py
├── DEV.md
├── AGENTS.md
├── pyproject.toml
└── README.md
```

---

## 架构

```
用户 → CLI (cmds/) → 参数解析 → API (apis/) → 结构化 Result
                                              ↘ 可选的 Event 流
→ 渲染 → 用户
```

### 分层规则

- **`apis/`** 不允许 import 任何 `cmds/` 中的东西，不允许 import `rich`、`typer` 等 UI 库
- **`cmds/`** 只能 import `apis/`，不能跨命令 import 另一个 `cmd_*.py` 的内部函数
- **`apis/`** 返回值必须是 `pyrsult.Result[T, E]`
- **`cmds/`** 拿到 `Result` 后 match 分支渲染，不做业务决策

### 调用约定

**短操作（同步函数）—— 直接返回 Result：**

| 函数 | 位置 | 签名 | 说明 |
|---|---|---|---|
| `delete_package` | `apis/pkg.py` | `Result[None, Error]` | 删除包目录 |
| `list_packages` | `apis/pkg.py` | `Result[list[PackageInfo], Error]` | 遍历 libs 目录列出所有包 |
| `prune_packages` | `apis/pkg.py` | `Result[PruneReport, Error]` | 清理无 vindex.toml / 空目录 / 未使用的包 |
| `scaffold_project` | `apis/scaffold.py` | `Result[Path, Error]` | 创建 vindex.toml + main.vix + .gitignore 等 |
| `search_packages` | `apis/search.py` | `Result[list[PackageInfo], Error]` | 从 GitHub API 搜索 vlib-* 或 vtool-* 仓库 |
| `check_files` | `apis/build.py` | `Result[CheckReport, Error]` | 调用 `vixc --check` 检查语法和类型 |
| `delete_tool` | `apis/tool.py` | `Result[None, Error]` | 删除工具源码目录 + 编译产物 |

CLI 调用模板：

```python
match apis.pkg.delete_package(spec):
    case Success(None):
        log.ok(f"已删除 {spec}")
    case Failure(err):
        log.error(str(err))
```

**长操作（generator 流式）—— Generator[Event, None, Result[T, E]]：**

| 函数 | 位置 | 签名 | 说明 |
|---|---|---|---|
| `install_package` | `apis/pkg.py` | `Generator[Event, None, Result[PackageInfo, Error]]` | git clone + vindex 更新 + 传递依赖安装 |
| `update_package` | `apis/pkg.py` | `Generator[Event, None, Result[UpdateInfo, Error]]` | git pull + 传递依赖更新 |
| `install_dependencies` | `apis/pkg.py` | `Generator[Event, None, Result[list[PackageInfo], Error]]` | 从当前目录 vindex.toml 读取依赖并批量安装 |
| `install_tool` | `apis/tool.py` | `Generator[Event, None, Result[ToolInfo, Error]]` | git clone + vixc 编译，返回二进制路径 |
| `update_tool` | `apis/tool.py` | `Generator[Event, None, Result[UpdateInfo, Error]]` | git pull + 重新编译 |
| `build_project` | `apis/build.py` | `Generator[Event, None, Result[Path, BuildError]]` | 编译 main.vix，返回产物路径 |
| `build_and_run` | `apis/build.py` | `Generator[Event, None, Result[int, Error]]` | 编译 → 运行 → 清理；int 为子进程退出码 |

CLI 调用模板：

```python
for event in apis.pkg.install_package(spec):
    match event:
        case Progress(msg, pct):
            bar.update(pct or 0, description=msg)
        case Log(level, msg):
            getattr(log, level)(msg)

match event:  # false — 上面 for 循环出来后 event 是最后一个元素
```

正确的模式：

```python
gen = apis.pkg.install_package(spec)
for event in gen:
    match event:
        case Progress(msg, pct):
            ...
        case Log(level, msg):
            ...
try:
    result = gen.send(None)  # generator 的 return 值
except StopIteration as e:
    result = e.value

match result:
    case Success(info): ...
    case Failure(err):  ...
```

或更简洁的辅助函数（见下文）。

---

## Event 类型（`apis/_event.py`）

仅两种，通用所有长操作：

```python
@dataclass
class Progress:
    msg: str
    pct: float | None = None   # 0-100，None 表示不确定进度

@dataclass
class Log:
    level: str    # "debug" | "info" | "warn" | "error"
    msg: str
```

---

## Error 类型（`apis/_error.py`）

用 dataclass 联盟，不用异常继承。

```python
@dataclass
class NotFound:
    kind: str     # "package" | "tool" | "vindex" | "binary"
    name: str

@dataclass
class Validation:
    reason: str   # 包名格式错、路径穿越等

@dataclass
class IOError:        # 文件系统读写失败
    path: str
    detail: str

@dataclass
class GitClone:        # git clone 失败
    url: str
    detail: str

@dataclass
class GitPull:         # git pull 失败
    path: str
    detail: str

@dataclass
class Compile:         # vixc 编译失败
    exit_code: int
    output: str

@dataclass
class Network:         # GitHub API 请求失败
    url: str
    status: int | None
    detail: str

# 所有可能错误类型的联合
Error = NotFound | Validation | IOError | GitClone | GitPull | Compile | Network
```

CLI 渲染时 match `Failure(err)` 的 `err` 类型决定输出颜色和格式。

---

## 编程规范

### 命名

| 范畴 | 规则 | 示例 |
|---|---|---|
| 文件/目录 | 小写 + 下划线 | `cmd_add.py`, `_error.py` |
| 函数/变量 | 小写 + 下划线 | `install_package`, `pack_path` |
| 数据类 | 大驼峰 | `PackageNameInfo`, `InstallResult` |
| 私有模块 | 下划线前缀 | `_error.py`, `_event.py` |
| 复杂条件 | 大驼峰下划线变量 | `Is_Pure_Msg` |
| 模块级常量 | 全大写 | `VIX_HOME`, `DEFAULT_ORG` |
| 私有函数 | 下划线前缀 | `_read_cache`, `_fetch_with_retry` |

### 条件表达式

稍微长或难理解的 `if` 条件不要直接写，单独赋值变量（大驼峰下划线）：

```python
# 好
Is_Referenced = spec in referenced
Is_Global_Install = parent is not None

if Is_Referenced or Is_Global_Install:
    ...

# 不好
if spec in referenced or (parent is not None and ...):
    ...
```

### 错误处理

- 业务逻辑层（`apis/`）禁止使用 `try/except`（边缘情况用 `pyrsult.Result` 兜底）
- 外部交互（git clone、文件 I/O、subprocess）用 `try/except` 包裹并转为 `Failure(Error)`
- CLI 层（`cmds/`）收到 `Failure` 后 match 渲染，也不抛异常

```python
# apis/ 层 — 好
def delete_package(spec: str) -> Result[None, Error]:
    path = resolve_package_path(spec).map_err(...)
    try:
        shutil.rmtree(path.unwrap())
        return Success(None)
    except OSError as e:
        return Failure(IOError(path=str(path), detail=str(e)))
```

### 导入规则

| 层 | 允许 import | 禁止 import |
|---|---|---|
| `apis/` | Python 标准库、`pyrsult` | `rich`, `typer`, `gitpython`（由 CLI 传入回调查看进度）, `cmds.*` |
| `cmds/` | `apis.*`, `rich`, `typer`, `gitpython` | 跨命令 import 另一个 `cmd_*.py` 的内部函数 |

私有函数（下划线前缀）只能在模块内部使用。

### 注释

- 业务代码不写注释
- 公共 API 函数可以有大文档字符串描述参数和行为
- 私有函数不写文档字符串

### 代码风格

```bash
ruff check .    # lint
black .         # 自动格式化
```

---

## 依赖

运行时（`pyproject.toml` `[dependencies]`）：

| 库 | 用途 | 所在层 |
|---|---|---|
| `gitpython` | Git clone/pull | cmds（apis 通过回调解耦） |
| `rich` | 终端输出 | cmds 独占 |
| `typer` | CLI 框架 | cmds 独占 |
| `tqdm` | 进度条 | cmds 独占 |
| `tomli-w` | 写 vindex.toml | apis |
| `pyrsult` | Result/Option 类型 | apis |

---

## 如何添加一个新命令

1. 在 `apis/` 对应文件添加业务函数（同步或 generator，返回 `Result`）
2. 在 `cmds/` 创建 `cmd_xxx.py`，写 typer app + 回调函数
3. 回调函数解析参数 → 调用 apis 函数 → match Result 渲染
4. 在 `main.py` import 并注册 `app.add_typer(cmd_xxx.app)`
5. 更新版本号 + git 提交

---

## 辅助函数

generator 长操作的 `StopIteration` 取值比较繁琐，`apis/__init__.py` 导出一个辅助：

```python
from collections.abc import Generator

def collect(gen: Generator) -> Result:
    """消费 generator 所有事件，返回最终 Result"""
    for _ in gen:
        pass
    try:
        gen.send(None)
    except StopIteration as e:
        return e.value
```

CLI 在不需要事件时直接调用：

```python
match apis.collect(apis.pkg.install_package(spec)):
    case Success(info): log.ok(f"已安装 {info.full_name}")
    case Failure(err):  log.error(str(err))
```

---

## 测试

```bash
pytest tests/ -v
```

- `apis/` 层的纯功能测试（`parse_pack_name`, `PackageNameInfo`）用同步断言
- `apis/` 层的带 I/O 测试（`delete_package` 等）用 `tmp_path` fixture
- CLI 测试用 `typer.testing.CliRunner`
- `apis/` 函数返回 `Result` → 测试直接 `.unwrap()` 或 match 断言

---

## 移除的模块 / 重构要点

本次重构完整目标：

| 当前 | 目标 | 状态 |
|---|---|---|
| `cmds/tool/` | → `cmds/cmd_tool/` | 待改 |
| `cmds/installer.py` | → 合入 `apis/pkg.py` | 待改 |
| `cmds/utils.py` 中非 UI 函数 | → 迁移至 `apis/` | 待改 |
| `cmds/share/search.py` 中 fetch/cache | → 迁移至 `apis/search.py` | 待改 |
| `cmds/cmd_search.py` `cmds/cmd_tool/search.py` | → 共用 `apis/search.py` | 待改 |
| `cmds` 各 cmd_*.py 中的业务逻辑 | → 抽到 `apis/`，仅保留渲染 | 待改 |
| 重复的 git clone 逻辑（4 处） | → 统一在 `apis/pkg.py` | 待改 |
| 重复的传递依赖遍历（3 处） | → 统一在 `apis/vindex.py` | 待改 |
