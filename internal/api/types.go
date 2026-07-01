package api

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var (
	_VIX_HOME = func() string {
		if v := os.Getenv("VIX_HOME"); v != "" {
			return v
		}
		return "./.vix"
	}()

	DEFAULT_HOST = "github.com"
	DEFAULT_ORG  = "vixlang"
	VLIB_PREFIX  = "vlib-"
	VTOOL_PREFIX = "vtool-"
)

type Config struct{}

func (Config) VIX_HOME() string        { return _VIX_HOME }
func (Config) VIX_LIBS_PATH() string   { return filepath.Join(_VIX_HOME, "libs") }
func (Config) VIX_TOOLS_PATH() string  { return filepath.Join(_VIX_HOME, "tools") }
func (Config) LocalLibsPath() string   { return filepath.Join(".", ".vix", "libs") }

type PackageNameInfo struct {
	RepoName   string
	GitMaster  string
	UserName   string
	BranchName string
	Parent     string
}

func (i PackageNameInfo) PackPath() string {
	parent := i.Parent
	if parent == "" {
		parent = Config{}.VIX_LIBS_PATH()
	}
	return filepath.Join(parent, i.GitMaster, i.UserName, i.RepoName)
}

func (i PackageNameInfo) GitURL() string {
	return fmt.Sprintf("https://%s/%s/%s", i.GitMaster, i.UserName, i.RepoName)
}

func (i PackageNameInfo) FullName() string {
	return fmt.Sprintf("%s:%s.%s", i.GitMaster, i.UserName, i.RepoName)
}

var _gitSuffixRE = regexp.MustCompile(`\.git$`)

func parsePackName(packageName string, parent string, barePrefix string) (PackageNameInfo, error) {
	original := packageName
	defaultHost := DEFAULT_HOST

	if strings.HasPrefix(packageName, "@") && !strings.Contains(packageName, "://") {
		defaultHost = "gitee.com"
		packageName = packageName[1:]
	}

	if strings.Contains(packageName, "://") {
		parsed := strings.TrimPrefix(packageName, "https://")
		parsed = strings.TrimPrefix(parsed, "http://")
		host := parsed
		pathPart := ""
		if idx := strings.Index(parsed, "/"); idx >= 0 {
			host = parsed[:idx]
			pathPart = parsed[idx+1:]
		}
		pathPart = _gitSuffixRE.ReplaceAllString(pathPart, "")
		parts := strings.Split(pathPart, "/")
		if len(parts) >= 2 {
			return PackageNameInfo{
				GitMaster: host,
				UserName:  parts[0],
				RepoName:  parts[1],
				Parent:    parent,
			}, nil
		}
		return PackageNameInfo{}, fmt.Errorf("URL 格式无法提取用户/仓库: %s", original)
	}

	var branch string
	if strings.Contains(packageName, "@") && !strings.HasPrefix(packageName, "@") {
		idx := strings.LastIndex(packageName, "@")
		after := packageName[idx+1:]
		if after != "" && !strings.Contains(after, "/") && !strings.Contains(after, ":") {
			branch = after
			packageName = packageName[:idx]
		}
	}

	if strings.Contains(packageName, "@") && strings.Contains(packageName, ":") {
		parts := strings.SplitN(packageName, ":", 2)
		hostPart := parts[0]
		thePath := parts[1]
		host := hostPart
		if idx := strings.LastIndex(hostPart, "@"); idx >= 0 {
			host = hostPart[idx+1:]
		}
		if !strings.Contains(host, ".") {
			host += ".com"
		}
		thePath = _gitSuffixRE.ReplaceAllString(thePath, "")
		var pathParts []string
		if strings.Contains(thePath, "/") {
			pathParts = strings.Split(thePath, "/")
		} else {
			pathParts = strings.Split(strings.ReplaceAll(thePath, ".", "/"), "/")
		}
		if len(pathParts) >= 2 {
			return PackageNameInfo{
				GitMaster:   host,
				UserName:    pathParts[0],
				RepoName:    pathParts[1],
				BranchName:  branch,
				Parent:      parent,
			}, nil
		}
		return PackageNameInfo{}, fmt.Errorf("SCP 格式无法解析路径: %s", original)
	}

	if strings.Contains(packageName, ":") {
		parts := strings.SplitN(packageName, ":", 2)
		host := parts[0]
		thePath := parts[1]
		if !strings.Contains(host, ".") {
			host += ".com"
		}
		thePath = _gitSuffixRE.ReplaceAllString(thePath, "")
		if !strings.Contains(thePath, "/") && !strings.Contains(thePath, ".") {
			thePath = fmt.Sprintf("%s.%s%s", DEFAULT_ORG, VLIB_PREFIX, thePath)
		}
		if !strings.Contains(thePath, "/") {
			thePath = strings.ReplaceAll(thePath, ".", "/")
		}
		pathParts := strings.Split(thePath, "/")
		if len(pathParts) >= 2 {
			return PackageNameInfo{
				GitMaster:   host,
				UserName:    pathParts[0],
				RepoName:    pathParts[1],
				BranchName:  branch,
				Parent:      parent,
			}, nil
		}
		return PackageNameInfo{}, fmt.Errorf("包名格式错误: %s", original)
	}

	if strings.Contains(packageName, "/") {
		parts := strings.Split(packageName, "/")
		if len(parts) >= 2 {
			repo := _gitSuffixRE.ReplaceAllString(parts[1], "")
			return PackageNameInfo{
				GitMaster:   defaultHost,
				UserName:    parts[0],
				RepoName:    repo,
				BranchName:  branch,
				Parent:      parent,
			}, nil
		}
		return PackageNameInfo{}, fmt.Errorf("包名格式错误: %s", original)
	}

	if strings.Contains(packageName, ".") {
		pathStr := strings.ReplaceAll(packageName, ".", "/")
		parts := strings.Split(pathStr, "/")
		if len(parts) >= 2 {
			repo := _gitSuffixRE.ReplaceAllString(parts[1], "")
			return PackageNameInfo{
				GitMaster:   defaultHost,
				UserName:    parts[0],
				RepoName:    repo,
				BranchName:  branch,
				Parent:      parent,
			}, nil
		}
		return PackageNameInfo{}, fmt.Errorf("包名格式错误: %s", original)
	}

	return PackageNameInfo{
		GitMaster:   defaultHost,
		UserName:    DEFAULT_ORG,
		RepoName:    barePrefix + packageName,
		BranchName:  branch,
		Parent:      parent,
	}, nil
}

func ParsePackName(packageName string, parent string) (PackageNameInfo, error) {
	return parsePackName(packageName, parent, VLIB_PREFIX)
}

func ParseToolName(packageName string, parent string) (PackageNameInfo, error) {
	return parsePackName(packageName, parent, VTOOL_PREFIX)
}
