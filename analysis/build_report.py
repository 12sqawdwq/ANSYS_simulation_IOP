from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from common import fmt, load_config, md_table, output_dir


def bool_text(value: object) -> str:
    if pd.isna(value):
        return "不可评价"
    return "满足" if bool(value) else "不满足"


def build(config: dict | None = None) -> Path:
    config = config or load_config()
    out = output_dir(config)
    inventory = pd.read_csv(out / "data_inventory.csv")
    tidy = pd.read_csv(out / "tidy_data.csv")
    fitted = pd.read_csv(out / "fitted_parameters.csv")
    pressure_pred = pd.read_csv(out / "pressure_fit_predictions.csv")
    stiffness = pd.read_csv(out / "stiffness_parameters.csv")
    power = pd.read_csv(out / "stiffness_power_law.csv").iloc[0]
    sensitivity = pd.read_csv(out / "sensitivity_results.csv")
    threshold = pd.read_csv(out / "threshold_evaluation.csv")
    errors = pd.read_csv(out / "pressure_error_summary.csv")
    theory_inputs = pd.read_csv(out / "theory_input_availability.csv")
    agreement = pd.read_csv(out / "agreement_statistics.csv").iloc[0]

    successful = fitted[fitted["fit_status"] == "success"].copy()
    parameter_view = successful[
        [
            "state",
            "a_per_mmhg",
            "b_dimensionless",
            "g0_1_over_b",
            "lambda_a_over_b_per_mmhg",
            "pstar_b_over_a_mmhg",
            "r2_probe_space",
            "rmse_probe_mmhg",
            "mae_probe_mmhg",
            "parameter_correlation_a_b",
            "identifiability_status",
        ]
    ].rename(
        columns={
            "state": "状态",
            "a_per_mmhg": "a (1/mmHg)",
            "b_dimensionless": "b",
            "g0_1_over_b": "1/b",
            "lambda_a_over_b_per_mmhg": "a/b (1/mmHg)",
            "pstar_b_over_a_mmhg": "b/a (mmHg)",
            "r2_probe_space": "R²(Pprobe)",
            "rmse_probe_mmhg": "RMSE(Pprobe)",
            "mae_probe_mmhg": "MAE(Pprobe)",
            "parameter_correlation_a_b": "corr(a,b)",
            "identifiability_status": "辨识状态",
        }
    )

    sensitivity_view = sensitivity[
        sensitivity["output"].isin(
            [
                "a",
                "b",
                "G0=1/b",
                "lambda=a/b",
                "zero_iop_baseline_force",
                "total_probe_force_at_20",
                "G_eff_at_20=P_probe/P_IOP",
                "shared_calibration_iop_prediction",
            ]
        )
    ][
        [
            "output",
            "status",
            "log_sensitivity",
            "sensitivity_ci95_low",
            "sensitivity_ci95_high",
            "maximum_relative_deviation_from_reference",
            "coefficient_of_variation",
        ]
    ].rename(
        columns={
            "output": "输出",
            "status": "状态",
            "log_sensitivity": "S_h",
            "sensitivity_ci95_low": "S 95%CI下限",
            "sensitivity_ci95_high": "S 95%CI上限",
            "maximum_relative_deviation_from_reference": "最大相对偏差",
            "coefficient_of_variation": "CV",
        }
    )

    proxy = sensitivity[sensitivity["output"] == "G_eff_at_20=P_probe/P_IOP"].iloc[0]
    error20 = errors[errors["scope"] == "thickness_scan_at_20_mmhg_total_error"].iloc[0]
    shift20 = errors[errors["scope"] == "thickness_scan_at_20_mmhg_thickness_attributable_shift"].iloc[0]
    normal_error = errors[errors["scope"] == "reference_curve_normal_iop_model_error"].iloc[0]
    high_error = errors[errors["scope"] == "reference_curve_high_iop_model_error"].iloc[0]
    proxy_check = threshold[threshold["quantity"] == "G_eff_at_20 proxy"].iloc[0]

    n_pressure = int((tidy["record_type"] == "pressure_scan").sum())
    n_endpoints = int((tidy["record_type"] == "thickness_pressure_endpoint").sum())
    n_force = int((tidy["record_type"] == "force_displacement").sum())
    n_thickness = int(
        tidy.loc[tidy["record_type"] == "thickness_pressure_endpoint", "eyelid_thickness_mm"].nunique()
    )
    no_theory = agreement["status"] != "complete"
    exact_not_estimable = all(
        threshold.loc[threshold["is_exact_requested_parameter"] == True, "decision"]
        == "not_evaluable_due_to_nonidentifiability"
    )
    conclusion_class = "C（当前数据不能支持一般性结论；这是不可识别性结论，不等同于证明相反效应）" if exact_not_estimable else "待判定"

    residual_notes = []
    for state, group in pressure_pred.groupby("state"):
        low = group.loc[group["p_iop_mmhg"] <= 7.5, "residual_probe_mmhg"].abs().max()
        high = group.loc[group["p_iop_mmhg"] >= 10, "residual_probe_mmhg"].abs().max()
        residual_notes.append(f"`{state}`：0–7.5 mmHg 最大绝对探头空间残差 {fmt(low)} mmHg；≥10 mmHg 为 {fmt(high)} mmHg")

    report = rf"""# 眼睑厚度对重参数化压力系数影响的有限元验证

## 执行摘要

**最终判定：{conclusion_class}。**

现有有限元结果只在眼睑厚度 1.25 mm 下提供完整多眼压曲线；其余厚度只有独立的 0 与 20 mmHg 端点。因此，除 1.25 mm 外，两个曲线参数不能被分别识别，无法计算逐厚度的 $a$、$b$、$1/b$、$a/b$、相应 CV 或厚度灵敏度。任何把 20 mmHg 单端点拆成 $G_0$ 与 $\lambda$ 的做法都会引入无穷多组等价解。

另一方面，20 mmHg 下可直接观测的组合增益 $G_{{eff,20}}=P_{{probe}}/P_{{IOP}}=G_0/(1+20\lambda)$ 在 0.80–2.00 mm 厚度范围内确实较稳定：对数灵敏度为 {fmt(proxy['log_sensitivity'])}（95% CI {fmt(proxy['sensitivity_ci95_low'])} 至 {fmt(proxy['sensitivity_ci95_high'])}），相对 1.25 mm 的最大偏差为 {fmt(100*proxy['maximum_relative_deviation_from_reference'])}%、CV 为 {fmt(100*proxy['coefficient_of_variation'])}%。这只能支持“20 mmHg、0.28 mm 推进时，零基线后的单点有效增益厚度敏感性较低”，不能外推为 $G_0$ 与 $\lambda$ 各自稳定，更不能证明其相对 $a,b$ 的敏感性必然更低。

## 1. 数据概况和有效工况数量

- 递归登记数据文件 {len(inventory)} 个；完整清单见 [`data_inventory.csv`](data_inventory.csv)。
- 统一长表共 {len(tidy)} 行：多眼压曲线 {n_pressure} 行、全厚度 0/20 mmHg 端点 {n_endpoints} 行、力—位移曲线 {n_force} 行。
- 厚度端点共 {n_thickness} 个厚度：0.80、1.00、1.20、1.25、1.40、1.50、1.60、1.80、2.00 mm。
- 1.25 mm 多眼压扫描为 0–60 mmHg、2.5 mmHg 步长，包含 0.259875 与 0.28 mm 两个推进状态。
- 厚度×多眼压矩阵未形成；材料模量、探头面积和曲率也没有与厚度正交交叉。因此多因素 partial $R^2$、ANOVA 或 Sobol 指数不可估计。

## 2. 参数及单位检查

内部压力统一使用 mmHg，同时保存 Pa；换算使用 $1\,\mathrm{{mmHg}}={config['units']['pa_per_mmhg']}\,\mathrm{{Pa}}$。长度用 mm、力用 N、结构刚度用 N/mm、面积用 mm²。

模型拟合使用 `delta_probe_pressure_mmhg`，即相对独立 0 IOP 基线的探头压力增量。绝对 `probe_pressure_mmhg` 在 0 IOP 时仍包含约束组织所需的非零反力，与题设零截距模型不相容，故只保留、不用于拟合。探头面积为 {config['geometry']['probe_area_mm2']:.8f} mm²。单位反算误差记录在 [`data_quality_summary.json`](data_quality_summary.json)。完整映射及含义见 [`data_dictionary.csv`](data_dictionary.csv)。

## 3. $a,b,1/b,a/b$ 的直接拟合结果

拟合目标为原始探头压力尺度：

$$P_{{probe}}=\frac{{G_0 P_{{IOP}}}}{{1+\lambda P_{{IOP}}}}.$$

每个可拟合状态均使用全部 0–60 mmHg 工况，采用非线性最小二乘；1000 次非零压力点成对 bootstrap 并固定原点。线性化仅作为交叉验证，结果保存在 [`fitted_parameters.csv`](fitted_parameters.csv)。

{md_table(parameter_view)}

参数 CI 采用 bootstrap 百分位区间，标准误采用局部雅可比协方差。`corr(a,b)` 绝对值超过配置阈值 0.95 时标为弱辨识。有限元状态是确定性设计点，bootstrap 表示对当前压力网格/曲线形状的重采样稳定性，不是人群或实验重复的不确定性。

残差并非均匀随机散布：{'；'.join(residual_notes)}。低压接触启用区存在结构性模型偏差，完整残差见 [`pressure_fit_predictions.csv`](pressure_fit_predictions.csv) 和图 11。

![压力曲线](figures/fig01_pressure_curves.svg)

![参数与厚度](figures/fig02_parameters_vs_thickness.svg)

![残差](figures/fig11_pressure_fit_residuals.svg)

## 4. $k_l,k_{{c,0}},\alpha$ 的提取结果

现有 7 条厚度力—位移曲线可在 0.20–0.35 mm 目标窗口提取总探头反力斜率。该斜率同时包含眼睑、角膜、bonded 界面和整体运动，故严格记为 $k_{{probe,coupled}}$，不能命名为 $k_l$。逐厚度的局部线性、割线、平均切线和目标点切线结果见 [`stiffness_parameters.csv`](stiffness_parameters.csv)。

耦合刚度幂律拟合给出 $k_{{probe,coupled}}=C h^m$，其中 $m={fmt(power['exponent_m_for_k_proportional_h_to_m'])}$；若强行写成题设 $C h^{{-n}}$，则 $n={fmt(power['n_for_k_proportional_h_to_minus_n'])}$（95% CI {fmt(power['n_ci95_low'])} 至 {fmt(power['n_ci95_high'])}，对数空间 $R^2={fmt(power['r2_log_space'])}$）。因此该**耦合结构刚度**不支持 $n=1$ 的一维逆厚度规律；但这不能作为眼睑单体 $k_l$ 的直接反证，因为观测量不同。

每个 IOP 仅有一个保留推进状态，没有每个压力下的角膜力—位移斜率，故 $k_c(P)$、$k_{{c,0}}$ 与 $\alpha$ 均不可识别。材料弹性模量未被用作结构刚度替代。审计见 [`mechanical_identifiability.csv`](mechanical_identifiability.csv)。

![耦合刚度](figures/fig05_coupled_stiffness_power_law.svg)

![角膜刚度不可识别](figures/fig06_corneal_stiffness_identifiability.svg)

![刚度比不可识别](figures/fig07_stiffness_ratio_identifiability.svg)

## 5. 理论值与拟合值的一致性

$A_p$、$s$、$R_c$ 可用，但独立 $k_l$、$k_{{c,0}}$、$\alpha$ 缺失，因此 $a_{{theory}}$、$b_{{theory}}$、$G_{{0,theory}}$、$\lambda_{{theory}}$ 不能计算。可比较配对数为 {int(agreement['n_pairs'])}；Pearson、Spearman、相对误差、Bland–Altman 和一致性回归均无定义，而不是“相关系数为零”。现有面积代理推导依赖未独立验证的 $A_{{c,5^\circ}}$ 与耦合假设，未冒充独立理论验证。

![理论一致性审计](figures/fig08_theory_fit_identity.svg)

## 6. 厚度对四个参数的灵敏度

{md_table(sensitivity_view)}

四个精确参数的厚度灵敏度与 CV 均不可估计。可观测组合 $G_{{eff,20}}$ 的三项代理检查为：灵敏度阈值 {bool_text(proxy_check['passes_sensitivity_threshold'])}，相对偏差阈值 {bool_text(proxy_check['passes_relative_deviation_threshold'])}，共享标定误差阈值 {bool_text(proxy_check['passes_iop_error_threshold'])}。即使代理全部通过，也不能替代对 $G_0$ 和 $\lambda$ 的分别检验。

![归一化灵敏度](figures/fig03_normalized_sensitivity.svg)

![变异系数](figures/fig04_coefficient_of_variation.svg)

![灵敏度排序](figures/fig10_sensitivity_ranking.svg)

## 7. 厚度对最终眼压误差的影响

以 1.25 mm、0.28 mm 推进的完整压力曲线得到共享 $G_0,\lambda$，再用于各厚度 20 mmHg 端点。总误差 MAE 为 {fmt(error20['mae_mmhg'])} mmHg，RMSE 为 {fmt(error20['rmse_mmhg'])} mmHg，最大绝对误差为 {fmt(error20['maximum_absolute_error_mmhg'])} mmHg，最大相对误差为 {fmt(100*error20['maximum_absolute_relative_error'])}%。相对 1.25 mm 参考预测的纯厚度位移最大绝对值为 {fmt(shift20['maximum_absolute_error_mmhg'])} mmHg。

厚度矩阵只含 20 mmHg，因此“厚度效应在高眼压是否被放大”无法直接检验。仅对 1.25 mm 的模型误差分层时，正常范围 MAE 为 {fmt(normal_error['mae_mmhg'])} mmHg，高眼压范围 MAE 为 {fmt(high_error['mae_mmhg'])} mmHg；这是模型随压力的误差，不是厚度×压力交互效应。

![眼压误差](figures/fig09_iop_error_vs_thickness.svg)

## 8. 结论成立的参数范围

当前唯一可支持的窄结论是：在眼睑厚度 0.80–2.00 mm、角膜厚度 0.60 mm、固定材料设定、探头面积 {config['geometry']['probe_area_mm2']:.4f} mm²、推进 0.28 mm、IOP=20 mmHg 且逐厚度使用独立 0 IOP 基线时，组合增益 $G_{{eff,20}}$ 的厚度敏感性较低。此结论不等价于低压极限 $G_0=1/b$ 稳定，也不包含高眼压、不同推进、不同模量、曲率或面积的范围。

## 9. 不支持该结论的条件

- 不能声称逐厚度 $a,b,1/b,a/b$ 已完成拟合；除 1.25 mm 外缺少足够压力点。
- 不能声称重参数化相对 $a,b$ 降低了厚度敏感性；两组量都没有逐厚度可比估计。
- 不能以耦合探头刚度代替 $k_l$，也不能以材料模量代替结构刚度。
- 不能计算理论值—拟合值相关性或 Bland–Altman 一致性；独立理论参数缺失。
- 不能判断厚度效应在高眼压下是否放大；全厚度矩阵只有 20 mmHg。
- 低压接触启用区有系统残差，单一二参数有理式并未完全描述全部 FE 曲线形状。
- 接触归零面积和 5°面积仍是代理/候选定义，不作为独立力学标定真值。

完成验证所需的最小新增矩阵为：至少 5 个压力点（建议 0、10、20、40、60 mmHg）× 当前 9 个厚度，并在每个压力下保存目标窗口内至少 5 个位移点；同时分别积分眼睑承载、角膜承载、界面力和整体支撑反力。这样才能对每个厚度拟合两个压力参数，并独立得到 $k_l$ 与 $k_c(P)$。

## 10. 可直接用于论文 Results 的中文结论段落

在当前有限元数据中，眼睑厚度 0.80–2.00 mm 的扫描仅在 20 mmHg 下提供了逐厚度压力端点，而完整的 0–60 mmHg 压力曲线仅存在于 1.25 mm 厚度。因此，除参考厚度外，$a$、$b$、$1/b$ 和 $a/b$ 无法分别识别，也不能比较重参数化前后的厚度灵敏度。作为受限证据，20 mmHg 下的零基线组合增益 $P_{{probe}}/P_{{IOP}}$ 对厚度的归一化敏感度为 {fmt(proxy['log_sensitivity'])}，相对参考厚度的最大偏差为 {fmt(100*proxy['maximum_relative_deviation_from_reference'])}%，显示单点增量传递对厚度较不敏感。然而，该组合量等于 $G_0/(1+20\lambda)$，不能证明 $G_0=1/b$ 与 $\lambda=a/b$ 各自稳定。故本研究现有有限元结果**不能支持**“重参数化参数普遍比 $a$、$b$ 或直接测量量更不受眼睑厚度影响”的一般性结论；最多只能表述为：在固定材料、0.28 mm 推进和 20 mmHg 工作点，独立零基线后的有效传递增益呈较低厚度敏感性，仍需厚度×多眼压交叉扫描验证。

## 可复现性

运行命令：

```powershell
E:\\SOFTWARE\\annaconda\\annaconda_evn\\python.exe analysis\\run_all.py
```

配置见 [`config.yaml`](../config.yaml)，排除记录见 [`exclusion_log.csv`](exclusion_log.csv)，输出清单见 [`output_manifest.csv`](output_manifest.csv)。所有原始数据均只读。
"""
    path = out / "report.md"
    path.write_text(report, encoding="utf-8")
    return path


if __name__ == "__main__":
    build()
