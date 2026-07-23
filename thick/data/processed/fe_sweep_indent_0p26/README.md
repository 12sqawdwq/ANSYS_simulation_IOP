# 0.26 mm 推进厚度状态数据

本目录保存批次 `20260721T070542Z_6a75cde2_calibration_0p26` 从已收敛 `0.80 mm` 加载路径中提取的 `0.26 mm` 状态。当前参数为眼睑材料倍率 `1.00`、角膜材料倍率 `0.75`、IOP `20 mmHg`。

| 文件 | 内容 |
|---|---|
| `summary.csv` | 9 个厚度点的 GAT 几何 `Ae`、内侧 `Ac`、闭合接触、反力、压力及历史诊断指标 |
| `manifest.csv` | 每个状态的来源算例、结果时间、位移、QC 字段和 Git 来源 |
| `metadata.json` | 结果目录、状态提取方法、MAPDL 版本与宏文件校验信息 |
| `qc.json` | 完整性、位移、接触和折点敏感性检查 |
| `trend_analysis.json` | GAT `Ae/Ac` 的端点变化和描述性趋势参数 |
| `contact_endpoint_scan.csv` | `0.35-0.80 mm` 的闭合接触面积平台诊断，不作为 GAT 几何端点 |
| `indent_comparison.csv` | 旧 `Ae/Ac(2°)` 推进对照，仅用于历史追溯 |
| `strain_007_manifest.csv` / `strain_007_metadata.json` | 校准前参数的仅眼睑 `EPEL,EQV` 图像归档 |
| `strain_probe_007_manifest.csv` / `strain_probe_007_metadata.json` | 校准前参数的眼睑与探头 `EPEL,EQV` 图像归档 |
| `excluded_endpoint_exploration/` | 被排除的独立终点试算和排除依据 |

状态对应载荷步 2 的结果时间 `1.36470588235294`。总探头位移为 `0.05+0.26=0.31 mm`，其中 `0.05 mm` 是初始间隙；结果中的 `indent_mm=0.26` 已表示间隙闭合后的名义推进。

## 面积口径

GAT 正式外侧面积使用：

```text
R = 7.8 + eyelid_thickness_mm
r = min(2.16, sqrt(2*R*indent_mm - indent_mm^2))
Ae = pi*r^2
```

`geometric_full_contact_indent_mm=R-sqrt(R²-2.16²)`。在该推进处，`gat_ae_area_mm2` 达到探头面积 `14.6574 mm²`。主比例 `ae_over_ac_gat` 使用 `gat_ae_area_mm2 / inner_projected_area_mm2`。

| 字段 | 含义 |
|---|---|
| `gat_ae_area_mm2` | 正式 GAT 平面外侧面积 `Ae` |
| `inner_projected_area_mm2` | 当前内侧中心连续压平区 `Ac` |
| `outer_contact_area_mm2` | 闭合接触承载区，只作诊断 |
| `outer_surface_area_mm2` | 外侧径向折点曲面积分，只作诊断 |
| `probe_area_mm2` | 直径 4.32 mm 探头面积上限 |

九个状态全部完成，QC 为 `0 error、36 warning、1 info`。warning 主要来自保留的内外折点尺度敏感性和旧角度阈值敏感性，不影响解析计算的 GAT `Ae`，但限制当前 `Ac` 的精度。

5090d 发布结果目录：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_calibration/20260721T070542Z_6a75cde2_calibration_0p26/final/candidates/eyelid_s1p00_cornea_s0p75/applanation_breakpoint
```

接触平台诊断目录共约 `52 MB`，未复制源 `.db/.rst`。其中只有 `0.80、1.20、2.00 mm` 保留完整源结果；其他厚度的 `invalid_metrics` 是源文件按存储策略删除后的预期跳过，不进入 `contact_endpoint_scan.csv`。

报告见 [0.26 mm 补充报告](../../../docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)，图片见 [视图索引](../../../figures/fe_sweep_indent_0p26/views/README.md)。
