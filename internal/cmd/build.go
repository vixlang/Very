package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var buildCmd = &cobra.Command{
	Use:   "build [vixc 选项...]",
	Short: "编译 Vix 项目",
	Run: func(cmd *cobra.Command, args []string) {
		path, err := api.BuildProject(getRootDir(), args)
		if err != nil {
			logError(fmt.Sprintf("编译失败: %v", err))
			return
		}
		logOk(fmt.Sprintf("编译成功: %s", path))
	},
}

func getRootDir() string {
	return "."
}

func init() {
	RootCmd.AddCommand(buildCmd)
}
