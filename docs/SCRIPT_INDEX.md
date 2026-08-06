# 全局脚本索引

> 最后核对：2026-08-06
> 版本规则：脚本文件名描述职责，不使用 `v1/v2/final/latest/old/copy` 表示状态；版本、回滚和并行开发由 Git commit、tag 和 branch 管理。

## 1. 统一有限元模型

|路径|职责|
|---|---|
|`models/apdl/param_eye_sweep.mac`|统一眼球、角膜、眼睑和探头参数化模型；IOP 预载、几何初接触和正式压入三载荷步|
|`models/apdl/plot_sweep_views.mac`|批量工况几何/变形多视图|
|`models/apdl/plot_thickness_eyelid_strain.mac`|眼睑厚度扫描应变图|
|`models/apdl/post_sweep.mac`|通用扫描状态后处理|
|`models/apdl/post_thickness_geometry.mac`|厚度研究几何、接触、位移、压力和界面量导出|
|`models/apdl/post_contact_force_integrals.mac`|CONTA174 全局接触力/切向力/面积积分|
|`models/apdl/post_contact_history.mac`|接触启用与加载历史|
|`models/apdl/post_probe_force_curve.mac`|探头力—位移曲线提取|
|`models/apdl/post_geometry_zero_probe_pressure_curve.mac`|几何初接触零点下的探头压力曲线|

## 2. 求解运行器

|路径|职责|
|---|---|
|`src/runners/run_indentation_sweep.py`|参数化压入批量运行、隔离尝试、重试、QC、清理、manifest 和元数据|
|`src/runners/run_thickness_calibration.py`|眼睑厚度校准矩阵调度|

所有正式实验应复用运行器，不在实验目录复制一个带版本后缀的新 runner。

## 3. 通用后处理

### 3.1 汇总与恢复

|路径|职责|
|---|---|
|`src/postprocess/summarize_indentation_sweep.py`|压入扫描汇总与趋势图|
|`src/postprocess/summarize_thickness_sweep.py`|厚度扫描汇总、面积/压力/反力趋势和 QC|
|`src/postprocess/recover_thickness_run.py`|从保留结果恢复中断的厚度后处理|
|`src/postprocess/reprocess_thickness_geometry.py`|重新处理厚度几何导出|
|`src/postprocess/prune_solver_artifacts.py`|按保留策略清理求解器中间大文件|
|`src/postprocess/check_calibration_run.py`|校准运行完整性检查|
|`src/postprocess/build_thickness_view_matrix.py`|厚度视图矩阵拼接|

### 3.2 状态与曲线提取

|路径|职责|
|---|---|
|`src/postprocess/extract_thickness_state.py`|提取指定厚度/推进状态|
|`src/postprocess/extract_thickness_strain_views.py`|提取厚度应变视图|
|`src/postprocess/extract_geometry_zero_state.py`|从保留 RST 提取几何初接触参考下的指定推进状态|
|`src/postprocess/extract_probe_force_curves.py`|批量提取探头力—位移曲线|
|`src/postprocess/extract_contact_rezeroed_states.py`|按首次接触重新归零并提取状态|
|`src/postprocess/extract_contact_force_integrals.py`|运行接触力 APDL 并解析积分 CSV|
|`src/postprocess/summarize_contact_rezeroed.py`|接触重归零面积结果汇总|

### 3.3 面积、平坦度与力学诊断

|路径|职责|
|---|---|
|`src/postprocess/thickness_geometry.py`|厚度几何指标和选择规则的共享实现|
|`src/postprocess/geom_extent.py`|网格/几何范围计算|
|`src/postprocess/analyze_inner_pressure_area.py`|角膜内侧压力参与面积候选|
|`src/postprocess/analyze_mechanical_area_comparison.py`|多种机械面积定义对比|
|`src/postprocess/analyze_probe_force_curve.py`|力—位移拐点、终点和参考曲线分析|
|`src/postprocess/calibrate_inner_planarity.py`|由外侧接触校准内表面平坦区候选|
|`src/postprocess/plot_flat_region_2deg.py`|角度阈值平坦区及多视图诊断|
|`src/postprocess/plot_inner_planarity_trial.py`|内表面平坦度试验图|
|`src/postprocess/plot_displacement_support.py`|位移支承区域和候选面积叠加图|
|`src/postprocess/plot_displacement_probe_profiles.py`|径向位移探针剖面|

### 3.4 绘图基础

|路径|职责|
|---|---|
|`src/postprocess/raster_plot.py`|栅格绘图共享函数|
|`src/postprocess/visu.py`|结果可视化共享函数|

## 4. 高眼压机械传递实验

高眼压模块已建立独立的完整索引，见：

