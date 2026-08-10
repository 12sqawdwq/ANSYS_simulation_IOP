# 网格无关性轻量结果

本目录只接收可进入 Git 的轻量产物：

- `baseline_mesh_inventory.csv`：从既有 0.30 mm 运行 manifest 和 `solve.out` 提取的轻量求解器/QC 清单；
- `screening/iop0_run_manifest.csv`
- `screening/iop20_run_manifest.csv`
- `screening/iop0_run_metadata.json`
- `screening/iop20_run_metadata.json`
- `screening/campaign_status.csv`
- `screening/mesh_comparison.csv`
- `screening/screening_summary.json`
- `screening/mesh_independence_screening.png`
- `screening/mesh_independence_screening.svg`
- `confirmation/mesh_comparison.csv`：0.30/0.24/0.20 mm 三级比较；
- `confirmation/screening_summary.json`：最终机器可读判定；
- `confirmation/mesh_independence_screening.png/.svg`：三级网格图；
- `confirmation/CONCLUSION.md`：结论与 claim boundary；
- `confirmation/iop*_run_manifest.csv`、`iop*_run_metadata.json` 和 source campaign status：被接收的 0.20 mm 端点来源；
- `confirmation/external_artifact_manifest.json`：5090d 源文件路径、大小和 SHA-256；
- `visual_evidence/raw/*.png`：0.30/0.24/0.20 mm 的原始 MAPDL 网格与等效应力中央剖面；
- `visual_evidence/*_comparison.png`：统一条件下的三级截图拼版；
- `visual_evidence/simulation_timing.csv`：18 个接收终点的逐项墙钟时间、MPI ranks 和求解规模；
- `visual_evidence/resource_preflight_timing.csv`：未接收资源预检的时间成本；
- `visual_evidence/source_manifest.json`：外部 DB/RST、后处理宏和 PNG 的路径、大小及 SHA-256；
- `visual_evidence/timing_summary.json` 和 `artifact_manifest.json`：时间汇总与 Git 轻量文件哈希。

实际截图和时间解释见 [`../DETAILED_REPORT.md`](../DETAILED_REPORT.md)。

大体积 DB/RST、面场 CSV 和完整 MAPDL 文件继续位于配置登记的 5090d 外部数据目录，不进入 Git。资源预检中止的 20 mmHg 端点没有进入三级比较；相应中止和清理标记保留在 `confirmation/`。

最终判定为：三个网格均保持厚端下降次序，但 0.20 mm 相对 0.24 mm 的最大 $q$ 变化仍为 12.31%，因此绝对幅值未达到网格无关。
