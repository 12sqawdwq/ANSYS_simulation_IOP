# 全模型压力载荷分流机制推导

> 严谨性定位：这是具有物理解释的机制重参数化，不是独立正向验证。几何压力投影面积是独立输入，但载荷分流参数 $c_0$、$c_1$仍由同一组已知 $p$、$q$数据识别。

## 1. 目标

直接RST积分已经证明：

$$
\tau_{interface}=\frac{\Delta F_{eyelid-cornea}}{\Delta F_{probe}}
$$

在10–50 mmHg内只从0.981降至0.916。单独使用 $\tau_{interface}K_A$无法解释探头响应。

本轮不直接经验拟合 $\chi$，而是从全模型压力合力如何在“探头路径”和“固定边界路径”之间分流出发，尝试推导分式公式。

## 2. IOP总投影面积

模型内表面压力边缘的初始投影半径为：

$$
r_i=r_{max}\frac{R_c-t_c}{R_c}
$$

代入：

- $r_{max}=6.0\ \mathrm{mm}$；
- $R_c=7.8\ \mathrm{mm}$；
- $t_c=0.6\ \mathrm{mm}$。

得到：

$$
r_i=5.5384615\ \mathrm{mm}
$$

因此几何投影面积为：

$$
\boxed{
A_{IOP,proj}^{geo}=\pi r_i^2=96.3669605\ \mathrm{mm^2}
}
$$

全模型Y向平衡给出压力投影合力：

$$
F_{IOP}
=F_{probe,reaction}-F_{support,reaction}-F_{residual,0}
$$

再计算：

$$
A_{IOP,proj}^{balance}=\frac{F_{IOP}}{p}
$$

21点结果中：

| 指标 | 数值/mm² |
|---|---:|
| 几何初始投影面积 | 96.36696 |
| 力平衡最小值 | 96.52049 |
| 力平衡全正压均值 | 96.60926 |
| 力平衡10–50 mmHg均值 | 96.61728 |
| 力平衡最大值 | 96.69262 |

几何面积相对稳定区力平衡均值只差−0.2591%。该小差异可由大变形后的随动力投影解释，说明全模型压力合力口径正确。

## 3. 探头载荷份额λ

定义IOP总投影合力中进入探头增量反力的份额：

$$
\boxed{
\lambda(p)=\frac{\Delta F_{probe}(p)}{F_{IOP}(p)}
}
$$

代表值：

| IOP/mmHg | FIOP/N | ΔFprobe/N | λ |
|---:|---:|---:|---:|
| 2.5 | 0.03220 | 0.000416 | 0.01293 |
| 5 | 0.06434 | 0.002775 | 0.04313 |
| 10 | 0.12875 | 0.007923 | 0.06154 |
| 20 | 0.25751 | 0.012785 | 0.04965 |
| 30 | 0.38638 | 0.015397 | 0.03984 |
| 40 | 0.51543 | 0.017464 | 0.03388 |
| 50 | 0.64455 | 0.019359 | 0.03003 |

2.5–7.5 mmHg仍表现为接触启用段。10 mmHg后，进入探头的压力载荷份额随IOP升高而稳定下降。

## 4. 两路径刚度分流模型

将压力载荷简化为两个反力路径：

- 探头耦合路径刚度：$k_p$；
- 固定边界旁路刚度：$k_b(p)$。

静态载荷分流给出：

$$
\lambda(p)=\frac{k_p}{k_p+k_b(p)}
$$

若压力预张力使旁路刚度在稳定区近似线性增加：

$$
k_b(p)=k_{b,0}+\beta p
$$

则：

$$
\frac{1}{\lambda(p)}
=1+\frac{k_{b,0}}{k_p}+\frac{\beta}{k_p}p
=c_0+c_1p
$$

使用10–50 mmHg的实际RST结果拟合得到：

$$
\boxed{
\frac1\lambda
=11.34481494+0.4494957833p
}
$$

$$
R^2=0.997294
$$

对应的刚度比为：

$$
\boxed{
\frac{k_{b,0}}{k_p}=c_0-1=10.34481494
}
$$

$$
\boxed{
\frac{1}{k_p}\frac{dk_b}{dp}
=c_1=0.4494957833\ \mathrm{mmHg^{-1}}
}
$$

也可写成：

$$
\lambda(p)
=\frac{\lambda_0}{1+\gamma p}
$$

其中：

$$
\lambda_0=\frac1{c_0}=0.088145995
$$

$$
\gamma=\frac{c_1}{c_0}=0.0396212530\ \mathrm{mmHg^{-1}}
$$

