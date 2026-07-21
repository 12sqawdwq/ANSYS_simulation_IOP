# 0.26 mm 推进厚度状态视图索引

本目录保存 `0.26 mm` 名义推进下全部 7 个眼睑厚度状态。每个状态包含 9 张固定视图，共 63 张。

| 后缀 | 视图 |
|---:|---|
| `000` | 按材料编号着色的几何与网格 |
| `001` | 探头-眼睑接触压力俯视图 |
| `002` | 探头-眼睑接触压力正视图 |
| `003` | 眼睑 Von Mises 应力正视图 |
| `004` | 角膜 Von Mises 应力正视图 |
| `005` | 探头 Von Mises 应力正视图 |
| `006` | 未变形中央应力截面 |
| `007` | 实际比例变形中央应力截面 |
| `008` | 探头-眼睑数值接触穿透俯视图 |

| 眼睑厚度 (mm) | 状态目录 |
|---:|---|
| 0.80 | [9 张视图](eyelid_0p80mm_indent_0p26mm/) |
| 1.00 | [9 张视图](eyelid_1p00mm_indent_0p26mm/) |
| 1.20 | [9 张视图](eyelid_1p20mm_indent_0p26mm/) |
| 1.40 | [9 张视图](eyelid_1p40mm_indent_0p26mm/) |
| 1.60 | [9 张视图](eyelid_1p60mm_indent_0p26mm/) |
| 1.80 | [9 张视图](eyelid_1p80mm_indent_0p26mm/) |
| 2.00 | [9 张视图](eyelid_2p00mm_indent_0p26mm/) |

不同工况使用自动色标，跨图定量比较应读取 [summary.csv](../../../data/processed/fe_sweep_indent_0p26/summary.csv)。

全部厚度的 `007` 实际比例中央截面已汇总为 [云图展示矩阵](../matrices/indent_0p26_view_007_thickness_matrix.png)。
