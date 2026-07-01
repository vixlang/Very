package api

import "fmt"

type Error interface {
	error
	IsError()
}

type NotFound struct {
	Kind string
	Name string
}
func (e *NotFound) Error() string   { return fmt.Sprintf("未找到 %s: %s", e.Kind, e.Name) }
func (e *NotFound) IsError()        {}

type Validation struct {
	Reason string
}
func (e *Validation) Error() string  { return e.Reason }
func (e *Validation) IsError()       {}

type IOError struct {
	Path   string
	Detail string
}
func (e *IOError) Error() string     { return fmt.Sprintf("IO 错误 %s: %s", e.Path, e.Detail) }
func (e *IOError) IsError()          {}

type GitClone struct {
	URL    string
	Detail string
}
func (e *GitClone) Error() string    { return fmt.Sprintf("克隆失败 %s: %s", e.URL, e.Detail) }
func (e *GitClone) IsError()         {}

type GitPull struct {
	Path   string
	Detail string
}
func (e *GitPull) Error() string     { return fmt.Sprintf("拉取失败 %s: %s", e.Path, e.Detail) }
func (e *GitPull) IsError()          {}

type Compile struct {
	ExitCode int
	Output   string
}
func (e *Compile) Error() string     { return fmt.Sprintf("编译失败 (退出码 %d)", e.ExitCode) }
func (e *Compile) IsError()          {}

type Network struct {
	URL    string
	Status int
	Detail string
}
func (e *Network) Error() string     { return fmt.Sprintf("网络错误 %s: %s", e.URL, e.Detail) }
func (e *Network) IsError()          {}
