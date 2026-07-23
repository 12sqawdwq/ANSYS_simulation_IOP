# 0.26 mm 推进厚度状态视图索引

本目录保存校准材料下 9 个眼睑厚度状态。每个目录包含 9 张固定 MAPDL 视图和 1 张压平边界质控图，共 90 张 PNG。

| 后缀 | 视图 |
|---:|---|
| `000` | 按材料编号着色的几何与网格 |
| `001` | 探头—眼睑接触压力俯视图 |
| `002` | 探头—眼睑接触压力正视图 |
| `003` | 眼睑 Von Mises 应力正视图 |
| `004` | 角膜 Von Mises 应力正视图 |
| `005` | 探头 Von Mises 应力正视图 |
| `006` | 未变形中央应力截面 |
| `007` | 实际比例变形中央应力截面 |
| `008` | 探头—眼睑数值接触穿透俯视图 |
| `applanation_boundary_qc.png` | 外/内表面径向剖面、折点边界和尺度敏感性检查 |

| 眼睑厚度 (mm) | 状态目录 |
|---:|---|
| 0.80 | [10 张视图](eyelid_0p80mm_indent_0p26mm/) |
| 1.00 | [10 张视图](eyelid_1p00mm_indent_0p26mm/) |
| 1.20 | [10 张视图](eyelid_1p20mm_indent_0p26mm/) |
| 1.25 | [10 张视图](eyelid_1p25mm_indent_0p26mm/) |
| 1.40 | [10 张视图](eyelid_1p40mm_indent_0p26mm/) |
| 1.50 | [10 张视图](eyelid_1p50mm_indent_0p26mm/) |
| 1.60 | [10 张视图](eyelid_1p60mm_indent_0p26mm/) |
| 1.80 | [10 张视图](eyelid_1p80mm_indent_0p26mm/) |
| 2.00 | [10 张视图](eyelid_2p00mm_indent_0p26mm/) |

不同工况使用独立自动色标，跨图定量比较应读取 [summary.csv](../../../data/processed/fe_sweep_indent_0p26/summary.csv)。九组压平边界汇总图见 [applanation_boundary_matrix.png](../trends/applanation_boundary_matrix.png)。

已有的 `007` 应变矩阵和应变后处理形成于校准前参数，仅作为历史图像归档。校准前同视角应变后处理另见 [仅眼睑应变视图](../strain_views/README.md)和[眼睑与探头应变视图](../strain_probe_views/README.md)。
