# 仓库系统日志与更改日志

本日志是仓库级可读索引：按 Git 提交逆时间排列，保存每个提交的时间、主题和完整 `name-status` 文件清单。科学结论应读取各模块主要结论文档；运行时环境与外部求解日志读取 launch metadata/manifest。完整差异仍以 `git show <commit>` 为唯一真源。

## Unreleased

- 将所有新实验的统一参考眼睑厚度冻结为 1.25 mm，新增 `config/model_baseline.json` 机器可读真源和仓库级叙述文档；
- 普通压入/偏心 profile、5090d 标准 launcher 和 APDL 直接调用兜底统一读取或使用 1.25 mm，并在新运行元数据中记录基线配置哈希、实际厚度模式和显式覆盖原因；
- 厚度扫描、厚端网格无关性及 L010 2.00 mm 锚点保留为预注册显式厚度覆盖，既有 1.00 mm/其他厚度结果不追溯改写，正在运行的 2.00 mm campaign 不改变输入；
- 增加全局基线漂移测试，并冻结历史 TSV/混合换行轻量证据的跨平台字节口径；
- 评估全局 0.10/0.12/0.15 mm 的单元、方程、RST 和墙钟资源包络，拒绝在当前 123 GiB RAM、148 GiB 空闲磁盘条件下直接启动全局 0.10 mm 非线性矩阵；
- 在统一 APDL 模型中增加显式 opt-in 的局部四面体细化：0.20 mm 背景、1.80 mm 中央半宽、两条 0.80 mm 界面带，一级名义目标 0.10 mm，默认生产路径保持不变；
- 建立 P0 mesh-only、P1 2.00 mm 压力对、条件 P2 厚端扩展和仅 mesh-only 的 0.05 mm P3 四级设计；开发期 L005 已达到约 288 万实体单元、399 万节点，当前资源下明确拒绝其非线性求解；
- 新增 clean-commit/server-capacity 守卫、压力串行 launcher、运行中内存/磁盘保护、资源投影和配对评估脚本；
- 保留开发期 mesh-only 审计和失败尝试边界；在 commit `8768e6ec...` 上完成 G015/L010 正式 P0，二者 MAPDL error 与 shape error 均为 0，P0 不进入 $q$ 比较；
- 审计 commit `d334fd1...` 上首次 L010 P1：0 mmHg 因内存保护中止，20 mmHg 未启动，无完整端点或 $q$；登记 337.095 万方程、out-of-core 资源包络、最低 11.50 GiB 可用内存、独立 MAPDL/MPI session 和 83.15 GiB失败临时分配清理；
- 将 P1 launcher 重构为 user-systemd cgroup + 随机 campaign token，强制单压力 campaign、10 s资源监测、30/100 GiB中止线、完整 TERM→KILL和零残留核验；在 clean commit `c62987d...` 上完成嵌套 `setsid` helper 与完整 launcher TERM 路径正式测试，两者均升级 KILL、残留 0，测试未调用 ANSYS。

## 2026-08-10 · `3661f68` · Merge fixed-scale mesh stress visual aid

- 保留三级网格原生自动色标图不变，新增固定 0–60 kPa 色标的同工况中央剖面，用于跨网格同色同值空间定位；
- 60 kPa 高于既有最大原生图例上限 55.606 kPa，不通过截断极值制造视觉一致性；
- 增加三张原始固定色标 PNG、三级拼版、独立外部 provenance manifest、构建脚本支持和报告解读；
- 明确统一色标只能辅助比较高应力区位置和范围，不能替代积分力、接触 QC、2% 幅值判据或原生自动色标证据。

## 2026-08-10 · `3a5b003` · Merge mesh visual evidence and timing audit

- 为三级网格审计增加统一 MAPDL 后处理宏，在同一 2.00 mm、20 mmHg、0.28 mm 工况下输出 0.30/0.24/0.20 mm 的实际比例中央网格剖面和带单元边等效应力云图；
- 新增三级网格截图拼版、原始 PNG、外部 DB/RST/PNG SHA-256 provenance 和 Git 轻量产物哈希；
- 汇总 18 个接收终点的逐项墙钟时间、MPI ranks、rank·h、单元/节点/方程规模，并单列三次未接收资源预检和既有 RST 图片后处理时间；
- 新增 `thickness_mesh_independence/DETAILED_REPORT.md`，严格区分厚端次序稳健与绝对幅值未网格无关，并披露自动色标、历史异构 rank 数和 0.20 mm 资源竞争边界。

## 2026-08-09 · `136fae6` · Merge rational IOP manuscript and mesh audit

- 新建 `paper/` 论文目录；
- 基于本地冻结 CSV/JSON 数据撰写以第二版本经验分式为唯一拟合 claim 的高眼压外推和厚度可识别性中文完整初稿；
- 增加中英文题目与摘要、方法、结果、讨论、结论、声明、数据溯源和投稿前核对清单；
- 增加固定推进串联结构、球面小压平、压力增刚、面积修正及 $p=\eta K_Aq$ 到第二版本分式的详细推导，并显式映射两套 $a/b$ 符号；
- 将 RESULTS 重构为“IOP 相关耦合等效刚度—有限元场变量重分布—角膜至探头载荷路径—非线性输出与反演”，再导出第二版本方程；
- 使用 0.259875 和 0.280000 mm 两个相邻状态计算系统级耦合割线刚度，明确其不等于独立眼睑/角膜刚度或材料模量；
- 从 5090d 外部数据区的既有收敛 RST 对 0、20、40、50 mmHg 统一后处理探头—眼睑—角膜中央剖面等效应力云图，采用变形后实际比例，并保存轻量 PNG、SHA-256 provenance manifest 和自动色标限制说明；
- 更新可复现四联图及构建脚本，展示耦合刚度、角膜压力合力、面积修正、接口/探头力和正向分式响应，并增加云图哈希校验与组合输出；
- 论文不再引用由四个不可识别参数 `NA` 柱主导的归一化厚度灵敏度图，改为直接展示 0/20 mmHg 总反力、20 mmHg 零基线输出及各厚度压力状态覆盖，从数据层面呈现厚度响应与参数不可识别性；
- 新建 `thickness_mesh_independence/`，对 1.60、1.80、2.00 mm 厚端零基线输出开展 0/20 mmHg 配对网格细化；完成 0.30/0.24/0.20 mm 三级比较，大体积 DB/RST 留在 5090d；
- 三级网格的 18 个状态完整、9 组厚度 × 网格配对全部通过 QC，三个网格均保持 `q(1.60) > q(1.80) > q(2.00)`；但 0.20 mm 相对 0.24 mm 的最大 $q$ 变化仍为 12.31%，最终判定为“厚端次序稳健、绝对幅值未达到网格无关”，不把 1.60 mm 升级为物理阈值；
- 记录细网格并发时的内存/I/O 资源预检、中止和清理边界；最终 0.20 mm 采用单压力串行完成，未完整的预检端点不进入结果；
- 将 0.20 mm manifests、metadata、campaign status、外部求解日志 SHA-256、三级 CSV/JSON、PNG/SVG 和结论纳入轻量结果治理，并在论文方法、结果、讨论、局限性和结论中同步披露；
- 外部文献尚未系统检索，正文明确保留待补标记，不生成虚假引用。

## 2026-08-07 · `cef09f9` · Merge three-version IOP algorithm presentation

- 将算法展示统一为三个概念版本：有效压平面积比换算、$p=aq/(1-bq)$ 经验分式反演、力学传递效率/修正模型；
- 新增版本一说明，保留其高压失效负结果，并明确面积项继续作为版本三的组成部分；
- 统一版本二展示符号，同时保留与历史 `a_per_mmhg`、`b_dimensionless` 字段的显式映射；
- 将机器可读注册表升级为三版本 schema，并继续声明 `production_algorithm_available=false`；
- 保留逐文件分类、Git 演化链、历史设计/实现/结果的提交号和 Git blob，不复制旧脚本；
- 扩展自动测试，校验三版本顺序、生命周期、参数映射和完整历史对象。

## 2026-08-06 · `bea2e5d` · Merge repository reorganization

- 通过非快进合并纳入 `e70b506` 和 `ae5f69f`；
- 建立仓库级脚本索引和文档治理规则；
- 系统整理高眼压实验目录并做无损文档合并；
- 审计并删除已被当前密集压力链替代的阶段入口；
- 保留结果证据、整理分支和 Git 可恢复性。

## 2026-08-06T15:46:10+08:00 · `e70b506` · Add thickness sensitivity analysis and ignore local sponge runs

- 完整提交：`e70b506efc6b819a420a23bd4292971228ef41e4`
- 修改文件数：63
- 文件：

```text
M	.gitignore
A	analysis/README.md
A	analysis/__init__.py
A	analysis/build_report.py
A	analysis/common.py
A	analysis/config.yaml
A	analysis/discover_data.py
A	analysis/extract_stiffness.py
A	analysis/fit_pressure_model.py
A	analysis/make_figures.py
A	analysis/outputs/agreement_statistics.csv
A	analysis/outputs/corneal_stiffness_parameters.csv
A	analysis/outputs/data_dictionary.csv
A	analysis/outputs/data_inventory.csv
A	analysis/outputs/data_inventory_summary.json
A	analysis/outputs/data_quality_summary.json
A	analysis/outputs/exclusion_log.csv
A	analysis/outputs/figure_manifest.csv
A	analysis/outputs/figures/fig01_pressure_curves.png
A	analysis/outputs/figures/fig01_pressure_curves.svg
A	analysis/outputs/figures/fig02_parameters_vs_thickness.png
A	analysis/outputs/figures/fig02_parameters_vs_thickness.svg
A	analysis/outputs/figures/fig03_normalized_sensitivity.png
A	analysis/outputs/figures/fig03_normalized_sensitivity.svg
A	analysis/outputs/figures/fig04_coefficient_of_variation.png
A	analysis/outputs/figures/fig04_coefficient_of_variation.svg
A	analysis/outputs/figures/fig05_coupled_stiffness_power_law.png
A	analysis/outputs/figures/fig05_coupled_stiffness_power_law.svg
A	analysis/outputs/figures/fig06_corneal_stiffness_identifiability.png
A	analysis/outputs/figures/fig06_corneal_stiffness_identifiability.svg
A	analysis/outputs/figures/fig07_stiffness_ratio_identifiability.png
A	analysis/outputs/figures/fig07_stiffness_ratio_identifiability.svg
A	analysis/outputs/figures/fig08_theory_fit_identity.png
A	analysis/outputs/figures/fig08_theory_fit_identity.svg
A	analysis/outputs/figures/fig09_iop_error_vs_thickness.png
A	analysis/outputs/figures/fig09_iop_error_vs_thickness.svg
A	analysis/outputs/figures/fig10_sensitivity_ranking.png
A	analysis/outputs/figures/fig10_sensitivity_ranking.svg
A	analysis/outputs/figures/fig11_pressure_fit_residuals.png
A	analysis/outputs/figures/fig11_pressure_fit_residuals.svg
A	analysis/outputs/fitted_parameters.csv
A	analysis/outputs/mechanical_identifiability.csv
A	analysis/outputs/model_validation.csv
A	analysis/outputs/output_manifest.csv
A	analysis/outputs/pipeline_validation.json
A	analysis/outputs/pressure_error_summary.csv
A	analysis/outputs/pressure_fit_bootstrap.csv
A	analysis/outputs/pressure_fit_predictions.csv
A	analysis/outputs/report.md
A	analysis/outputs/run_manifest.json
A	analysis/outputs/sensitivity_results.csv
A	analysis/outputs/stiffness_parameters.csv
A	analysis/outputs/stiffness_power_law.csv
A	analysis/outputs/stiffness_power_law_bootstrap.csv
A	analysis/outputs/theory_input_availability.csv
A	analysis/outputs/thickness_iop_predictions.csv
A	analysis/outputs/threshold_evaluation.csv
A	analysis/outputs/tidy_data.csv
A	analysis/outputs/variance_decomposition.csv
A	analysis/preprocess.py
A	analysis/run_all.py
A	analysis/sensitivity_analysis.py
A	analysis/validate_theory.py
```

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
- 修改文件数：8
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/ETA_EFF_EFFECTIVE_CORRECTION_ANALYSIS.md
M	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_eta_eff_analysis_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
M	ops/audit-markdown-formulas.py
M	ops/normalize-markdown-math-delimiters.py
```

## 2026-07-31T13:06:36+08:00 · `af9b970` · Report frozen-model extrapolation through 60 mmHg

- 完整提交：`af9b970febc106bee648f40044fc91cf61aafd56`
- 修改文件数：17
- 文件：

```text
M	docs/IOP修正算法全局方向.md
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
M	ops/audit-markdown-formulas.py
M	ops/normalize-markdown-math-delimiters.py
M	tests/test_iop60_extension.py
```

## 2026-07-31T12:21:14+08:00 · `5017b61` · Add frozen-model IOP extension through 60 mmHg

- 完整提交：`5017b6193ccb0b6e85162e9df2293aaba0cb837b`
- 修改文件数：6
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/evaluate_iop60_extrapolation.py
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop_50_to_60_step2p5_5090d.sh
M	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_2p5.py
M	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop_5_to_50_supplement.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_iop_50_to_60_step2p5.json
A	tests/test_iop60_extension.py
```

## 2026-07-31T12:11:43+08:00 · `5ab65f3` · Use portable Markdown math delimiters

- 完整提交：`5ab65f358f766297cf739440ef61d550f99534e0`
- 修改文件数：15
- 文件：

