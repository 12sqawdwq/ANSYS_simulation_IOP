# Git远程与GitHub同步约定

## 远程拓扑

本项目保留两级远程：

1. `origin`：5090d服务器上的内部裸仓库，作为服务器求解工作区的低延迟提交目标；
2. `github`：`git@github.com:12sqawdwq/ANSYS_simulation_IOP.git`，作为对外主同步仓库。

本地工作区通过Tailscale SSH别名访问内部仓库：

```text
origin = 5090d:/home/xuanyu/PROJECT/ziyu/git/blueknow-simulation.git
github = git@github.com:12sqawdwq/ANSYS_simulation_IOP.git
```

5090d服务器工作区配置为：

```text
origin = /home/xuanyu/PROJECT/ziyu/git/blueknow-simulation.git
github = git@github-ansys-iop:12sqawdwq/ANSYS_simulation_IOP.git
```

## 标准发布流程

服务器完成任务后：

```bash
git add <明确文件>
git commit -m "..."
git push origin main
```

随后在具有GitHub授权的本地工作区执行：

```bash
ops/sync-main-to-github.sh
```

该脚本只读取并推送 `origin/main`，不会切换分支、覆盖工作区或提交未跟踪文件。完成后会核对内部仓库和GitHub的提交SHA。

每次正式任务结束时必须同时报告：

- 内部 `origin/main` SHA；
- GitHub `main` SHA；
- 两者是否一致。

## 5090d直接推送GitHub

服务器已创建专用SSH密钥：

```text
~/.ssh/github_ansys_simulation_iop_ed25519
```

并通过SSH别名 `github-ansys-iop` 绑定到 `github` 远程。将对应公钥添加到GitHub仓库的 **Settings → Deploy keys**，并启用写权限后，服务器可直接执行：

```bash
git push github main
```

在部署密钥尚未授权前，服务器继续推送内部 `origin`，再由本地同步脚本发布到GitHub，避免中断正在运行的求解任务。

## 安全约束

- 不复制本地GitHub私钥到服务器；
- 不提交 `.ssh`、令牌或私钥；
- 大型RST、DB和视频继续保存在 `blueknow-data`，不进入GitHub；
- 同步脚本只发布已提交的Git对象，不处理未提交工作区文件。
