package api

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const VSTD_URL = "https://github.com/vixlang/vstd"

func SyncStd() (string, error) {
	stdPath := filepath.Join(Config{}.VIX_HOME(), "std")
	if err := os.MkdirAll(stdPath, 0755); err != nil {
		return "", &IOError{Path: stdPath, Detail: err.Error()}
	}

	gitDir := filepath.Join(stdPath, ".git")
	if _, err := os.Stat(gitDir); err == nil {
		cmd := exec.Command("git", "-C", stdPath, "pull")
		out, err := cmd.CombinedOutput()
		if err != nil {
			return "", &GitPull{Path: stdPath, Detail: strings.TrimSpace(string(out))}
		}
		return stdPath, nil
	}

	os.RemoveAll(stdPath)
	if err := os.MkdirAll(stdPath, 0755); err != nil {
		return "", &IOError{Path: stdPath, Detail: err.Error()}
	}

	cmd := exec.Command("git", "clone", VSTD_URL, stdPath)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return "", &GitClone{URL: VSTD_URL, Detail: strings.TrimSpace(string(out))}
	}

	return stdPath, nil
}
