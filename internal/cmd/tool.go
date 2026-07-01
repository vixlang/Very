package cmd

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"very/internal/api"
)

var toolCmd = &cobra.Command{
	Use:   "tool",
	Short: "工具管理",
}

var toolAddCmd = &cobra.Command{
	Use:   "add <package>",
	Short: "安装 Vix 工具",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		packageName := args[0]
		logInfo(fmt.Sprintf("安装工具: %s", packageName))
		info, err := api.InstallTool(packageName)
		if err != nil {
			logError(fmt.Sprintf("安装失败: %v", err))
			return
		}
		logOk(fmt.Sprintf("工具已安装: %s", info.BinaryPath))
	},
}

var toolDelCmd = &cobra.Command{
	Use:   "del <package>",
	Short: "删除 Vix 工具",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		packageName := args[0]
		err := api.DeleteTool(packageName)
		if err != nil {
			logError(fmt.Sprintf("删除失败: %v", err))
			return
		}
		logOk("工具已删除")
	},
}

var toolListCmd = &cobra.Command{
	Use:   "list",
	Short: "列出已安装的工具",
	Run: func(cmd *cobra.Command, args []string) {
		tree, _ := cmd.Flags().GetBool("tree")
		names, err := api.ListTools()
		if err != nil {
			logError(fmt.Sprintf("列出工具失败: %v", err))
			return
		}
		if len(names) == 0 {
			logInfo("没有已安装的工具")
			return
		}
		if tree {
			for _, name := range names {
				fmt.Println(name)
			}
		} else {
			for _, name := range names {
				fmt.Printf("  %s\n", name)
			}
			logDim(fmt.Sprintf("共 %d 个工具", len(names)))
		}
	},
}

var toolUpdateCmd = &cobra.Command{
	Use:   "update [package]",
	Short: "更新 Vix 工具",
	Long:  "更新 Vix 工具。不指定工具名则更新所有已安装的工具。",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) > 0 {
			updateToolOne(args[0])
			return
		}
		names, err := api.ListTools()
		if err != nil {
			logError(fmt.Sprintf("列出工具失败: %v", err))
			return
		}
		if len(names) == 0 {
			logInfo("没有已安装的工具")
			return
		}
		for _, name := range names {
			updateToolOne(name)
		}
	},
}

func updateToolOne(packname string) {
	info, err := api.UpdateTool(packname)
	if err != nil {
		logError(fmt.Sprintf("更新失败: %v", err))
		return
	}
	logOk(fmt.Sprintf("工具已更新: %s", info.BinaryPath))
}

var toolSearchCmd = &cobra.Command{
	Use:   "search [keyword]",
	Short: "搜索可用的 Vix 工具",
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
			api.ClearCache(toolSearchCacheFile)
			logOk("缓存已清理")
			return
		}
		if cacheStatus {
			cached := api.ReadCache(toolSearchCacheFile, api.CACHE_EXPIRY)
			if cached == nil {
				logInfo("缓存文件不存在\n运行 very tool search 将自动创建缓存")
				return
			}
			logInfo(fmt.Sprintf("缓存文件: %s", toolSearchCacheFile))
			logInfo(fmt.Sprintf("工具数量: %d", len(cached)))
			return
		}

		logInfo(fmt.Sprintf("搜索工具: %s", keyword))
		packages := fetchToolSearchPackages(noCache)
		if packages == nil {
			return
		}

		if keyword != "" {
			packages = api.FilterPackages(packages, keyword)
		}

		if len(packages) == 0 {
			if keyword != "" {
				logWarn(fmt.Sprintf("未找到包含 '%s' 的工具", keyword))
			} else {
				logWarn("未找到任何工具")
			}
			return
		}

		packages = api.SortPackages(packages, sortBy)
		if limit > 0 && limit < len(packages) {
			packages = packages[:limit]
		}

		printToolSearchResults(packages, keyword != "", sortBy)
	},
}

var toolSearchCacheDir = filepath.Join(api.Config{}.VIX_TOOLS_PATH(), "cache")
var toolSearchCacheFile = filepath.Join(toolSearchCacheDir, "tool_search_cache.json")
var _ = toolSearchCacheDir

