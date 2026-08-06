# 高眼压实验更改日志

本日志按 Git 提交逆时间排列，保存高眼压模块每次提交的时间、提交号、主题和全部路径状态。实验运行本身的时间、主机、输入哈希和外部数据根仍以 `results/*launch_metadata.json`、controller state 和完整实验记录为准。Git 是版本真源，本文件不使用 v1/v2/final 状态命名。

## Unreleased（整理分支 `repo-reorganization-20260806`）

- 将实验根目录整理为 `config/`、`scripts/{analysis,postprocess,server}/`、`docs/`、`results/`、`figures/`；
- 将 14 份原实验文档全文合并到 `EXPERIMENT_RECORD.md`，同时保存原 SHA-256、Git blob 和段落哈希；
- 建立主要结论、系统工程、脚本索引和中间结论生命周期文档；
- 删除已被密集网格替代的 40 mmHg 预检、首轮矩阵和 5 mmHg 补点当前入口；历史结果不删除；
- 把 0–50、50–60 和界面积分入口改为职责/范围命名，并更新测试；
- 修复高压绘图脚本只识别 Linux Noto CJK 字体的问题。

## 2026-07-31T14:26:08+08:00 · `956a0ec` · Add direct RST implications to eta_eff analysis

- 完整提交：`956a0ec87abcbd168a8d1e34445307d0d906c6cd`
- 修改文件数：5
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/ETA_EFF_EFFECTIVE_CORRECTION_ANALYSIS.md
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_eta_eff_analysis_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
```

## 2026-07-31T14:18:05+08:00 · `596c92d` · Document eta_eff correction factor and range

- 完整提交：`596c92dba00d29e3ed49e8e581d9e6c33cbd10f4`
- 修改文件数：6
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/ETA_EFF_EFFECTIVE_CORRECTION_ANALYSIS.md
M	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_eta_eff_analysis_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
```

## 2026-07-31T13:06:36+08:00 · `af9b970` · Report frozen-model extrapolation through 60 mmHg

- 完整提交：`af9b970febc106bee648f40044fc91cf61aafd56`
- 修改文件数：13
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_INVERSE_RIGOR_AUDIT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/IOP_50_TO_60_EXTENSION_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/iop60_frozen_model_extrapolation.png
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_scatter_0_to_60_step2p5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop60_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop60_controller_state.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop60_frozen_model_extrapolation.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop60_frozen_model_extrapolation.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop60_launch_metadata.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop_0_to_60_step2p5_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop_0_to_60_step2p5_summary.json
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
```

## 2026-07-31T12:21:14+08:00 · `5017b61` · Add frozen-model IOP extension through 60 mmHg

- 完整提交：`5017b6193ccb0b6e85162e9df2293aaba0cb837b`
- 修改文件数：5
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/evaluate_iop60_extrapolation.py
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop_50_to_60_step2p5_5090d.sh
M	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_2p5.py
M	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop_5_to_50_supplement.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_iop_50_to_60_step2p5.json
```

## 2026-07-31T12:11:43+08:00 · `5ab65f3` · Use portable Markdown math delimiters

- 完整提交：`5ab65f358f766297cf739440ef61d550f99534e0`
- 修改文件数：12
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_INVERSE_RIGOR_AUDIT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_RATIONAL_PARAMETER_DERIVATION.md
M	high_iop_mechanical_transfer_t1p25_c0p60/GLOBAL_LOAD_SHARE_DERIVATION.md
M	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/IOP_2P5_SUPPLEMENT_RESULT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/RATIONAL_REGRESSION_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/forward_rational_section3_math_render.png
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
```

## 2026-07-31T12:00:40+08:00 · `a689a16` · Support structural formula audits without LaTeX

- 完整提交：`a689a16b68df5d46f76a1a7ae0e35f80994f379c`
- 修改文件数：2
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
```

## 2026-07-31T11:59:48+08:00 · `a4d5620` · Repair and audit report formula rendering

- 完整提交：`a4d56202687308cad90e7564a88400690271374b`
- 修改文件数：6
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_INVERSE_RIGOR_AUDIT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/GLOBAL_LOAD_SHARE_DERIVATION.md
M	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
```

## 2026-07-31T11:52:27+08:00 · `8b2c8a1` · Audit forward and inverse model rigor

- 完整提交：`8b2c8a11a62c9aff3cc2e774f769f043279a6927`
- 修改文件数：5
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_INVERSE_RIGOR_AUDIT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/GLOBAL_LOAD_SHARE_DERIVATION.md
M	high_iop_mechanical_transfer_t1p25_c0p60/figures/global_load_share_rational_derivation.png
M	high_iop_mechanical_transfer_t1p25_c0p60/plot_global_load_share_derivation.py
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
```

## 2026-07-31T11:35:59+08:00 · `0e49d5c` · Normalize load-share CSV artifact hashing

