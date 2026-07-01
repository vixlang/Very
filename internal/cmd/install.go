package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var installCmd = &cobra.Command{
	Use:   "install",
	Short: "安装 vindex.toml 中声明的所有依赖",
	Run: func(cmd *cobra.Command, args []string) {
		local, _ := cmd.Flags().GetBool("local")

		packages, err := api.InstallDependencies(local)
		if err != nil {
			logError(fmt.Sprintf("安装依赖失败: %v", err))
			return
		}

		for _, p := range packages {
			logOk(fmt.Sprintf("安装完成: %s", p.FullName))
		}

		if len(packages) == 0 {
			logInfo("没有依赖需要安装")
		}
	},
}

func init() {
	installCmd.Flags().BoolP("local", "l", false, "强制在项目 .vix 目录下载（即使全局已存在）")
	RootCmd.AddCommand(installCmd)
}