func fetchToolSearchPackages(noCache bool) []*api.SearchPackage {
	if !noCache {
		cached := api.ReadCache(toolSearchCacheFile, api.CACHE_EXPIRY)
		if cached != nil {
			logInfo(fmt.Sprintf("使用缓存数据（%d 个工具）", len(cached)))
			return cached
		}
	}

	logInfo("正在从 GitHub 获取工具列表...")
	packages, err := api.FetchWithRetry(func() ([]*api.SearchPackage, error) {
		return api.FetchGitHubPackages(api.VTOOL_PREFIX, "")
	}, 3)
	if err != nil {
		logError(fmt.Sprintf("搜索失败: %v", err))
		return nil
	}
	api.SaveCache(toolSearchCacheDir, toolSearchCacheFile, packages)
	return packages
}

func printToolSearchResults(packages []*api.SearchPackage, hasKeyword bool, sortBy string) {
	fmt.Println()
	green := color.New(color.FgGreen)
	white := color.New(color.FgWhite)
	yellow := color.New(color.FgYellow)
	magenta := color.New(color.FgMagenta)
	dim := color.New(color.Faint)

	fmt.Printf("%-25s %-50s %6s %-12s %s\n", "工具名", "描述", "星标", "语言", "更新时间")
	fmt.Println(strings.Repeat("─", 100))

	for _, p := range packages {
		shortName := strings.TrimPrefix(p.Name, api.VTOOL_PREFIX)
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
	logOk(fmt.Sprintf("共找到 %d 个工具（按%s排序）", len(packages), label))
}

var toolPruneCmd = &cobra.Command{
	Use:   "prune",
	Short: "清理无效工具、空目录和孤立二进制文件",
	Run: func(cmd *cobra.Command, args []string) {
		emptyOnly, _ := cmd.Flags().GetBool("empty-only")
		invalidOnly, _ := cmd.Flags().GetBool("invalid-only")

		report, err := api.PruneTools(emptyOnly, invalidOnly)
		if err != nil {
			logError(fmt.Sprintf("清理失败: %v", err))
			return
		}

		total := len(report.RemovedInvalid) + len(report.RemovedEmpty) + len(report.RemovedOrphaned)
		if emptyOnly {
			fmt.Printf("清理的空目录数: %d\n", len(report.RemovedEmpty))
		} else if invalidOnly {
			fmt.Printf("删除的无效工具数: %d\n", len(report.RemovedInvalid))
		} else {
			if len(report.RemovedInvalid) > 0 {
				fmt.Printf("删除的无效工具数: %d\n", len(report.RemovedInvalid))
			}
			if len(report.RemovedEmpty) > 0 {
				fmt.Printf("清理的空目录数: %d\n", len(report.RemovedEmpty))
			}
			if len(report.RemovedOrphaned) > 0 {
				fmt.Printf("删除的孤立二进制文件数: %d\n", len(report.RemovedOrphaned))
			}
		}
		fmt.Printf("合计: %d\n", total)
	},
}

func init() {
	toolAddCmd.Flags()
	toolDelCmd.Flags()
	toolListCmd.Flags().BoolP("tree", "t", false, "以树形结构显示工具列表")
	toolUpdateCmd.Flags()
	toolSearchCmd.Flags().Bool("no-cache", false, "不使用缓存")
	toolSearchCmd.Flags().Bool("clear-cache", false, "清理缓存")
	toolSearchCmd.Flags().Bool("cache-status", false, "查看缓存状态")
	toolSearchCmd.Flags().String("sort", "stars", "排序方式：stars(星标数), updated(更新时间), name(名称)")
	toolSearchCmd.Flags().Int("limit", 0, "限制显示的工具数量")
	toolPruneCmd.Flags().Bool("empty-only", false, "只删除空目录")
	toolPruneCmd.Flags().Bool("invalid-only", false, "只删除没有 vindex.toml 的工具")

	toolCmd.AddCommand(toolAddCmd)
	toolCmd.AddCommand(toolDelCmd)
	toolCmd.AddCommand(toolListCmd)
	toolCmd.AddCommand(toolUpdateCmd)
	toolCmd.AddCommand(toolSearchCmd)
	toolCmd.AddCommand(toolPruneCmd)
	RootCmd.AddCommand(toolCmd)
}