```text
M	docs/IOP修正算法全局方向.md
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
M	ops/audit-markdown-formulas.py
A	ops/normalize-markdown-math-delimiters.py
```

## 2026-07-31T12:00:40+08:00 · `a689a16` · Support structural formula audits without LaTeX

- 完整提交：`a689a16b68df5d46f76a1a7ae0e35f80994f379c`
- 修改文件数：3
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
M	ops/audit-markdown-formulas.py
```

## 2026-07-31T11:59:48+08:00 · `a4d5620` · Repair and audit report formula rendering

- 完整提交：`a4d56202687308cad90e7564a88400690271374b`
- 修改文件数：8
- 文件：

```text
M	docs/IOP修正算法全局方向.md
M	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_INVERSE_RIGOR_AUDIT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/GLOBAL_LOAD_SHARE_DERIVATION.md
M	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
M	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_markdown_formula_render_audit.json
A	ops/audit-markdown-formulas.py
```

## 2026-07-31T11:52:27+08:00 · `8b2c8a1` · Audit forward and inverse model rigor

- 完整提交：`8b2c8a11a62c9aff3cc2e774f769f043279a6927`
- 修改文件数：6
- 文件：

```text
M	docs/IOP修正算法全局方向.md
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
- 修改文件数：10
- 文件：

```text
M	docs/IOP修正算法全局方向.md
A	high_iop_mechanical_transfer_t1p25_c0p60/GLOBAL_LOAD_SHARE_DERIVATION.md
M	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/derive_global_load_share_model.py
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/global_load_share_rational_derivation.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_global_load_share_derivation.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_derivation.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_derivation.json
A	tests/test_global_load_share_derivation.py
```

## 2026-07-31T11:11:07+08:00 · `fe8687e` · Complete direct RST interface-force integration

- 完整提交：`fe8687e6b4a98267bec458a04034d7669b4fa5ef`
- 修改文件数：11
- 文件：

```text
M	docs/IOP修正算法全局方向.md
A	high_iop_mechanical_transfer_t1p25_c0p60/INTERFACE_FORCE_INTEGRAL_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/interface_force_direct_forward_vs_inverse.png
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/interface_force_factor_decomposition.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_interface_force_forward_analysis.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_controller_state.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_launch_metadata.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_summary.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_interface_force_integrals_artifact_sha256.txt
M	tests/test_interface_force_integrals.py
```

## 2026-07-31T11:03:24+08:00 · `3ce7c95` · Map reused 40 mmHg integration source

- 完整提交：`3ce7c957e7920d63334c86657f182a7027ba3404`
- 修改文件数：3
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_interface_force_integrals.py
M	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_interface_force_integrals.json
M	tests/test_interface_force_integrals.py
```

## 2026-07-31T10:59:20+08:00 · `88c5786` · Integrate interface forces from retained RST files

- 完整提交：`88c5786a464c464762ecafc74999682be27f8c89`
- 修改文件数：6
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_interface_force_integrals_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_interface_force_integrals.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_interface_force_integrals.json
A	models/apdl/post_contact_force_integrals.mac
A	src/postprocess/extract_contact_force_integrals.py
A	tests/test_interface_force_integrals.py
```

## 2026-07-31T10:35:28+08:00 · `df2915d` · Derive forward rational IOP parameters

- 完整提交：`df2915dd95f6dbdc0935d47d430395b1bdb941ff`
- 修改文件数：8
- 文件：

```text
M	docs/IOP修正算法全局方向.md
A	high_iop_mechanical_transfer_t1p25_c0p60/FORWARD_RATIONAL_PARAMETER_DERIVATION.md
A	high_iop_mechanical_transfer_t1p25_c0p60/derive_forward_rational_parameters.py
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/forward_vs_inverse_rational_iop_0_to_50_step2p5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_ac5_proxy.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_ac5_proxy.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_artifact_sha256.txt
A	tests/test_forward_rational_derivation.py
```

## 2026-07-30T23:36:49+08:00 · `0cb7f24` · Relax cross-platform regression tolerance

- 完整提交：`0cb7f24b17bfcb32d87a17b258efd20a5d47d23f`
- 修改文件数：1
- 文件：

```text
M	tests/test_rational_iop_regression.py
```

## 2026-07-30T23:36:13+08:00 · `b3509ff` · Fit rational probe-to-IOP regression

- 完整提交：`b3509ff33c871c77182048ec31d9e82cf5a2ae79`
- 修改文件数：8
- 文件：

```text
M	docs/IOP修正算法全局方向.md
A	high_iop_mechanical_transfer_t1p25_c0p60/RATIONAL_REGRESSION_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_rational_regression_0_to_50_step2p5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/fit_rational_piop_vs_pprobe.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_0_to_50_step2p5.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_0_to_50_step2p5.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_artifact_sha256.txt
A	tests/test_rational_iop_regression.py
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
- 修改文件数：9
- 文件：

```text
M	docs/IOP修正算法全局方向.md
A	high_iop_mechanical_transfer_t1p25_c0p60/IOP_2P5_SUPPLEMENT_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_scatter_0_to_50_step2p5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_controller_state.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_launch_metadata.json
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_summary.json
M	tests/test_high_iop_preflight.py
```

## 2026-07-30T21:32:01+08:00 · `e04b0c9` · Adopt mechanistic IOP correction direction

- 完整提交：`e04b0c989a3038ffc9c8b401a8db79a8bd9206d0`
- 修改文件数：2
- 文件：

```text
M	README.md
A	docs/IOP修正算法全局方向.md
```

## 2026-07-30T21:17:11+08:00 · `7169968` · Render formulas in archived IOP conversation

- 完整提交：`716996880abbabc55bfb24e17afb855d600bfc9b`
- 修改文件数：1
- 文件：

```text
M	docs/ChatGPT共享对话_眼压测量模型分析.md
```

## 2026-07-30T18:22:48+08:00 · `cc31b79` · Archive shared IOP modeling conversation

- 完整提交：`cc31b79fb466120d526adba75e7cd536f2284f3c`
- 修改文件数：1
- 文件：

```text
A	docs/ChatGPT共享对话_眼压测量模型分析.md
```

## 2026-07-30T18:06:54+08:00 · `290d054` · Launch 2.5 mmHg pressure-grid supplement

- 完整提交：`290d0544218a3928009fc28f907a001cfed34c2c`
- 修改文件数：5
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop_2p5_supplement_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_2p5.py
M	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop_5_to_50_supplement.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_iop_2p5.json
M	tests/test_high_iop_preflight.py
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
- 修改文件数：8
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/AREA_RATIO_K_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/IOP_5_TO_50_SUPPLEMENT_RESULT.md
A	high_iop_mechanical_transfer_t1p25_c0p60/figures/piop_vs_delta_pprobe_scatter_5_to_50_step5.png
A	high_iop_mechanical_transfer_t1p25_c0p60/plot_piop_vs_delta_pprobe_5_to_50.py
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_440e44e5_iop_5_to_50_artifact_sha256.txt
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_440e44e5_iop_5_to_50_summary.csv
A	high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_440e44e5_iop_5_to_50_summary.json
M	tests/test_high_iop_preflight.py
```

## 2026-07-30T14:16:12+08:00 · `440e44e` · Prepare five-millimeter IOP supplement through 50

- 完整提交：`440e44e523e87d8248b8eea0a614dc77138c0471`
- 修改文件数：4
- 文件：

```text
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop_5_to_50_supplement_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop_5_to_50_supplement.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_iop_5_to_50.json
M	tests/test_high_iop_preflight.py
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
- 修改文件数：5
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_full_experiment_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_full_high_iop.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec_full.json
M	tests/test_high_iop_preflight.py
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
- 修改文件数：7
- 文件：

```text
M	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
A	high_iop_mechanical_transfer_t1p25_c0p60/launch_iop40_preflight_5090d.sh
A	high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop40_preflight.py
A	high_iop_mechanical_transfer_t1p25_c0p60/run_spec.json
M	src/postprocess/extract_geometry_zero_state.py
M	src/runners/run_indentation_sweep.py
A	tests/test_high_iop_preflight.py
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
R099	thick/experiments/high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md	high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```

## 2026-07-30T11:29:48+08:00 · `4bc0f9f` · Design high-IOP mechanical transfer validation

- 完整提交：`4bc0f9ff21df849da629d09bf0ef95ce7d73aec9`
- 修改文件数：1
- 文件：

```text
A	thick/experiments/high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md
```

## 2026-07-29T19:32:51+08:00 · `590217f` · Add internal-to-GitHub synchronization workflow

- 完整提交：`590217fb7a30fc5b9b27a6e12a16cfb294a5688e`
- 修改文件数：2
- 文件：

```text
A	docs/GIT_REMOTE_SYNC.md
A	ops/sync-main-to-github.sh
```

## 2026-07-29T18:36:46+08:00 · `319b334` · Replace primary IOP table with 0.26 mm states

- 完整提交：`319b334a2f91b8c12146d4ff2857b93d59b04952`
- 修改文件数：7
- 文件：

```text
A	models/apdl/post_geometry_zero_probe_pressure_curve.mac
A	src/postprocess/extract_geometry_zero_state.py
A	thick/code/compare_geometry_zero_0p26_0p28.py
M	thick/docs/0眼压材料基线与Kgeo_5度_IOP换算验证报告.md
A	thick/experiments/geometric_observable_5deg/iop_from_material_baseline_0p26/geometry_zero_0p26_primary_full9.csv
A	thick/experiments/geometric_observable_5deg/iop_from_material_baseline_0p26/geometry_zero_0p26_vs_0p28_full9.csv
A	thick/experiments/geometric_observable_5deg/iop_from_material_baseline_0p26/metadata.json
```

## 2026-07-29T17:55:27+08:00 · `777ef37` · Test zero-IOP baseline additivity across pressures

- 完整提交：`777ef3752bb44c70959fdb539ba6615dc5a8dfca`
- 修改文件数：6
- 文件：

```text
A	thick/code/validate_iop_baseline_additivity.py
M	thick/docs/0眼压材料基线与Kgeo_5度_IOP换算验证报告.md
A	thick/docs/1.25mm多眼压下0眼压基线可加性验证报告.md
A	thick/experiments/iop_baseline_additivity_t1p25/geometry_and_iop_conversion_by_iop.csv
A	thick/experiments/iop_baseline_additivity_t1p25/iop_baseline_additivity_t1p25.csv
A	thick/experiments/iop_baseline_additivity_t1p25/metadata.json
```

## 2026-07-29T17:15:18+08:00 · `4e4bd74` · Add Ae and geometric K to IOP validation table

- 完整提交：`4e4bd74097213d4ac49123664f84762d867e0e3b`
- 修改文件数：1
- 文件：

```text
M	thick/docs/0眼压材料基线与Kgeo_5度_IOP换算验证报告.md
```

## 2026-07-29T16:47:03+08:00 · `cffa10a` · Finalize nine-point zero-IOP baseline validation

- 完整提交：`cffa10a2e16064da7e47ec6cfabe1b903a59c7b5`
- 修改文件数：3
- 文件：

```text
M	thick/docs/0眼压材料基线与Kgeo_5度_IOP换算验证报告.md
M	thick/experiments/geometric_observable_5deg/iop_from_material_baseline/iop_from_kgeo_material_baseline_full9.csv
M	thick/experiments/geometric_observable_5deg/iop_from_material_baseline/metadata.json
```

## 2026-07-29T15:40:19+08:00 · `fcde428` · Validate baseline-corrected geometric IOP conversion

- 完整提交：`fcde428b1af9cf7081fabd31a69f7d6d16317b09`
- 修改文件数：6
- 文件：

```text
A	thick/code/validate_iop_from_kgeo_material_baseline.py
A	thick/docs/0眼压材料基线与Kgeo_5度_IOP换算验证报告.md
A	thick/experiments/geometric_observable_5deg/geometry_zero_server_full9.csv
A	thick/experiments/geometric_observable_5deg/geometry_zero_server_full9_metadata.json
A	thick/experiments/geometric_observable_5deg/iop_from_material_baseline/iop_from_kgeo_material_baseline_full9.csv
A	thick/experiments/geometric_observable_5deg/iop_from_material_baseline/metadata.json
```

## 2026-07-29T14:59:49+08:00 · `447b349` · Allow explicit zero-IOP validation runs

- 完整提交：`447b349f41d1ef26cdb6a3d587fca974735e715a`
- 修改文件数：2
- 文件：

```text
M	models/apdl/param_eye_sweep.mac
M	src/runners/run_indentation_sweep.py
```

## 2026-07-24T19:18:33+08:00 · `17c547a` · Document geometry-based contact zero

- 完整提交：`17c547a2dc3f6bd7f6f5c8005a2193f46db6c070`
- 修改文件数：2
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	thick/README.md
```

## 2026-07-24T18:58:46+08:00 · `371ed27` · Keep indentation load steps continuous

- 完整提交：`371ed27d6a624be7352eb57688f978cbe4b03e2c`
- 修改文件数：3
- 文件：

```text
M	models/apdl/param_eye_sweep.mac
M	models/apdl/post_sweep.mac
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T18:51:53+08:00 · `8271d7a` · Use geometry-based indentation zero

- 完整提交：`8271d7a9840087a1e3f286a620b08a1977f3482a`
- 修改文件数：6
- 文件：

```text
M	models/apdl/param_eye_sweep.mac
M	ops/launch-thickness-sweep-5090d.sh
M	src/postprocess/extract_thickness_state.py
M	src/postprocess/recover_thickness_run.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T18:31:46+08:00 · `4d8d859` · Add contact-rezeroed area results

