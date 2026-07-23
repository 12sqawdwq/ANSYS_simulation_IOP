# 0.26 mm 推进厚度状态数据

本目录保存批次 `20260721T070542Z_6a75cde2_calibration_0p26` 从已收敛 `0.80 mm` 推进加载路径中提取的 `0.26 mm` 状态。当前参数为眼睑材料倍率 `1.00`、角膜材料倍率 `0.75`、IOP `20 mmHg`。原 `0.80 mm` 基准材料发布数据仍保存在相邻 `fe_sweep/`，未被覆盖。

| 文件 | 内容 |
|---|---|
| `summary.csv` | 9 个厚度点的工程量、闭合接触、折点曲面积分/投影及历史角度阈值指标 |
| `manifest.csv` | 每个状态的来源算例、结果时间、位移、QC 字段和 Git 来源 |
| `metadata.json` | 结果目录、状态提取方法、MAPDL 版本与宏文件校验信息 |
| `qc.json` | 完整性、位移、视图、接触和面积判据检查 |
| `indent_comparison.csv` | 旧 `Ae/Ac(2°)` 在 `0.26 mm` 与 `0.80 mm` 推进下的历史对照，不进入新口径结论 |
| `trend_analysis.json` | 曲面积分 `Ae/Ac` 和探头名义面积诊断量的描述性趋势参数 |
| `strain_007_manifest.csv` / `strain_007_metadata.json` | 校准前参数的仅眼睑 `EPEL,EQV` 后处理归档，不进入当前数值结论 |
| `strain_probe_007_manifest.csv` / `strain_probe_007_metadata.json` | 校准前参数的眼睑与探头 `EPEL,EQV` 后处理归档，不进入当前数值结论 |
| `excluded_endpoint_exploration/` | 被排除的独立终点试算清单、异常日志与排除依据，不进入发布趋势 |

5090d 发布结果目录：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_calibration/20260721T070542Z_6a75cde2_calibration_0p26/final/candidates/eyelid_s1p00_cornea_s0p75/applanation_breakpoint
```

状态对应载荷步 2 的结果时间 `1.36470588235294`。总目标位移为 `0.05+0.26=0.31 mm`，原加载路径总位移为 `0.05+0.80=0.85 mm`，因此结果时间为 `1+0.31/0.85`。MAPDL 使用 `SET,,,,,TIME` 在同一条已收敛加载路径中读取该状态。

主面积边界采用中心近似平面段与外侧曲面段的连续折点，边界内变形后三角面的曲面积分为正式面积，沿探头轴的投影为诊断面积。`1°-3°` 结果只用于说明旧判据的网格敏感性。

以下三个尺度不得混写：

| 尺度 | 含义 |
|---|---|
| `outer_contact_area_mm2` | 实际闭合承载区 |
| `outer_surface_area_mm2` | 外侧中心几何压平区 `Ae` |
| `probe_area_mm2=14.6574` | 直径 4.32 mm 探头的名义全表面面积 |

9/9 状态完成。最终 QC 为 `0 error、36 warning、1 info`，`passed=true`。warning 来自折点拟合窗口尺度敏感、几何折点与闭合接触边界差异，以及历史角度阈值敏感；不表示 MAPDL 求解失败或结果缺失。报告见 [0.26 mm 补充报告](../../../docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)，图片见 [视图索引](../../../figures/fe_sweep_indent_0p26/views/README.md)。
