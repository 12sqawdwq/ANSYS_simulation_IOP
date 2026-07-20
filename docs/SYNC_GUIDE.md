# 三端 Git 同步说明

中心远端：ssh://xuanyu@113.44.57.56:8025/home/xuanyu/PROJECT/ziyu/git/blueknow-simulation.git

- 本地与 5090d 使用完整克隆。
- arch 使用 blob:none 和 cone sparse-checkout，仅展开 baseline/、offset/、thick/、docs/、results/summary/ 和根目录说明文件；不检出 models/、src/、ops/ 及任何 Workbench 工程。
- 三端统一使用 main，并设置 pull.ff=only。
- rst/db/mechdb、Workbench 缓存、scratch 和压缩结果均不进入 Git。
- 工作树只保留当前实现。代码历史只使用 commit、branch 和 tag，不在流程脚本名中添加版本数字、`final`、`old` 或 `backup` 后缀，也不维护历史代码目录。
- 正式求解必须从干净工作区启动，并在结果清单中保存完整 Git commit。

日常同步：git pull --ff-only，然后 git push origin main。
