package cmd

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"very/internal/api"
)

var searchCacheDir = filepath.Join(api.Config{}.VIX_HOME(), "cache")
var searchCacheFile = filepath.Join(searchCacheDir, "search_cache.json")

var searchCmd = &cobra.Command{
	Use:   "search [keyword]",
	Short: "搜索可用的包",
	Run: func(cmd *cobra.Command, args []string) {
		keyword := ""
		if len(args) > 0 {
			keyword = args[0]
		}

		noCache, _ := cmd.Flags().GetBool("no-cache")
		clearCache, _ := cmd.Flags().GetBool("clear-cache")
		cacheStatus, _ := cmd.Flags().GetBool("cache-status")
		sortBy, _ := cmd.Flags().GetString("sort")
		limit, _ := cmd.Flags().GetInt("limit")

		if clearCache {
			clearSearchCache()
			return
		}
		if cacheStatus {
			showSearchCacheStatus()
			return
		}

		packages := fetchSearchPackages(noCache)
		if packages == nil {
			return
		}

		if keyword != "" {
			packages = api.FilterPackages(packages, keyword)
		}

		if len(packages) == 0 {
			if keyword != "" {
				logWarn(fmt.Sprintf("未找到包含 '%s' 的包", keyword))
			} else {
				logWarn("未找到任何包")
			}
			return
		}

		packages = api.SortPackages(packages, sortBy)
		if limit > 0 && limit < len(packages) {
			packages = packages[:limit]
		}

		printSearchResults(packages, keyword != "", sortBy)
	},
}

func clearSearchCache() {
	api.ClearCache(searchCacheFile)
	logOk("缓存已清理")
}

func showSearchCacheStatus() {
	cached := api.ReadCache(searchCacheFile, api.CACHE_EXPIRY)
	if cached == nil {
		logInfo("缓存文件不存在")
		logInfo("运行 very search 将自动创建缓存")
		return
	}
	logInfo(fmt.Sprintf("缓存文件: %s", searchCacheFile))
	logInfo(fmt.Sprintf("包数量: %d", len(cached)))
}

func fetchSearchPackages(noCache bool) []*api.SearchPackage {
	if !noCache {
		cached := api.ReadCache(searchCacheFile, api.CACHE_EXPIRY)
		if cached != nil {
			logInfo(fmt.Sprintf("使用缓存数据（%d 个包）", len(cached)))
			return cached
		}
	}

	logInfo("正在从 GitHub 获取包列表...")
	packages, err := api.FetchWithRetry(func() ([]*api.SearchPackage, error) {
		return api.FetchGitHubPackages(api.VLIB_PREFIX, "ver")
	}, 3)
	if err != nil {
		logError(fmt.Sprintf("搜索失败: %v", err))
		return nil
	}
	api.SaveCache(searchCacheDir, searchCacheFile, packages)
	return packages
}

func printSearchResults(packages []*api.SearchPackage, hasKeyword bool, sortBy string) {
	fmt.Println()
	green := color.New(color.FgGreen)
	white := color.New(color.FgWhite)
	yellow := color.New(color.FgYellow)
	magenta := color.New(color.FgMagenta)
	dim := color.New(color.Faint)

	fmt.Printf("%-25s %-50s %6s %-12s %s\n", "包名", "描述", "星标", "语言", "更新时间")
	fmt.Println(strings.Repeat("─", 100))

	for _, p := range packages {
		shortName := strings.TrimPrefix(p.Name, api.VLIB_PREFIX)
		desc := p.Description
		if len(desc) > 47 {
			desc = desc[:47] + "..."
		}

		green.Print(shortName)
		fmt.Print(strings.Repeat(" ", 25-len(shortName)))
		white.Print(desc)
		fmt.Print(strings.Repeat(" ", 50-len(desc)))
		yellow.Printf("%6d ", p.Stars)
		magenta.Printf("%-12s ", p.Language)
		dim.Println(p.Updated)
	}
	fmt.Println()

	sortLabels := map[string]string{"stars": "星标数", "updated": "更新时间", "name": "名称"}
	label := sortLabels[sortBy]
	if label == "" {
		label = "星标数"
	}
	logOk(fmt.Sprintf("共找到 %d 个包（按%s排序）", len(packages), label))
}



func init() {
	searchCmd.Flags().Bool("no-cache", false, "不使用缓存，强制从 GitHub 获取最新数据")
	searchCmd.Flags().Bool("clear-cache", false, "清理本地缓存文件")
	searchCmd.Flags().Bool("cache-status", false, "查看缓存状态信息")
	searchCmd.Flags().String("sort", "stars", "排序方式：stars(星标数), updated(更新时间), name(名称)")
	searchCmd.Flags().Int("limit", 0, "限制显示的包数量")
	RootCmd.AddCommand(searchCmd)
}
