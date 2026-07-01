package api

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"sort"
	"strings"
	"time"
)

const CACHE_EXPIRY = 3600

type SearchPackage struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Stars       int    `json:"stars"`
	Language    string `json:"language"`
	Updated     string `json:"updated"`
	URL         string `json:"url"`
}

type cacheData struct {
	Timestamp float64          `json:"timestamp"`
	Packages  []*SearchPackage `json:"packages"`
}

func ReadCache(cacheFile string, expiry int) []*SearchPackage {
	data, err := os.ReadFile(cacheFile)
	if err != nil {
		return nil
	}
	var cd cacheData
	if err := json.Unmarshal(data, &cd); err != nil {
		return nil
	}
	if time.Now().Unix()-int64(cd.Timestamp) > int64(expiry) {
		return nil
	}
	return cd.Packages
}

func SaveCache(cacheDir, cacheFile string, packages []*SearchPackage) {
	os.MkdirAll(cacheDir, 0755)
	cd := cacheData{
		Timestamp: float64(time.Now().Unix()),
		Packages:  packages,
	}
	data, err := json.MarshalIndent(cd, "", "  ")
	if err != nil {
		return
	}
	os.WriteFile(cacheFile, data, 0644)
}

func ClearCache(cacheFile string) {
	os.Remove(cacheFile)
}

type githubRepo struct {
	Name            string `json:"name"`
	Description     string `json:"description"`
	StargazersCount int    `json:"stargazers_count"`
	Language        string `json:"language"`
	UpdatedAt       string `json:"updated_at"`
	HTMLURL         string `json:"html_url"`
}

func FetchGitHubPackages(prefix string, includeExtra string) ([]*SearchPackage, error) {
	var packages []*SearchPackage
	page := 1
	perPage := 100

	tr := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{
		Transport: tr,
		Timeout:   10 * time.Second,
	}

	for {
		url := fmt.Sprintf("https://api.github.com/orgs/%s/repos?per_page=%d&page=%d&type=sources",
			DEFAULT_ORG, perPage, page)
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			return nil, &Network{URL: url, Detail: err.Error()}
		}
		req.Header.Set("Accept", "application/vnd.github.v3+json")
		req.Header.Set("User-Agent", "Very-Project-Manager")

		resp, err := client.Do(req)
		if err != nil {
			return nil, &Network{URL: url, Detail: err.Error()}
		}
		defer resp.Body.Close()

		if resp.StatusCode != 200 {
			body, _ := io.ReadAll(resp.Body)
			return nil, &Network{URL: url, Status: resp.StatusCode, Detail: string(body)}
		}

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, &Network{URL: url, Detail: err.Error()}
		}

		var repos []githubRepo
		if err := json.Unmarshal(body, &repos); err != nil {
			return nil, &Network{URL: url, Detail: err.Error()}
		}

		if len(repos) == 0 {
			break
		}

		for _, repo := range repos {
			if strings.HasPrefix(repo.Name, prefix) || (includeExtra != "" && repo.Name == includeExtra) {
				desc := repo.Description
				if desc == "" {
					desc = "无描述"
				}
				lang := repo.Language
				if lang == "" {
					lang = "Unknown"
				}
				updated := repo.UpdatedAt
				if len(updated) >= 10 {
					updated = updated[:10]
				}
				packages = append(packages, &SearchPackage{
					Name:        repo.Name,
					Description: desc,
					Stars:       repo.StargazersCount,
					Language:    lang,
					Updated:     updated,
					URL:         repo.HTMLURL,
				})
			}
		}

		if len(repos) < perPage {
			break
		}
		page++
	}

	sort.Slice(packages, func(i, j int) bool {
		return packages[i].Stars > packages[j].Stars
	})

	return packages, nil
}

func FetchWithRetry(fetchFn func() ([]*SearchPackage, error), maxRetries int) ([]*SearchPackage, error) {
	var lastErr error
	for attempt := 1; attempt <= maxRetries; attempt++ {
		if attempt > 1 {
			time.Sleep(2 * time.Second)
		}
		result, err := fetchFn()
		if err == nil {
			return result, nil
		}
		lastErr = err
		if netErr, ok := err.(*Network); ok {
			if netErr.Status >= 500 || netErr.Status == 403 {
				if attempt < maxRetries {
					time.Sleep(time.Duration(2*(1<<(attempt-1))) * time.Second)
					continue
				}
				if netErr.Status == 403 {
					return nil, fmt.Errorf("GitHub API 速率限制已用完，请稍后再试")
				}
				return nil, fmt.Errorf("GitHub API 服务器错误 (%d)", netErr.Status)
			}
			if netErr.Status == 404 {
				return nil, fmt.Errorf("GitHub API 端点不存在")
			}
		}
		if attempt >= maxRetries {
			return nil, fmt.Errorf("经过 %d 次重试后仍然失败: %v", maxRetries, lastErr)
		}
	}
	return nil, lastErr
}

func SortPackages(packages []*SearchPackage, sortBy string) []*SearchPackage {
	sorted := make([]*SearchPackage, len(packages))
	copy(sorted, packages)

	switch sortBy {
	case "stars":
		sort.Slice(sorted, func(i, j int) bool {
			return sorted[i].Stars > sorted[j].Stars
		})
	case "updated":
		sort.Slice(sorted, func(i, j int) bool {
			return sorted[i].Updated > sorted[j].Updated
		})
	case "name":
		sort.Slice(sorted, func(i, j int) bool {
			return strings.ToLower(sorted[i].Name) < strings.ToLower(sorted[j].Name)
		})
	default:
		sort.Slice(sorted, func(i, j int) bool {
			return sorted[i].Stars > sorted[j].Stars
		})
	}
	return sorted
}

func FilterPackages(packages []*SearchPackage, keyword string) []*SearchPackage {
	kw := strings.ToLower(keyword)
	var filtered []*SearchPackage
	for _, p := range packages {
		if strings.Contains(strings.ToLower(p.Name), kw) || strings.Contains(strings.ToLower(p.Description), kw) {
			filtered = append(filtered, p)
		}
	}
	return filtered
}
