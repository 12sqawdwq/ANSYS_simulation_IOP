# 算法文件分类清单

## 1. 判定规则

本清单按文件的**算法职责**分类，而不是按文件修改时间分类：

- `current_canonical`：定义当前认可的机制框架或冻结结论；
- `current_diagnostic`：当前仍使用的分析工具，但输出不是生产算法；
- `historical_algorithm`：历史线性 `Ksensor` 的设计、配置或实现；
- `mixed_compatibility`：当前文件主体仍有效，但保留旧算法诊断字段；
- `rejected_branch`：有价值的负结果，不能作为当前完整算法；
- `evidence_only`：不可变结果/QC，不是算法源码；
- `not_algorithm`：FE 模型、运行器、绘图或实验编排。

## 2. 当前代权威文件

|文件|分类|说明|
|---|---|---|
|`docs/IOP修正算法全局方向.md`|`current_canonical`|当前面积—传力分解总设计；分界提交 `e04b0c9`|
|`high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md`|`current_canonical`|当前冻结数值、允许/禁止表述和验证失败|
|`high_iop_mechanical_transfer_t1p25_c0p60/docs/intermediate/MECHANICAL_TRANSFER_PATH.md`|`current_canonical`|机制路径审计及关闭判定|
|`high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md`|`evidence_only`|14 份阶段原文的无损记录，包含新旧两代历史|
|`algorithms/current/MECHANISTIC_PRESSURE_TRANSFER.md`|`current_canonical`|面向接手者的当前代算法摘要|

## 3. 当前代分析与验证脚本

|文件|分类|准确角色|
|---|---|---|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/fit_rational_piop_vs_pprobe.py`|`current_diagnostic`|0–50 mmHg 经验逆向分式拟合；不是生产算法|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/derive_forward_rational_parameters.py`|`current_diagnostic`|面积＋综合修正代理；含已知 IOP，存在闭环|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/derive_global_load_share_model.py`|`current_diagnostic`|全局载荷份额机制重参数化|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/postprocess/postprocess_interface_force_integrals.py`|`current_diagnostic`|RST 界面力与力平衡证据提取|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/evaluate_iop60_extrapolation.py`|`current_diagnostic`|冻结分式的独立高压外推评估；结果为失败|
|`analysis/fit_pressure_model.py`|`current_diagnostic`|跨厚度可识别性和分式拟合；除 1.25 mm 外不能识别完整参数|
|`analysis/sensitivity_analysis.py`|`current_diagnostic`|厚度敏感性及共享参数诊断，不定义新生产公式|

## 4. 历史代原文件

这些文件已经从当前工作树移除或被重构，但可由 Git 精确恢复。

|Git 对象|分类|说明|
|---|---|---|
|`4bc0f9f:thick/experiments/high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md`|`historical_algorithm`|首次明确线性 `Ksensor` 设计和参数|
|`23d4f22:high_iop_mechanical_transfer_t1p25_c0p60/run_spec_full.json`|`historical_algorithm`|历史算法正式配置|
|`23d4f22:high_iop_mechanical_transfer_t1p25_c0p60/postprocess_full_high_iop.py`|`historical_algorithm`|历史 $\alpha q/(1-\beta q)$ 实现|
|`33e9f46:high_iop_mechanical_transfer_t1p25_c0p60/FULL_EXPERIMENT_RESULT.md`|`evidence_only`|历史算法首轮正式结果|
|`e70b506:high_iop_mechanical_transfer_t1p25_c0p60/postprocess_iop40_preflight.py`|`historical_algorithm`|40 mmHg 历史零点预检实现，结果当时已标记 provisional|
|`e70b506:high_iop_mechanical_transfer_t1p25_c0p60/run_spec.json`|`historical_algorithm`|对应预检配置|

其中设计与结果原文已保存在 `EXPERIMENT_RECORD.md`，源码和 JSON 配置仍以 Git 对象为恢复真源。

## 5. 当前文件中的旧算法兼容层

|当前文件|分类|旧内容|为什么不能把整个文件判为旧版|
|---|---|---|---|
|`high_iop_mechanical_transfer_t1p25_c0p60/config/calibration_0_to_50.json`|`mixed_compatibility`|两组 `frozen_sensor_models_for_diagnostic_only` 参数|同一配置还定义当前正式 FE 网格、材料、几何和 QC|
|`high_iop_mechanical_transfer_t1p25_c0p60/config/extrapolation_50_to_60.json`|`mixed_compatibility`|历史 `alpha/beta` 和当前三个冻结分式候选|主要用途是冻结模型外推验证|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/postprocess/postprocess_pressure_sweep.py`|`mixed_compatibility`|计算 `frozen_model_iop_calc_diagnostic_mmhg`|同时负责当前压力矩阵聚合和 QC|
|`high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_summary.json`|`evidence_only`|含历史诊断列|不可变 FE 汇总证据|
|`high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop_0_to_60_step2p5_summary.json`|`evidence_only`|含历史诊断列|不可变高压扩展证据|

