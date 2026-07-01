# vindex.toml 配置

`vindex.toml` 是 Vix 项目的配置文件，采用 [TOML](https://toml.io) 格式，位于项目根目录。

## 示例

```toml
[project]
name = "myapp"
version = "0.1.0"
entrypoint = "src/main.vix"
deps = [
    "vnet",
    "fexcode.vlib-json",
]
```

## 配置项

### `[project]` — 项目配置

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `name` | string | 是 | — | 项目名称，用于编译产物的默认输出文件名 |
| `version` | string | 否 | — | 项目版本号 |
| `entrypoint` | string | 否 | `"main.vix"` | 编译型项目的入口文件。**第三方库不应设置此项**，库的入口必须是 `main.vix` |
| `deps` | array | 否 | `[]` | 依赖的包列表，每个元素是一个包名（支持 `add` 命令的所有简写格式） |

### `[dependencies]` — 已弃用

旧版依赖声明方式，使用 TOML 表格键值对形式：

```toml
[dependencies]
vnet = "latest"
```

该格式已被 `project.deps` 数组取代。`very add` 写入时会自动将旧格式迁移到新格式并移除 `[dependencies]` 表格。

## 示例：完整项目

```toml
[project]
name = "webapp"
version = "1.0.0"
entrypoint = "app/main.vix"
deps = [
    "vnet@master",
    "gitee.com:fexcode.vlib-html",
    "vlib-json",
]
```

## 生成的项目骨架（`very init`）

```
my-project/
├── vindex.toml          # 项目配置（版本、依赖、入口）
├── main.vix             # 主入口
├── src/
│   └── lib.vix          # 示例库模块
├── .gitignore
└── README.md
```

## 依赖包名格式

`deps` 数组中每个元素和 `very add` 命令的包名完全一致：

| 格式 | 示例 | 解析结果 |
|---|---|---|
| bare name | `vnet` | `github.com/vixlang/vlib-vnet` |
| user.repo | `fexcode.vnet` | `github.com/fexcode/vnet` |
| user.repo@branch | `fexcode.vnet@master` | `github.com/fexcode/vnet` #master |
| host:user.repo | `gitee.com:fexcode.vnet` | `gitee.com/fexcode/vnet` |
| @user.repo | `@fexcode.vnet` | `gitee.com/fexcode/vnet` |
