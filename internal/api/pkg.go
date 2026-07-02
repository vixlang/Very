package api

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/BurntSushi/toml"
)

type PackageInfo struct {
	Host      string
	User      string
	Repo      string
	FullName  string
	Path      string
	HasVIndex bool
}

type PruneReport struct {
	RemovedInvalid []string
	RemovedEmpty   []string
	RemovedUnused  []string
}

type UpdateInfo struct {
	FullName string
	Updated  bool
}

// iterPackageDirs 遍历 libs 目录下的 host/user/repo 三级嵌套目录。
// 返回 Go 1.23 风格的迭代器，供 ListPackages/PrunePackages 等函数消费。
func iterPackageDirs(libsPath string) func(func(string, string, string, string) bool) {
	return func(yield func(host, user, repo, fullName string) bool) {
		entries, err := os.ReadDir(libsPath)
		if err != nil {
			return
		}
		for _, hostEntry := range entries {
			if !hostEntry.IsDir() {
				continue
			}
			hostDir := filepath.Join(libsPath, hostEntry.Name())
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
					fullName := fmt.Sprintf("%s:%s.%s", hostEntry.Name(), userEntry.Name(), repoEntry.Name())
					if !yield(hostEntry.Name(), userEntry.Name(), repoEntry.Name(), fullName) {
						return
					}
				}
			}
		}
	}
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func gitClone(url, dest, branch string) error {
	args := []string{"clone", url, dest}
	if branch != "" {
		args = append(args, "-b", branch)
	}
	cmd := exec.Command("git", args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return &GitClone{URL: url, Detail: strings.TrimSpace(string(out))}
	}
	return nil
}

func gitPull(path string) (bool, error) {
	cmd := exec.Command("git", "-C", path, "pull")
	out, err := cmd.CombinedOutput()
	if err != nil {
		return false, &GitPull{Path: path, Detail: strings.TrimSpace(string(out))}
	}
	output := string(out)
	alreadyUpToDate := strings.Contains(output, "Already up to date") || strings.Contains(output, "已经是最新的")
	return !alreadyUpToDate, nil
}

func removeReadonly(path string) {
	os.RemoveAll(path)
}

func ListPackages() ([]*PackageInfo, error) {
	libsPath := Config{}.LocalLibsPath()
	if !fileExists(libsPath) {
		return nil, &NotFound{Kind: "libs_path", Name: libsPath}
	}

	var packages []*PackageInfo
	iterPackageDirs(libsPath)(func(host, user, repo, fullName string) bool {
		repoDir := filepath.Join(libsPath, host, user, repo)
		packages = append(packages, &PackageInfo{
			Host:      host,
			User:      user,
			Repo:      repo,
			FullName:  fullName,
			Path:      repoDir,
			HasVIndex: fileExists(filepath.Join(repoDir, "vindex.toml")),
		})
		return true
	})
	return packages, nil
}

func DeletePackage(spec string) error {
	pathsToCheck := []string{Config{}.LocalLibsPath(), Config{}.VIX_LIBS_PATH()}
	for _, libsPath := range pathsToCheck {
		info, err := ParsePackName(spec, libsPath)
		if err != nil {
			continue
		}
		packPath := info.PackPath()
		if fileExists(packPath) {
			if err := os.RemoveAll(packPath); err != nil {
				return &IOError{Path: packPath, Detail: err.Error()}
			}
			return nil
		}
	}
	return &NotFound{Kind: "package", Name: spec}
}

func FindUnusedPackages(libsPath string) map[string]bool {
	vindexPath := filepath.Join(".", "vindex.toml")
	var rootDeps []string
	if data, err := os.ReadFile(vindexPath); err == nil {
		var m map[string]any
		if err := toml.Unmarshal(data, &m); err == nil {
			if proj, ok := m["project"].(map[string]any); ok {
				if deps, ok := proj["deps"].([]any); ok {
					for _, d := range deps {
						if s, ok := d.(string); ok {
							rootDeps = append(rootDeps, s)
						}
					}
				}
			}
			if deps, ok := m["dependencies"].(map[string]any); ok {
				for d := range deps {
					rootDeps = append(rootDeps, d)
				}
			}
		}
	}

	referenced := BuildDepTree(libsPath, rootDeps)
	unused := make(map[string]bool)
	iterPackageDirs(libsPath)(func(host, user, repo, fullName string) bool {
		if !referenced[fullName] {
			unused[fullName] = true
		}
		return true
	})
	return unused
}

