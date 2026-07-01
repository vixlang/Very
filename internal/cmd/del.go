package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var delCmd = &cobra.Command{
	Use:   "del <package>",
	Short: "删除包",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		packageName := args[0]

		err := api.DeletePackage(packageName)
		if err != nil {
			switch e := err.(type) {
			case *api.NotFound:
				logError(fmt.Sprintf("包不存在: %s\n  • 包名拼写错误\n  • 该包尚未安装", e.Name))
			case *api.IOError:
				logError(fmt.Sprintf("删除失败: %s", e.Detail))
			default:
				logError(fmt.Sprintf("删除失败: %v", err))
			}
			return
		}
		logOk(fmt.Sprintf("包 %s 已删除", packageName))
	},
}

func init() {
	RootCmd.AddCommand(delCmd)
}
