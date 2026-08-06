# 历史代：经验线性 Ksensor 反演

```text
algorithm_generation: historical_empirical_ksensor
lifecycle_status: retired_diagnostic_only
first_explicit_design_commit: 4bc0f9ff21df849da629d09bf0ef95ce7d73aec9
demoted_by_commit: e04b0c989a3038ffc9c8b401a8db79a8bd9206d0
classification_date: 2026-08-06
```

## 1. 历史算法定义

历史代先建立同一推进状态下的零眼压结构参考：

$$
\Delta F(p)=F(p)-F(0)
$$

再按完整探头面积换算扣除后的探头压力：

$$
q=\frac{\Delta F}{A_p}
$$

由已知 FE 输入 IOP 定义经验系数：

$$
K_{sensor,\Delta}^{FE}(p)=\frac{p}{q}
$$

并假设：

$$
K_{sensor}(p)=\alpha+\beta p
$$

代入 $p=K_{sensor}(p)q$ 后得到历史显式反演式：

$$
\boxed{
p=\frac{\alpha q}{1-\beta q}
}
$$

必须满足 $1-\beta q>0$。

## 2. 历史冻结参数

|工作点|$\alpha$|$\beta$/mmHg⁻¹|历史用途|
|---|---:|---:|---|
|0.259875 mm 主状态|1.7958537965375994|0.06706030329458683|20–40 mmHg 高眼压预注册预测|
|0.28 mm 敏感性状态|1.6587166492607621|0.06254272079315978|推进量对照|

这些参数由当时已有的稀疏压力响应形成，最早以明确算法设计形式出现在提交 `4bc0f9f`。它们后来继续出现在密集压力配置中，但字段已经明确命名为 `frozen_sensor_models_for_diagnostic_only`。

## 3. 历史原文件

以下文件不重新复制到当前工作树；用 Git 提交和 blob 精确恢复。

|阶段|提交与原路径|Git blob|作用|
|---|---|---|---|
|首次明确设计|`4bc0f9f:thick/experiments/high_iop_mechanical_transfer_t1p25_c0p60/EXPERIMENT_DESIGN.md`|`61e0dc0327b36cf588c1be727854345db7ab6c9d`|定义线性 `Ksensor` 假设和两组参数|
|正式配置|`23d4f22:high_iop_mechanical_transfer_t1p25_c0p60/run_spec_full.json`|`11c14e20be33126f1d60cd8141b6c33a011f7d29`|冻结 `alpha/beta`、材料和工作点|
|正式实现|`23d4f22:high_iop_mechanical_transfer_t1p25_c0p60/postprocess_full_high_iop.py`|`52b6cb237e15c8eddffeddd96adef86740250c81`|执行 $\alpha q/(1-\beta q)$ 并计算误差|
|首轮结果|`33e9f46:high_iop_mechanical_transfer_t1p25_c0p60/FULL_EXPERIMENT_RESULT.md`|`334eea7ff5c60beb9515a0b04ecc2871520cdb86`|报告 0/20/25/30/35/40 mmHg 结果|

恢复示例：

```bash
git show 23d4f22:high_iop_mechanical_transfer_t1p25_c0p60/postprocess_full_high_iop.py
git show 23d4f22:high_iop_mechanical_transfer_t1p25_c0p60/run_spec_full.json
```

完整设计和结果原文也已无损并入：

- [`../../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md`](../../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md) 中的 `EXPERIMENT_DESIGN.md`、`FULL_EXPERIMENT_RESULT.md` 段落。

## 4. 当前工作树中为何仍能看到旧参数

以下当前文件含有旧算法兼容字段，但不代表旧算法仍是当前方向：

|当前文件|保留内容|分类|
|---|---|---|
|`high_iop_mechanical_transfer_t1p25_c0p60/config/calibration_0_to_50.json`|`frozen_sensor_models_for_diagnostic_only`|历史诊断输入|
|`high_iop_mechanical_transfer_t1p25_c0p60/config/extrapolation_50_to_60.json`|相同旧参数及冻结分式参数|混合评估配置|
|`high_iop_mechanical_transfer_t1p25_c0p60/scripts/postprocess/postprocess_pressure_sweep.py`|输出 `frozen_model_iop_calc_diagnostic_mmhg`|兼容历史诊断列；脚本主体同时承担当前数据汇总|
|`high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_290d0544_iop_0_to_50_step2p5_summary.json`|历史模型诊断预测和误差|不可变结果证据|
|`high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop_0_to_60_step2p5_summary.json`|延续历史诊断列|不可变外推证据|

所以不能简单地把包含 `alpha/beta` 的整个当前后处理脚本删除或归为旧文件；应把其中的旧模型列视为兼容诊断层。

## 5. 退役原因

历史代被降级，不是因为代数求解错误，而是因为物理解释和可迁移性不足：

1. `Ksensor=p/q` 直接使用已知输入 IOP 定义，不能作为未知 IOP 时的独立正向观测；
2. 单个经验系数同时吸收面积变化、组织预张力、界面传力、旁路载荷和边界效应；
3. 参数来自单一厚度、材料、推进量和有限压力点，不能直接迁移；
4. 低压存在接触启用/载荷路径转换，单一固定曲线不能无条件覆盖；
5. 高压增益继续变化，固定斜率不能无条件外推；
6. 公式与当前分式外形相同并不提供新的独立物理证据。

提交 `e04b0c9` 建立面积—传力分解方向后，旧模型正式降为历史诊断。当前配置和文档继续保留参数，是为了复现实验和比较算法演化，不是为了恢复其生产地位。

## 6. 允许的使用方式

允许：

- 复现历史报告；
- 与新模型做同一数据上的诊断对照；
- 检查历史运行产物是否一致；
- 研究为什么不同算法会得到相似分式外形。

禁止：

- 直接用于真实硬件；
- 对 60 mmHg、其他厚度或推进量无条件外推；
- 把 `Ksensor` 称为几何面积比或直接力传递效率；
- 因当前配置仍保留参数而声称该算法仍是主算法。
