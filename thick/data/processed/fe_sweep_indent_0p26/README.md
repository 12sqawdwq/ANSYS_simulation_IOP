# 0.26 mm 推进厚度状态数据

本目录保存批次 `20260721T070542Z_6a75cde2_calibration_0p26` 从已收敛 `0.80 mm` 加载路径中提取的 `0.26 mm` 状态。当前参数为眼睑材料倍率 `1.00`、角膜材料倍率 `0.75`、IOP `20 mmHg`。

| 文件 | 内容 |
|---|---|
| `summary.csv` | 9 个厚度点的闭合接触、反力、压力及历史面积字段；其中 `gat_*` 和相关比例已失效 |
| `manifest.csv` | 每个状态的来源算例、结果时间、位移、QC 字段和 Git 来源 |
| `metadata.json` | 结果目录、状态提取方法、MAPDL 版本与宏文件校验信息 |
| `qc.json` | 完整性、位移、接触和折点敏感性检查 |
| `trend_analysis.json` | 已失效球面相交面积比的历史趋势，禁止用于结论 |
| `contact_endpoint_scan.csv` | `0.35-0.80 mm` 的闭合接触面积平台诊断，不作为 GAT 几何端点 |
| `indent_comparison.csv` | 旧 `Ae/Ac(2°)` 推进对照，仅用于历史追溯 |
| `strain_007_manifest.csv` / `strain_007_metadata.json` | 校准前参数的仅眼睑 `EPEL,EQV` 图像归档 |
| `strain_probe_007_manifest.csv` / `strain_probe_007_metadata.json` | 校准前参数的眼睑与探头 `EPEL,EQV` 图像归档 |
| `excluded_endpoint_exploration/` | 被排除的独立终点试算和排除依据 |

状态对应载荷步 2 的结果时间 `1.36470588235294`。总探头位移为 `0.05+0.26=0.31 mm`，其中 `0.05 mm` 是初始间隙；结果中的 `indent_mm=0.26` 已表示间隙闭合后的名义推进。

## 已撤销的面积口径

本目录的历史 `summary.csv` 曾使用：

```text
R = 7.8 + eyelid_thickness_mm
r = min(2.16, sqrt(2*R*indent_mm - indent_mm^2))
Ae = pi*r^2
```

该式只计算推进平面与未变形球面的交线，并通过 `min(2.16, ...)` 人为截断到探头半径。它不使用有限元形变场，不能表示GAT压平面积。原 `gat_ae_area_mm2`、`gat_ae_fill_fraction`、`ae_over_ac_gat` 及其派生统计已经失效；历史CSV表头已统一改成 `invalidated_sphere_plane_*`，数值仅用于追溯。活动汇总代码已停止生成这些字段。

| 字段 | 含义 |
|---|---|
| `invalidated_sphere_plane_area_mm2` | **已失效**的球面相交面积，原名 `gat_ae_area_mm2` |
| `invalidated_sphere_plane_over_inner_projected` | **已失效**的混合口径比例，原名 `ae_over_ac_gat` |
| `inner_projected_area_mm2` | 内侧径向折点投影面积，仅作诊断 |
| `outer_contact_area_mm2` | 闭合接触承载区，仅作诊断 |
| `outer_surface_area_mm2` | 外侧径向折点曲面积分，仅作诊断 |
| `probe_area_mm2` | 直径 `4.32 mm` 探头名义面积，不是压平面积 |

九个有限元状态全部完成，原批次 QC 为 `0 error、36 warning、1 info`。这个QC只说明文件、位移、接触和当时数值检查完成，不验证面积定义正确。位移场、反力、接触压力、穿透量和视图仍可使用；所有现存 `Ae/Ac` 字段只能追溯，不能评分。

5090d 发布结果目录：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_calibration/20260721T070542Z_6a75cde2_calibration_0p26/final/candidates/eyelid_s1p00_cornea_s0p75/applanation_breakpoint
```

接触平台诊断目录共约 `52 MB`，未复制源 `.db/.rst`。其中只有 `0.80、1.20、2.00 mm` 保留完整源结果；其他厚度的 `invalid_metrics` 是源文件按存储策略删除后的预期跳过，不进入 `contact_endpoint_scan.csv`。

本目录只作为 `0.26 mm` 历史数据保留。当前面积口径和 `0.28 mm` 结果见 [0.28 mm 补充报告](../../../docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md)，历史图片见 [视图索引](../../../figures/fe_sweep_indent_0p26/views/README.md)。
