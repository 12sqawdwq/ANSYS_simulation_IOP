# Offset Study

本目录是偏心测量研究的唯一归档位置。新的偏心实验统一采用 **1.25 mm 眼睑厚度**全局基线；runner 默认值和基线规则见 [`../config/model_baseline.json`](../config/model_baseline.json) 与 [`../docs/GLOBAL_BASELINE.md`](../docs/GLOBAL_BASELINE.md)。

既有提交 `bc861060...` 的参数化 3D coarse 扫描实际使用 1.00 mm，继续作为历史证据保留，不得追溯改标为 1.25 mm；新旧偏心结果比较前必须核对实际厚度。

- `docs/`：偏心参数扫描和参数化 3D 结果说明。
- `data/`：轻量汇总 CSV。
- `figures/`：偏心与零偏心对比视图。
- `workbench/`：本地 1 mm 偏心工程，Git 忽略。

其中的半经验面积和 3D 接触单元代理属于不同证据层级，不能直接互换为绝对面积。
