package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var updateCmd = &cobra.Command{
	Use:   "update [package]",
	Short: "更新已安装的包",
	Long:  "更新已安装的包。不指定包名则更新所有已安装的包。",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) > 0 {
			updateOne(args[0])
			return
		}

		packages, err := api.ListPackages()
		if err != nil {
			logError(fmt.Sprintf("列出包失败: %v", err))
			return
		}
		if len(packages) == 0 {
			logInfo("没有已安装的包")
			return
		}

		for _, p := range packages {
			updateOne(p.FullName)
		}
	},
}

func updateOne(spec string) {
	logInfo(fmt.Sprintf("正在更新 %s", spec))
	info, err := api.UpdatePackage(spec)
	if err != nil {
		switch e := err.(type) {
		case *api.NotFound:
			logWarn(fmt.Sprintf("包不存在: %s", e.Name))
		default:
			logError(fmt.Sprintf("更新失败: %v", err))
		}
		return
	}
	if info.Updated {
		logOk(fmt.Sprintf("已更新 %s", info.FullName))
	} else {
		logInfo(fmt.Sprintf("%s 已是最新", info.FullName))
	}
}

func init() {
	RootCmd.AddCommand(updateCmd)
}