- 完整提交：`4d8d8596d2a6497229c98672a3f1a41c8cb7a048`
- 修改文件数：62
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	thick/README.md
A	thick/experiments/contact_rezeroed_0p26_0p28/README.md
A	thick/experiments/contact_rezeroed_0p26_0p28/contact_rezeroed_area_summary.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/contact_rezeroed_area_trends.png
A	thick/experiments/contact_rezeroed_0p26_0p28/contact_zero.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/displacement_support_manifest.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/eyelid_0p80mm_effective_indent_0p26mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/eyelid_1p00mm_effective_indent_0p26mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/eyelid_1p20mm_effective_indent_0p26mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/eyelid_1p25mm_effective_indent_0p26mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/eyelid_1p40mm_effective_indent_0p26mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/eyelid_1p50mm_effective_indent_0p26mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support/eyelid_1p60mm_effective_indent_0p26mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/displacement_support_matrix.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/inner_pressure_area/inner_pressure_area_candidate.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/inner_pressure_area/inner_pressure_area_matrix.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/inner_pressure_area/inner_pressure_area_sensitivity.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/inner_pressure_area/inner_pressure_area_trend.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/mechanical_area_comparison.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/mechanical_area_matrix.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/mechanical_area_trend.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/states/eyelid_0p80mm_effective_indent_0p26mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/states/eyelid_1p00mm_effective_indent_0p26mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/states/eyelid_1p20mm_effective_indent_0p26mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/states/eyelid_1p25mm_effective_indent_0p26mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/states/eyelid_1p40mm_effective_indent_0p26mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/states/eyelid_1p50mm_effective_indent_0p26mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/analysis/mechanical_area/states/eyelid_1p60mm_effective_indent_0p26mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p26/run_manifest.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/displacement_support_manifest.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/eyelid_0p80mm_effective_indent_0p28mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/eyelid_1p00mm_effective_indent_0p28mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/eyelid_1p20mm_effective_indent_0p28mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/eyelid_1p25mm_effective_indent_0p28mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/eyelid_1p40mm_effective_indent_0p28mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/eyelid_1p50mm_effective_indent_0p28mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support/eyelid_1p60mm_effective_indent_0p28mm_displacement_support.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/displacement_support_matrix.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/inner_pressure_area/inner_pressure_area_candidate.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/inner_pressure_area/inner_pressure_area_matrix.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/inner_pressure_area/inner_pressure_area_sensitivity.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/inner_pressure_area/inner_pressure_area_trend.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/mechanical_area_comparison.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/mechanical_area_matrix.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/mechanical_area_trend.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/states/eyelid_0p80mm_effective_indent_0p28mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/states/eyelid_1p00mm_effective_indent_0p28mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/states/eyelid_1p20mm_effective_indent_0p28mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/states/eyelid_1p25mm_effective_indent_0p28mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/states/eyelid_1p40mm_effective_indent_0p28mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/states/eyelid_1p50mm_effective_indent_0p28mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/analysis/mechanical_area/states/eyelid_1p60mm_effective_indent_0p28mm_mechanical_area.png
A	thick/experiments/contact_rezeroed_0p26_0p28/effective_0p28/run_manifest.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/history/eyelid_0p80mm_indent_0p28mm.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/history/eyelid_1p00mm_indent_0p28mm.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/history/eyelid_1p20mm_indent_0p28mm.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/history/eyelid_1p25mm_indent_0p28mm.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/history/eyelid_1p40mm_indent_0p28mm.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/history/eyelid_1p50mm_indent_0p28mm.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/history/eyelid_1p60mm_indent_0p28mm.csv
A	thick/experiments/contact_rezeroed_0p26_0p28/metadata.json
```

## 2026-07-24T18:28:21+08:00 · `417a5f2` · Add contact-rezeroed area summary

- 完整提交：`417a5f2812798370b99751664a68bcc1c96615e1`
- 修改文件数：2
- 文件：

```text
A	src/postprocess/summarize_contact_rezeroed.py
A	tests/test_contact_rezero_summary.py
```

## 2026-07-24T18:24:25+08:00 · `aa8e390` · Correct preload contact zero detection

- 完整提交：`aa8e3909aea91847390a5dc6c54f2e08d856ea92`
- 修改文件数：2
- 文件：

```text
M	src/postprocess/extract_contact_rezeroed_states.py
M	tests/test_contact_rezero.py
```

## 2026-07-24T18:17:50+08:00 · `efc748d` · Add contact-rezeroed state extraction

- 完整提交：`efc748dce4a185e66120ea4ec5b51a3506311623`
- 修改文件数：3
- 文件：

```text
A	models/apdl/post_contact_history.mac
A	src/postprocess/extract_contact_rezeroed_states.py
A	tests/test_contact_rezero.py
```

## 2026-07-24T18:00:42+08:00 · `4c9a004` · Document geometric applanation derivation

- 完整提交：`4c9a0049c8727af6232ffb9bb4e3223f733b3c55`
- 修改文件数：1
- 文件：

```text
M	thick/experiments/probe_force_curve_0p8/README.md
```

## 2026-07-24T17:40:11+08:00 · `6a7b571` · Add thickness probe force curve analysis

- 完整提交：`6a7b5718769379ce12b2ca200edd286b429b2d7f`
- 修改文件数：24
- 文件：

```text
M	src/postprocess/analyze_probe_force_curve.py
M	tests/test_probe_force_curve.py
M	thick/README.md
A	thick/experiments/probe_force_curve_0p8/README.md
A	thick/experiments/probe_force_curve_0p8/breakpoint_analysis.csv
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/breakpoint_analysis.csv
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/extraction_metadata.json
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/metadata.json
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/probe_force_curve.csv
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/probe_force_curve.png
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/raw/eyelid_0p80mm.csv
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/raw/eyelid_1p20mm.csv
A	thick/experiments/probe_force_curve_0p8/calibrated_reference/raw/eyelid_2p00mm.csv
A	thick/experiments/probe_force_curve_0p8/extraction_metadata.json
A	thick/experiments/probe_force_curve_0p8/metadata.json
A	thick/experiments/probe_force_curve_0p8/probe_force_curve.csv
A	thick/experiments/probe_force_curve_0p8/probe_force_curve.png
A	thick/experiments/probe_force_curve_0p8/raw/eyelid_0p80mm.csv
A	thick/experiments/probe_force_curve_0p8/raw/eyelid_1p00mm.csv
A	thick/experiments/probe_force_curve_0p8/raw/eyelid_1p20mm.csv
A	thick/experiments/probe_force_curve_0p8/raw/eyelid_1p40mm.csv
A	thick/experiments/probe_force_curve_0p8/raw/eyelid_1p60mm.csv
A	thick/experiments/probe_force_curve_0p8/raw/eyelid_1p80mm.csv
A	thick/experiments/probe_force_curve_0p8/raw/eyelid_2p00mm.csv
```

## 2026-07-24T17:34:21+08:00 · `7db3afd` · Add probe force curve postprocessing

- 完整提交：`7db3afd89c739bf67b4ab949e8643635eff1b7f3`
- 修改文件数：4
- 文件：

```text
A	models/apdl/post_probe_force_curve.mac
A	src/postprocess/analyze_probe_force_curve.py
A	src/postprocess/extract_probe_force_curves.py
A	tests/test_probe_force_curve.py
```

## 2026-07-24T16:47:52+08:00 · `a1c4a83` · Document mechanical area comparison

- 完整提交：`a1c4a839693cf6fbecdfb259d108d1b09e6dcd7b`
- 修改文件数：15
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	thick/README.md
M	thick/docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md
A	thick/experiments/mechanical_area_comparison/README.md
A	thick/experiments/mechanical_area_comparison/mechanical_area_comparison.csv
A	thick/experiments/mechanical_area_comparison/mechanical_area_matrix.png
A	thick/experiments/mechanical_area_comparison/mechanical_area_trend.png
A	thick/experiments/mechanical_area_comparison/states/eyelid_0p80mm_indent_0p28mm_mechanical_area.png
A	thick/experiments/mechanical_area_comparison/states/eyelid_1p00mm_indent_0p28mm_mechanical_area.png
A	thick/experiments/mechanical_area_comparison/states/eyelid_1p20mm_indent_0p28mm_mechanical_area.png
A	thick/experiments/mechanical_area_comparison/states/eyelid_1p25mm_indent_0p28mm_mechanical_area.png
A	thick/experiments/mechanical_area_comparison/states/eyelid_1p40mm_indent_0p28mm_mechanical_area.png
A	thick/experiments/mechanical_area_comparison/states/eyelid_1p50mm_indent_0p28mm_mechanical_area.png
A	thick/experiments/mechanical_area_comparison/states/eyelid_1p60mm_indent_0p28mm_mechanical_area.png
```

## 2026-07-24T16:40:20+08:00 · `9c4539f` · Add pressure-based area comparison

- 完整提交：`9c4539f76d1eb82f71614bf6018393e439bac936`
- 修改文件数：4
- 文件：