- 完整提交：`0e49d5c44e364d3c16f8d7ee0e4e5ad65bea6136`
- 修改文件数：3
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/derive_global_load_share_model.py
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_derivation.json
```

## 2026-07-31T11:35:13+08:00 · `2f454fd` · Derive rational IOP model from global load sharing

- 完整提交：`2f454fd8e8ba09056e242f4e443e20f70dd0fea3`
- 修改文件数：8
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/GLOBAL_LOAD_SHARE_DERIVATION.md
M	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/derive_global_load_share_model.py
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/global_load_share_rational_derivation.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_global_load_share_derivation.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_derivation.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_derivation.json
```

## 2026-07-31T11:11:07+08:00 · `fe8687e` · Complete direct RST interface-force integration

- 完整提交：`fe8687e6b4a98267bec458a04034d7669b4fa5ef`
- 修改文件数：9
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/interface_force_direct_forward_vs_inverse.png
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/interface_force_factor_decomposition.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_interface_force_forward_analysis.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_controller_state.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_launch_metadata.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_summary.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
```

## 2026-07-31T11:03:24+08:00 · `3ce7c95` · Map reused 40 mmHg integration source

- 完整提交：`3ce7c957e7920d63334c86657f182a7027ba3404`
- 修改文件数：2
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_interface_force_integrals.py
M	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_interface_force_integrals.json
```

## 2026-07-31T10:59:20+08:00 · `88c5786` · Integrate interface forces from retained RST files

- 完整提交：`88c5786a464c464762ecafc74999682be27f8c89`
- 修改文件数：3
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_interface_force_integrals_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_interface_force_integrals.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_interface_force_integrals.json
```

## 2026-07-31T10:35:28+08:00 · `df2915d` · Derive forward rational IOP parameters

- 完整提交：`df2915dd95f6dbdc0935d47d430395b1bdb941ff`
- 修改文件数：6
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_RATIONAL_PARAMETER_DERIVATION.md
A	high_iop_mechanical_transfer_t1p25_c0p60/derive_forward_rational_parameters.py
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/forward_vs_inverse_rational_iop_0_to_50_step2p5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_ac5_proxy.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_ac5_proxy.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_artifact_sha256.txt
```

## 2026-07-30T23:36:13+08:00 · `b3509ff` · Fit rational probe-to-IOP regression

- 完整提交：`b3509ff33c871c77182048ec31d9e82cf5a2ae79`
- 修改文件数：6
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/RATIONAL_REGRESSION_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_rational_regression_0_to_50_step2p5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/fit_rational_piop_vs_pprobe.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_0_to_50_step2p5.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_0_to_50_step2p5.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_artifact_sha256.txt
```

## 2026-07-30T21:41:01+08:00 · `246335b` · Normalize dense result artifact checksums

- 完整提交：`246335bcfd5b9274bb40abfc72a7c2d5d11520f2`
- 修改文件数：1
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_artifact_sha256.txt
```

## 2026-07-30T21:40:41+08:00 · `31cdc02` · Complete 2.5 mmHg pressure-grid validation

- 完整提交：`31cdc024859fe25a7e15dfd4936944d94807bb19`
- 修改文件数：7
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/IOP_2P5_SUPPLEMENT_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_scatter_0_to_50_step2p5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_controller_state.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_launch_metadata.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_summary.json
```

## 2026-07-30T18:06:54+08:00 · `290d054` · Launch 2.5 mmHg pressure-grid supplement

- 完整提交：`290d0544218a3928009fc28f907a001cfed34c2c`
- 修改文件数：4
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop_2p5_supplement_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_2p5.py
M	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop_5_to_50_supplement.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_iop_2p5.json
```

## 2026-07-30T17:11:29+08:00 · `7dca01a` · Swap axes in supplemental IOP scatter plot

- 完整提交：`7dca01a2c5d1049f74dcbe687e9ac548ab3eabca`
- 修改文件数：3
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/IOP_5_TO_50_SUPPLEMENT_RESULT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_scatter_5_to_50_step5.png
M	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_5_to_50.py
```

## 2026-07-30T17:09:23+08:00 · `563eb16` · Complete five-millimeter IOP supplement through 50

- 完整提交：`563eb161488a1c0d0eb9d329a675d585f30efbba`
- 修改文件数：7
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/AREA_RATIO_K_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/IOP_5_TO_50_SUPPLEMENT_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_scatter_5_to_50_step5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_5_to_50.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_440e44e5_iop_5_to_50_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_440e44e5_iop_5_to_50_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_440e44e5_iop_5_to_50_summary.json
```

## 2026-07-30T14:16:12+08:00 · `440e44e` · Prepare five-millimeter IOP supplement through 50

