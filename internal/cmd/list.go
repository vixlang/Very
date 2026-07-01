package cmd

import (
	"fmt"
	"sort"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"very/internal/api"
)

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "列出所有已安装的包",
	Run: func(cmd *cobra.Command, args []string) {
		tree, _ := cmd.Flags().GetBool("tree")

		packages, err := api.ListPackages()
		if err != nil {
			logInfo("当前没有安装任何包")
			return
		}

		if len(packages) == 0 {
			logInfo("当前没有安装任何包")
			return
		}

		if tree {
			printTree(packages)
		} else {
			printTable(packages)
		}
	},
}

func printTable(packages []*api.PackageInfo) {
	fmt.Println()
	cyan := color.New(color.FgCyan, color.Bold)
	cyan.Println("已安装的 Vix 包")
	fmt.Println(strings.Repeat("─", 60))

	avail := 0
	for _, p := range packages {
		status := "[不可用]"
		statusColor := color.RedString
		if p.HasVIndex {
			status = "[可用]"
			statusColor = color.GreenString
			avail++
		}

		name := p.FullName
		if !p.HasVIndex {
			name = color.RedString(name)
		}

		fmt.Printf("  %s  %s\n", statusColor(status), name)
	}
	fmt.Println(strings.Repeat("─", 60))
	logDim(fmt.Sprintf("共 %d 个包, %d 个可用, %d 个不可用", len(packages), avail, len(packages)-avail))
}

func printTree(packages []*api.PackageInfo) {
	hosts := make(map[string]map[string][]*api.PackageInfo)
	for _, p := range packages {
		if hosts[p.Host] == nil {
			hosts[p.Host] = make(map[string][]*api.PackageInfo)
		}
		hosts[p.Host][p.User] = append(hosts[p.Host][p.User], p)
	}

	cyan := color.New(color.FgCyan, color.Bold)
	cyan.Println("包列表")

	var hostNames []string
	for h := range hosts {
		hostNames = append(hostNames, h)
	}
	sort.Strings(hostNames)

	for _, host := range hostNames {
		fmt.Printf("  %s\n", color.CyanString(host))
		var userNames []string
		for u := range hosts[host] {
			userNames = append(userNames, u)
		}
		sort.Strings(userNames)
		for _, user := range userNames {
			fmt.Printf("    %s\n", color.GreenString(user))
			sort.Slice(hosts[host][user], func(i, j int) bool {
				return hosts[host][user][i].Repo < hosts[host][user][j].Repo
			})
			for _, p := range hosts[host][user] {
				if p.HasVIndex {
					fmt.Printf("      %s\n", p.Repo)
				} else {
					fmt.Printf("      %s %s\n", color.RedString(p.Repo), color.RedString("(不可用)"))
				}
			}
		}
	}
}

func init() {
	listCmd.Flags().BoolP("tree", "t", false, "以树形结构显示包列表")
	RootCmd.AddCommand(listCmd)
}
