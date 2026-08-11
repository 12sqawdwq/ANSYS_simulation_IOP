# Baseline

无偏心基线资料。仓库级实验参考统一为 **1.25 mm 眼睑厚度**，定义见 [`../config/model_baseline.json`](../config/model_baseline.json) 和 [`../docs/GLOBAL_BASELINE.md`](../docs/GLOBAL_BASELINE.md)。`figures/` 保存当前可同步的零偏心结果；`workbench/tonometer_baseline/` 是本地 Workbench 副本，不进入 Git。

新建普通基线工况必须使用 1.25 mm；若既有 Workbench 或图件来自其他厚度，必须保留并标注原始输入，不得因全局默认值更新而重命名为 1.25 mm 结果。基线 Workbench 来源为根目录中较新的 `tonometer_baseline` 副本。大体积求解文件和缓存必须保留在 5090d 外部数据区或本地，不得加入版本库。
