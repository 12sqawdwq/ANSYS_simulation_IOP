# 0.26 mm 推进厚度状态数据

本目录保存校准批次 `20260721T070542Z_6a75cde2_calibration_0p26` 从已收敛的 `0.80 mm` 推进加载路径中提取的 `0.26 mm` 状态。当前参数为眼睑材料倍率 `1.00`、角膜材料倍率 `0.75`、IOP `20 mmHg`。原 `0.80 mm` 基准材料发布数据仍保存在相邻的 `fe_sweep/`，未被覆盖。

| 文件 | 内容 |
|---|---|
| `summary.csv` | 9 个厚度点的工程量、原始及平滑 `Ae/Ac` 指标 |
| `manifest.csv` | 每个状态的来源算例、结果时间、位移、QC 字段和 Git 来源 |
| `metadata.json` | 原始结果目录、状态提取方法、MAPDL 与宏文件信息 |
| `qc.json` | 完整性、位移、视图、接触和面积判据检查 |
| `indent_comparison.csv` | 同一校准材料下 `0.26 mm` 与 `0.80 mm` 推进的九点原始 `Ae/Ac(2°)` 对照 |
| `trend_analysis.json` | 平滑 `Ae/Ac(2°)` 的端点增幅、线性及指数描述参数 |
| `strain_007_manifest.csv` / `strain_007_metadata.json` | 校准前参数的仅眼睑 `EPEL,EQV` 后处理归档，不进入当前数值结论 |
| `strain_probe_007_manifest.csv` / `strain_probe_007_metadata.json` | 校准前参数的眼睑与探头 `EPEL,EQV` 后处理归档，不进入当前数值结论 |
| `excluded_endpoint_exploration/` | 被排除的独立终点试算清单、异常日志与排除依据，不进入发布趋势 |

5090d 发布结果目录：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_calibration/20260721T070542Z_6a75cde2_calibration_0p26/final/candidates/eyelid_s1p00_cornea_s0p75/full_state_0p26
```

状态对应载荷步 2 的结果时间 `1.36470588235294`。计算关系为：总目标位移 `0.05+0.26=0.31 mm`，原加载路径总位移 `0.05+0.80=0.85 mm`，因此结果时间为 `1+0.31/0.85`。MAPDL 使用 `SET,,,,,TIME` 在同一已收敛加载路径中读取该状态。

9 个状态全部完成，QC 为 `0 error、7 warning`。warning 来自 `Ac` 对 `1°-3°` 平面角阈值的敏感性，不代表结果缺失或求解不收敛。远程每个状态均保留 9 张图片；本地按“不新增文件”要求只覆盖原有 7 个厚度的视图。报告见 [0.26 mm 补充报告](../../../docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)，本地图片见 [视图索引](../../../figures/fe_sweep_indent_0p26/views/README.md)。
