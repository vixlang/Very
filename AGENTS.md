# AGENTS.md — very

## Project

Vix language project management & build tool. CLI name: `very`.

- **Python** >=3.13, **uv**-managed, setuptools build
- Entrypoint: `main.py` → `main:main` (installed as `very` via `pyproject.toml` `[project.scripts]`)
- Commands: `add`, `del`, `list`, `prune`, `init`, `search`, `install`, `update` — registered in `cmds/__init__.py`, all extend `Command` from `cmds/base.py`

## Commands

```bash
uv tool install .                    # install `very` CLI
very add <package>                   # git-clone into .vix/libs/
very del <package>                   # rm -rf from .vix/libs/
very list [-t|--tree]                # list installed packages
very prune [--empty-only | --invalid-only]
very init <name>                     # scaffold new vix project
very search [keyword] [--sort stars|updated|name] [--limit N] [--no-cache] [--clear-cache] [--cache-status]
very install                         # install deps from vix.toml
very update [<package>]              # git pull package(s)
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

## Lint & format

```bash
ruff check .       # linter (dev dep)
black .            # formatter (dev dep)
```

Test framework: `pytest` (dev dep). Run: `uv run pytest tests/` (100 tests, all passing).

## Config & paths

- `VIX_HOME` env var overrides default `.vix/` (gitignored)
- Installed packages: `$VIX_HOME/libs/{host}/{user}/{repo}/`
- Package validity: must contain `vindex.toml`
- Search cache: `$VIX_HOME/cache/search_cache.json` (1 h expiry)

## Dependencies

- Runtime: `gitpython`, `rich`, `tqdm`
- Dev: `ruff`, `black`

PyPI index defaults to Tsinghua mirror (commented out in `pyproject.toml`; uncomment `[[tool.uv.index]]` to enable).

`uv.lock` is gitignored — run `uv lock` to regenerate.

## Workflow

- 任何修改都要及时 git 提交
- 对于探索类型任务, 拆分模块发动多个 subagent 并发探索, 不要只用单个 agent
