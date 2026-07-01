# very-vix

`very-vix` is a bootstrap Vix implementation of the Very project manager.
It is intentionally small and isolated from the Python implementation in the
parent directory.

## Build

```sh
./build.sh
```

The script uses `/home/zty/Vix-lang/bootstrap/vixc0` by default. Override with
`VIX_BOOTSTRAP=/path/to/bootstrap` or `VIXC0=/path/to/vixc0`.

The generated `very-vix` binary also uses the bootstrap compiler for local
project commands:

- `build` runs `vixc0 -exe`
- `good` runs `vixc0 --check`
- `run` builds with `vixc0` before executing the output

Project source and output paths are resolved to absolute paths before invoking
`vixc0`, so commands work from normal project directories.

## Implemented commands

- `init <name>`
- `build [file] [-o out]`
- `run [file] [-o out]`
- `good [file]`
- `info`
- `add <package>`
- `list`
- `--help`
- `--version`

Package support is a first bootstrap pass: `add` normalizes the same common
Very shorthand forms and clones into `.vix/libs`, but full dependency graph
resolution remains in the Python implementation.

## TOML support

`very-vix` parses the subset of `vindex.toml` needed for bootstrap project
management:

- `[project].name`
- `[project].entrypoint`
- `[project].deps` as a string array
- legacy `[dependencies]` keys as dependency names

`build`, `good`, and `run` use `project.entrypoint` when no source file is
provided. `build` and `run` use `project.name` when `-o` is not provided.

Commands not yet implemented in Vix are delegated to the Python Very entrypoint
as a compatibility bridge.

## Source Layout

- `main.vix`: command dispatch and top-level help/version output
- `util.vix`: file IO, process execution, path helpers, and string helpers
- `vindex.vix`: bootstrap TOML parsing and `vindex.toml` loading
- `package.vix`: package name normalization and argument safety checks
- `project_args.vix`: shared source/output argument defaults
- `cmd_*.vix`: one module per command implementation
