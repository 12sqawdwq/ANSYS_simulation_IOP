# Dryad 原始工作簿放置目录

数据集：<https://doi.org/10.5061/dryad.z8w9ghx9f>（CC0 1.0）。

当前网络访问文件下载端点时触发 AWS 人机验证，因此仓库只保存官方文件清单和 SHA-256，不保存 403/401 响应或图像数字化曲线。通过浏览器下载 15 个工作簿后，保持官方文件名放在本目录，再运行：

```powershell
conda run -n base python data/build_dataset.py
```

`data/dryad_file_manifest.csv` 中对应状态应由 `not_downloaded_aws_waf` 变为 `verified`。任何 `checksum_mismatch` 文件都不得进入后续反演。
