package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var addCmd = &cobra.Command{
	Use:   "add <package>",
	Short: "添加包",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		packageName := args[0]
		global, _ := cmd.Flags().GetBool("global")
		local, _ := cmd.Flags().GetBool("local")

		if !global {
			vindexPath := filepath.Join(".", "vindex.toml")
			if _, err := os.Stat(vindexPath); os.IsNotExist(err) {
				logError("未找到 vindex.toml\n请在项目根目录下运行此命令")
				return
			}
		}

		info, err := api.ParsePackName(packageName, api.Config{}.LocalLibsPath())
		if err != nil {
			logError(fmt.Sprintf("解析包名失败: %v", err))
			return
		}
		dest := info.PackPath()
		if _, err := os.Stat(dest); err == nil {
			logWarn(fmt.Sprintf("包已存在: %s", info.FullName()))
			logWarn("已取消操作")
			return
		}

		logInfo(fmt.Sprintf("正在安装 %s", packageName))
		packInfo, err := api.InstallPackage(packageName, local)
		if err != nil {
			logError(fmt.Sprintf("安装失败: %v", err))
			return
		}

		if !global {
			added, _ := api.AddDepToVindex(packageName)
			if added {
				logOk(fmt.Sprintf("已添加 %s 到 deps", packageName))
			}
		}
		logOk(fmt.Sprintf("包 %s 添加成功", packInfo.FullName))
	},
}

func init() {
	addCmd.Flags().BoolP("global", "g", false, "全局安装到 VIX_HOME 目录")
	addCmd.Flags().BoolP("local", "l", false, "强制在项目 .vix 目录下载（即使全局已存在）")
	RootCmd.AddCommand(addCmd)
}