```text
M	models/apdl/post_thickness_geometry.mac
M	src/postprocess/analyze_inner_pressure_area.py
A	src/postprocess/analyze_mechanical_area_comparison.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T16:21:21+08:00 · `e46f37d` · Organize flat region angle sweep experiment

- 完整提交：`e46f37dee95c8356d34c064e9fd1e18fa3d7bf50`
- 修改文件数：197
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/plot_flat_region_2deg.py
M	thick/README.md
M	thick/docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md
A	thick/experiments/flat_region_angle_sweep/README.md
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_0p80mm_indent_0p28mm_flat_region_0p5deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_0p80mm_indent_0p28mm_flat_region_0p5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p00mm_indent_0p28mm_flat_region_0p5deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p00mm_indent_0p28mm_flat_region_0p5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p20mm_indent_0p28mm_flat_region_0p5deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p20mm_indent_0p28mm_flat_region_0p5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p25mm_indent_0p28mm_flat_region_0p5deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p25mm_indent_0p28mm_flat_region_0p5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p40mm_indent_0p28mm_flat_region_0p5deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p40mm_indent_0p28mm_flat_region_0p5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p50mm_indent_0p28mm_flat_region_0p5deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p50mm_indent_0p28mm_flat_region_0p5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p60mm_indent_0p28mm_flat_region_0p5deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/eyelid_1p60mm_indent_0p28mm_flat_region_0p5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg/flat_region_0p5deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_0p5deg_multiview_matrix.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_0p80mm_indent_0p28mm_flat_region_10deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_0p80mm_indent_0p28mm_flat_region_10deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_0p80mm_indent_0p28mm_flat_region_10deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_0p80mm_indent_0p28mm_flat_region_10deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p00mm_indent_0p28mm_flat_region_10deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p00mm_indent_0p28mm_flat_region_10deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p00mm_indent_0p28mm_flat_region_10deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p00mm_indent_0p28mm_flat_region_10deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p20mm_indent_0p28mm_flat_region_10deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p20mm_indent_0p28mm_flat_region_10deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p20mm_indent_0p28mm_flat_region_10deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p20mm_indent_0p28mm_flat_region_10deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p25mm_indent_0p28mm_flat_region_10deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p25mm_indent_0p28mm_flat_region_10deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p25mm_indent_0p28mm_flat_region_10deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p25mm_indent_0p28mm_flat_region_10deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p40mm_indent_0p28mm_flat_region_10deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p40mm_indent_0p28mm_flat_region_10deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p40mm_indent_0p28mm_flat_region_10deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p40mm_indent_0p28mm_flat_region_10deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p50mm_indent_0p28mm_flat_region_10deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p50mm_indent_0p28mm_flat_region_10deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p50mm_indent_0p28mm_flat_region_10deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p50mm_indent_0p28mm_flat_region_10deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p60mm_indent_0p28mm_flat_region_10deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p60mm_indent_0p28mm_flat_region_10deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p60mm_indent_0p28mm_flat_region_10deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/eyelid_1p60mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg/flat_region_10deg_manifest.csv
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg_matrix.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg_matrix.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_10deg_multiview_matrix.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_10deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_0p80mm_indent_0p28mm_flat_region_1deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_0p80mm_indent_0p28mm_flat_region_1deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p00mm_indent_0p28mm_flat_region_1deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p00mm_indent_0p28mm_flat_region_1deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p20mm_indent_0p28mm_flat_region_1deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p20mm_indent_0p28mm_flat_region_1deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p25mm_indent_0p28mm_flat_region_1deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p25mm_indent_0p28mm_flat_region_1deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p40mm_indent_0p28mm_flat_region_1deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p40mm_indent_0p28mm_flat_region_1deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p50mm_indent_0p28mm_flat_region_1deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p50mm_indent_0p28mm_flat_region_1deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p60mm_indent_0p28mm_flat_region_1deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/eyelid_1p60mm_indent_0p28mm_flat_region_1deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg/flat_region_1deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_1deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_0p80mm_indent_0p28mm_flat_region_2deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_0p80mm_indent_0p28mm_flat_region_2deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p00mm_indent_0p28mm_flat_region_2deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p00mm_indent_0p28mm_flat_region_2deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p20mm_indent_0p28mm_flat_region_2deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p20mm_indent_0p28mm_flat_region_2deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p25mm_indent_0p28mm_flat_region_2deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p25mm_indent_0p28mm_flat_region_2deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p40mm_indent_0p28mm_flat_region_2deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p40mm_indent_0p28mm_flat_region_2deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p50mm_indent_0p28mm_flat_region_2deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p50mm_indent_0p28mm_flat_region_2deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p60mm_indent_0p28mm_flat_region_2deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/eyelid_1p60mm_indent_0p28mm_flat_region_2deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg/flat_region_2deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_2deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_0p80mm_indent_0p28mm_flat_region_3deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_0p80mm_indent_0p28mm_flat_region_3deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p00mm_indent_0p28mm_flat_region_3deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p00mm_indent_0p28mm_flat_region_3deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p20mm_indent_0p28mm_flat_region_3deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p20mm_indent_0p28mm_flat_region_3deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p25mm_indent_0p28mm_flat_region_3deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p25mm_indent_0p28mm_flat_region_3deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p40mm_indent_0p28mm_flat_region_3deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p40mm_indent_0p28mm_flat_region_3deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p50mm_indent_0p28mm_flat_region_3deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p50mm_indent_0p28mm_flat_region_3deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p60mm_indent_0p28mm_flat_region_3deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/eyelid_1p60mm_indent_0p28mm_flat_region_3deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg/flat_region_3deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_3deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_0p80mm_indent_0p28mm_flat_region_4deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_0p80mm_indent_0p28mm_flat_region_4deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p00mm_indent_0p28mm_flat_region_4deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p00mm_indent_0p28mm_flat_region_4deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p20mm_indent_0p28mm_flat_region_4deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p20mm_indent_0p28mm_flat_region_4deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p25mm_indent_0p28mm_flat_region_4deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p25mm_indent_0p28mm_flat_region_4deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p40mm_indent_0p28mm_flat_region_4deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p40mm_indent_0p28mm_flat_region_4deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p50mm_indent_0p28mm_flat_region_4deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p50mm_indent_0p28mm_flat_region_4deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p60mm_indent_0p28mm_flat_region_4deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/eyelid_1p60mm_indent_0p28mm_flat_region_4deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg/flat_region_4deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_4deg_multiview_matrix.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_0p80mm_indent_0p28mm_flat_region_5deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_0p80mm_indent_0p28mm_flat_region_5deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_0p80mm_indent_0p28mm_flat_region_5deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_0p80mm_indent_0p28mm_flat_region_5deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p00mm_indent_0p28mm_flat_region_5deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p00mm_indent_0p28mm_flat_region_5deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p00mm_indent_0p28mm_flat_region_5deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p00mm_indent_0p28mm_flat_region_5deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p20mm_indent_0p28mm_flat_region_5deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p20mm_indent_0p28mm_flat_region_5deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p20mm_indent_0p28mm_flat_region_5deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p20mm_indent_0p28mm_flat_region_5deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p25mm_indent_0p28mm_flat_region_5deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p25mm_indent_0p28mm_flat_region_5deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p25mm_indent_0p28mm_flat_region_5deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p25mm_indent_0p28mm_flat_region_5deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p40mm_indent_0p28mm_flat_region_5deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p40mm_indent_0p28mm_flat_region_5deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p40mm_indent_0p28mm_flat_region_5deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p40mm_indent_0p28mm_flat_region_5deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p50mm_indent_0p28mm_flat_region_5deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p50mm_indent_0p28mm_flat_region_5deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p50mm_indent_0p28mm_flat_region_5deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p50mm_indent_0p28mm_flat_region_5deg_multiview.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p60mm_indent_0p28mm_flat_region_5deg.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p60mm_indent_0p28mm_flat_region_5deg.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p60mm_indent_0p28mm_flat_region_5deg_multiview.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/eyelid_1p60mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg/flat_region_5deg_manifest.csv
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg_matrix.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg_matrix.png
R100	thick/figures/fe_sweep_indent_0p28/flat_region_5deg_multiview_matrix.png	thick/experiments/flat_region_angle_sweep/figures/flat_region_5deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_0p80mm_indent_0p28mm_flat_region_6deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_0p80mm_indent_0p28mm_flat_region_6deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p00mm_indent_0p28mm_flat_region_6deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p00mm_indent_0p28mm_flat_region_6deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p20mm_indent_0p28mm_flat_region_6deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p20mm_indent_0p28mm_flat_region_6deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p25mm_indent_0p28mm_flat_region_6deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p25mm_indent_0p28mm_flat_region_6deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p40mm_indent_0p28mm_flat_region_6deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p40mm_indent_0p28mm_flat_region_6deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p50mm_indent_0p28mm_flat_region_6deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p50mm_indent_0p28mm_flat_region_6deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p60mm_indent_0p28mm_flat_region_6deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/eyelid_1p60mm_indent_0p28mm_flat_region_6deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg/flat_region_6deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_6deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_0p80mm_indent_0p28mm_flat_region_7deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_0p80mm_indent_0p28mm_flat_region_7deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p00mm_indent_0p28mm_flat_region_7deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p00mm_indent_0p28mm_flat_region_7deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p20mm_indent_0p28mm_flat_region_7deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p20mm_indent_0p28mm_flat_region_7deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p25mm_indent_0p28mm_flat_region_7deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p25mm_indent_0p28mm_flat_region_7deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p40mm_indent_0p28mm_flat_region_7deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p40mm_indent_0p28mm_flat_region_7deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p50mm_indent_0p28mm_flat_region_7deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p50mm_indent_0p28mm_flat_region_7deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p60mm_indent_0p28mm_flat_region_7deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/eyelid_1p60mm_indent_0p28mm_flat_region_7deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg/flat_region_7deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_7deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_0p80mm_indent_0p28mm_flat_region_8deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_0p80mm_indent_0p28mm_flat_region_8deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p00mm_indent_0p28mm_flat_region_8deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p00mm_indent_0p28mm_flat_region_8deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p20mm_indent_0p28mm_flat_region_8deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p20mm_indent_0p28mm_flat_region_8deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p25mm_indent_0p28mm_flat_region_8deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p25mm_indent_0p28mm_flat_region_8deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p40mm_indent_0p28mm_flat_region_8deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p40mm_indent_0p28mm_flat_region_8deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p50mm_indent_0p28mm_flat_region_8deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p50mm_indent_0p28mm_flat_region_8deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p60mm_indent_0p28mm_flat_region_8deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/eyelid_1p60mm_indent_0p28mm_flat_region_8deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg/flat_region_8deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_8deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_0p80mm_indent_0p28mm_flat_region_9deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_0p80mm_indent_0p28mm_flat_region_9deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p00mm_indent_0p28mm_flat_region_9deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p00mm_indent_0p28mm_flat_region_9deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p20mm_indent_0p28mm_flat_region_9deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p20mm_indent_0p28mm_flat_region_9deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p25mm_indent_0p28mm_flat_region_9deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p25mm_indent_0p28mm_flat_region_9deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p40mm_indent_0p28mm_flat_region_9deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p40mm_indent_0p28mm_flat_region_9deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p50mm_indent_0p28mm_flat_region_9deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p50mm_indent_0p28mm_flat_region_9deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p60mm_indent_0p28mm_flat_region_9deg.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/eyelid_1p60mm_indent_0p28mm_flat_region_9deg_multiview.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg/flat_region_9deg_manifest.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_9deg_multiview_matrix.png
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_angle_sweep.csv
A	thick/experiments/flat_region_angle_sweep/figures/flat_region_angle_sweep.png
D	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/flat_region_10deg_manifest.csv
D	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/flat_region_5deg_manifest.csv
```

## 2026-07-24T16:10:58+08:00 · `da93eb5` · Handle empty angle sweep ratios

- 完整提交：`da93eb548e827248607c38d9afda4fdb203ad7fe`
- 修改文件数：2
- 文件：

```text
M	src/postprocess/plot_flat_region_2deg.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T16:09:37+08:00 · `c34a57b` · Summarize flat region angle sweeps

- 完整提交：`c34a57ba066d6c08abc67f0cd6d45b2a7d024306`
- 修改文件数：2
- 文件：

```text
M	src/postprocess/plot_flat_region_2deg.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T15:56:04+08:00 · `48b3a34` · Add five and ten degree flat region diagnostics

- 完整提交：`48b3a34a3466e30ae9c0af7b6fd23006faddb2c8`
- 修改文件数：38
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	thick/README.md
M	thick/docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_0p80mm_indent_0p28mm_flat_region_10deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_0p80mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p00mm_indent_0p28mm_flat_region_10deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p00mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p20mm_indent_0p28mm_flat_region_10deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p20mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p25mm_indent_0p28mm_flat_region_10deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p25mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p40mm_indent_0p28mm_flat_region_10deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p40mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p50mm_indent_0p28mm_flat_region_10deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p50mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p60mm_indent_0p28mm_flat_region_10deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/eyelid_1p60mm_indent_0p28mm_flat_region_10deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg/flat_region_10deg_manifest.csv
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg_matrix.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_10deg_multiview_matrix.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_0p80mm_indent_0p28mm_flat_region_5deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_0p80mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p00mm_indent_0p28mm_flat_region_5deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p00mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p20mm_indent_0p28mm_flat_region_5deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p20mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p25mm_indent_0p28mm_flat_region_5deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p25mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p40mm_indent_0p28mm_flat_region_5deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p40mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p50mm_indent_0p28mm_flat_region_5deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p50mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p60mm_indent_0p28mm_flat_region_5deg.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/eyelid_1p60mm_indent_0p28mm_flat_region_5deg_multiview.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg/flat_region_5deg_manifest.csv
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg_matrix.png
A	thick/figures/fe_sweep_indent_0p28/flat_region_5deg_multiview_matrix.png
```

## 2026-07-24T15:42:20+08:00 · `a8c14c5` · Update inner pressure mesh visualizations

- 完整提交：`a8c14c59393aa2caf673d0a12a5080701bdf52fd`
- 修改文件数：8
- 文件：

```text
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_0p80mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p00mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p20mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p25mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p40mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p50mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p60mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support_matrix.png
```

## 2026-07-24T15:40:56+08:00 · `8f22b14` · Render inner pressure selection on surface mesh

- 完整提交：`8f22b1407ef0ea474f2174223051bb57abdce26c`
- 修改文件数：4
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/plot_displacement_support.py
M	tests/test_sweep_pipeline.py
M	thick/docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md
```

## 2026-07-24T15:24:18+08:00 · `7f46a98` · Update Ae Ac comparison matrix

- 完整提交：`7f46a98150693e282463a2aab02b778059f6cfac`
- 修改文件数：9
- 文件：

```text
M	thick/figures/fe_sweep_indent_0p28/displacement_support/displacement_support_manifest.csv
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_0p80mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p00mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p20mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p25mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p40mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p50mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p60mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support_matrix.png
```

## 2026-07-24T15:22:51+08:00 · `578ff20` · Label Ae Ac comparison outputs

- 完整提交：`578ff20ac04ecda034846791833a25437ddbce66`
- 修改文件数：3
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/plot_displacement_support.py
M	thick/docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md
```

## 2026-07-24T15:19:56+08:00 · `8824be9` · Render current inner pressure area in comparison maps

- 完整提交：`8824be99b30b16b0995b8ec37215d16da3d2e24d`
- 修改文件数：1
- 文件：

```text
M	src/postprocess/plot_displacement_support.py
```

## 2026-07-24T15:15:45+08:00 · `62b7554` · Refactor thickness area calibration docs

- 完整提交：`62b7554ce28ffce5c8ac7e494e7cc00cc84dbeed`
- 修改文件数：5
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	thick/README.md
M	thick/data/processed/fe_sweep_indent_0p26/README.md
D	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
A	thick/docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md
```

## 2026-07-24T15:07:57+08:00 · `cfc2eee` · Update conservative support visualizations

- 完整提交：`cfc2eee31f0fb9b362f8a30c1208c779870d90fc`
- 修改文件数：12
- 文件：

```text
M	thick/figures/fe_sweep_indent_0p28/displacement_support/displacement_support_manifest.csv
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_0p80mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p00mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p20mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p25mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p40mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p50mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p60mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support_matrix.png
M	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_candidate.csv
M	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_sensitivity.csv
M	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_trend.png
```

## 2026-07-24T15:07:23+08:00 · `0b28a76` · Document conservative external area bound

- 完整提交：`0b28a765b3c3215e419ecde7858f402aecceed65`
- 修改文件数：2
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/analyze_inner_pressure_area.py
```

## 2026-07-24T15:04:25+08:00 · `7e20cc1` · Use conservative outer support lower bound

- 完整提交：`7e20cc1aca2777482128ea454a562bfe1f152397`
- 修改文件数：4
- 文件：

```text
M	src/postprocess/analyze_inner_pressure_area.py
M	src/postprocess/plot_displacement_support.py
M	src/postprocess/thickness_geometry.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T14:56:07+08:00 · `3962e91` · Update hybrid area results

- 完整提交：`3962e914e3b7606ed841601cb78c99d22961b131`
- 修改文件数：4
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_candidate.csv
M	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_sensitivity.csv
M	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_trend.png
```

## 2026-07-24T14:55:06+08:00 · `d7da26a` · Combine outer coverage with inner pressure area

- 完整提交：`d7da26a5e388f2c6b556135c2af8743e70bb04c0`
- 修改文件数：3
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/analyze_inner_pressure_area.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T14:14:41+08:00 · `8136fb1` · Add inner area calibration results

- 完整提交：`8136fb18519de0e076b925328dd96ab0373826d8`
- 修改文件数：9
- 文件：

```text
A	thick/figures/fe_sweep_indent_0p28/inner_planarity_calibration/calibrated_area_vs_thickness.png
A	thick/figures/fe_sweep_indent_0p28/inner_planarity_calibration/calibration_grid.csv
A	thick/figures/fe_sweep_indent_0p28/inner_planarity_calibration/inner_planarity_candidate.csv
A	thick/figures/fe_sweep_indent_0p28/inner_planarity_calibration/inner_planarity_candidate_matrix.png
A	thick/figures/fe_sweep_indent_0p28/inner_planarity_calibration/outer_contact_calibration_heatmap.png
A	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_candidate.csv
A	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_matrix.png
A	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_sensitivity.csv
A	thick/figures/fe_sweep_indent_0p28/inner_pressure_area/inner_pressure_area_trend.png
```

## 2026-07-24T14:13:46+08:00 · `31a410d` · Document pressure-based inner area candidate

- 完整提交：`31a410dadcd4fd6855aaee0a7f2af8df1e33b44f`
- 修改文件数：2
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/analyze_inner_pressure_area.py
```