func PrunePackages(emptyOnly, invalidOnly, removeUnused bool) (*PruneReport, error) {
	libsPath := Config{}.LocalLibsPath()
	if !fileExists(libsPath) {
		return nil, &NotFound{Kind: "libs_path", Name: libsPath}
	}

	report := &PruneReport{}
	SpecificFlag := emptyOnly || invalidOnly || removeUnused

	if !emptyOnly && !(removeUnused && !invalidOnly) {
		iterPackageDirs(libsPath)(func(host, user, repo, fullName string) bool {
			repoDir := filepath.Join(libsPath, host, user, repo)
			if !fileExists(filepath.Join(repoDir, "vindex.toml")) {
				report.RemovedInvalid = append(report.RemovedInvalid, fullName)
				os.RemoveAll(repoDir)
			}
			return true
		})
	}

	if !invalidOnly && !(removeUnused && !emptyOnly) {
		removeEmptyDirs(libsPath, &report.RemovedEmpty)
	}

	shouldFindUnused := removeUnused || (!SpecificFlag)
	if shouldFindUnused {
		unused := FindUnusedPackages(libsPath)
		iterPackageDirs(libsPath)(func(host, user, repo, fullName string) bool {
			if unused[fullName] {
				report.RemovedUnused = append(report.RemovedUnused, fullName)
				repoDir := filepath.Join(libsPath, host, user, repo)
				os.RemoveAll(repoDir)
			}
			return true
		})
	}

	return report, nil
}

// removeEmptyDirs 从最深层向根目录删除空目录，避免父目录非空导致无法删除子目录。
func removeEmptyDirs(libsPath string, removed *[]string) {
	entries, _ := os.ReadDir(libsPath)
	for i := len(entries) - 1; i >= 0; i-- {
		hostDir := filepath.Join(libsPath, entries[i].Name())
		userEntries, _ := os.ReadDir(hostDir)
		for j := len(userEntries) - 1; j >= 0; j-- {
			userDir := filepath.Join(hostDir, userEntries[j].Name())
			repoEntries, _ := os.ReadDir(userDir)
			for k := len(repoEntries) - 1; k >= 0; k-- {
				repoDir := filepath.Join(userDir, repoEntries[k].Name())
				if isEmptyDir(repoDir) {
					*removed = append(*removed, relPath(libsPath, repoDir))
					os.Remove(repoDir)
				}
			}
			if isEmptyDir(userDir) {
				*removed = append(*removed, relPath(libsPath, userDir))
				os.Remove(userDir)
			}
		}
		if isEmptyDir(hostDir) {
			*removed = append(*removed, relPath(libsPath, hostDir))
			os.Remove(hostDir)
		}
	}
}

func isEmptyDir(path string) bool {
	entries, err := os.ReadDir(path)
	if err != nil {
		return false
	}
	return len(entries) == 0
}

func relPath(base, target string) string {
	rel, err := filepath.Rel(base, target)
	if err != nil {
		return target
	}
	return rel
}

func InstallPackage(spec string, forceLocal bool) (*PackageInfo, error) {
	libsPath := Config{}.LocalLibsPath()
	globalPath := Config{}.VIX_LIBS_PATH()

	info, err := ParsePackName(spec, libsPath)
	if err != nil {
		return nil, err
	}
	dest := info.PackPath()

	if fileExists(dest) {
		return &PackageInfo{
			Host:      info.GitMaster,
			User:      info.UserName,
			Repo:      info.RepoName,
			FullName:  info.FullName(),
			Path:      dest,
			HasVIndex: fileExists(filepath.Join(dest, "vindex.toml")),
		}, nil
	}

	if !forceLocal {
		globalInfo, err := ParsePackName(spec, globalPath)
		if err == nil {
			globalDest := globalInfo.PackPath()
			if fileExists(globalDest) {
				return &PackageInfo{
					Host:      globalInfo.GitMaster,
					User:      globalInfo.UserName,
					Repo:      globalInfo.RepoName,
					FullName:  globalInfo.FullName(),
					Path:      globalDest,
					HasVIndex: fileExists(filepath.Join(globalDest, "vindex.toml")),
				}, nil
			}
		}
	}

	if err := os.MkdirAll(libsPath, 0755); err != nil {
		return nil, &IOError{Path: libsPath, Detail: err.Error()}
	}
	hostDir := filepath.Join(libsPath, info.GitMaster)
	userDir := filepath.Join(hostDir, info.UserName)
	if err := os.MkdirAll(userDir, 0755); err != nil {
		return nil, &IOError{Path: userDir, Detail: err.Error()}
	}

	if err := gitClone(info.GitURL(), dest, info.BranchName); err != nil {
		return nil, err
	}

	hasVIndex := fileExists(filepath.Join(dest, "vindex.toml"))

	packInfo := &PackageInfo{
		Host:      info.GitMaster,
		User:      info.UserName,
		Repo:      info.RepoName,
		FullName:  info.FullName(),
		Path:      dest,
		HasVIndex: hasVIndex,
	}

	if hasVIndex {
		deps := GetTransitiveDeps(dest)
		for _, depSpec := range deps {
			_, err := InstallPackage(depSpec, forceLocal)
			if err != nil {
				_ = err // log in CLI layer
			}
		}
	}

	return packInfo, nil
}

