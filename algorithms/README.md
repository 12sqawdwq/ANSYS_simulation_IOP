# IOP 修正算法总入口

本目录依据当前工作树、合并后的完整实验记录和 Git 历史，将项目中的 IOP 反演路线统一展示为**三个算法版本**。版本号表示模型从“面积单因素”到“经验输入—输出关系”再到“面积与力学传递分解”的概念迭代，不表示三个都可部署的成品，也不替代 Git 的提交历史。

这里不复制既有源码，也不创建带 `v1/v2/final` 后缀的平行实现；算法源码、结果和实验记录仍位于原权威路径，版本和回滚由 Git 管理。

## 三版本总览

统一定义零眼压结构参考后的探头增量读数：

$$
q=\frac{F_{probe}(p)-F_{probe}(0)}{A_p}
$$

其中差值是 IOP 改变造成的总耦合响应差，不是“纯 IOP 反力”。

|版本|核心关系|模型含义|当前状态|
|---|---|---|---|
|版本一：有效压平面积比换算|$p=(A_p/A_c)q$；等价地，使用外侧面积口径时 $p=(A_e/A_c)(\Delta F/A_e)$|假设探头增量力可直接按内侧有效压平面积换算|已否定为完整算法；保留为版本三的几何组成和负结果|
|版本二：经验分式反演|$p=aq/(1-bq)$|用经验增益和压力相关非线性直接描述 $p/q$|诊断算法；样本内有效但未见高压外推失败|
|版本三：力学传递效率/修正模型|$p=\eta_{eff}(p)K_A(p)q=K_A(p)q/T_{mech}(p)$|把有效面积和力学传递分开，并可等价写成全局载荷份额模型|当前研究框架；尚未独立识别，不能生产部署|

三个版本目前都不能作为真实硬件生产标定。`algorithm_registry.json` 中的 `production_algorithm_available` 仍为 `false`。

## 版本一：有效压平面积比换算

若外侧和内侧有效压平面积分别为 $A_e$ 和 $A_c$，外侧面积口径的探头压力为：

$$
q_e=\frac{\Delta F}{A_e}
$$

则版本一写为：

$$
p=\frac{A_e}{A_c}q_e=\frac{\Delta F}{A_c}
$$

若 $q$ 按完整探头面积 $A_p$ 定义，则必须写为：

$$
\boxed{p=\frac{A_p}{A_c}q}
$$

版本一在 20 mmHg 附近近似成立，但高压下系统性低估；主工作点面积法 RMSE 为 6.7007 mmHg。详细说明见 [`historical/AREA_ONLY_EFFECTIVE_APPLANATION.md`](historical/AREA_ONLY_EFFECTIVE_APPLANATION.md)。

## 版本二：经验分式反演

版本二采用用户指定的统一展示形式：

$$
\boxed{p=\frac{aq}{1-bq}}
$$

其中 $a$ 是无量纲分子增益，$b$ 的单位为 $\mathrm{mmHg^{-1}}$。历史 `Ksensor=\alpha+\beta p` 模型与其完全等价，此时：

$$
a=\alpha,\qquad b=\beta
$$

当前 0–50 mmHg 密集网格得到的诊断拟合按该展示符号为：

$$
a=1.8273148619678283,
\qquad
b=0.06531173069023494\ \mathrm{mmHg^{-1}}
$$

旧脚本和结果为了历史兼容，把分母系数命名为 `a_per_mmhg`、把分子系数命名为 `b_dimensionless`；因此它们与本目录统一展示符号的映射是：

```text
a_display = b_dimensionless
b_display = a_per_mmhg
```

不得静默交换这两个字段。该模型 0–50 mmHg 样本内 RMSE 为 0.954059 mmHg，但冻结后在 52.5–60 mmHg 未见点 RMSE 为 4.781690 mmHg，因此仍是诊断算法。详细说明见 [`historical/EMPIRICAL_KSENSOR.md`](historical/EMPIRICAL_KSENSOR.md)。

## 版本三：力学传递效率/修正模型

定义面积项：

