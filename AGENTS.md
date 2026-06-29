# AGENTS.md — very

## Project

Vix language project management & build tool. CLI name: `very`.

- **Python** >=3.13, **uv**-managed, setuptools build
- Entrypoint: `main.py` → `main:entry` (installed as `very` via `pyproject.toml` `[project.scripts]`)
- Commands: `add`, `del`, `list`, `prune`, `init`, `search`, `install`, `update`, `run`, `exe`, `tool` — registered in `main.py` via typer subcommands

## Commands

```bash
uv tool install .                    # install `very` CLI
very add <package> [-g|--global]     # git-clone into .vix/libs/ (local default; -g for $VIX_HOME)
very del <package>                   # rm -rf from .vix/libs/
very list [-t|--tree]                # list installed packages
very prune [--empty-only | --invalid-only]
very init <name>                     # scaffold new vix project
very search [keyword] [options]      # search packages from github.com/vixlang
very build [vixc options...]         # compile main.vix
very run [-k|--keep] [vixc options...] # build + run + cleanup (keep with -k)
very install                         # install deps from vindex.toml
very update [<package>]              # git pull package(s)
very tool add <package>              # clone + compile a vix tool into $VIX_HOME/tools/
very tool del <package>              # rm -rf tool source + binary from $VIX_HOME/tools/
very tool update <package>           # git pull + recompile a vix tool
very tool update <package>           # git pull + recompile a vix tool
very tool search [keyword] [options] # search vix tools (vtool-* repos on github.com/vixlang)
very tool prune [--empty-only | --invalid-only]  # clean orphaned binaries, empty dirs, invalid tool sources
very exe <tool> [args...]            # find and run a compiled tool (auto-installs if missing)
```

## Package naming (`cmds/utils.py:161`)

`parse_pack_name()` handles many shorthand forms:

| Input | Resolves to |
|---|---|
| `fexcode.vnet` | `github.com/fexcode/vnet` |
| `fexcode.vnet@master` | `github.com/fexcode/vnet` branch master |
| `gitee.com:fexcode.vnet` | `gitee.com/fexcode/vnet` |
| `gitee:fexcode.vnet` | `gitee.com/fexcode/vnet` (`.com` auto-added) |
| `@fexcode.vnet` | `gitee.com/fexcode/vnet` (`@` prefix → gitee) |
| `vnet` (bare name) | `github.com/vixlang/vlib-vnet` |

## Lint & format & test

```bash
ruff check .       # linter (dev dep)
black .            # formatter (dev dep)
pytest tests/ -v   # 29 tests (dev dep: pytest)
```

## Config & paths

- `VIX_HOME` env var overrides default `.vix/` (gitignored)
- `very add` installs locally (`.vix/libs/`) by default; use `-g` for `$VIX_HOME/libs/`
- `very tool add` installs tools to `$VIX_HOME/tools/` (cloned source) with compiled binaries at `$VIX_HOME/tools/<name>.exe`
- Installed packages: `$VIX_HOME/libs/{host}/{user}/{repo}/`
- Package validity: must contain `vindex.toml`
- Search cache: `$VIX_HOME/cache/search_cache.json` (1 h expiry)
- Tool search cache: `$VIX_HOME/tools/cache/tool_search_cache.json` (1 h expiry)

## Dependencies

- Runtime: `gitpython`, `rich`, `tqdm`, `tomli-w`
- Dev: `ruff`, `black`

PyPI index defaults to Tsinghua mirror (enabled in `pyproject.toml`).

`uv.lock` is gitignored — run `uv lock` to regenerate.

## Workflow

- 任何修改都要及时 git 提交
- ⚠️ **任何代码/功能修改后一定一定一定要更新版本号 (pyproject.toml)** ⚠️
- 对于探索类型任务, 拆分模块发动多个 subagent 并发探索, 不要只用单个 agent
