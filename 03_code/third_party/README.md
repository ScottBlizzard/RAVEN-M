# Third-party repositories

本目录用于本地克隆官方代码，但父仓库不直接追踪这些嵌套 Git 仓库。

执行：

```powershell
powershell -ExecutionPolicy Bypass -File ..\..\scripts\clone_repositories.ps1
```

克隆结果和 HEAD commit 写入：

`03_code/manifests/repositories.lock.csv`

不要在第三方仓库内直接实现 RAVEN-M；自己的代码统一放在 `05_project/`。