## 2026-07-24T14:10:49+08:00 · `0e4b142` · Analyze inner pressure participation area

- 完整提交：`0e4b1427948258815e4217eea79655c79d3cb15d`
- 修改文件数：3
- 文件：

```text
M	models/apdl/post_thickness_geometry.mac
A	src/postprocess/analyze_inner_pressure_area.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T14:05:15+08:00 · `9ee3ac7` · Export bonded interface pressure states

- 完整提交：`9ee3ac76d9a010a2de277dcdd536ec72579d8709`
- 修改文件数：2
- 文件：

```text
M	models/apdl/post_thickness_geometry.mac
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T13:59:06+08:00 · `fcf8f01` · Calibrate contact-equivalent inner area

- 完整提交：`fcf8f01ef4a3d257cd402b0aa088c9f5125e6526`
- 修改文件数：2
- 文件：

```text
M	src/postprocess/calibrate_inner_planarity.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T13:53:39+08:00 · `3c02e13` · Weight planarity area by curvature reduction

- 完整提交：`3c02e13c02db34732ca980f354f5da65cd0bce4b`
- 修改文件数：2
- 文件：

```text
M	src/postprocess/calibrate_inner_planarity.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T13:48:50+08:00 · `01b7f52` · Calibrate inner planarity from outer contact

- 完整提交：`01b7f52751f67ed4750e6136e7c34e69e2e6e90b`
- 修改文件数：3
- 文件：

```text
A	src/postprocess/calibrate_inner_planarity.py
M	src/postprocess/plot_inner_planarity_trial.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T13:44:13+08:00 · `d8e7428` · Export outer contact calibration state

- 完整提交：`d8e742826382d07ed31add1ac027a598128638bf`
- 修改文件数：2
- 文件：

```text
M	models/apdl/post_thickness_geometry.mac
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T12:57:29+08:00 · `2e13008` · Add inner planarity trial results

- 完整提交：`2e13008aed36ca40d0ae1addb51115d533ef1faa`
- 修改文件数：3
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
A	thick/figures/fe_sweep_indent_0p28/inner_planarity_trial/inner_planarity_trial.csv
A	thick/figures/fe_sweep_indent_0p28/inner_planarity_trial/inner_planarity_trial_matrix.png
```

## 2026-07-24T12:56:19+08:00 · `a04a34a` · Add inner planarity trial maps

- 完整提交：`a04a34a649a0479f4f872bf55fd17dc6eceeb4bf`
- 修改文件数：2
- 文件：

```text
A	src/postprocess/plot_inner_planarity_trial.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T12:46:13+08:00 · `beda558` · Document inner surface displacement diagnosis

- 完整提交：`beda558c8cbdd24211a338e39615deeb1cda886e`
- 修改文件数：13
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
A	thick/figures/fe_sweep_indent_0p28/displacement_probes/displacement_probe_profiles.csv
A	thick/figures/fe_sweep_indent_0p28/displacement_probes/displacement_probe_profiles.png
A	thick/figures/fe_sweep_indent_0p28/displacement_probes/displacement_probe_summary.csv
M	thick/figures/fe_sweep_indent_0p28/displacement_support/displacement_support_manifest.csv
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_0p80mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p00mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p20mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p25mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p40mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p50mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p60mm_indent_0p28mm_displacement_support.png
M	thick/figures/fe_sweep_indent_0p28/displacement_support_matrix.png
```

## 2026-07-24T12:40:18+08:00 · `96cf6d6` · Export eyelid side of bonded interface

- 完整提交：`96cf6d655faafb00a4394a12f50d78b5e5e8738c`
- 修改文件数：2
- 文件：

```text
M	models/apdl/post_thickness_geometry.mac
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T12:37:41+08:00 · `05da60d` · Add radial displacement probe diagnostics

- 完整提交：`05da60d8198541531db95b03d89f978d5cdd0077`
- 修改文件数：1
- 文件：

```text
A	src/postprocess/plot_displacement_probe_profiles.py
```

## 2026-07-24T12:29:35+08:00 · `1142cf8` · Add 0.28 mm displacement support matrix

- 完整提交：`1142cf8794a292b1bba352ea1a95429a238aa055`
- 修改文件数：9
- 文件：

```text
A	thick/figures/fe_sweep_indent_0p28/displacement_support/displacement_support_manifest.csv
A	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_0p80mm_indent_0p28mm_displacement_support.png
A	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p00mm_indent_0p28mm_displacement_support.png
A	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p20mm_indent_0p28mm_displacement_support.png
A	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p25mm_indent_0p28mm_displacement_support.png
A	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p40mm_indent_0p28mm_displacement_support.png
A	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p50mm_indent_0p28mm_displacement_support.png
A	thick/figures/fe_sweep_indent_0p28/displacement_support/eyelid_1p60mm_indent_0p28mm_displacement_support.png
A	thick/figures/fe_sweep_indent_0p28/displacement_support_matrix.png
```

## 2026-07-24T12:29:01+08:00 · `99af8f3` · Document displacement support diagnostics

- 完整提交：`99af8f39995da62a08917c63eebb33036be88502`
- 修改文件数：3
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/thickness_geometry.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T12:26:59+08:00 · `678bc84` · Add robust displacement support maps

- 完整提交：`678bc849b6b9ecc74f78d8760a87e3750a705f9e`
- 修改文件数：3
- 文件：

```text
A	src/postprocess/plot_displacement_support.py
M	src/postprocess/thickness_geometry.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-24T11:25:59+08:00 · `5984fe5` · docs: specify deformation-based thickness area metric

- 完整提交：`5984fe5a2b32c73e7eed071897165037fb04d57c`
- 修改文件数：7
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/extract_thickness_state.py
M	src/postprocess/plot_flat_region_2deg.py
M	src/postprocess/summarize_thickness_sweep.py
M	src/postprocess/thickness_geometry.py
M	tests/test_sweep_pipeline.py
M	thick/README.md
```

## 2026-07-23T22:39:10+08:00 · `f4c7dab` · fix: remove spherical proxy from thickness area metrics

- 完整提交：`f4c7dabedffd9ab620ffa6071328d51facd58aae`
- 修改文件数：13
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	ops/start-thickness-calibration-5090d.sh
M	src/postprocess/summarize_thickness_sweep.py
M	src/runners/run_thickness_calibration.py
M	tests/test_sweep_pipeline.py
M	thick/README.md
M	thick/data/processed/fe_sweep_indent_0p26/README.md
M	thick/data/processed/fe_sweep_indent_0p26/summary.csv
M	thick/data/processed/fe_sweep_indent_0p26/trend_analysis.json
M	thick/docs/Ae_Ac实验差异与材料及眼压参数评估.md
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
M	thick/docs/眼睑厚度有限元实验报告.md
```

## 2026-07-23T22:16:14+08:00 · `ea6c207` · docs: document flat-area metric limitations

- 完整提交：`ea6c207d9b23e17b49e5b43737a821fe6121c658`
- 修改文件数：6
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	thick/README.md
M	thick/docs/Ae_Ac实验差异与材料及眼压参数评估.md
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
M	thick/docs/眼睑厚度有限元实验报告.md
```

## 2026-07-23T21:28:39+08:00 · `e2c8fa0` · thick: render flat-region angle sensitivity views

- 完整提交：`e2c8fa0104b78e2a60db3e9e01e4f709b2a338fe`
- 修改文件数：2
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/plot_flat_region_2deg.py
```

## 2026-07-23T20:24:07+08:00 · `46d3eac` · thick: render true center section for flat regions

- 完整提交：`46d3eac031e6f746f45adc2423b1803141904c93`
- 修改文件数：1
- 文件：

```text
M	src/postprocess/plot_flat_region_2deg.py
```

## 2026-07-23T20:21:59+08:00 · `40c0502` · thick: add 3D multiview flat-region plots

- 完整提交：`40c0502e1c91ee2c9020189ccb64b738d547a8d4`
- 修改文件数：1
- 文件：

```text
M	src/postprocess/plot_flat_region_2deg.py
```

## 2026-07-23T20:15:48+08:00 · `f888ddf` · thick: render objective 2 degree flat regions

- 完整提交：`f888ddf1bf750234693a54d1eeec3280040251fa`
- 修改文件数：3
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
A	src/postprocess/plot_flat_region_2deg.py
M	src/postprocess/thickness_geometry.py
```

## 2026-07-23T19:42:21+08:00 · `973a834` · thick: use objective flat area at 0.28 mm

- 完整提交：`973a834aa6797f9ffe729c6f24eb2e91db2196fc`
- 修改文件数：14
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	ops/launch-thickness-sweep-5090d.sh
M	ops/start-thickness-calibration-5090d.sh
M	src/postprocess/build_thickness_view_matrix.py
M	src/postprocess/extract_thickness_state.py
M	src/postprocess/extract_thickness_strain_views.py
M	src/postprocess/summarize_thickness_sweep.py
M	src/postprocess/thickness_geometry.py
M	src/runners/run_indentation_sweep.py
M	src/runners/run_thickness_calibration.py
M	tests/test_sweep_pipeline.py
M	thick/README.md
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
```

## 2026-07-23T18:55:24+08:00 · `ac8f483` · thick: anchor GAT area to spherical geometry

- 完整提交：`ac8f483851ab39754ec45f681179ea6ab7bc63a5`
- 修改文件数：18
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/summarize_thickness_sweep.py
M	src/runners/run_thickness_calibration.py
M	tests/test_sweep_pipeline.py
M	thick/data/processed/fe_sweep_indent_0p26/README.md
M	thick/data/processed/fe_sweep_indent_0p26/qc.json
M	thick/data/processed/fe_sweep_indent_0p26/summary.csv
M	thick/data/processed/fe_sweep_indent_0p26/trend_analysis.json
M	thick/docs/Ae_Ac实验差异与材料及眼压参数评估.md
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
M	thick/docs/眼睑厚度有限元实验报告.md
M	thick/figures/fe_sweep_indent_0p26/trends/area_ratio_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/equivalent_diameter_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/force_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/inner_area_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/outer_area_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/pressure_vs_thickness.png
```

## 2026-07-23T18:33:33+08:00 · `bbfefe8` · thick: locate full contact endpoint

- 完整提交：`bbfefe8de8b98af98a2c9ef6e4f214fc757ec978`
- 修改文件数：7
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	thick/data/processed/fe_sweep_indent_0p26/README.md
A	thick/data/processed/fe_sweep_indent_0p26/contact_endpoint_scan.csv
M	thick/docs/Ae_Ac实验差异与材料及眼压参数评估.md
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
A	thick/figures/fe_sweep_indent_0p26/trends/contact_fill_vs_indent.png
```

## 2026-07-23T18:15:58+08:00 · `9fc9405` · thick: publish breakpoint area results

- 完整提交：`9fc940534c51968dd32edf1c4aee6fff1f89ede5`
- 修改文件数：45
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/THICKNESS_CALIBRATION.md
M	src/postprocess/build_thickness_view_matrix.py
M	thick/README.md
M	thick/data/processed/fe_sweep_indent_0p26/README.md
M	thick/data/processed/fe_sweep_indent_0p26/manifest.csv
M	thick/data/processed/fe_sweep_indent_0p26/metadata.json
M	thick/data/processed/fe_sweep_indent_0p26/qc.json
M	thick/data/processed/fe_sweep_indent_0p26/summary.csv
M	thick/data/processed/fe_sweep_indent_0p26/trend_analysis.json
M	thick/docs/Ae_Ac实验差异与材料及眼压参数评估.md
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
A	thick/figures/fe_sweep_indent_0p26/trends/applanation_boundary_matrix.png
M	thick/figures/fe_sweep_indent_0p26/trends/area_ratio_vs_thickness.png
A	thick/figures/fe_sweep_indent_0p26/trends/equivalent_diameter_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/inner_area_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/outer_area_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/views/README.md
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p25mm_indent_0p26mm/eyelid_1p25mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p50mm_indent_0p26mm/eyelid_1p50mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/applanation_boundary_qc.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/applanation_boundary_qc.png
```

## 2026-07-23T17:59:36+08:00 · `bf30a99` · thick: shorten extracted-state job names

- 完整提交：`bf30a9930337f3e96e11dc6798a50ed160c097f2`
- 修改文件数：2
- 文件：

```text
M	src/postprocess/extract_thickness_state.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-23T16:58:20+08:00 · `1dd9957` · thick: retain converged source results

- 完整提交：`1dd9957534cce6738885a9302b9bc4ac8b21669a`
- 修改文件数：5
- 文件：

```text
M	src/postprocess/build_thickness_view_matrix.py
M	src/postprocess/summarize_thickness_sweep.py
M	src/postprocess/thickness_geometry.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-23T15:50:33+08:00 · `9cc1e7c` · thick: expose applanation scale sensitivity

