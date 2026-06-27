# Vix CLI 重构: Typer + Rich 替换方案

**Goal:** 用 Typer 函数替换 argparse class + CMD_REGISTRY，删除 Logger/GitProgress/命令格式说明等 500+ 行样板代码

**Architecture:** 保留每个 cmd_*.py 的业务逻辑不变，仅将 class+set_parser+execute 替换为 @app.command() 函数。main.py 从 Very(60行) 缩为 Typer.app(15行)。UI 输出: log.xxx → typer.echo/secho，Rich Table/Panel/Tree 保留原样。

**Tech Stack:** Python 3.13+, Typer≥0.15, Rich (已有)

## 文件结构总览

| 文件 | 操作 | 行数变化 |
|---|---|---|
| `pyproject.toml` | 加 `typer>=0.15` | +1 |
| `main.py` | 重写为 Typer app | -60 |
| `cmds/base.py` | 删除 | -23 |
| `cmds/__init__.py` | 删 CMD_REGISTRY | -30 |
| `cmds/utils.py` | 删 Logger 类 + create_git_progress | -65 |
| `cmds/installer.py` | 删 GitProgress 类，加回调参数 | -45 |
| `cmds/cmd_add.py` | class → typer fn + 删 命令格式说明 | -70 |
| `cmds/cmd_del.py` | class → typer fn + 删 命令格式说明 | -40 |
| `cmds/cmd_list.py` | class → typer fn + 删 命令格式说明 | -50 |
| `cmds/cmd_prune.py` | class → typer fn + 删 命令格式说明 | -60 |
| `cmds/cmd_good.py` | class → typer fn + 删 命令格式说明 | -50 |
| `cmds/cmd_build.py` | class → typer fn | -40 |
| `cmds/cmd_run.py` | class → typer fn | -40 |
| `cmds/cmd_init.py` | class → typer fn | -40 |
| `cmds/cmd_search.py` | class → typer fn | -80 |
| `cmds/cmd_install.py` | class → typer fn | -50 |
| `cmds/cmd_update.py` | class → typer fn | -30 |
| `cmds/cmd_tool.py` | class → nested typer apps | -150 |
| `cmds/cmd_exe.py` | class → typer fn | -20 |

### Task 1: 加 Typer 依赖 + 删 cmds/base.py + 更新 cmds/__init__.py

**Files:**
- Modify: `pyproject.toml` — 加 `"typer>=0.15"`
- Delete: `cmds/base.py`
- Rewrite: `cmds/__init__.py` — 删 CMD_REGISTRY，只保留子模块 import

### Task 2: 重写 main.py 为 Typer app

**Files:**
- Modify: `main.py` — 整个文件重写 ~15 行

### Task 3-15: 重写每个 cmd_*.py 为 typer 函数

**模式:** 每个文件导出 typer.Typer() app。class set_parser+execute → @app.command() 函数。命令格式说明变量删除。log.xxx → typer.secho/console.print。

### Task 16: 清理 cmds/utils.py

- 删除 Logger 类、log 单例、create_git_progress
- 保留 Config、parse_pack_name、console、ask_confirm、iter_package_dirs、build_dep_tree 等

### Task 17: 重构 cmds/installer.py

- 删除 GitProgress 类
- install_one / install_transitive_deps 去掉 log 调用

### Task 18: 最终验证

- `very --help`、`very add --help`、`very --version`
- `ruff check .`
