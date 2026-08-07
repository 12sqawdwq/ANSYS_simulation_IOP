# 版本一：有效压平面积比换算

```text
algorithm_version: 1
algorithm_id: area_only_effective_applanation
lifecycle_status: rejected_as_complete_algorithm_retained_as_geometry_component
classification_date: 2026-08-06
```

## 1. 算法定义

版本一假设探头增量力可以直接由眼内压作用在角膜有效压平面积上的轴向合力解释。

同一厚度和推进工作点下，先定义零眼压结构参考差：

$$
\Delta F_{probe}(p)=F_{probe}(p)-F_{probe}(0)
$$

若外侧有效压平面积为 $A_e$、内侧有效压平面积为 $A_c$，则外侧面积口径的探头压力和面积比为：

$$
q_e=\frac{\Delta F_{probe}}{A_e},
\qquad
K_{area}=\frac{A_e}{A_c}
$$

版本一换算式为：

$$
\boxed{p_{area}=K_{area}q_e}
$$

即：

$$
p_{area}=\frac{\Delta F_{probe}}{A_c}
$$

当前项目通常把探头读数按完整探头面积 $A_p$ 定义：

$$
q=\frac{\Delta F_{probe}}{A_p}
$$

因此同一公式应面积一致地写成：

$$
\boxed{p_{area}=\frac{A_p}{A_c}q}
$$

$A_e$ 在该表达式中严格消去。不能把 $A_e/A_c$ 直接乘在完整探头面积口径的 $q$ 上，否则面积分母不一致。

## 2. 隐含假设

版本一等价于假设：

$$
\Delta F_{probe}=pA_c
$$

也就是假设零眼压参考后的全部探头增量力都对应于内压在 $A_c$ 上形成的轴向合力，不再单独考虑：

- 眼睑—角膜界面传递；
- 外围支承和旁路载荷；
- 压力预张力引起的结构刚度变化；
- 接触启用和载荷路径转换；
- 几何面积与机械承载面积之间的差别。

## 3. 当前证据和关闭结论

冻结的 $A_{c,5^\circ}$ 只能作为几何代理。版本一在 20 mmHg 附近近似成立，但随压力升高系统性低估：

|实际 IOP|版本一面积法结果|误差|
|---:|---:|---:|
|20 mmHg|19.4185 mmHg|-0.5815 mmHg|
|25 mmHg|22.6348 mmHg|-2.3652 mmHg|
|30 mmHg|24.8097 mmHg|-5.1903 mmHg|
|35 mmHg|26.9033 mmHg|-8.0967 mmHg|
|40 mmHg|28.7720 mmHg|-11.2280 mmHg|

主工作点面积法 MAE 为 5.4923 mmHg，RMSE 为 6.7007 mmHg。因此版本一已经被否定为完整 IOP 反演算法，但它保留为版本三中的几何面积组成部分和重要负结果。

## 4. 权威实现和证据

当前工作树保留：

- `high_iop_mechanical_transfer_t1p25_c0p60/scripts/postprocess/postprocess_area_ratio_iop.py`：面积一致换算；
- `high_iop_mechanical_transfer_t1p25_c0p60/scripts/analysis/analyze_area_ratio_error.py`：误差来源分析；
- `high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_area_ratio_k_iop_results.json`：不可变结果证据；
- `high_iop_mechanical_transfer_t1p25_c0p60/docs/MAIN_CONCLUSIONS.md`：冻结结论。

首次正式结果和实现也可由 Git 恢复：

```text
61eb289:high_iop_mechanical_transfer_t1p25_c0p60/AREA_RATIO_K_RESULT.md
61eb289:high_iop_mechanical_transfer_t1p25_c0p60/postprocess_area_ratio_iop.py
```

## 5. 允许与禁止

允许：

- 作为有效面积变化的几何诊断；
- 作为版本三中 $K_A=A_p/A_c$ 的面积组成部分；
- 复现面积法为何在高压下失效。

禁止：

- 把 $A_{c,5^\circ}$称为已经验证的机械有效承载面积；
- 通过调整 5° 阈值吸收压力误差；
- 忽略面积口径直接计算 `Ae/Ac × 完整探头压力`；
- 把版本一恢复为全压力、全厚度生产算法。
