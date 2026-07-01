package cmd

import (
	"fmt"
	"math/rand"

	"github.com/fatih/color"
)

var happyOk = []string{"NICE", "GOOD", "GREAT", "WON", "YEAH"}
var happyErr = []string{"FUCK", "SHIT", "OHNO"}

var (
	okColor    = color.New(color.FgGreen, color.Bold)
	infoColor  = color.New(color.FgCyan, color.Bold)
	warnColor  = color.New(color.FgYellow, color.Bold)
	errorColor = color.New(color.FgRed, color.Bold)
	dimColor   = color.New(color.Faint)
	boldWhite  = color.New(color.FgWhite, color.Bold)
)

func logOk(msg string) {
	word := happyOk[rand.Intn(len(happyOk))]
	okColor.Printf("%s!\t", word)
	fmt.Println(msg)
}

func logInfo(msg string) {
	infoColor.Print("INFO\t")
	fmt.Println(msg)
}

func logWarn(msg string) {
	warnColor.Print("WARN!\t")
	fmt.Println(msg)
}

func logError(msg string) {
	word := happyErr[rand.Intn(len(happyErr))]
	errorColor.Printf("%s!\t", word)
	color.Red(msg)
}

func logDim(msg string) {
	dimColor.Println(msg)
}
