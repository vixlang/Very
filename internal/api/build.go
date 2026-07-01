package api

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/BurntSushi/toml"
)

type CheckReport struct {
	Passed    bool
	Errors    []string
	FileCount int
}

func hasGCC() bool {
	_, err := exec.LookPath("gcc")
	return err == nil
}

func findEntrypoint(root string) (string, error) {
	vindex := filepath.Join(root, "vindex.toml")
	entrypoint := "main.vix"

	data, err := os.ReadFile(vindex)
	if err == nil {
		var m map[string]any
		if err := toml.Unmarshal(data, &m); err == nil {
			if proj, ok := m["project"].(map[string]any); ok {
				if ep, ok := proj["entrypoint"].(string); ok {
					entrypoint = ep
				}
			}
		}
	}

	path := filepath.Join(root, entrypoint)
	if _, err := os.Stat(path); err != nil {
		return "", &NotFound{Kind: "file", Name: path}
	}
	return path, nil
}

func defaultOutputName(root string) string {
	vindex := filepath.Join(root, "vindex.toml")
	name := "main"
	data, err := os.ReadFile(vindex)
	if err == nil {
		var m map[string]any
		if err := toml.Unmarshal(data, &m); err == nil {
			if proj, ok := m["project"].(map[string]any); ok {
				if n, ok := proj["name"].(string); ok {
					name = n
				}
			}
		}
	}
	if runtime.GOOS == "windows" {
		return name + ".exe"
	}
	return name
}

func BuildProject(root string, extraArgs []string) (string, error) {
	outputName := ""
	var restArgs []string
	for i := 0; i < len(extraArgs); i++ {
		if extraArgs[i] == "-o" && i+1 < len(extraArgs) {
			outputName = extraArgs[i+1]
			i++
		} else {
			restArgs = append(restArgs, extraArgs[i])
		}
	}
	if outputName == "" {
		outputName = defaultOutputName(root)
	}

	inputFile := ""
	var vixcFlags []string
	for _, a := range restArgs {
		if strings.HasSuffix(a, ".vix") && inputFile == "" {
			inputFile = a
		} else {
			vixcFlags = append(vixcFlags, a)
		}
	}

	if inputFile == "" {
		ep, err := findEntrypoint(root)
		if err != nil {
			return "", &IOError{Path: filepath.Join(root, "main.vix"), Detail: "入口文件不存在"}
		}
		inputFile = ep
	}

	tempDir := filepath.Join(root, ".vix", "temp")
	os.MkdirAll(tempDir, 0755)
	outputPath, _ := filepath.Abs(filepath.Join(root, outputName))
	hasGcc := hasGCC()

	if hasGcc {
		objPath := filepath.Join(tempDir, strings.TrimSuffix(filepath.Base(inputFile), ".vix")+".o")

		cmd1 := exec.Command("vixc", inputFile, "-obj", objPath)
		cmd1.Args = append(cmd1.Args, vixcFlags...)
		cmd1.Dir = root
		if out, err := cmd1.CombinedOutput(); err != nil {
			return "", &Compile{ExitCode: cmd1.ProcessState.ExitCode(), Output: strings.TrimSpace(string(out))}
		}

		cmd2 := exec.Command("gcc", objPath, "-o", outputPath)
		cmd2.Dir = root
		if out, err := cmd2.CombinedOutput(); err != nil {
			return "", &Compile{ExitCode: cmd2.ProcessState.ExitCode(), Output: strings.TrimSpace(string(out))}
		}
	} else {
		cmd := exec.Command("vixc", inputFile)
		cmd.Args = append(cmd.Args, vixcFlags...)
		cmd.Dir = root
		if out, err := cmd.CombinedOutput(); err != nil {
			return "", &Compile{ExitCode: cmd.ProcessState.ExitCode(), Output: strings.TrimSpace(string(out))}
		}
	}

	return outputPath, nil
}

func BuildAndRun(root string, extraArgs []string, keep bool) (int, error) {
	outputPath, err := BuildProject(root, extraArgs)
	if err != nil {
		return 1, err
	}

	cmd := exec.Command(outputPath)
	cmd.Dir = root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			if !keep {
				os.Remove(outputPath)
			}
			return exitErr.ExitCode(), nil
		}
		return 1, err
	}

	code := cmd.ProcessState.ExitCode()

	if !keep {
		os.Remove(outputPath)
	}

	return code, nil
}

func CheckFiles(patterns []string, root string) (*CheckReport, error) {
	var files []string
	if len(patterns) == 0 {
		ep, err := findEntrypoint(root)
		if err != nil {
			return nil, &NotFound{Kind: "file", Name: "main.vix"}
		}
		files = append(files, ep)
	} else {
		seen := make(map[string]bool)
		for _, p := range patterns {
			path := filepath.Join(root, p)
			info, err := os.Stat(path)
			if err != nil {
				continue
			}
			if info.IsDir() {
				filepath.Walk(path, func(walkPath string, walkInfo os.FileInfo, err error) error {
					if err != nil || walkInfo.IsDir() {
						return nil
					}
					if strings.HasSuffix(walkPath, ".vix") {
						abs, _ := filepath.Abs(walkPath)
						if !seen[abs] {
							seen[abs] = true
							files = append(files, walkPath)
						}
					}
					return nil
				})
			} else {
				abs, _ := filepath.Abs(path)
				if !seen[abs] {
					seen[abs] = true
					files = append(files, path)
				}
			}
		}
	}

	if len(files) == 0 {
		return nil, &NotFound{Kind: "file", Name: strings.Join(patterns, ", ")}
	}

	var errors []string
	for _, f := range files {
		cmd := exec.Command("vixc", f, "--check")
		cmd.Dir = root
		out, err := cmd.CombinedOutput()
		if err != nil {
			errMsg := strings.TrimSpace(string(out))
			if errMsg == "" {
				errMsg = "退出码 " + string(rune(cmd.ProcessState.ExitCode()))
			}
			errors = append(errors, f+": "+errMsg)
		}
	}

	return &CheckReport{
		Passed:    len(errors) == 0,
		Errors:    errors,
		FileCount: len(files),
	}, nil
}
