package api

import (
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
)

type VIndexTool struct {
	Path string
}

func NewVIndexTool(dirPath string) VIndexTool {
	return VIndexTool{Path: filepath.Join(dirPath, "vindex.toml")}
}

func (v VIndexTool) Content() (map[string]any, bool) {
	data, err := os.ReadFile(v.Path)
	if err != nil {
		return nil, false
	}
	var m map[string]any
	if err := toml.Unmarshal(data, &m); err != nil {
		return nil, false
	}
	return m, true
}

func BuildDepTree(libsPath string, rootDeps []string) map[string]bool {
	referenced := make(map[string]bool)
	queue := make([]string, len(rootDeps))
	copy(queue, rootDeps)

	for len(queue) > 0 {
		spec := queue[0]
		queue = queue[1:]
		if referenced[spec] {
			continue
		}
		info, err := ParsePackName(spec, libsPath)
		if err != nil {
			continue
		}
		fullName := info.FullName()
		referenced[fullName] = true

		vindexPath := filepath.Join(info.PackPath(), "vindex.toml")
		data, err := os.ReadFile(vindexPath)
		if err != nil {
			continue
		}
		var m map[string]any
		if err := toml.Unmarshal(data, &m); err != nil {
			continue
		}

		var subDeps []string
		if proj, ok := m["project"].(map[string]any); ok {
			if deps, ok := proj["deps"].([]any); ok {
				for _, d := range deps {
					if s, ok := d.(string); ok {
						subDeps = append(subDeps, s)
					}
				}
			}
		}
		if deps, ok := m["dependencies"].(map[string]any); ok {
			for d := range deps {
				subDeps = append(subDeps, d)
			}
		}
		seen := make(map[string]bool)
		for _, d := range subDeps {
			if !seen[d] && !referenced[d] {
				seen[d] = true
				queue = append(queue, d)
			}
		}
	}
	return referenced
}

func AddDepToVindex(packSpec string) (bool, error) {
	vindexPath := filepath.Join(".", "vindex.toml")
	data, err := os.ReadFile(vindexPath)
	if err != nil {
		return false, err
	}
	var m map[string]any
	if err := toml.Unmarshal(data, &m); err != nil {
		return false, err
	}

	var existing []string
	if proj, ok := m["project"].(map[string]any); ok {
		if deps, ok := proj["deps"].([]any); ok {
			for _, d := range deps {
				if s, ok := d.(string); ok {
					existing = append(existing, s)
				}
			}
		}
	}
	if deps, ok := m["dependencies"].(map[string]any); ok {
		for d := range deps {
			existing = append(existing, d)
		}
	}

	deduped := make([]string, 0, len(existing))
	seen := make(map[string]bool)
	for _, d := range existing {
		if !seen[d] {
			seen[d] = true
			deduped = append(deduped, d)
		}
	}

	for _, d := range deduped {
		if d == packSpec {
			return false, nil
		}
	}

	deduped = append(deduped, packSpec)
	if proj, ok := m["project"].(map[string]any); ok {
		proj["deps"] = deduped
	} else {
		m["project"] = map[string]any{"deps": deduped}
	}
	delete(m, "dependencies")

	out, err := os.Create(vindexPath)
	if err != nil {
		return false, err
	}
	defer out.Close()
	if err := toml.NewEncoder(out).Encode(m); err != nil {
		return false, err
	}
	return true, nil
}

func GetTransitiveDeps(packPath string) []string {
	vindexPath := filepath.Join(packPath, "vindex.toml")
	data, err := os.ReadFile(vindexPath)
	if err != nil {
		return nil
	}
	var m map[string]any
	if err := toml.Unmarshal(data, &m); err != nil {
		return nil
	}
	var deps []string
	if proj, ok := m["project"].(map[string]any); ok {
		if d, ok := proj["deps"].([]any); ok {
			for _, v := range d {
				if s, ok := v.(string); ok {
					deps = append(deps, s)
				}
			}
		}
	}
	if d, ok := m["dependencies"].(map[string]any); ok {
		for k := range d {
			deps = append(deps, k)
		}
	}
	deduped := make([]string, 0, len(deps))
	seen := make(map[string]bool)
	for _, d := range deps {
		if !seen[d] {
			seen[d] = true
			deduped = append(deduped, d)
		}
	}
	return deduped
}
