# 高眼压实验脚本索引

> 原则：文件名描述职责或实验范围，不描述 `v1/v2/final/latest` 状态；当前版本由 Git 提交确定。
> 当前入口和配置以本页为准，历史脚本从 Git 恢复，不在工作树复制多份。

## 1. 正式服务器入口

|脚本|职责|主要配置|状态|
|---|---|---|---|
|`scripts/server/launch_calibration_0_to_50_5090d.sh`|在 5090d 求解 0–50 mmHg 密集网格、提取两个推进状态、汇总并绘图|`config/calibration_0_to_50.json`|当前|
|`scripts/server/launch_extrapolation_50_to_60_5090d.sh`|冻结 0–50 参数后求解 52.5–60 mmHg，并执行外推评估|`config/extrapolation_50_to_60.json`|当前|
|`scripts/server/launch_interface_force_integrals_5090d.sh`|读取已保留 RST，完成 0–50 mmHg 接触力矢量积分|`config/interface_force_integrals.json`|当前|

共同约束：

- 仅允许主机短名 `xuanyu`；
- 正式工作树必须清洁；
- 输出目录必须全新；
- launch metadata 记录 Git SHA、环境、输入 SHA-256 和运行顺序；
- ANSYS 大文件只能写入 `blueknow-data`。

## 2. 后处理脚本

|脚本|主要输入|主要输出|说明|
|---|---|---|---|
|`scripts/postprocess/postprocess_pressure_sweep.py`|运行根、当前 JSON 规格、复用的历史 summary|压力网格 summary JSON/CSV|同时服务 0–50 校准和 50–60 扩展，不再按某一旧补点阶段命名|
|`scripts/postprocess/postprocess_interface_force_integrals.py`|界面力规格、各压力保留状态、FE summary|界面力 summary JSON/CSV|调度只读 RST 积分，校验探头接触力与反力及因子恒等式|
|`scripts/postprocess/postprocess_area_ratio_iop.py`|完整高眼压 summary|面积比例换算 JSON/CSV|历史面积路径的可复现分析；结果用于说明面积公式边界，不是生产标定|

## 3. 分析与绘图脚本

|脚本|职责|默认产物|
|---|---|---|
|`scripts/analysis/fit_rational_piop_vs_pprobe.py`|按历史源字段拟合 0–50 mmHg 的 $p=b_{source}q/(1-a_{source}q)$；三版本展示映射为 $p=a_{display}q/(1-b_{display}q)$|`results/20260730_rational_regression_*`、分式图|
|`scripts/analysis/derive_forward_rational_parameters.py`|由面积和综合修正代理推导局部参数，并与逆向回归比较|`results/20260731_forward_rational_parameters_*`|
|`scripts/analysis/derive_global_load_share_model.py`|将分式重参数化为全局载荷份额模型|`results/20260731_global_load_share_derivation.*`|
|`scripts/analysis/evaluate_iop60_extrapolation.py`|用冻结参数评估 52.5–60 mmHg 未见点|`results/20260731_5017b619_iop60_frozen_model_extrapolation.*`|
|`scripts/analysis/analyze_area_ratio_error.py`|拆分面积换算误差和压力相关传力衰减|`results/20260730_area_ratio_error_decomposition.*`|
|`scripts/analysis/plot_pressure_sweep.py`|绘制任意均匀实际 FE 压力网格散点|0–50、0–60 散点图|
|`scripts/analysis/plot_iop_vs_kae_ac.py`|绘制面积比例诊断图|`figures/iop_vs_k_ae_over_ac_0p259875.png`|
|`scripts/analysis/plot_interface_force_forward_analysis.py`|绘制直接界面力模型和 $\tau/\chi/\eta$ 分解|两张界面力图|
|`scripts/analysis/plot_global_load_share_derivation.py`|绘制载荷份额重参数化结果|`figures/global_load_share_rational_derivation.png`|

上述带默认输入/输出的分析脚本把实验根解析为 `Path(__file__).resolve().parents[2]`，移动到分层目录后仍从模块根的 `results/` 和 `figures/` 读写。

## 4. 仓库级共享依赖

### 4.1 求解

|路径|作用|
|---|---|
|`src/runners/run_indentation_sweep.py`|参数化工况生成、隔离运行、重试、QC、清理和 manifest|
|`models/apdl/param_eye_sweep.mac`|眼球—角膜—眼睑—探头三维模型和连续三载荷步|

### 4.2 状态提取与接触积分

|路径|作用|
|---|---|
|`src/postprocess/extract_geometry_zero_state.py`|从保留 RST 提取 0.259875/0.28 mm 几何与反力状态|
|`src/postprocess/extract_contact_force_integrals.py`|运行 MAPDL 只读接触积分并解析拆分 CSV|
|`models/apdl/post_contact_force_integrals.mac`|从 CONTA174 提取全局接触力、切向力和面积|

### 4.3 审计与仓库运维

|路径|作用|
|---|---|
|`ops/audit-markdown-formulas.py`|公式结构/可选 LaTeX 渲染审计|
|`ops/normalize-markdown-math-delimiters.py`|Markdown 数学分隔符规范化|
|`ops/verify-repository.sh`|仓库禁入大文件、命名和状态检查|
|`ops/sync-main-to-github.sh`|内部 `origin/main` 到 GitHub 的同步工作流|

仓库全部脚本的模块级索引见根目录 [`../../docs/SCRIPT_INDEX.md`](../../docs/SCRIPT_INDEX.md)。

## 5. 测试映射

|测试|保护的契约|
|---|---|
|`tests/test_high_iop_configuration.py`|当前配置、材料、压力网格、工作点和历史输入证据|
|`tests/test_iop60_extension.py`|50–60 规格、未见点、冻结参数和跨平台绘图|
|`tests/test_interface_force_integrals.py`|压力源分区、APDL 标签、积分解析和直接模型|
|`tests/test_rational_iop_regression.py`|分式参数与样本内指标|
|`tests/test_forward_rational_derivation.py`|面积/综合代理的推导数值和循环性标记|
|`tests/test_global_load_share_derivation.py`|载荷份额拟合、几何映射和 QC|
|`tests/test_high_iop_document_archive.py`|14 份原文合并段落与 manifest 哈希一致性|

## 6. 已退役入口与替代关系

|退役入口|原因|当前替代|
|---|---|---|
|`launch_iop40_preflight_5090d.sh`、`run_spec.json`、`postprocess_iop40_preflight.py`|单点收敛闸门已完成|当前校准启动器及已提交预检结果|
|`launch_full_experiment_5090d.sh`、`run_spec_full.json`、`postprocess_full_high_iop.py`|稀疏首轮矩阵已被密集网格覆盖|`launch_calibration_0_to_50_5090d.sh` + `postprocess_pressure_sweep.py`|
|`launch_iop_5_to_50_supplement_5090d.sh`、`run_spec_iop_5_to_50.json`|5 mmHg 补点阶段已被 2.5 mmHg 网格覆盖|`config/calibration_0_to_50.json`|
|`plot_piop_vs_delta_pprobe_5_to_50.py`|只支持旧 5 mmHg 网格|`plot_pressure_sweep.py`|
|`plot_piop_vs_delta_pprobe_scatter.py`|只支持首轮六点并内嵌数据|`plot_pressure_sweep.py`|

退役只表示“不再是当前工作树入口”，不否定其历史实验。原实现由 Git 保存，原结果和完整报告继续保留。