结论：旧参数仍然出现是为了复现和比较，不代表旧算法仍在服役。

## 6. 当前机制代中的诊断或已否定分支

|文件/结果|分类|结论|
|---|---|---|
|`scripts/postprocess/postprocess_area_ratio_iop.py`|`rejected_branch`|实现直接面积一致换算；高压系统性低估|
|`scripts/analysis/analyze_area_ratio_error.py`|`rejected_branch`|证明调整 5°离散边界不足以解释误差|
|`results/20260730_area_ratio_k_iop_results.json`|`evidence_only`|直接面积法的负结果|
|`results/20260731_3ce7c957_interface_force_integrals_summary.json` 中 `direct_area_interface_iop_mmhg`|`rejected_branch`|直接界面传力 × 5°面积，21 点 RMSE 9.54752 mmHg|
|`results/20260731_forward_rational_parameters_ac5_proxy.json`|`current_diagnostic`|综合修正代理重建，定义中使用已知 IOP|
|`results/20260731_global_load_share_derivation.json`|`current_diagnostic`|载荷份额机制重参数化，不是独立验证|
|`results/20260730_rational_regression_0_to_50_step2p5.json`|`current_diagnostic`|固定分式样本内拟合|
|`results/20260731_5017b619_iop60_frozen_model_extrapolation.json`|`evidence_only`|固定分式高压外推失败|

表中相对路径未写模块前缀的文件均位于 `high_iop_mechanical_transfer_t1p25_c0p60/` 下。

## 7. 不属于“算法版本”的文件

以下内容与算法有关，但不应贴上新/旧算法版本标签：

|范围|分类原因|
|---|---|
|`models/apdl/param_eye_sweep.mac`|FE 物理模型；新旧算法都使用其求解结果|
|`src/runners/run_indentation_sweep.py`|工况运行与 QC，不执行 IOP 标定策略选择|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/*.sh`|服务器编排入口|
|`plot_*.py`|可视化，不定义算法参数来源|
|`figures/`|图件证据|
|`results/*launch_metadata.json`、controller state、artifact SHA|运行溯源与完整性证据|
|厚度、偏心和 baseline 模块|独立实验域；可能提供未来参数，但不是两代 IOP 反演算法本身|

## 8. 最终文件归属结论

- **旧版本算法文件**：以 `4bc0f9f`、`23d4f22` 中的设计、配置和 `postprocess_full_high_iop.py` 为核心；当前只残留诊断兼容字段。
- **新版本算法文件**：以 `docs/IOP修正算法全局方向.md` 和当前高眼压主要结论为核心；现有分析脚本用于识别、审计和证伪，尚没有可直接发布的生产算法文件。
- **不能归入任一生产版本**：固定逆向分式、面积法、直接界面法、综合代理和载荷分流现阶段分别属于诊断拟合、已否定路径或机制重参数化。
