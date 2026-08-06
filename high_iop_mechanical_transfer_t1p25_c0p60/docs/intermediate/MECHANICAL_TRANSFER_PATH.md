# 中间路径：从几何面积到全局载荷份额

```text
status: concluded
opened_at: 2026-07-30
last_updated_at: 2026-08-06
base_git_commit: 61eb289
question: 面积、界面传力或全局载荷份额能否在未知 IOP 条件下独立给出正向模型？
main_conclusion_sync: ../MAIN_CONCLUSIONS.md（第 3、6、7、8 节）
```

## 1. 路径为什么启动

首轮 20–40 mmHg 结果中，5°面积比例随压力变化，但简单面积换算在高压系统性低估。需要区分三种可能：

1. 几何面积本身是否计算错误；
2. 探头增量力是否没有完整传到眼睑—角膜界面；
3. 即使界面力已知，它与 `IOP × 5°几何面积` 是否仍不等价。

完整阶段文档全文见 [`../EXPERIMENT_RECORD.md`](../EXPERIMENT_RECORD.md) 中以下原文段落：

- `AREA_RATIO_K_RESULT.md`；
- `AREA_RATIO_ERROR_ANALYSIS.md`；
- `FORWARD_RATIONAL_PARAMETER_DERIVATION.md`；
- `FORWARD_INVERSE_RIGOR_AUDIT.md`；
- `INTERFACE_FORCE_INTEGRAL_RESULT.md`；
- `GLOBAL_LOAD_SHARE_DERIVATION.md`；
- `ETA_EFF_EFFECTIVE_CORRECTION_ANALYSIS.md`。

## 2. 阶段 A：面积公式

检验式：

$$
\Delta F_{probe}\stackrel{?}{=}pA_{c,5^\circ}
$$

观察：面积法在 20 mmHg 误差仅 -0.5815 mmHg，但在 40 mmHg 误差达到 -11.2280 mmHg；传递因子从 0.97093 降至 0.71930。为使 40 mmHg 精确成立，需要把实际 5°面积人为缩小 28.07%，远大于表面/投影口径约 0.38% 的理论差异。

阶段结论：几何离散可能贡献小误差，但不能解释主要系统偏差；禁止通过调整角度阈值吸收标定误差。

## 3. 阶段 B：综合修正代理

定义：

$$
\eta_{eff}=\frac{pA_{c,5^\circ}}{\Delta F_{probe}}
$$

10–50 mmHg 中它近似线性，进而产生与逆向分式接近的局部参数。但该量的分子直接使用已知输入 $p$，因此只是把原 FE 输入—输出关系重写为面积和修正因子乘积。

阶段结论：数值重建成功不等于独立正向验证；必须明确循环性。

## 4. 阶段 C：RST 直接界面力

预注册的独立量：

$$
\tau_{interface}=\frac{\Delta F_{eyelid-cornea}}{\Delta F_{probe}}
$$

21 个压力点完成 CONTA174 力矢量直接积分。稳定区中 $\tau$ 只从 0.98062 降到 0.91577。单独使用界面力和 5°面积时，50 mmHg 仅预测 29.7807 mmHg；21 点 RMSE 9.54752 mmHg。

因子分解：

$$
\eta_{eff}=\tau_{interface}\chi,
\qquad
\chi=\frac{pA_{c,5^\circ}}{\Delta F_{eyelid-cornea}}
$$

10–50 mmHg 中 $\chi$ 从 0.88738 升至 1.67894，是综合修正增长的主要来源。

阶段结论：“高压时更少的力到达界面”不是主要解释；界面力和压力—面积等效力不是同一物理量。

## 5. 阶段 D：全局载荷份额

将完整内压投影合力按全局载荷份额 $\lambda$ 分流，可写成：

$$
p=\frac{A_p}{\lambda(p)A_{IOP,proj}}q
$$

$1/\lambda$ 的局部线性可自然导出分式形式，从而解释为什么经验分式有效。但当前 $\lambda$ 仍由已知 $p/q$ 反推，未由独立机械测量预测。

阶段结论：这是合理的机制重参数化，不是生产正向模型。

## 6. 外推证伪

冻结 0–50 mmHg 的分式参数后，52.5–60 mmHg 四点均系统性高估，RMSE 4.781690 mmHg，60 mmHg 高估 6.964397 mmHg。散点仍连续，说明固定斜率假设失效，而不是出现新的接触不稳定。

## 7. 路径关闭判定

本路径已回答原问题：

- 几何面积：可诊断，不足以标定；
- 直接界面传力：可独立提取，但与 5°面积组合仍不足；
- 综合修正：可重建，但含已知 IOP，存在代数闭环；
- 全局载荷份额：给出机制框架，但尚不能独立预测；
- 固定 0–50 分式：不能作为 60 mmHg 无条件外推模型。

这些结论已同步到 [`../MAIN_CONCLUSIONS.md`](../MAIN_CONCLUSIONS.md)，所以本路径状态标记为 `concluded`，不是继续改名为下一“版本”。

## 8. 后继路径的预注册要求

若继续研究，应新建“工作点小扰动切线刚度与全局载荷份额”中间文档，并至少预注册：

- 压力网格及保留验证集；
- 每个工作点的正/负位移扰动；
- 探头、界面、旁路和外围支承反力；
- $k_p$、$k_b(p)$、$\lambda(p)$ 的识别式；
- 网格和扰动幅度收敛；
- 未使用已知 IOP 的预测步骤；
- 在查看验证集前冻结参数的时间点。
