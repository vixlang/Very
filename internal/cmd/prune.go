package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var pruneCmd = &cobra.Command{
	Use:   "prune",
	Short: "清理无效包、空目录和孤立包",
	Run: func(cmd *cobra.Command, args []string) {
		emptyOnly, _ := cmd.Flags().GetBool("empty-only")
		invalidOnly, _ := cmd.Flags().GetBool("invalid-only")
		unused, _ := cmd.Flags().GetBool("unused")

		report, err := api.PrunePackages(emptyOnly, invalidOnly, unused)
		if err != nil {
			logError(fmt.Sprintf("清理失败: %v", err))
			return
		}

		printPruneSummary(report, emptyOnly, invalidOnly, unused)
	},
}

func printPruneSummary(report *api.PruneReport, emptyOnly, invalidOnly, unusedOnly bool) {
	total := len(report.RemovedInvalid) + len(report.RemovedEmpty) + len(report.RemovedUnused)

	if emptyOnly {
		fmt.Printf("清理的空目录数: %d\n", len(report.RemovedEmpty))
		for _, d := range report.RemovedEmpty {
			logDim(fmt.Sprintf("  %s", d))
		}
	} else if invalidOnly {
		fmt.Printf("删除的无效包数: %d\n", len(report.RemovedInvalid))
		for _, d := range report.RemovedInvalid {
			logDim(fmt.Sprintf("  %s", d))
		}
	} else if unusedOnly {
		fmt.Printf("删除的孤立包数: %d\n", len(report.RemovedUnused))
		for _, d := range report.RemovedUnused {
			logDim(fmt.Sprintf("  %s", d))
		}
	} else {
		if len(report.RemovedInvalid) > 0 {
			fmt.Printf("删除的无效包数: %d\n", len(report.RemovedInvalid))
			for _, d := range report.RemovedInvalid {
				logDim(fmt.Sprintf("  %s", d))
			}
		}
		if len(report.RemovedEmpty) > 0 {
			fmt.Printf("清理的空目录数: %d\n", len(report.RemovedEmpty))
			for _, d := range report.RemovedEmpty {
				logDim(fmt.Sprintf("  %s", d))
			}
		}
		if len(report.RemovedUnused) > 0 {
			fmt.Printf("删除的孤立包数: %d\n", len(report.RemovedUnused))
			for _, d := range report.RemovedUnused {
				logDim(fmt.Sprintf("  %s", d))
			}
		}
	}

	fmt.Printf("合计: %d\n", total)
}

func init() {
	pruneCmd.Flags().Bool("empty-only", false, "只删除空目录")
	pruneCmd.Flags().Bool("invalid-only", false, "只删除没有 vindex.toml 的包")
	pruneCmd.Flags().Bool("unused", false, "只删除不被引用的孤立包")
	RootCmd.AddCommand(pruneCmd)
}
