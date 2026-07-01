package cmd

import (
	"fmt"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
)

var version string

var RootCmd = &cobra.Command{
	Use:   "very",
	Short: "Vix 项目管理与构建工具",
	Run: func(cmd *cobra.Command, args []string) {
		cmd.Help()
	},
}

func Execute(ver string) error {
	version = ver
	return RootCmd.Execute()
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "显示版本号",
	Run: func(cmd *cobra.Command, args []string) {
		cyan := color.New(color.FgCyan, color.Bold)
		green := color.New(color.FgGreen, color.Bold)
		yellow := color.New(color.FgYellow)
		cyan.Print("Very ")
		green.Printf("v%s", version)
		fmt.Println()
		yellow.Println("Vix 项目管理与构建工具")
	},
}

func init() {
	RootCmd.AddCommand(versionCmd)
}
