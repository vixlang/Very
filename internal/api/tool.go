package api

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/BurntSushi/toml"
)

type ToolInfo struct {
	FullName   string
	BinaryPath string
}

type ToolPruneReport struct {
	RemovedInvalid  []string
	RemovedEmpty    []string
	RemovedOrphaned []string
}

func toolEntrypoint(dirPath string) string {
	return getEntrypoint(filepath.Join(dirPath, "vindex.toml"))
}

func getEntrypoint(vindexPath string) string {
	data, err := os.ReadFile(vindexPath)
	if err != nil {
		return "main.vix"
	}
	var m map[string]any
	if err := toml.Unmarshal(data, &m); err != nil {
		return "main.vix"
	}
	if proj, ok := m["project"].(map[string]any); ok {
		if ep, ok := proj["entrypoint"].(string); ok {
			return ep
		}
	}
	return "main.vix"
}

func compileTool(sourceDir, binaryPath string) error {
	entryName := toolEntrypoint(sourceDir)
	inputFile := filepath.Join(sourceDir, entryName)

	if !fileExists(inputFile) {
		return &IOError{Path: inputFile, Detail: fmt.Sprintf("入口文件不存在: %s", inputFile)}
	}

	os.MkdirAll(filepath.Dir(binaryPath), 0755)

	if hasGCC() {
		tempDir := filepath.Join(sourceDir, ".vix", "temp")
		os.MkdirAll(tempDir, 0755)
		objPath := filepath.Join(tempDir, strings.TrimSuffix(entryName, ".vix")+".o")

		cmd1 := exec.Command("vixc", inputFile, "-obj", objPath)
		cmd1.Dir = sourceDir
		if out, err := cmd1.CombinedOutput(); err != nil {
			return &Compile{ExitCode: cmd1.ProcessState.ExitCode(), Output: strings.TrimSpace(string(out))}
		}

		cmd2 := exec.Command("gcc", objPath, "-o", binaryPath)
		if out, err := cmd2.CombinedOutput(); err != nil {
			return &Compile{ExitCode: cmd2.ProcessState.ExitCode(), Output: strings.TrimSpace(string(out))}
		}
	} else {
		cmd := exec.Command("vixc", inputFile, "-o", binaryPath)
		cmd.Dir = sourceDir
		if out, err := cmd.CombinedOutput(); err != nil {
			return &Compile{ExitCode: cmd.ProcessState.ExitCode(), Output: strings.TrimSpace(string(out))}
		}
	}

	if !fileExists(binaryPath) {
		return &IOError{Path: binaryPath, Detail: "编译产物未生成"}
	}

	return nil
}

func InstallTool(packname string) (*ToolInfo, error) {
	info, err := ParseToolName(packname, Config{}.VIX_TOOLS_PATH())
	if err != nil {
		return nil, err
	}
	packPath := info.PackPath()

	if !fileExists(packPath) {
		if err := gitClone(info.GitURL(), packPath, info.BranchName); err != nil {
			os.RemoveAll(packPath)
			return nil, err
		}
	}

	vindex := NewVIndexTool(packPath)
	content, ok := vindex.Content()
	if !ok {
		return nil, &Validation{Reason: fmt.Sprintf("%s 缺少 vindex.toml", info.FullName())}
	}

	projectName := info.RepoName
	if proj, ok := content["project"].(map[string]any); ok {
		if n, ok := proj["name"].(string); ok {
			projectName = n
		}
	}

	suffix := ""
	if runtime.GOOS == "windows" {
		suffix = ".exe"
	}
	binaryName := projectName + suffix
	binaryPath, _ := filepath.Abs(filepath.Join(Config{}.VIX_TOOLS_PATH(), binaryName))

	if err := compileTool(packPath, binaryPath); err != nil {
		return nil, err
	}

	return &ToolInfo{FullName: info.FullName(), BinaryPath: binaryPath}, nil
}

func DeleteTool(packname string) error {
	info, err := ParseToolName(packname, Config{}.VIX_TOOLS_PATH())
	if err != nil {
		return err
	}
	packPath := info.PackPath()

	if !fileExists(packPath) {
		return &NotFound{Kind: "tool", Name: info.FullName()}
	}

	vindex := NewVIndexTool(packPath)
	projectName := info.RepoName
	if content, ok := vindex.Content(); ok {
		if proj, ok := content["project"].(map[string]any); ok {
			if n, ok := proj["name"].(string); ok {
				projectName = n
			}
		}
	}

	suffix := ""
	if runtime.GOOS == "windows" {
		suffix = ".exe"
	}
	binaryPath := filepath.Join(Config{}.VIX_TOOLS_PATH(), projectName+suffix)
	os.Remove(binaryPath)
	os.RemoveAll(packPath)

	for _, d := range []string{filepath.Dir(packPath), filepath.Dir(filepath.Dir(packPath))} {
		if isEmptyDir(d) {
			os.Remove(d)
		}
	}

	return nil
}

