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
- `add <package>`
- `list`
- `--help`
- `--version`

Package support is a first bootstrap pass: `add` normalizes the same common
Very shorthand forms and clones into `.vix/libs`, but full dependency graph
resolution remains in the Python implementation.

Commands not yet implemented in Vix are delegated to the Python Very entrypoint
as a compatibility bridge.
