package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var runCmd = &cobra.Command{
	Use:   "run [vixc 选项...]",
	Short: "编译并运行 Vix 项目",
	Run: func(cmd *cobra.Command, args []string) {
		keep, _ := cmd.Flags().GetBool("keep")

		code, err := api.BuildAndRun(getRootDir(), args, keep)
		if err != nil {
			logError(fmt.Sprintf("运行失败: %v", err))
			os.Exit(1)
		}
		if code != 0 {
			logWarn(fmt.Sprintf("程序以退出码 %d 退出", code))
		}
		os.Exit(code)
	},
}

func init() {
	runCmd.Flags().BoolP("keep", "k", false, "运行后保留生成的可执行文件")
	RootCmd.AddCommand(runCmd)
}