$$
K_A(p)=\frac{A_p}{A_c(p)}
$$

若把增量探头力相对于压力—面积合力的比值定义为力学传递比：

$$
T_{mech}(p)=\frac{\Delta F_{probe}(p)}{pA_c(p)}
$$

则版本三为：

$$
\boxed{p=\frac{K_A(p)}{T_{mech}(p)}q}
$$

也可定义力学传递修正因子：

$$
\eta_{eff}(p)=\frac{1}{T_{mech}(p)}
=\frac{pA_c(p)}{\Delta F_{probe}(p)}
$$

从而得到：

$$
\boxed{p=\eta_{eff}(p)K_A(p)q}
$$

这里的 $T_{mech}$ 或 $\eta_{eff}$ 是综合力学传递量，不能与直接界面传力比例 $\tau_{interface}$ 混同。等价的全局载荷份额形式为：

$$
p=\frac{A_p}{\lambda_{load}(p)A_{IOP,proj}}q
$$

当前版本三的阻塞点是：$T_{mech}$、$\eta_{eff}$ 或 $\lambda_{load}$ 仍由已知 IOP 响应反推，尚未由未知 IOP 时的独立可观测量预测。详细说明见 [`current/MECHANISTIC_PRESSURE_TRANSFER.md`](current/MECHANISTIC_PRESSURE_TRANSFER.md)。

## 为什么版本二和版本三可能出现相同分式

若版本三在一个冻结区间内满足：

$$
K_A(p)=c_0+c_1p
$$

且 $\eta_{eff}$ 可由独立证据近似为常数，则版本三可以降阶为分式。两者即使代数外形相同，参数来源仍不同：

- 版本二直接从同一组 $p/q$ 数据拟合，是经验反演；
- 版本三要求面积和传递分别识别，或者从独立机械观测预测全局载荷份额；
- 如果版本三的参数仍由同组 $p/q$ 反推，它仍只是机制重参数化，不能宣称已独立验证。

## 目录内容

- [`historical/AREA_ONLY_EFFECTIVE_APPLANATION.md`](historical/AREA_ONLY_EFFECTIVE_APPLANATION.md)：版本一公式、假设和高压失效证据；
- [`historical/EMPIRICAL_KSENSOR.md`](historical/EMPIRICAL_KSENSOR.md)：版本二公式、参数、原始实现和退役原因；
- [`current/MECHANISTIC_PRESSURE_TRANSFER.md`](current/MECHANISTIC_PRESSURE_TRANSFER.md)：版本三定义、证据、限制和权威文件；
- [`ALGORITHM_LINEAGE.md`](ALGORITHM_LINEAGE.md)：三版本的概念演化和 Git 时间线；
- [`FILE_CLASSIFICATION.md`](FILE_CLASSIFICATION.md)：逐文件说明其所属版本和算法职责；
- [`algorithm_registry.json`](algorithm_registry.json)：机器可读三版本登记及历史 Git blob 清单。

## 版本号与 Git 时间线

三版本编号用于展示模型层级，不改写真实提交顺序。历史经验 `Ksensor` 设计在 Git 中早于面积法完整负结果；面积法被编号为版本一，是因为它代表最基础的“仅面积换算”模型，而不是因为它一定是仓库中最早提交的公式。精确时间顺序以 [`ALGORITHM_LINEAGE.md`](ALGORITHM_LINEAGE.md) 和 Git commit 为准。

## 权威性顺序

发生数值或结论冲突时按以下顺序判断：

1. 当前冻结结论：[`../high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md`](../high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md)；
2. 当前全局方向：[`../docs/IOP修正算法全局方向.md`](../docs/IOP修正算法全局方向.md)；
3. 版本三说明：[`current/MECHANISTIC_PRESSURE_TRANSFER.md`](current/MECHANISTIC_PRESSURE_TRANSFER.md)；
4. 完整阶段原文：[`../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md`](../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md)；
5. Git 中对应提交的原文件。

本目录负责分类和导航，不覆盖实验原文，也不把任何诊断模型升级为生产算法。
