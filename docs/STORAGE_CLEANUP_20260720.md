# 存储清理记录（2026-07-20）

## 状态

- 5090d 上 `indentation_sweep_20260720` 的调度器及 4 组 MPI 求解树已停止；清理后未发现残留 sweep 进程。
- 本地活动数据目录由约 266.17 GiB 缩减至约 1.02 GiB，另保留 1.88 GiB 清理归档；活动目录释放约 265 GiB。
- 5090d 将约 84 GB 的本轮 sweep 和旧求解目录压缩为约 7.5 GB 归档，四个归档均通过 `zstd -t` 和 SHA-256 校验。
- arch 仅保留文档/总结用 sparse checkout，约 20 MB，无求解数据需要清理。

## 本地归档

归档目录：`D:\PROJECT\blueknow\archives\cleanup_20260720`

| 文件 | 大小 | 用途 |
|---|---:|---|
| `19a_solved_complete.wbpz` | 979.05 MiB | 旧 offset 19a 的完整可恢复 Workbench 项目 |
| `offset_evidence_20260720.tar.gz` | 66.41 MiB | 旧 offset 目录中的文档、表格、轻量结果及清理时的追溯材料 |
| `offset_selected_models_20260720.tar.gz` | 850.34 MiB | 07、18a/b/c、19a/b 及材料扫描的代表性模型输入 |
| `workbench_metadata_20260720.tar.gz` | 29.90 MiB | `exp`、`new` 的 Workbench 元数据，不含可再生大体积结果 |
| `duplicate_workbench_logs_20260720.tar.gz` | 0.11 MiB | 被删除重复 Workbench 目录中存在差异的日志和文本 |

每个归档均已成功列出内容；SHA-256 见同目录 `SHA256SUMS`。

## 5090d 归档

归档目录：`/home/xuanyu/PROJECT/ziyu/blueknow-archive/cleanup_20260720`

| 文件 | 归档内容 |
|---|---|
| `indentation_sweep_interrupted_20260720_anchor_results.tar.zst` | 中止扫描的 4 个代表性 `.rst/.db` 锚点及对应日志、驱动和指标 |
| `indentation_sweep_interrupted_20260720_metadata.tar.zst` | 中止扫描的元数据和文本结果，不含大体积求解二进制 |
| `eccentric_anchor_results_20260720.tar.zst` | x=0、0.5、1、2 mm 的旧三维代表性 `.rst/.db` |
| `tonometer_metadata_20260720.tar.zst` | 旧 tonometer 工程元数据和文本记录 |

`SHA256SUMS`、`indentation_sweep_interrupted_20260720_inventory.txt` 和 `tonometer_inventory_20260720.txt` 与归档共同保留。中止扫描只有 21 个完成工况，且后处理定义仍需修订，因此这些结果仅用于追溯和脚本复核，不作为厚度实验或最终眼压修正结论。

## 已删除内容

- 本地旧 `simulation/offset` 全树、`test_remote` 传输副本和两个 `_ProjectScratch`。
- 与 `simulation/new` 内容重复的 `simulation_new/new`。
- `simulation/exp_files` 与 `simulation/new/exp_files` 中两个可再生 `.rst`。
- 当前仓库根目录下未跟踪的 `tonometer_baseline`、`tonometer_sim_results` 及重复图像目录；规范副本仍在 `baseline/`、`offset/` 和 `assets/`。
- 5090d 的本轮 sweep 工作目录、validation 临时目录和旧 `ansys_simunation/tonometer_sim`。

## 保留边界

- Git 管理的模型、APDL/Python 代码、文档、CSV、汇总结果和图片。
- `baseline/workbench/tonometer_baseline` 与 `offset/workbench/tonometer_offset_1mm` 规范工程副本。
- `thick/` 的占位数据、实验设计和后续重算入口。
- 本地完整 19a WBPZ、代表性旧模型，以及 5090d 上的代表性求解锚点。

恢复前先校验归档。`.tar.gz` 使用 `tar -xzf`，`.tar.zst` 使用 `tar --zstd -xf`；恢复到独立临时目录，避免覆盖当前规范仓库。
