package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var stdCmd = &cobra.Command{
	Use:   "std",
	Short: "标准库管理",
	Run: func(cmd *cobra.Command, args []string) {
		doSync()
	},
}

var stdSyncCmd = &cobra.Command{
	Use:   "sync",
	Short: "同步标准库 vstd",
	Run: func(cmd *cobra.Command, args []string) {
		doSync()
	},
}

func doSync() {
	logInfo("正在同步标准库 vstd ...")
	path, err := api.SyncStd()
	if err != nil {
		switch e := err.(type) {
		case *api.GitClone:
			logError(fmt.Sprintf("克隆失败: %s", e.Detail))
		case *api.GitPull:
			logError(fmt.Sprintf("拉取失败: %s", e.Detail))
		default:
			logError(fmt.Sprintf("同步失败: %v", err))
		}
		return
	}
	logOk(fmt.Sprintf("标准库已同步到 %s", path))
}

func init() {
	stdCmd.AddCommand(stdSyncCmd)
	RootCmd.AddCommand(stdCmd)
}
