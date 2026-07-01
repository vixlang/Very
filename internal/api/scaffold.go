package api

import (
	"os"
	"path/filepath"
)

func ScaffoldProject(name string, dirPath string) (string, error) {
	projectPath := dirPath
	if projectPath == "" {
		projectPath = name
	}

	if _, err := os.Stat(projectPath); err == nil {
		return "", &Validation{Reason: "目录 '" + projectPath + "' 已存在"}
	}

	if err := os.MkdirAll(projectPath, 0755); err != nil {
		return "", &IOError{Path: projectPath, Detail: err.Error()}
	}

	srcDir := filepath.Join(projectPath, "src")
	if err := os.MkdirAll(srcDir, 0755); err != nil {
		return "", &IOError{Path: srcDir, Detail: err.Error()}
	}

	files := map[string]string{
		filepath.Join(projectPath, "vindex.toml"): `[project]
name = "` + name + `"
version = "0.1.0"
authors = []
deps = []
`,
		filepath.Join(srcDir, "lib.vix"): `pub fn greet() {
    print("Hello from src/lib.vix!")
}
`,
		filepath.Join(projectPath, "main.vix"): `import "src/lib.vix"

fn main(): i32 {
    greet()
    return 0
}
`,
		filepath.Join(projectPath, ".gitignore"): `# Vix
*.o
*.out
*.exe
target/
.very/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
`,
		filepath.Join(projectPath, "README.md"): `# ` + name + `

Vix 项目

## 构建

` + "```" + `bash
very build
` + "```" + `
`,
	}

	for path, content := range files {
		if err := os.WriteFile(path, []byte(content), 0644); err != nil {
			return "", &IOError{Path: path, Detail: err.Error()}
		}
	}

	return projectPath, nil
}