- [`../high_iop_mechanical_transfer_t1p25_c0p60/docs/SCRIPT_INDEX.md`](../high_iop_mechanical_transfer_t1p25_c0p60/docs/SCRIPT_INDEX.md)
- [`../high_iop_mechanical_transfer_t1p25_c0p60/docs/SYSTEM_ENGINEERING.md`](../high_iop_mechanical_transfer_t1p25_c0p60/docs/SYSTEM_ENGINEERING.md)
- [`../algorithms/README.md`](../algorithms/README.md)：历史经验算法、当前机制框架及逐文件归属
- [`../algorithms/algorithm_registry.json`](../algorithms/algorithm_registry.json)：机器可读算法代际和历史 Git blob 清单

当前三条正式入口是：

```text
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_calibration_0_to_50_5090d.sh
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_extrapolation_50_to_60_5090d.sh
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_interface_force_integrals_5090d.sh
```

## 5. 厚度敏感性分析管线

|路径|职责|
|---|---|
|`analysis/run_all.py`|按固定顺序运行完整分析、验证和产物清单|
|`analysis/common.py`|仓库根、配置、CSV/JSON、哈希和数值共享函数|
|`analysis/discover_data.py`|递归数据清点和来源分类|
|`analysis/preprocess.py`|把高眼压、厚度和材料数据整理为 tidy 表|
|`analysis/fit_pressure_model.py`|按厚度评估分式模型可识别性并拟合可识别状态|
|`analysis/extract_stiffness.py`|提取厚度—刚度代理和幂律关系|
|`analysis/sensitivity_analysis.py`|归一化敏感度、方差分解和 IOP 误差传播|
|`analysis/validate_theory.py`|检查理论输入可用性与理论/拟合一致性边界|
|`analysis/make_figures.py`|生成 11 组 PNG/SVG 图件|
|`analysis/build_report.py`|生成完整 Markdown 报告、门限和限制说明|

配置入口：`analysis/config.yaml`；当前结论：除 1.25 mm 外缺少完整多压力曲线，不能逐厚度识别分式参数。

## 6. 厚度研究专用分析

|路径|职责|
|---|---|
|`thick/code/process_experiment.py`|处理仿体/厚度实验数据|
|`thick/code/generate_placeholder_report.py`|生成明确标记为 placeholder 的结构报告，不作为 FE 证据|
|`thick/code/validate_iop_from_kgeo_material_baseline.py`|零 IOP 材料基线与 5°几何换算验证|
|`thick/code/validate_iop_baseline_additivity.py`|1.25 mm 多 IOP 下零压基线可加性验证|
|`thick/code/compare_geometry_zero_0p26_0p28.py`|0.26/0.28 mm 几何初接触参考状态对比|

这些脚本对应不同问题，不是彼此的 v1/v2 版本。

## 7. 数据构建

|路径|职责|
|---|---|
|`data/build_dataset.py`|从权威 Dryad 原始文件构建轻量派生数据、校验来源和哈希|

浏览器下载产生的 `(1)` 重复文件已在 `.gitignore` 精确排除，不参与构建。

## 8. 服务器与仓库运维

|路径|职责|
|---|---|
|`ops/bootstrap-5090d.sh`|初始化 5090d 求解环境|
|`ops/bootstrap-arch.sh`|初始化 Arch/Linux 工作环境|
|`ops/launch-indentation-sweep-5090d.sh`|5090d 通用压入扫描入口|
|`ops/launch-thickness-sweep-5090d.sh`|5090d 厚度扫描入口|
|`ops/start-thickness-calibration-5090d.sh`|启动厚度校准流程|
|`ops/sync-main-to-github.sh`|把内部 origin 的 main 同步到 GitHub|
|`ops/verify-repository.sh`|检查大文件、求解器产物、命名和仓库策略|
|`ops/audit-markdown-formulas.py`|Markdown 公式结构/渲染审计|
|`ops/normalize-markdown-math-delimiters.py`|规范数学分隔符|

`launch-indentation-sweep`、`launch-thickness-sweep` 和 `start-thickness-calibration` 分别服务不同工作流，不按文件名相似度视为旧版本。

## 9. 测试

`tests/test_*.py` 是上述脚本的契约测试，不是运行入口。主要覆盖：

- runner 参数、APDL 宏契约、重试和产物策略；
- 厚度面积、接触归零、探头力曲线；
- 高眼压当前配置、分式模型、外推和界面力；
- 高眼压原文无损合并完整性；
- 算法代际注册表、权威参数和历史 Git blob 完整性。

标准命令：

```powershell
E:\SOFTWARE\annaconda\annaconda_evn\python.exe -m pytest -q
```

## 10. 新脚本准入规则

1. 先确认能否扩展现有共享 runner/postprocessor；
2. 新文件按物理职责命名，不按“新旧状态”命名；
3. 参数变化进入 JSON/YAML 配置，不复制整个脚本；
4. 阶段性实验入口在结论冻结后删除当前副本，结果与 Git 历史保留；
5. 正式入口必须写运行 metadata、输入哈希和 Git SHA；
6. 新脚本必须同步更新本索引及对应模块索引；
7. 删除前用 `git grep` 检查调用者，并运行相关测试。
