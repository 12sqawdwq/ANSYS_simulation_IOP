# Dryad 原始工作簿放置目录

数据集：<https://doi.org/10.5061/dryad.z8w9ghx9f>（CC0 1.0）。

15 个官方工作簿现已保存于本目录，并通过文件大小和 SHA-256 校验。保持官方文件名，运行：

```powershell
conda run -n base python data/build_dataset.py
```

`data/dryad_file_manifest.csv` 中 15 个文件的状态应全部为 `verified`。任何 `checksum_mismatch` 文件都不得进入后续反演。

`Tangent_(Et)_vs_stress_curve (1).xlsx` 与官方 `Tangent_(Et)_vs_stress_curve.xlsx` 的 SHA-256 完全相同，是浏览器生成的重复副本，不参与构建和反演。
