# 当前代：面积—传力分解与全局载荷份额框架

```text
algorithm_generation: current_mechanistic_framework
lifecycle_status: research_framework_not_production
introduced_by_commit: e04b0c989a3038ffc9c8b401a8db79a8bd9206d0
frozen_conclusion_commit: 956a0ec87abcbd168a8d1e34445307d0d906c6cd
classification_date: 2026-08-06
```

## 1. 当前代算法到底是什么

当前代不是一组已经冻结的万能数值参数，而是一套必须分别识别几何和传力机制的算法设计。

首先用同一工作点的零眼压状态建立结构参考：

$$
\Delta F_{probe}(p)=F_{probe}(p)-F_{probe}(0)
$$

$$
q=P_{probe}=\frac{\Delta F_{probe}}{A_p}
$$

其中 $\Delta F$ 是 IOP 改变造成的总耦合响应差，不是“纯 IOP 反力”。

面积项定义为：

$$
K_A(p)=\frac{A_p}{A_c(p)}
$$

综合压力—面积修正定义为：

$$
\eta_{eff}(p)=\frac{pA_c(p)}{\Delta F_{probe}(p)}
$$

得到当前代总式：

$$
\boxed{p=\eta_{eff}(p)K_A(p)q}
$$

RST 直接界面力可进一步分解：

$$
\tau_{interface}
=\frac{\Delta F_{eyelid-cornea}}{\Delta F_{probe}},
\qquad
\chi=\frac{pA_c}{\Delta F_{eyelid-cornea}}
$$

$$
\eta_{eff}=\tau_{interface}\chi
$$

因此，$\eta_{eff}$ 不是单纯的“眼睑传力效率”，而是直接界面传力与压力—面积等效关系的乘积。

## 2. 等价的全局载荷份额形式

若完整内压投影合力为 $pA_{IOP,proj}$，探头增量反力占该合力的份额为 $\lambda(p)$，则：

$$
\boxed{
p=\frac{A_p}{\lambda(p)A_{IOP,proj}}q
}
$$

该形式把接触面积、边界旁路、组织刚度和界面传力对总响应的影响集中到 $\lambda$。当前结果说明这个框架具有合理机械解释，但现有 $\lambda$ 仍由已知 $p/q$ 反推，尚未由未知 IOP 时可观测的独立机械量预测。

## 3. 固定分式只是有条件的降阶形式

如果在一个已验证区间内：

- $K_A(p)=c_0+c_1p$ 近似成立；
- $\eta_{eff}$ 可视为常数，或其变化已由独立子模型给出；

则可得到：

$$
p=\frac{bq}{1-aq}
$$

当前固定 FE 配置下，0–50 mmHg 的经验逆向拟合为：

$$
a=0.06531173069023494\ \mathrm{mmHg^{-1}},
\qquad
b=1.8273148619678283
$$

样本内 RMSE 为 0.954059 mmHg。但冻结参数后的 52.5–60 mmHg 未见点 RMSE 为 4.781690 mmHg，60 mmHg 高估 6.964397 mmHg。因此：

- 该式可以描述当前配置的 0–50 mmHg 样本；
- 不能称为已经通过外推的当前生产算法；
- 不能无条件用于 60 mmHg、其他厚度、推进量、材料或真实硬件；
- 不允许把未见点重新并入拟合后，再声称原模型通过外推验证。

## 4. 当前代文件

### 4.1 权威设计与结论

|文件|作用|
|---|---|
|[`../../docs/IOP修正算法全局方向.md`](../../docs/IOP修正算法全局方向.md)|当前代算法的全局定义和参数识别流程|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md`](../../high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md)|冻结数值、证伪结果及适用边界|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/docs/intermediate/MECHANICAL_TRANSFER_PATH.md`](../../high_iop_mechanical_transfer_t1p25_c0p60/docs/intermediate/MECHANICAL_TRANSFER_PATH.md)|面积、界面力、综合修正和载荷份额的路径审计|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md`](../../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md)|全部阶段原文和失败路径|

### 4.2 当前分析实现

|文件|算法角色|状态|
|---|---|---|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/fit_rational_piop_vs_pprobe.py`](../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/fit_rational_piop_vs_pprobe.py)|拟合固定分式|样本内诊断，不是生产实现|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/derive_forward_rational_parameters.py`](../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/derive_forward_rational_parameters.py)|面积和综合修正代理的局部参数化|含已知 IOP，存在闭环|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/derive_global_load_share_model.py`](../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/derive_global_load_share_model.py)|载荷份额机制重参数化|机制解释，不是独立验证|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/postprocess/postprocess_interface_force_integrals.py`](../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/postprocess/postprocess_interface_force_integrals.py)|提取 $\tau_{interface}$、$\chi$ 和力平衡|当前机制证据|
|[`../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/evaluate_iop60_extrapolation.py`](../../high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/evaluate_iop60_extrapolation.py)|冻结模型的未见高压检验|已证明固定参数外推失败|

### 4.3 当前证据

|文件|证据|
|---|---|
|`results/20260730_rational_regression_0_to_50_step2p5.json`|0–50 mmHg 逆向分式参数和样本内误差|
|`results/20260731_forward_rational_parameters_ac5_proxy.json`|面积＋综合修正代理及循环性警告|
|`results/20260731_3ce7c957_interface_force_integrals_summary.json`|21 点直接界面力积分|
|`results/20260731_global_load_share_derivation.json`|全局载荷份额重参数化|
|`results/20260731_5017b619_iop60_frozen_model_extrapolation.json`|52.5–60 mmHg 冻结外推失败证据|

上述结果均位于 `high_iop_mechanical_transfer_t1p25_c0p60/` 下。

## 5. 形成可部署算法还缺什么

当前代要成为生产算法，至少需要：

1. 在未知 IOP 条件下由工作点小扰动、切线刚度和完整轴向平衡独立预测 $\lambda(p)$，或分别独立预测 $A_c(p)$ 与 $\eta_{eff}(p)$；
2. 在看验证集之前冻结参数；
3. 在新压力、厚度、推进量、材料和网格上验证；
4. 与真实硬件的零点、力传感器比例和动态特性对齐；
5. 明确低压接触启用段和高压增益变缓段的门控；
6. 给出分母安全裕度、输入范围和失败返回策略。

在这些条件满足之前，“当前代”表示**当前认可的研究方向**，不表示已发布的固件算法。
