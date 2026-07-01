package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var exeCmd = &cobra.Command{
	Use:   "exe <tool> [args...]",
	Short: "执行已编译的 Vix 工具",
	Args:  cobra.MinimumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		tool := args[0]
		extra := args[1:]

		suffix := ""
		if runtime.GOOS == "windows" {
			suffix = ".exe"
		}
		binaryPath := filepath.Join(api.Config{}.VIX_TOOLS_PATH(), tool+suffix)

		if _, err := os.Stat(binaryPath); os.IsNotExist(err) {
			logInfo(fmt.Sprintf("工具 %s 未安装，正在自动安装...", tool))
			info, err := api.InstallTool(tool)
			if err != nil {
				logError(fmt.Sprintf("安装工具失败: %v", err))
				os.Exit(1)
				return
			}
			binaryPath = info.BinaryPath
			logOk(fmt.Sprintf("工具 %s 已安装", info.FullName))
		}

		if _, err := os.Stat(binaryPath); os.IsNotExist(err) {
			logError(fmt.Sprintf("找不到可执行文件: %s", tool))
			os.Exit(1)
			return
		}

		p := exec.Command(binaryPath, extra...)
		p.Stdout = os.Stdout
		p.Stderr = os.Stderr
		p.Stdin = os.Stdin

		if err := p.Run(); err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				code := exitErr.ExitCode()
				if code != 0 {
					logWarn(fmt.Sprintf("工具以退出码 %d 退出", code))
				}
				os.Exit(code)
				return
			}
			logError(fmt.Sprintf("执行失败: %v", err))
			os.Exit(1)
			return
		}

		code := p.ProcessState.ExitCode()
		if code != 0 {
			logWarn(fmt.Sprintf("工具以退出码 %d 退出", code))
		}
		os.Exit(code)
	},
}

func init() {
	RootCmd.AddCommand(exeCmd)
}
