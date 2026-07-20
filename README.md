# Blueknow 眼压计仿真

本仓库统一管理经眼睑眼压测量的可复现模型、运行代码、分析文档和轻量结果。原始 ANSYS 求解文件保存在 5090d 外部数据区，不进入 Git 历史。

## 当前核心结论

- 厚度相关数值当前为占位参数扫描：眼睑厚度从 0.80 mm 增加到 2.00 mm 时，`Ae/Ac` 从 1.46 增加到 5.68。真实仿体实验完成后将以受控内压、力/位移和双相机内外面积数据重新计算结论。
- 偏心量在 0-1 mm 时半经验面积比变化较小；2 mm 时内部有效面积和三维接触范围明显下降。3D 模型的接触单元代理从 351 降至 180，眼睑峰值应力从 27.15 kPa 增至 37.83 kPa。
- `Ac/Ae` 表示面积传递效率，`Ae/Ac` 表示厚度或偏心修正倍率。两者不得混写。

## 目录

- `baseline/`：无偏心基线图表、说明与本地 Workbench 工程入口。
- `offset/`：偏心研究的报告、轻量数据、图表、历史脚本与本地 Workbench 工程入口。
- `thick/`：厚度项目的实验协议、占位结果、真实实验数据契约、处理脚本与报告。
- `models/apdl/`：参数化 APDL 模型、后处理宏和测试输入。
- `src/runners/`：当前可复现的批量运行入口。
- `src/legacy/`：历史 Workbench/CAD 修复与偏心方案，仅作追溯。
- `scripts/reporting/`：共享报告工具。
- `docs/analysis/`：共享分析说明；项目报告分别位于 `offset/docs/` 与 `thick/docs/`。
- `docs/DATA_PROVENANCE.md`：模型层级、参数差异和结论适用范围。
- `results/summary/`：机器可读汇总和外部结果校验清单。
- `ops/`：本地、5090d 和 arch 的仓库初始化与同步脚本。

## 三端角色

- 本地：完整开发副本。
- 5090d：中心 bare 仓库、完整工作副本和外部求解数据区。
- arch：`blob:none` 部分克隆，只检出文档、汇总、图和报告脚本。

详细同步命令见 [docs/SYNC_GUIDE.md](docs/SYNC_GUIDE.md)。数据解释和限制见 [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md)。