- 完整提交：`9cc1e7c8803706fa87982e230b4deaca6b2d677b`
- 修改文件数：3
- 文件：

```text
M	src/postprocess/summarize_thickness_sweep.py
M	src/postprocess/thickness_geometry.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-23T15:41:47+08:00 · `29d268a` · thick: measure breakpoint surface areas

- 完整提交：`29d268ad3ad34a146586fd3595b105070ab7446a`
- 修改文件数：9
- 文件：

```text
M	models/apdl/post_thickness_geometry.mac
M	src/postprocess/extract_thickness_state.py
M	src/postprocess/recover_thickness_run.py
M	src/postprocess/reprocess_thickness_geometry.py
M	src/postprocess/summarize_thickness_sweep.py
M	src/postprocess/thickness_geometry.py
M	src/runners/run_indentation_sweep.py
M	src/runners/run_thickness_calibration.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-23T12:19:00+08:00 · `78ad7a2` · data: invert Dryad corneal material curves

- 完整提交：`78ad7a219e8a5b737cca37ed8325d171cebc80ab`
- 修改文件数：27
- 文件：

```text
M	data/README.md
M	data/build_dataset.py
M	data/dryad_file_manifest.csv
A	data/dryad_pressure_displacement.csv
A	data/dryad_pressure_displacement_validation.csv
A	data/dryad_stress_strain_workbook_qc.csv
A	data/figures/dryad_inverse_qc.png
A	data/figures/dryad_pressure_displacement.png
A	data/figures/mooney_rivlin_inverse_fits.png
A	data/mooney_rivlin_inverse_parameters.csv
A	data/mooney_rivlin_inverse_summary.csv
A	data/raw/dryad_z8w9ghx9f/EYE1_target_curve_before_after_CXL.xlsx
A	data/raw/dryad_z8w9ghx9f/EYE2_target_curve_before_after_CXL.xlsx
A	data/raw/dryad_z8w9ghx9f/EYE3_target_curve_before_after_CXL.xlsx
A	data/raw/dryad_z8w9ghx9f/EYE4_target_curve_before_after_CXL.xlsx
A	data/raw/dryad_z8w9ghx9f/EYE5_target_curve_before_after_CXL.xlsx
A	data/raw/dryad_z8w9ghx9f/EYE6_target_curve_before_after_CXL.xlsx
A	data/raw/dryad_z8w9ghx9f/EYE7_target_cuve_before_after_CXL.xlsx
M	data/raw/dryad_z8w9ghx9f/README.md
A	data/raw/dryad_z8w9ghx9f/Tangent_(Et)_vs_stress_curve.xlsx
A	data/raw/dryad_z8w9ghx9f/eye1_stressvsstrain.xlsx
A	data/raw/dryad_z8w9ghx9f/eye2_stressvsstrain.xlsx
A	data/raw/dryad_z8w9ghx9f/eye3_stressvsstrain.xlsx
A	data/raw/dryad_z8w9ghx9f/eye4_stressvsstrain.xlsx
A	data/raw/dryad_z8w9ghx9f/eye5_stressvsstrain.xlsx
A	data/raw/dryad_z8w9ghx9f/eye6_stressvsstrain.xlsx
A	data/raw/dryad_z8w9ghx9f/eye7_stressvsstrain.xlsx
```

## 2026-07-22T14:22:06+08:00 · `9dd612d` · data: add corneal inversion literature benchmarks

- 完整提交：`9dd612d408913fe109ae8a725a9317718d78c974`
- 修改文件数：19
- 文件：

```text
A	data/README.md
A	data/build_dataset.py
A	data/cid_group_metrics.csv
A	data/cid_repeatability.csv
A	data/current_model_benchmark.csv
A	data/dryad_file_manifest.csv
A	data/figures/cid_human_benchmark.png
A	data/figures/human_age_stress_strain.png
A	data/figures/human_oce_anisotropy.png
A	data/figures/porcine_ogden_pairs.png
A	data/human_age_reference_points.csv
A	data/human_age_stress_strain.csv
A	data/human_oce_anisotropy.csv
A	data/inverse_targets.csv
A	data/metric_priority.csv
A	data/porcine_inflation_summary.csv
A	data/porcine_ogden_parameters.csv
A	data/raw/dryad_z8w9ghx9f/README.md
A	data/sources.csv
```

## 2026-07-22T10:43:42+08:00 · `5e0c776` · docs: publish calibrated thickness results

- 完整提交：`5e0c776823b9f4873cf9d61f304f9c92e77a00c0`
- 修改文件数：73
- 文件：

```text
M	docs/THICKNESS_CALIBRATION.md
M	thick/README.md
M	thick/data/processed/fe_sweep_indent_0p26/README.md
M	thick/data/processed/fe_sweep_indent_0p26/indent_comparison.csv
M	thick/data/processed/fe_sweep_indent_0p26/manifest.csv
M	thick/data/processed/fe_sweep_indent_0p26/metadata.json
M	thick/data/processed/fe_sweep_indent_0p26/qc.json
M	thick/data/processed/fe_sweep_indent_0p26/summary.csv
M	thick/data/processed/fe_sweep_indent_0p26/trend_analysis.json
M	thick/docs/Ae_Ac实验差异与材料及眼压参数评估.md
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
M	thick/figures/fe_sweep_indent_0p26/trends/area_ratio_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/force_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/inner_area_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/outer_area_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/trends/pressure_vs_thickness.png
M	thick/figures/fe_sweep_indent_0p26/views/README.md
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm001.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm002.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm003.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm004.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm005.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm006.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm008.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm001.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm002.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm003.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm004.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm005.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm006.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm008.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm001.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm002.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm003.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm004.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm005.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm006.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm008.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm001.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm002.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm003.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm004.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm005.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm006.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm008.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm001.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm002.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm003.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm004.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm005.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm006.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm008.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm001.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm002.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm003.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm004.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm005.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm006.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm008.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm001.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm002.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm003.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm004.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm005.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm006.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm008.png
```

## 2026-07-21T14:50:33+08:00 · `6a75cde` · Add thickness material calibration workflow

- 完整提交：`6a75cde2c7e953c2210c17e21caf279eade4291d`
- 修改文件数：12
- 文件：

```text
A	docs/THICKNESS_CALIBRATION.md
M	models/apdl/param_eye_sweep.mac
A	ops/start-thickness-calibration-5090d.sh
A	src/postprocess/check_calibration_run.py
M	src/postprocess/extract_thickness_state.py
M	src/postprocess/recover_thickness_run.py
M	src/postprocess/summarize_thickness_sweep.py
M	src/postprocess/thickness_geometry.py
M	src/runners/run_indentation_sweep.py
A	src/runners/run_thickness_calibration.py
M	tests/test_sweep_pipeline.py
A	thick/docs/Ae_Ac实验差异与材料及眼压参数评估.md
```

## 2026-07-21T13:39:36+08:00 · `b5e4dc0` · Publish 0.26 mm eyelid strain view matrices

- 完整提交：`b5e4dc0ddd2f18287b0e4504fe9bb87a592f71e4`
- 修改文件数：25
- 文件：

```text
M	thick/data/processed/fe_sweep_indent_0p26/README.md
A	thick/data/processed/fe_sweep_indent_0p26/strain_007_manifest.csv
A	thick/data/processed/fe_sweep_indent_0p26/strain_007_metadata.json
A	thick/data/processed/fe_sweep_indent_0p26/strain_probe_007_manifest.csv
A	thick/data/processed/fe_sweep_indent_0p26/strain_probe_007_metadata.json
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
A	thick/figures/fe_sweep_indent_0p26/matrices/indent_0p26_view_007_eyelid_equivalent_strain_matrix.png
A	thick/figures/fe_sweep_indent_0p26/matrices/indent_0p26_view_007_eyelid_probe_equivalent_strain_matrix.png
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/README.md
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_probe_views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_views/README.md
A	thick/figures/fe_sweep_indent_0p26/strain_views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/strain_views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm007.png
M	thick/figures/fe_sweep_indent_0p26/views/README.md
```

## 2026-07-21T13:37:09+08:00 · `6f1e503` · Support probe-inclusive eyelid strain views

- 完整提交：`6f1e503b05df12d5e4bf902e1cefadfb6e43d68c`
- 修改文件数：3
- 文件：

```text
M	models/apdl/plot_thickness_eyelid_strain_007.mac
M	src/postprocess/extract_thickness_strain_views.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-21T13:35:19+08:00 · `a2ba5cb` · Use a common eyelid strain contour scale

- 完整提交：`a2ba5cbd86151b849c2603ba3e6e8a98dd28dcda`
- 修改文件数：2
- 文件：

```text
M	models/apdl/plot_thickness_eyelid_strain_007.mac
M	tests/test_sweep_pipeline.py
```

## 2026-07-21T13:32:37+08:00 · `1026f42` · Add eyelid strain section postprocessing

- 完整提交：`1026f421814c0f69fda9de81ee8a351aaa2b08d4`
- 修改文件数：3
- 文件：

```text
A	models/apdl/plot_thickness_eyelid_strain_007.mac
A	src/postprocess/extract_thickness_strain_views.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-21T13:29:35+08:00 · `9b50e95` · Add 0.26 mm thickness cloud matrix

- 完整提交：`9b50e95e8e980e2e3875b0ff880dbbd435be27cb`
- 修改文件数：5
- 文件：

```text
A	src/postprocess/build_thickness_view_matrix.py
M	tests/test_sweep_pipeline.py
M	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
A	thick/figures/fe_sweep_indent_0p26/matrices/indent_0p26_view_007_thickness_matrix.png
M	thick/figures/fe_sweep_indent_0p26/views/README.md
```

## 2026-07-21T13:23:18+08:00 · `8e1e094` · Track excluded endpoint solver evidence

- 完整提交：`8e1e094a9699ce242666b877c85d18900bc74137`
- 修改文件数：2
- 文件：

```text
M	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/exclusion.json
A	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/eyelid_1p60mm_solve_excerpt.txt
```

## 2026-07-21T13:22:23+08:00 · `91ee543` · Retain excluded endpoint solver log

- 完整提交：`91ee543d31e2415cee10f15c05267c96f59a86bf`
- 修改文件数：1
- 文件：

```text
M	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/exclusion.json
```

## 2026-07-21T13:21:35+08:00 · `21fee0c` · Publish 0.26 mm thickness state analysis

- 完整提交：`21fee0c81f75314bf8a66c9f17f6a84c2d87cf06`
- 修改文件数：87
- 文件：

```text
M	thick/README.md
M	thick/data/processed/fe_sweep/README.md
A	thick/data/processed/fe_sweep/database_recovery.json
A	thick/data/processed/fe_sweep_indent_0p26/README.md
A	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/exclusion.json
A	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/eyelid_1p60mm_metrics.csv
A	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/eyelid_1p60mm_thickness_geometry.csv
A	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/eyelid_1p60mm_thickness_geometry.json
A	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/run_manifest.csv
A	thick/data/processed/fe_sweep_indent_0p26/excluded_endpoint_exploration/run_metadata.json
A	thick/data/processed/fe_sweep_indent_0p26/indent_comparison.csv
A	thick/data/processed/fe_sweep_indent_0p26/manifest.csv
A	thick/data/processed/fe_sweep_indent_0p26/metadata.json
A	thick/data/processed/fe_sweep_indent_0p26/qc.json
A	thick/data/processed/fe_sweep_indent_0p26/summary.csv
A	thick/data/processed/fe_sweep_indent_0p26/trend_analysis.json
A	thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md
A	thick/figures/fe_sweep_indent_0p26/trends/area_ratio_vs_thickness.png
A	thick/figures/fe_sweep_indent_0p26/trends/comparison_ae_ac_2deg_by_indent.png
A	thick/figures/fe_sweep_indent_0p26/trends/force_vs_thickness.png
A	thick/figures/fe_sweep_indent_0p26/trends/inner_area_vs_thickness.png
A	thick/figures/fe_sweep_indent_0p26/trends/outer_area_vs_thickness.png
A	thick/figures/fe_sweep_indent_0p26/trends/pressure_vs_thickness.png
A	thick/figures/fe_sweep_indent_0p26/views/README.md
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_0p80mm_indent_0p26mm/eyelid_0p80mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p00mm_indent_0p26mm/eyelid_1p00mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p20mm_indent_0p26mm/eyelid_1p20mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p40mm_indent_0p26mm/eyelid_1p40mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p60mm_indent_0p26mm/eyelid_1p60mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_1p80mm_indent_0p26mm/eyelid_1p80mm_indent_0p26mm008.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm000.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm001.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm002.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm003.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm004.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm005.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm006.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm007.png
A	thick/figures/fe_sweep_indent_0p26/views/eyelid_2p00mm_indent_0p26mm/eyelid_2p00mm_indent_0p26mm008.png
```

## 2026-07-21T13:12:13+08:00 · `69b0a01` · Protect source results during state extraction

- 完整提交：`69b0a012457e28b85e40d890ce1961b06dc44a43`
- 修改文件数：1
- 文件：

```text
M	src/postprocess/extract_thickness_state.py
```

## 2026-07-21T13:09:22+08:00 · `2e24660` · Accept interpolated MAPDL result states

- 完整提交：`2e246600f134b986a971b4e0ea7df5514949f328`
- 修改文件数：2
- 文件：

