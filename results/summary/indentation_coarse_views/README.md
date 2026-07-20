# 偏心粗扫描完整视图索引

本目录保存 `indentation_coarse` 全部 12 个工况的 9 张固定 MAPDL 视图，共 108 张。工况目录名同时记录偏心量和名义推进量。

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

| 偏心量 (mm) | 0.0 mm 推进 | 0.4 mm 推进 | 0.8 mm 推进 |
|---:|---|---|---|
| 0.0 | [视图](offset_0p00mm_indent_0p00mm/) | [视图](offset_0p00mm_indent_0p40mm/) | [视图](offset_0p00mm_indent_0p80mm/) |
| 0.5 | [视图](offset_0p50mm_indent_0p00mm/) | [视图](offset_0p50mm_indent_0p40mm/) | [视图](offset_0p50mm_indent_0p80mm/) |
| 1.0 | [视图](offset_1p00mm_indent_0p00mm/) | [视图](offset_1p00mm_indent_0p40mm/) | [视图](offset_1p00mm_indent_0p80mm/) |
| 2.0 | [视图](offset_2p00mm_indent_0p00mm/) | [视图](offset_2p00mm_indent_0p40mm/) | [视图](offset_2p00mm_indent_0p80mm/) |

数值验收以同级目录中的 `indentation_coarse.csv` 和 `indentation_coarse_qc.json` 为准；图片用于检查几何、分布和异常形态。
