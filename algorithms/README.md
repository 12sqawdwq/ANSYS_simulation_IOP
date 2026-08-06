# IOP 修正算法总入口

本目录依据当前工作树、合并后的完整实验记录和 Git 历史，对项目中的 IOP 反演算法做**概念分代和文件归属**。这里不复制现有脚本，也不再制造一套带 `new/old/v2/final` 后缀的实现；算法源码、结果和实验记录仍保留在原权威路径，版本由 Git 提交确定。

## 结论先行

项目确实存在两代主要算法设计，但不能理解为“两套都可部署的成品算法”。

|代际|算法设计|生命周期状态|能否作为生产标定|
|---|---|---|---|
|历史代|经验线性 `Ksensor`：$K_{sensor}(p)=\alpha+\beta p$，反演为 $p=\alpha q/(1-\beta q)$|已退役，仅保留历史诊断|不能|
|当前代|面积—传力分解：$p=\eta_{eff}(p)K_A(p)q$；等价的全局载荷份额框架为 $p=A_pq/[\lambda(p)A_{IOP,proj}]$|当前研究框架，尚未完成独立参数识别|不能，仍需独立验证|

其中：

$$
q=\frac{F_{probe}(p)-F_{probe}(0)}{A_p},
\qquad
K_A(p)=\frac{A_p}{A_c(p)}
$$

当前代只有在面积模型和力传递修正分别通过验证后，才允许简化为固定分式：

$$
p=\frac{bq}{1-aq}
$$

0–50 mmHg 的固定分式虽然样本内拟合良好，但在冻结参数后的 52.5–60 mmHg 未见点上系统性高估，因此它是**当前框架下的诊断候选**，不是“新版本生产算法”。

## 为什么两代公式看起来相同

历史代可由

$$
K_{sensor}(p)=\alpha+\beta p,
\qquad p=K_{sensor}(p)q
$$

整理为

$$
p=\frac{\alpha q}{1-\beta q}
$$

当前研究中的局部固定分式也是 $p=bq/(1-aq)$。两者代数外形相同，但含义不同：

- 历史代把面积、传力、边界分流和预张力全部压缩进一个经验 `Ksensor`；
- 当前代要求先区分 $K_A$、直接界面传力、压力—面积等效修正和全局载荷份额；
- 当前分式参数如果仍由同一组 $p/q$ 数据识别，就只能算经验拟合或机制重参数化，不能算独立正向验证。

因此，**不能只根据是否使用分式公式判断新旧版本**。

## 目录内容

- [`current/MECHANISTIC_PRESSURE_TRANSFER.md`](current/MECHANISTIC_PRESSURE_TRANSFER.md)：当前代算法的定义、证据、限制和权威文件；
- [`historical/EMPIRICAL_KSENSOR.md`](historical/EMPIRICAL_KSENSOR.md)：历史代算法的公式、参数、原始实现和退役原因；
- [`ALGORITHM_LINEAGE.md`](ALGORITHM_LINEAGE.md)：从历史代到当前代的 Git 时间线；
- [`FILE_CLASSIFICATION.md`](FILE_CLASSIFICATION.md)：逐文件说明哪些属于当前代、历史代、混合兼容层或诊断分支；
- [`algorithm_registry.json`](algorithm_registry.json)：机器可读分类及历史 Git blob 清单。

## 权威性顺序

发生表述冲突时按以下顺序判断：

1. 当前冻结结论：[`../high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md`](../high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md)；
2. 当前全局方向：[`../docs/IOP修正算法全局方向.md`](../docs/IOP修正算法全局方向.md)；
3. 当前代说明：[`current/MECHANISTIC_PRESSURE_TRANSFER.md`](current/MECHANISTIC_PRESSURE_TRANSFER.md)；
4. 完整阶段原文：[`../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md`](../high_iop_mechanical_transfer_t1p25_c0p60/docs/EXPERIMENT_RECORD.md)；
5. Git 中对应提交的原文件。

本目录负责分类和导航，不覆盖实验原文，也不把诊断模型升级为生产算法。
