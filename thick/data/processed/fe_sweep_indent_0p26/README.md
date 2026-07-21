# 0.26 mm 推进厚度状态数据

本目录保存从已收敛的 `0.80 mm` 推进厚度扫描加载路径中提取的 `0.26 mm` 状态。原 `0.80 mm` 发布数据仍保存在相邻的 `fe_sweep/`，未被覆盖。

| 文件 | 内容 |
|---|---|
| `summary.csv` | 7 个厚度点的工程量、面积和 `Ae/Ac` 指标 |
| `manifest.csv` | 每个状态的来源算例、结果时间、位移、QC 字段和 Git 来源 |
| `metadata.json` | 原始结果目录、状态提取方法、MAPDL 与宏文件信息 |
| `qc.json` | 完整性、位移、视图、接触和面积判据检查 |
| `indent_comparison.csv` | `0.26 mm` 与原 `0.80 mm` 推进的七点 `Ae/Ac(2°)` 对照 |
| `trend_analysis.json` | 端点增幅、线性及指数描述参数 |
| `excluded_endpoint_exploration/` | 被排除的独立终点试算清单、异常日志与排除依据，不进入发布趋势 |

5090d 发布结果目录：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_sweep/20260721T051323Z_69b0a01_thickness_indent_0p26_state
```

状态对应载荷步 2 的结果时间 `1.36470588235294`。计算关系为：总目标位移 `0.05+0.26=0.31 mm`，原加载路径总位移 `0.05+0.80=0.85 mm`，因此结果时间为 `1+0.31/0.85`。MAPDL 使用 `SET,,,,,TIME` 在同一已收敛加载路径中读取该状态。

7 个状态全部完成，QC 为 `0 error、5 warning`。warning 来自 `Ac` 对 `1°-3°` 平面角阈值的敏感性，不代表结果缺失或求解不收敛。报告见 [0.26 mm 补充报告](../../../docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)，完整图片见 [视图索引](../../../figures/fe_sweep_indent_0p26/views/README.md)。
