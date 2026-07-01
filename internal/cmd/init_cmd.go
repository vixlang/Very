package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var initCmd = &cobra.Command{
	Use:   "init <name>",
	Short: "初始化一个新的 Vix 项目",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		name := args[0]
		dir, _ := cmd.Flags().GetString("dir")

		path, err := api.ScaffoldProject(name, dir)
		if err != nil {
			switch e := err.(type) {
			case *api.Validation:
				logError(e.Reason)
			case *api.IOError:
				logError(fmt.Sprintf("创建项目失败: %s", e.Detail))
			default:
				logError(fmt.Sprintf("创建项目失败: %v", err))
			}
			return
		}
		logOk(fmt.Sprintf("成功创建项目 '%s' 于 %s", name, path))
	},
}

func init() {
	initCmd.Flags().StringP("dir", "d", "", "初始化目录（默认使用项目名称）")
	RootCmd.AddCommand(initCmd)
}