```text
M	src/postprocess/extract_thickness_state.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-21T13:08:08+08:00 · `d77b684` · Extract intermediate thickness load states

- 完整提交：`d77b6840d186365f3e6656c731bc37489c4d824f`
- 修改文件数：5
- 文件：

```text
M	models/apdl/plot_sweep_views.mac
M	models/apdl/post_sweep.mac
M	models/apdl/post_thickness_geometry.mac
A	src/postprocess/extract_thickness_state.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-21T11:55:56+08:00 · `d9afa03` · Recover thickness results after supervisor interruption

- 完整提交：`d9afa039a65c02ab9c4c54f70b8352935cea3695`
- 修改文件数：1
- 文件：

```text
A	src/postprocess/recover_thickness_run.py
```

## 2026-07-21T09:57:21+08:00 · `a847e78` · Allow configurable thickness indentation sweeps

- 完整提交：`a847e78faf78b9373df3f7da94e708f2c53dd298`
- 修改文件数：3
- 文件：

```text
M	ops/launch-thickness-sweep-5090d.sh
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-21T00:50:56+08:00 · `f93b19b` · Publish thickness sweep report and complete view atlases

- 完整提交：`f93b19b626c4283f6d70f25b2344b6edb06daabd`
- 修改文件数：191
- 文件：

```text
M	README.md
M	docs/DATA_PROVENANCE.md
M	offset/docs/偏心压入粗扫描评估报告.md
A	results/summary/indentation_coarse_views/README.md
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm000.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm001.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm002.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm003.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm004.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm005.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm006.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm007.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm008.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm000.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm001.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm002.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm003.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm004.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm005.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm006.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm007.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p40mm/offset_0p00mm_indent_0p40mm008.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm000.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm001.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm002.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm003.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm004.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm005.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm006.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm007.png
A	results/summary/indentation_coarse_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm008.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm000.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm001.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm002.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm003.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm004.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm005.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm006.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm007.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p00mm/offset_0p50mm_indent_0p00mm008.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm000.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm001.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm002.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm003.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm004.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm005.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm006.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm007.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p40mm/offset_0p50mm_indent_0p40mm008.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm000.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm001.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm002.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm003.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm004.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm005.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm006.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm007.png
A	results/summary/indentation_coarse_views/offset_0p50mm_indent_0p80mm/offset_0p50mm_indent_0p80mm008.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm000.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm001.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm002.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm003.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm004.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm005.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm006.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm007.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p00mm/offset_1p00mm_indent_0p00mm008.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm000.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm001.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm002.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm003.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm004.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm005.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm006.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm007.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p40mm/offset_1p00mm_indent_0p40mm008.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm000.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm001.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm002.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm003.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm004.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm005.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm006.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm007.png
A	results/summary/indentation_coarse_views/offset_1p00mm_indent_0p80mm/offset_1p00mm_indent_0p80mm008.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm000.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm001.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm002.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm003.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm004.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm005.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm006.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm007.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p00mm/offset_2p00mm_indent_0p00mm008.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm000.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm001.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm002.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm003.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm004.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm005.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm006.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm007.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm008.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm000.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm001.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm002.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm003.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm004.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm005.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm006.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm007.png
A	results/summary/indentation_coarse_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm008.png
M	src/postprocess/raster_plot.py
M	src/postprocess/summarize_thickness_sweep.py
M	thick/README.md
A	thick/data/processed/fe_sweep/README.md
A	thick/data/processed/fe_sweep/manifest.csv
A	thick/data/processed/fe_sweep/metadata.json
A	thick/data/processed/fe_sweep/qc.json
A	thick/data/processed/fe_sweep/summary.csv
A	thick/docs/眼睑厚度有限元实验报告.md
M	thick/docs/眼睑角膜厚度影响分析.md
A	thick/figures/fe_sweep/trends/area_ratio_vs_thickness.png
A	thick/figures/fe_sweep/trends/force_vs_thickness.png
A	thick/figures/fe_sweep/trends/inner_area_vs_thickness.png
A	thick/figures/fe_sweep/trends/outer_area_vs_thickness.png
A	thick/figures/fe_sweep/trends/pressure_vs_thickness.png
A	thick/figures/fe_sweep/views/README.md
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm000.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm001.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm002.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm003.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm004.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm005.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm006.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm007.png
A	thick/figures/fe_sweep/views/eyelid_0p80mm_indent_0p80mm/eyelid_0p80mm_indent_0p80mm008.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm000.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm001.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm002.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm003.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm004.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm005.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm006.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm007.png
A	thick/figures/fe_sweep/views/eyelid_1p00mm_indent_0p80mm/eyelid_1p00mm_indent_0p80mm008.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm000.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm001.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm002.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm003.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm004.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm005.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm006.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm007.png
A	thick/figures/fe_sweep/views/eyelid_1p20mm_indent_0p80mm/eyelid_1p20mm_indent_0p80mm008.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm000.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm001.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm002.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm003.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm004.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm005.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm006.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm007.png
A	thick/figures/fe_sweep/views/eyelid_1p40mm_indent_0p80mm/eyelid_1p40mm_indent_0p80mm008.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm000.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm001.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm002.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm003.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm004.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm005.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm006.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm007.png
A	thick/figures/fe_sweep/views/eyelid_1p60mm_indent_0p80mm/eyelid_1p60mm_indent_0p80mm008.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm000.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm001.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm002.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm003.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm004.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm005.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm006.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm007.png
A	thick/figures/fe_sweep/views/eyelid_1p80mm_indent_0p80mm/eyelid_1p80mm_indent_0p80mm008.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm000.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm001.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm002.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm003.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm004.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm005.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm006.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm007.png
A	thick/figures/fe_sweep/views/eyelid_2p00mm_indent_0p80mm/eyelid_2p00mm_indent_0p80mm008.png
```

## 2026-07-20T23:29:09+08:00 · `2ecc954` · Define inner applanation with two-degree flatness

- 完整提交：`2ecc9546a26e66bfaf091dc01a422a71dcedcf43`
- 修改文件数：4
- 文件：

```text
M	src/postprocess/summarize_thickness_sweep.py
M	src/postprocess/thickness_geometry.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-20T23:25:45+08:00 · `1a664bc` · Fix retained result postprocessing context

- 完整提交：`1a664bca6b2f134c8d5370d95aa8eb6333c664de`
- 修改文件数：1
- 文件：

```text
M	src/postprocess/reprocess_thickness_geometry.py
```

## 2026-07-20T23:24:10+08:00 · `4730d10` · Measure inner applanation from interface geometry

- 完整提交：`4730d1071f334d91b733fa45d41724777ea997d2`
- 修改文件数：7
- 文件：

```text
D	models/apdl/post_thickness_area.mac
A	models/apdl/post_thickness_geometry.mac
A	src/postprocess/reprocess_thickness_geometry.py
M	src/postprocess/summarize_thickness_sweep.py
A	src/postprocess/thickness_geometry.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-20T23:02:25+08:00 · `39ee0e4` · Add validated eyelid thickness sweep

- 完整提交：`39ee0e4b4b577c65e73a3f8cd33257fd00251370`
- 修改文件数：19
- 文件：

```text
M	README.md
M	docs/DATA_PROVENANCE.md
M	models/apdl/param_eye_sweep.mac
A	models/apdl/post_thickness_area.mac
A	offset/docs/偏心压入粗扫描评估报告.md
A	ops/launch-thickness-sweep-5090d.sh
A	results/summary/indentation_coarse.csv
A	results/summary/indentation_coarse_figures/contact_area_vs_indent.png
A	results/summary/indentation_coarse_figures/contact_center_vs_indent.png
A	results/summary/indentation_coarse_figures/force_vs_indent.png
A	results/summary/indentation_coarse_figures/pmax_vs_indent.png
A	results/summary/indentation_coarse_manifest.csv
A	results/summary/indentation_coarse_metadata.json
A	results/summary/indentation_coarse_qc.json
A	src/postprocess/summarize_thickness_sweep.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
M	thick/README.md
M	thick/protocol/真实仿体实验方案.md
```

## 2026-07-20T20:27:43+08:00 · `bc86106` · Prune reproducible MAPDL solver artifacts

- 完整提交：`bc8610601a6cfeb201330ea96af96d1f253e4f3b`
- 修改文件数：4
- 文件：

```text
M	docs/INDENTATION_SWEEP.md
A	src/postprocess/prune_solver_artifacts.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-20T20:15:38+08:00 · `6ba4c2d` · Publish validated indentation smoke results

- 完整提交：`6ba4c2d92dad25bed882b0168b578df25e0f577b`
- 修改文件数：49
- 文件：

```text
M	README.md
M	docs/DATA_PROVENANCE.md
M	docs/SYNC_GUIDE.md
M	ops/bootstrap-arch.sh
A	results/summary/indentation_smoke.csv
A	results/summary/indentation_smoke_figures/contact_area_vs_indent.png
A	results/summary/indentation_smoke_figures/contact_center_vs_indent.png
A	results/summary/indentation_smoke_figures/force_vs_indent.png
A	results/summary/indentation_smoke_figures/pmax_vs_indent.png
A	results/summary/indentation_smoke_manifest.csv
A	results/summary/indentation_smoke_metadata.json
A	results/summary/indentation_smoke_qc.json
A	results/summary/indentation_smoke_views/README.md
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm000.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm001.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm002.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm003.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm004.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm005.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm006.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm007.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p00mm/offset_0p00mm_indent_0p00mm008.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm000.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm001.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm002.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm003.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm004.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm005.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm006.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm007.png
A	results/summary/indentation_smoke_views/offset_0p00mm_indent_0p80mm/offset_0p00mm_indent_0p80mm008.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm000.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm001.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm002.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm003.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm004.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm005.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm006.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm007.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p40mm/offset_2p00mm_indent_0p40mm008.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm000.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm001.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm002.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm003.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm004.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm005.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm006.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm007.png
A	results/summary/indentation_smoke_views/offset_2p00mm_indent_0p80mm/offset_2p00mm_indent_0p80mm008.png
```

## 2026-07-20T19:45:50+08:00 · `649550f` · Report contact penetration explicitly

- 完整提交：`649550f6769316eba99733421b09090da5d1a292`
- 修改文件数：7
- 文件：