func ListTools() ([]string, error) {
	toolsPath := Config{}.VIX_TOOLS_PATH()
	if !fileExists(toolsPath) {
		return []string{}, nil
	}

	var names []string
	entries, err := os.ReadDir(toolsPath)
	if err != nil {
		return nil, &IOError{Path: toolsPath, Detail: err.Error()}
	}

	for _, hostEntry := range entries {
		if !hostEntry.IsDir() {
			continue
		}
		hostDir := filepath.Join(toolsPath, hostEntry.Name())
		userEntries, err := os.ReadDir(hostDir)
		if err != nil {
			continue
		}
		for _, userEntry := range userEntries {
			if !userEntry.IsDir() {
				continue
			}
			userDir := filepath.Join(hostDir, userEntry.Name())
			repoEntries, err := os.ReadDir(userDir)
			if err != nil {
				continue
			}
			for _, repoEntry := range repoEntries {
				if !repoEntry.IsDir() {
					continue
				}
				names = append(names, fmt.Sprintf("%s:%s.%s", hostEntry.Name(), userEntry.Name(), repoEntry.Name()))
			}
		}
	}
	return names, nil
}

func UpdateTool(packname string) (*ToolInfo, error) {
	info, err := ParseToolName(packname, Config{}.VIX_TOOLS_PATH())
	if err != nil {
		return nil, err
	}
	packPath := info.PackPath()

	if !fileExists(packPath) {
		return InstallTool(packname)
	}

	isUpdated, err := gitPull(packPath)
	if err != nil {
		return nil, err
	}
	_ = isUpdated

	vindex := NewVIndexTool(packPath)
	content, ok := vindex.Content()
	if !ok {
		return nil, &Validation{Reason: fmt.Sprintf("%s 缺少 vindex.toml", info.FullName())}
	}

	projectName := info.RepoName
	if proj, ok := content["project"].(map[string]any); ok {
		if n, ok := proj["name"].(string); ok {
			projectName = n
		}
	}

	suffix := ""
	if runtime.GOOS == "windows" {
		suffix = ".exe"
	}
	binaryName := projectName + suffix
	binaryPath, _ := filepath.Abs(filepath.Join(Config{}.VIX_TOOLS_PATH(), binaryName))

	if err := compileTool(packPath, binaryPath); err != nil {
		return nil, err
	}

	return &ToolInfo{FullName: info.FullName(), BinaryPath: binaryPath}, nil
}

func PruneTools(emptyOnly, invalidOnly bool) (*ToolPruneReport, error) {
	toolsPath := Config{}.VIX_TOOLS_PATH()
	if !fileExists(toolsPath) {
		return nil, &NotFound{Kind: "tools_path", Name: toolsPath}
	}

	report := &ToolPruneReport{}

	if !emptyOnly {
		entries, _ := os.ReadDir(toolsPath)
		for _, hostEntry := range entries {
			if !hostEntry.IsDir() {
				continue
			}
			hostDir := filepath.Join(toolsPath, hostEntry.Name())
			userEntries, _ := os.ReadDir(hostDir)
			for _, userEntry := range userEntries {
				if !userEntry.IsDir() {
					continue
				}
				userDir := filepath.Join(hostDir, userEntry.Name())
				repoEntries, _ := os.ReadDir(userDir)
				for _, repoEntry := range repoEntries {
					if !repoEntry.IsDir() {
						continue
					}
					repoDir := filepath.Join(userDir, repoEntry.Name())
					fullName := fmt.Sprintf("%s:%s.%s", hostEntry.Name(), userEntry.Name(), repoEntry.Name())
					if !fileExists(filepath.Join(repoDir, "vindex.toml")) {
						report.RemovedInvalid = append(report.RemovedInvalid, fullName)
						os.RemoveAll(repoDir)
					}
				}
			}
		}
	}

	if !invalidOnly {
		removeEmptyDirs(toolsPath, &report.RemovedEmpty)
	}

	shouldFindOrphaned := !emptyOnly && !invalidOnly
	if shouldFindOrphaned {
		expected := make(map[string]bool)
		entries, _ := os.ReadDir(toolsPath)
		for _, hostEntry := range entries {
			if !hostEntry.IsDir() {
				continue
			}
			hostDir := filepath.Join(toolsPath, hostEntry.Name())
			userEntries, _ := os.ReadDir(hostDir)
			for _, userEntry := range userEntries {
				if !userEntry.IsDir() {
					continue
				}
				userDir := filepath.Join(hostDir, userEntry.Name())
				repoEntries, _ := os.ReadDir(userDir)
				for _, repoEntry := range repoEntries {
					if !repoEntry.IsDir() {
						continue
					}
					repoDir := filepath.Join(userDir, repoEntry.Name())
					vindex := NewVIndexTool(repoDir)
					projName := repoEntry.Name()
					if content, ok := vindex.Content(); ok {
						if proj, ok := content["project"].(map[string]any); ok {
							if n, ok := proj["name"].(string); ok {
								projName = n
							}
						}
					}
					expected[projName] = true
				}
			}
		}

		dirEntries, _ := os.ReadDir(toolsPath)
		for _, entry := range dirEntries {
			if entry.IsDir() {
				continue
			}
			name := strings.TrimSuffix(entry.Name(), ".exe")
			if !expected[name] {
				report.RemovedOrphaned = append(report.RemovedOrphaned, entry.Name())
				os.Remove(filepath.Join(toolsPath, entry.Name()))
			}
		}
	}

	return report, nil
}
