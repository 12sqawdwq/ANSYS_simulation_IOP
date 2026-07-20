# 眼睑厚度有限元数据

本目录是眼睑厚度三维有限元扫描的固定发布位置，不在文件名中保存版本号。历史结果通过 Git 提交查询。

| 文件 | 内容 |
|---|---|
| `summary.csv` | 7 个厚度状态的工程量与归一化指标 |
| `manifest.csv` | 每个算例的状态、收敛、指标、结果路径和 Git 来源 |
| `metadata.json` | 主机、ANSYS、并行参数、APDL SHA256 和算例矩阵 |
| `qc.json` | 完整性、位移、接触和面积判据质检 |

原始主 `.db/.rst` 位于 5090d：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_sweep/20260720T153013Z_2ecc954_thickness
```

对应报告见 [眼睑厚度有限元实验报告](../../../docs/眼睑厚度有限元实验报告.md)，完整图片见 [视图索引](../../../figures/fe_sweep/views/README.md)。
