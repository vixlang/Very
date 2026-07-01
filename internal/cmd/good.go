package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var goodCmd = &cobra.Command{
	Use:   "good [文件...]",
	Short: "检查 Vix 语法和类型",
	Run: func(cmd *cobra.Command, args []string) {
		report, err := api.CheckFiles(args, getRootDir())
		if err != nil {
			switch e := err.(type) {
			case *api.NotFound:
				logError(fmt.Sprintf("文件不存在: %s", e.Name))
			default:
				logError(fmt.Sprintf("检查失败: %v", err))
			}
			os.Exit(1)
			return
		}

		if report.Passed {
			logOk("全部通过")
		} else {
			for _, errMsg := range report.Errors {
				logError(errMsg)
			}
		}

		if !report.Passed {
			os.Exit(1)
		}
	},
}



func init() {
	RootCmd.AddCommand(goodCmd)
}
