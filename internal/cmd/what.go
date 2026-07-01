package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"very/internal/api"
)

var whatCmd = &cobra.Command{
	Use:   "what <package>",
	Short: "查看已安装包的 README",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		packageName := args[0]

		content, err := api.ReadPackageReadme(packageName)
		if err != nil {
			switch e := err.(type) {
			case *api.NotFound:
				logError(fmt.Sprintf("未找到: %s", e.Name))
			case *api.IOError:
				logError(fmt.Sprintf("读取失败: %s", e.Detail))
			default:
				logError(fmt.Sprintf("读取失败: %v", err))
			}
			return
		}

		fmt.Printf("=== %s ===\n\n%s\n", packageName, content)
	},
}

func init() {
	RootCmd.AddCommand(whatCmd)
}
