package main

import "very/internal/cmd"

var version = "0.38.1"

func main() {
	cmd.Execute(version)
}