- 完整提交：`440e44e523e87d8248b8eea0a614dc77138c0471`
- 修改文件数：3
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop_5_to_50_supplement_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop_5_to_50_supplement.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_iop_5_to_50.json
```

## 2026-07-30T14:06:15+08:00 · `1c9c883` · Plot IOP against baseline-subtracted probe reading

- 完整提交：`1c9c8831b2d22836f3ee979422ddbb0576538ee9`
- 修改文件数：3
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/AREA_RATIO_K_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_scatter_0p259875.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_scatter.py
```

## 2026-07-30T13:54:31+08:00 · `c48d62c` · Plot IOP against Ae over Ac ratio

- 完整提交：`c48d62cdbb8a3aaf0526ebc26a0efd93942eb5bc`
- 修改文件数：3
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/AREA_RATIO_K_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/iop_vs_k_ae_over_ac_0p259875.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_iop_vs_kae_ac.py
```

## 2026-07-30T13:42:04+08:00 · `c3a7fe7` · Analyze direct area-ratio IOP error

- 完整提交：`c3a7fe7f0beec21e5fa277b9d9ede590d84e6843`
- 修改文件数：4
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/AREA_RATIO_ERROR_ANALYSIS.md
A	high_iop_mechanical_transfer_t1p25_c0p60/analyze_area_ratio_error.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_area_ratio_error_decomposition.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_area_ratio_error_decomposition.json
```

## 2026-07-30T13:28:48+08:00 · `61eb289` · Add direct area-ratio K results

- 完整提交：`61eb289ad109f068993f9eaadb681597235681a8`
- 修改文件数：5
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/AREA_RATIO_K_RESULT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/FULL_EXPERIMENT_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_area_ratio_iop.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_area_ratio_k_iop_results.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_area_ratio_k_iop_results.json
```

## 2026-07-30T13:16:51+08:00 · `33e9f46` · Record complete high-IOP experiment results

- 完整提交：`33e9f4628c10be4018d9eb20491336cf4a0e1367`
- 修改文件数：5
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
A	high_iop_mechanical_transfer_t1p25_c0p60/FULL_EXPERIMENT_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_23d4f22f_full_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_23d4f22f_full_high_iop_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_23d4f22f_full_high_iop_summary.json
```

## 2026-07-30T12:31:09+08:00 · `23d4f22` · Prepare complete high-IOP experiment matrix

- 完整提交：`23d4f22fc9366c99edeee92acda68d880f4d21d2`
- 修改文件数：4
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_full_experiment_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_full_high_iop.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_full.json
```

## 2026-07-30T12:24:38+08:00 · `3ca8005` · Record successful 40 mmHg preflight

- 完整提交：`3ca800526c6dd06c34230f70fc3c7ec2684b42c5`
- 修改文件数：8
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
A	high_iop_mechanical_transfer_t1p25_c0p60/IOP40_PREFLIGHT_RESULT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop40_preflight_5090d.sh
M	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop40_preflight.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_bdca48fe_iop40_preflight_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_bdca48fe_iop40_preflight_summary.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_bdca48fe_iop40_primary_0p26_geometry_state.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_bdca48fe_iop40_sensitivity_0p28_geometry_state.json
```

## 2026-07-30T12:08:06+08:00 · `bdca48f` · Prepare 40 mmHg convergence preflight

- 完整提交：`bdca48fe1704b1cb1bf9f863a7275b0866b34f97`
- 修改文件数：4
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop40_preflight_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop40_preflight.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec.json
```

## 2026-07-30T11:52:19+08:00 · `24ae7d7` · Estimate parallel runtime for high-IOP study

- 完整提交：`24ae7d7675063fbfaa5b4ce714bab12bc475b1eb`
- 修改文件数：1
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```

## 2026-07-30T11:50:09+08:00 · `73381cd` · Add complete expected probe-to-IOP table

- 完整提交：`73381cde69664c8a0a74b81d3ab1d0aa99a3d4d5`
- 修改文件数：1
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```

## 2026-07-30T11:47:14+08:00 · `2c9d8ab` · Add expected IOP inversion results

- 完整提交：`2c9d8abc77b4807b1f4255c7ca392fef37a20ab0`
- 修改文件数：1
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```

## 2026-07-30T11:39:58+08:00 · `4e10088` · Specify absolute tissue mechanics for high-IOP study

- 完整提交：`4e10088c4113a694b59e29a611a7a637501a2ba9`
- 修改文件数：1
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```

## 2026-07-30T11:36:19+08:00 · `0c31c88` · Freeze 0.26 mm as primary high-IOP state

- 完整提交：`0c31c8809bc27560f06fe3ae2b976b8b789a6c6e`
- 修改文件数：1
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```

## 2026-07-30T11:34:06+08:00 · `cc3e84f` · Move high-IOP experiment beside thickness study

- 完整提交：`cc3e84fc61eb87fb6835c7b060b90565edb70030`
- 修改文件数：1
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```