这里的 $\lambda_0$是10–50 mmHg稳定区模型向零压的外推值，不代表2.5–7.5 mmHg接触启用段的真实载荷份额。

## 5. 从载荷分流推导分式a、b

探头扣除后压力为：

$$
q=P_{probe}=\frac{\Delta F_{probe}}{A_p}
$$

因为：

$$
\Delta F_{probe}
=\lambda(p)pA_{IOP,proj}
$$

压力单位一致时：

$$
q
=\frac{A_{IOP,proj}}{A_p}
\frac{p}{c_0+c_1p}
$$

整理得到：

$$
\boxed{
p=\frac{bq}{1-aq}}
$$

而且两个分式参数具有明确映射：

$$
\boxed{
b=\frac{A_pc_0}{A_{IOP,proj}}}
$$

$$
\boxed{
a=\frac{A_pc_1}{A_{IOP,proj}}}
$$

使用独立几何投影面积 $A_{IOP,proj}^{geo}=96.3669605\ \mathrm{mm^2}$和 $A_p=14.6574147\ \mathrm{mm^2}$，得到：

$$
\boxed{
a_{share}=0.0683683087\ \mathrm{mmHg^{-1}}}
$$

$$
\boxed{b_{share}=1.7255463542}
$$

正向公式为：

$$
\boxed{
P_{IOP}
=\frac{1.7255463542P_{probe}}
{1-0.0683683087P_{probe}}
}
$$

## 6. 与逆向回归比较

| 参数 | 载荷分流正向推导 | 逆向回归 | 相对差异 |
|---|---:|---:|---:|
| a/mmHg⁻¹ | 0.06836831 | 0.06531173 | +4.68% |
| b | 1.72554635 | 1.82731486 | −5.57% |

误差：

| 范围 | MAE/mmHg | RMSE/mmHg | 最大绝对误差/mmHg |
|---|---:|---:|---:|
| 0–50 mmHg全部21点 | 0.81201 | 1.12923 | 2.96976 |
| 10–50 mmHg稳定区 | 0.65827 | 0.93713 | 2.96976 |

该结果显著优于“直接界面传力×5°面积”正向模型的RMSE 9.54752 mmHg，并接近逆向回归的RMSE 0.95406 mmHg。

## 7. χ的物理重写及面积消去

此前定义：

$$
p=\tau_{interface}\chi K_Aq
$$

由于：

$$
\Delta F_{interface}
=\tau_{interface}\Delta F_{probe}
=\tau_{interface}\lambda pA_{IOP,proj}
$$

因此：

$$
\boxed{
\chi
=\frac{A_c}
{\tau_{interface}\lambda A_{IOP,proj}}
}
$$

代回总式：

$$
\tau_{interface}\chi K_A
=\tau_{interface}
\frac{A_c}{\tau_{interface}\lambda A_{IOP,proj}}
\frac{A_p}{A_c}
$$

得到：

$$
\boxed{
\tau_{interface}\chi K_A
=\frac{A_p}{\lambda A_{IOP,proj}}
}
$$

所以总探头响应可以简化为：

$$
\boxed{
p=\frac{A_p}{\lambda(p)A_{IOP,proj}}q}
$$

这不是说接触面积和界面传力没有力学作用，而是说它们最终都通过全局载荷份额 $\lambda$影响探头。若能够独立预测 $\lambda$，则反演公式不必显式使用 $A_{c,5^\circ}$或 $\tau_{interface}$。

## 8. 当前推导的边界

本轮取得的是比此前更清晰的机制降阶，但还不是独立验证：

1. $A_{IOP,proj}$由模型几何独立给出，并已被全局力平衡验证；
2. 分式结构和 $a$、$b$映射由两路径刚度分流正向推导；
3. 但是 $c_0$、$c_1$仍使用同一组已知IOP的FE响应识别；
4. 2.5–7.5 mmHg接触启用段不服从稳定区刚度分流；
5. 当前参数仍只适用于1.25 mm眼睑、0.60 mm角膜、0.259875 mm推进量及冻结材料配置。

真正独立的下一步是从工作点附近的力—位移切线刚度识别 $k_p$和 $k_b(p)$，验证：

$$
\frac{k_b(p)}{k_p}
\approx10.3448+0.449496p
$$

如果该关系可由RST内已有推进曲线或小扰动刚度直接获得，而不使用 $p/q$反算，就能把当前载荷分流模型推进为独立正向模型。

## 9. 产物

- `derive_global_load_share_model.py`
- `results/20260731_global_load_share_derivation.json`
- `results/20260731_global_load_share_derivation.csv`
- `plot_global_load_share_derivation.py`
- `figures/global_load_share_rational_derivation.png`