```text
M	docs/DATA_PROVENANCE.md
M	docs/INDENTATION_SWEEP.md
M	models/apdl/plot_sweep_views.mac
M	models/apdl/post_sweep.mac
M	src/postprocess/summarize_indentation_sweep.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-20T19:20:18+08:00 · `f969310` · Cap validated indentation at 0.8 mm

- 完整提交：`f969310b07a232600dabe5c1e70e1b20d8202baf`
- 修改文件数：8
- 文件：

```text
M	README.md
M	docs/DATA_PROVENANCE.md
M	docs/INDENTATION_SWEEP.md
M	models/apdl/param_eye_sweep.mac
A	results/summary/indentation_limit_evidence_20260720.csv
M	src/postprocess/summarize_indentation_sweep.py
M	src/runners/run_indentation_sweep.py
M	tests/test_sweep_pipeline.py
```

## 2026-07-20T18:32:15+08:00 · `7bd36dd` · Harden indentation sweep pipeline

- 完整提交：`7bd36dd8118e7fcce4305daa8b42304aca9af3bc`
- 修改文件数：11
- 文件：

```text
M	README.md
M	docs/DATA_PROVENANCE.md
A	docs/INDENTATION_SWEEP.md
M	models/apdl/param_eye_sweep.mac
M	models/apdl/plot_sweep_views.mac
M	models/apdl/post_sweep.mac
M	ops/launch-indentation-sweep-5090d.sh
A	src/postprocess/raster_plot.py
M	src/postprocess/summarize_indentation_sweep.py
M	src/runners/run_indentation_sweep.py
A	tests/test_sweep_pipeline.py
```

## 2026-07-20T15:52:20+08:00 · `3cb3a03` · Flatten simulation workflow under Git history

- 完整提交：`3cb3a03e8eb6909f639caaeabe3f58939afcfe24`
- 修改文件数：37
- 文件：

```text
M	.gitignore
M	README.md
M	docs/DATA_PROVENANCE.md
M	docs/STORAGE_CLEANUP_20260720.md
M	docs/SYNC_GUIDE.md
D	models/apdl/check_contact.dat
D	models/apdl/min_contact.dat
D	models/apdl/param_2d_test.dat
D	models/apdl/param_eye_2d.dat
D	models/apdl/param_eye_3d.mac
M	models/apdl/param_eye_sweep.mac
D	models/apdl/plot_3d.mac
D	models/apdl/plot_ecc.mac
D	models/apdl/plot_eye.dat
M	models/apdl/plot_sweep_views.mac
D	models/apdl/post_contact.dat
D	models/apdl/post_fixed.dat
D	models/apdl/post_geom.dat
D	models/apdl/post_normal.dat
M	models/apdl/post_sweep.mac
D	models/apdl/run3d_test.dat
M	offset/README.md
D	offset/code/apdl/plot_multiview.mac
D	offset/code/apdl/post_eccentric.mac
D	offset/code/legacy/run_eccentric_cases.py
D	offset/code/legacy/run_eccentric_final.py
D	offset/code/legacy/run_eccentric_v2.py
D	offset/code/legacy/run_eccentric_v3.py
M	offset/docs/参数化3D偏心仿真结果.md
M	ops/verify-repository.sh
D	src/legacy/README.md
D	src/legacy/workbench/fix_geom_and_run.py
D	src/legacy/workbench/fix_nblock_run.py
D	src/legacy/workbench/plan_a_baseline.py
D	src/legacy/workbench/plan_b_offset.py
D	src/runners/run3d_parallel.py
M	src/runners/run_indentation_sweep.py
```

## 2026-07-20T15:31:10+08:00 · `a5382c8` · Document solver data cleanup and archives

- 完整提交：`a5382c8e5e67b49f72768ed134330fa2ec799fc8`
- 修改文件数：1
- 文件：

```text
A	docs/STORAGE_CLEANUP_20260720.md
```

## 2026-07-20T14:31:19+08:00 · `db76b7f` · Normalize thickness experiment CSV headers

- 完整提交：`db76b7ffd5934a2bd56b7df9856f9a169349b96b`
- 修改文件数：1
- 文件：

```text
M	thick/code/process_experiment.py
```

## 2026-07-20T14:29:22+08:00 · `e6fefce` · Make thickness processing portable

- 完整提交：`e6fefceae6fcc559e563a7317f6f468bbf492a1f`
- 修改文件数：1
- 文件：

```text
M	thick/code/process_experiment.py
```

## 2026-07-20T14:25:28+08:00 · `9528545` · Organize baseline offset and thickness studies

- 完整提交：`95285457c6991bcf90b049aac559fb7aa4bfc755`
- 修改文件数：50
- 文件：

```text
M	.gitignore
M	README.md
A	baseline/README.md
R100	assets/figures/eccentric_3d/e3d_x0p0001.png	baseline/figures/e3d_x0p0001.png
R100	assets/figures/eccentric_3d/e3d_x0p0002.png	baseline/figures/e3d_x0p0002.png
R100	assets/figures/multiview/x0p0_0_geometry.png	baseline/figures/x0p0_0_geometry.png
R100	assets/figures/multiview/x0p0_1_front.png	baseline/figures/x0p0_1_front.png
R100	assets/figures/multiview/x0p0_2_top.png	baseline/figures/x0p0_2_top.png
R100	assets/figures/multiview/x0p0_3_side.png	baseline/figures/x0p0_3_side.png
R100	assets/figures/multiview/x0p0_4_section.png	baseline/figures/x0p0_4_section.png
R100	assets/figures/multiview/x0p0_5_deformed.png	baseline/figures/x0p0_5_deformed.png
M	docs/DATA_PROVENANCE.md
M	docs/SYNC_GUIDE.md
A	offset/README.md
R100	models/apdl/plot_multiview.mac	offset/code/apdl/plot_multiview.mac
R100	models/apdl/post_eccentric.mac	offset/code/apdl/post_eccentric.mac
R100	src/legacy/workbench/run_eccentric_cases.py	offset/code/legacy/run_eccentric_cases.py
R100	src/legacy/workbench/run_eccentric_final.py	offset/code/legacy/run_eccentric_final.py
R100	src/legacy/workbench/run_eccentric_v2.py	offset/code/legacy/run_eccentric_v2.py
R100	src/legacy/workbench/run_eccentric_v3.py	offset/code/legacy/run_eccentric_v3.py
R100	results/summary/eccentric_3d.csv	offset/data/eccentric_3d.csv
R100	results/summary/eccentric_semianalytical.csv	offset/data/eccentric_semianalytical.csv
R093	docs/analysis/偏心测量曲线分析.md	offset/docs/偏心测量曲线分析.md
R097	docs/analysis/参数化3D偏心仿真结果.md	offset/docs/参数化3D偏心仿真结果.md
R100	assets/figures/eccentric/fig1_areas.png	offset/figures/eccentric/fig1_areas.png
R100	assets/figures/eccentric/fig2_ratio_pressure.png	offset/figures/eccentric/fig2_ratio_pressure.png
R100	assets/figures/eccentric/fig3_overlay_probe.png	offset/figures/eccentric/fig3_overlay_probe.png
R100	assets/figures/eccentric/fig4_pressure_grid.png	offset/figures/eccentric/fig4_pressure_grid.png
R100	assets/figures/eccentric_3d/e3d_x2p0001.png	offset/figures/eccentric_3d/e3d_x2p0001.png
R100	assets/figures/eccentric_3d/e3d_x2p0002.png	offset/figures/eccentric_3d/e3d_x2p0002.png
R100	assets/figures/multiview/x2p0_0_geometry.png	offset/figures/multiview/x2p0_0_geometry.png
R100	assets/figures/multiview/x2p0_1_front.png	offset/figures/multiview/x2p0_1_front.png
R100	assets/figures/multiview/x2p0_2_top.png	offset/figures/multiview/x2p0_2_top.png
R100	assets/figures/multiview/x2p0_3_side.png	offset/figures/multiview/x2p0_3_side.png
R100	assets/figures/multiview/x2p0_4_section.png	offset/figures/multiview/x2p0_4_section.png
R100	assets/figures/multiview/x2p0_5_deformed.png	offset/figures/multiview/x2p0_5_deformed.png
M	ops/bootstrap-arch.sh
A	thick/README.md
R098	scripts/reporting/generate_analysis_md.py	thick/code/generate_placeholder_report.py
A	thick/code/process_experiment.py
A	thick/data/README.md
A	thick/data/manifest.csv
R100	results/summary/thickness_semianalytical.csv	thick/data/placeholder/thickness_semianalytical.csv
A	thick/data/raw/README.md
R090	docs/analysis/眼睑角膜厚度影响分析.md	thick/docs/眼睑角膜厚度影响分析.md
R100	assets/figures/thickness/fig1_eyelid_area.png	thick/figures/placeholder/fig1_eyelid_area.png
R100	assets/figures/thickness/fig2_cornea_area.png	thick/figures/placeholder/fig2_cornea_area.png
R100	assets/figures/thickness/fig3_pressure.png	thick/figures/placeholder/fig3_pressure.png
R100	assets/figures/thickness/fig4_pressure_grid.png	thick/figures/placeholder/fig4_pressure_grid.png
A	thick/protocol/真实仿体实验方案.md
```

## 2026-07-20T12:52:12+08:00 · `354da00` · Run indentation sweep across four parallel MAPDL cases

- 完整提交：`354da0007e0d24e7e50bebc1874b335f49600568`
- 修改文件数：2
- 文件：

```text
A	ops/launch-indentation-sweep-5090d.sh
M	src/runners/run_indentation_sweep.py
```

## 2026-07-20T12:50:43+08:00 · `46687ba` · Write APDL sweep drivers with real newlines

- 完整提交：`46687ba0b3d77a995abb56a638f7eb8e8b1d1cdc`
- 修改文件数：1
- 文件：

```text
M	src/runners/run_indentation_sweep.py
```

## 2026-07-20T12:49:38+08:00 · `9a65c69` · Parse MAPDL contact-node coordinate columns

- 完整提交：`9a65c69d3e64d311a91232d63759c254767ebb6d`
- 修改文件数：1
- 文件：

```text
M	src/postprocess/summarize_indentation_sweep.py
```

## 2026-07-20T12:48:26+08:00 · `cad191c` · Export contact footprints from POST1

- 完整提交：`cad191c65e8570f3b93682b840daf63205359291`
- 修改文件数：1
- 文件：

```text
M	models/apdl/post_sweep.mac
```

## 2026-07-20T12:47:47+08:00 · `2a8e491` · Derive contact footprint areas from active nodes

- 完整提交：`2a8e4913c7a3c0f86c7d9b12d17c44529d9fa222`
- 修改文件数：2
- 文件：

```text
M	models/apdl/post_sweep.mac
A	src/postprocess/summarize_indentation_sweep.py
```

## 2026-07-20T12:46:36+08:00 · `3a0b818` · Select sweep result file before postprocessing

- 完整提交：`3a0b81845c6785f34d4876e2e7c350e96441f2cd`
- 修改文件数：1
- 文件：

```text
M	src/runners/run_indentation_sweep.py
```

## 2026-07-20T12:45:51+08:00 · `b24b131` · Resume sweep cases in generated drivers

- 完整提交：`b24b131524504ed2ffac6b79685554f30fa9ddc5`
- 修改文件数：3
- 文件：

```text
M	models/apdl/plot_sweep_views.mac
M	models/apdl/post_sweep.mac
M	src/runners/run_indentation_sweep.py
```

## 2026-07-20T12:45:16+08:00 · `722438c` · Expand APDL postprocess job parameter

- 完整提交：`722438cbbc75ce5e8a91986f88abec90ca7a88ee`
- 修改文件数：2
- 文件：

```text
M	models/apdl/plot_sweep_views.mac
M	models/apdl/post_sweep.mac
```

## 2026-07-20T12:44:47+08:00 · `3a3ab2d` · Pass solver job names to sweep postprocessing

- 完整提交：`3a3ab2d5acf63a603ea39afd7957d86e5cea0c0c`
- 修改文件数：3
- 文件：

```text
M	models/apdl/plot_sweep_views.mac
M	models/apdl/post_sweep.mac
M	src/runners/run_indentation_sweep.py
```

## 2026-07-20T12:43:20+08:00 · `e3c2c15` · Add indentation sweep solver and contact metrics

- 完整提交：`e3c2c159df95f6204dc36396d856e0000f3f7be0`
- 修改文件数：4
- 文件：

```text
A	models/apdl/param_eye_sweep.mac
A	models/apdl/plot_sweep_views.mac
A	models/apdl/post_sweep.mac
A	src/runners/run_indentation_sweep.py
```

## 2026-07-20T12:18:07+08:00 · `a3aa585` · Make 3D runner repository-relative

- 完整提交：`a3aa5855da55b0a3053d577e8ae9b300c003da3c`
- 修改文件数：1
- 文件：

```text
M	src/runners/run3d_parallel.py
```

## 2026-07-20T12:16:01+08:00 · `a9f3fa2` · Add report figures and visualization assets

- 完整提交：`a9f3fa26b0ddf5fe519b011d42a8a706f144c2b6`
- 修改文件数：27
- 文件：

```text
A	assets/figures/eccentric/fig1_areas.png
A	assets/figures/eccentric/fig2_ratio_pressure.png
A	assets/figures/eccentric/fig3_overlay_probe.png
A	assets/figures/eccentric/fig4_pressure_grid.png
A	assets/figures/eccentric_3d/e3d_x0p0001.png
A	assets/figures/eccentric_3d/e3d_x0p0002.png
A	assets/figures/eccentric_3d/e3d_x2p0001.png
A	assets/figures/eccentric_3d/e3d_x2p0002.png
A	assets/figures/geometry/eye000.png
A	assets/figures/geometry/eye001.png
A	assets/figures/geometry/eye002.png
A	assets/figures/multiview/x0p0_0_geometry.png
A	assets/figures/multiview/x0p0_1_front.png
A	assets/figures/multiview/x0p0_2_top.png
A	assets/figures/multiview/x0p0_3_side.png
A	assets/figures/multiview/x0p0_4_section.png
A	assets/figures/multiview/x0p0_5_deformed.png
A	assets/figures/multiview/x2p0_0_geometry.png
A	assets/figures/multiview/x2p0_1_front.png
A	assets/figures/multiview/x2p0_2_top.png
A	assets/figures/multiview/x2p0_3_side.png
A	assets/figures/multiview/x2p0_4_section.png
A	assets/figures/multiview/x2p0_5_deformed.png
A	assets/figures/thickness/fig1_eyelid_area.png
A	assets/figures/thickness/fig2_cornea_area.png
A	assets/figures/thickness/fig3_pressure.png
A	assets/figures/thickness/fig4_pressure_grid.png
```

## 2026-07-20T12:15:44+08:00 · `133eb3d` · Initialize managed tonometer simulation repository

- 完整提交：`133eb3d28856d8cca17e47008e8a1e3cf80463f7`
- 修改文件数：45
- 文件：

```text
A	.gitattributes
A	.gitignore
A	README.md
A	docs/DATA_PROVENANCE.md
A	docs/SYNC_GUIDE.md
A	docs/analysis/三维模型图集说明.md
A	docs/analysis/偏心测量曲线分析.md
A	docs/analysis/参数化3D偏心仿真结果.md
A	docs/analysis/眼睑角膜厚度影响分析.md
A	docs/reference/眼球剖面图与曲线分析.pdf
A	models/apdl/check_contact.dat
A	models/apdl/min_contact.dat
A	models/apdl/param_2d_test.dat
A	models/apdl/param_eye_2d.dat
A	models/apdl/param_eye_3d.mac
A	models/apdl/plot_3d.mac
A	models/apdl/plot_ecc.mac
A	models/apdl/plot_eye.dat
A	models/apdl/plot_multiview.mac
A	models/apdl/post_contact.dat
A	models/apdl/post_eccentric.mac
A	models/apdl/post_fixed.dat
A	models/apdl/post_geom.dat
A	models/apdl/post_normal.dat
A	models/apdl/run3d_test.dat
A	ops/bootstrap-5090d.sh
A	ops/bootstrap-arch.sh
A	ops/verify-repository.sh
A	results/summary/eccentric_3d.csv
A	results/summary/eccentric_semianalytical.csv
A	results/summary/external_runs_manifest.csv
A	results/summary/thickness_semianalytical.csv
A	scripts/reporting/generate_analysis_md.py
A	src/legacy/README.md
A	src/legacy/workbench/fix_geom_and_run.py
A	src/legacy/workbench/fix_nblock_run.py
A	src/legacy/workbench/plan_a_baseline.py
A	src/legacy/workbench/plan_b_offset.py
A	src/legacy/workbench/run_eccentric_cases.py
A	src/legacy/workbench/run_eccentric_final.py
A	src/legacy/workbench/run_eccentric_v2.py
A	src/legacy/workbench/run_eccentric_v3.py
A	src/postprocess/geom_extent.py
A	src/postprocess/visu.py
A	src/runners/run3d_parallel.py
```