func UpdatePackage(spec string) (*UpdateInfo, error) {
	return updatePackageInternal(spec, make(map[string]bool))
}

func updatePackageInternal(spec string, visited map[string]bool) (*UpdateInfo, error) {
	if visited[spec] {
		return &UpdateInfo{FullName: spec, Updated: false}, nil
	}
	visited[spec] = true

	pathsToCheck := []string{Config{}.LocalLibsPath(), Config{}.VIX_LIBS_PATH()}
	var packPath string
	var fullName string

	for _, libsPath := range pathsToCheck {
		info, err := ParsePackName(spec, libsPath)
		if err != nil {
			continue
		}
		if fileExists(info.PackPath()) {
			packPath = info.PackPath()
			fullName = info.FullName()
			break
		}
	}

	if packPath == "" {
		return nil, &NotFound{Kind: "package", Name: spec}
	}

	updated, err := gitPull(packPath)
	if err != nil {
		return nil, err
	}

	vindexFile := filepath.Join(packPath, "vindex.toml")
	if fileExists(vindexFile) {
		deps := GetTransitiveDeps(packPath)
		for _, depSpec := range deps {
			_, _ = updatePackageInternal(depSpec, visited)
		}
	}

	return &UpdateInfo{FullName: fullName, Updated: updated}, nil
}

func InstallDependencies(forceLocal bool) ([]*PackageInfo, error) {
	vindexPath := filepath.Join(".", "vindex.toml")
	if !fileExists(vindexPath) {
		return nil, &NotFound{Kind: "vindex.toml", Name: vindexPath}
	}

	data, err := os.ReadFile(vindexPath)
	if err != nil {
		return nil, &IOError{Path: vindexPath, Detail: err.Error()}
	}

	var m map[string]any
	if err := toml.Unmarshal(data, &m); err != nil {
		return nil, &IOError{Path: vindexPath, Detail: err.Error()}
	}

	var depSpecs []string
	if proj, ok := m["project"].(map[string]any); ok {
		if deps, ok := proj["deps"].([]any); ok {
			for _, d := range deps {
				if s, ok := d.(string); ok {
					depSpecs = append(depSpecs, s)
				}
			}
		}
	}
	if deps, ok := m["dependencies"].(map[string]any); ok {
		for d := range deps {
			depSpecs = append(depSpecs, d)
		}
	}

	deduped := make([]string, 0, len(depSpecs))
	seen := make(map[string]bool)
	for _, d := range depSpecs {
		if !seen[d] {
			seen[d] = true
			deduped = append(deduped, d)
		}
	}

	if len(deduped) == 0 {
		return []*PackageInfo{}, nil
	}

	var installed []*PackageInfo
	for _, depSpec := range deduped {
		packInfo, err := InstallPackage(depSpec, forceLocal)
		if err != nil {
			continue
		}
		installed = append(installed, packInfo)
	}

	return installed, nil
}

func ReadPackageReadme(spec string) (string, error) {
	pathsToCheck := []string{Config{}.LocalLibsPath(), Config{}.VIX_LIBS_PATH()}
	var packPath string

	for _, libsPath := range pathsToCheck {
		info, err := ParsePackName(spec, libsPath)
		if err != nil {
			continue
		}
		if fileExists(info.PackPath()) {
			packPath = info.PackPath()
			break
		}
	}

	if packPath == "" {
		return "", &NotFound{Kind: "package", Name: spec}
	}

	readmeName := "README.md"
	vindexFile := filepath.Join(packPath, "vindex.toml")
	if data, err := os.ReadFile(vindexFile); err == nil {
		var m map[string]any
		if err := toml.Unmarshal(data, &m); err == nil {
			if proj, ok := m["project"].(map[string]any); ok {
				if r, ok := proj["readme"].(string); ok {
					readmeName = r
				}
			}
		}
	}

	readmePath := filepath.Join(packPath, readmeName)
	if !fileExists(readmePath) {
		return "", &NotFound{Kind: "readme", Name: readmePath}
	}

	data, err := os.ReadFile(readmePath)
	if err != nil {
		return "", &IOError{Path: readmePath, Detail: err.Error()}
	}

	return string(data), nil
}
