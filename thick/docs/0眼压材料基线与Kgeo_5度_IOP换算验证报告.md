# 0眼压材料基线与 Kgeo,5° IOP 换算验证报告

## 1. 汇报目的

本报告冻结纯仿真范围内的 IOP 换算策略：先从 20 mmHg 仿真总反力中扣除相同厚度、材料、推进量和边界条件下的 0 mmHg 材料/结构基线，再使用既有的 5° 几何面积比进行换算，并与实际施加的 `20 mmHg` IOP 对比。

本报告不讨论硬件传感器、固件或硬件标定。

## 2. 冻结定义

### 2.1 5° 几何 K

继续使用已批准的几何定义：

$$
K_{\mathrm{geo},5^\circ}=\frac{A_e}{A_{c,5^\circ}}
$$

其中：

- $A_e$：外侧可观测几何面积下界，字段为 `outer_ae_lower_mm2`；
- $A_{c,5^\circ}$：内侧 5° 中央平坦面积，字段为 `inner_ac_5deg_mm2`；
- $K_{\mathrm{geo},5^\circ}$：字段为 `approved_ae_over_ac`。

### 2.2 材料/结构基线

对厚度 $t$ 和推进量 $d$，0 mmHg 仿真的探头反力定义为材料/结构基线：

$$
F_{0}(t,d)=F_{\mathrm{FE}}(t,d,IOP=0)
$$

该基线包含当前模型中的材料压缩、弯曲、几何、粘结、接触和边界约束贡献。

20 mmHg 相对 0 mmHg 的净反力为：

$$
\Delta F(t,d)=\left|F_{20}(t,d)\right|-\left|F_0(t,d)\right|
$$

### 2.3 与 Kgeo,5° 配套的基线扣除压强

由于 $K_{\mathrm{geo},5^\circ}$ 的分子是 $A_e$，与它相乘的压强必须也以 $A_e$ 为分母：

$$
\Delta P_{A_e}(t,d)=\frac{\Delta F(t,d)}{A_e(t,d)}
$$

单位换算为 mmHg 后，正式 IOP 计算式为：

$$
\boxed{
IOP_{\mathrm{calc}}(t,d)
=K_{\mathrm{geo},5^\circ}(t,d)\times\Delta P_{A_e}(t,d)
}
$$

将 $K_{\mathrm{geo},5^\circ}=A_e/A_{c,5^\circ}$ 代入，可得完全等价的形式：

$$
IOP_{\mathrm{calc}}
=\frac{\Delta F}{A_{c,5^\circ}}
$$

这说明换算结果由“扣除 0 mmHg 材料基线后的净反力”和“内侧 5° 有效面积”共同决定。

## 3. 完整探头压强与面积口径修正

现有压力曲线字段 `probe_mean_pressure_mmhg` 使用完整探头面积：

$$
A_{\mathrm{probe}}=\pi(4.32/2)^2=14.6574147\ \mathrm{mm^2}
$$

因此，如果输入数据是完整探头反力等效压强：

$$
\Delta P_{\mathrm{probe}}=P_{20,\mathrm{probe}}-P_{0,\mathrm{probe}}
$$

必须先转换到 $A_e$ 口径：

$$
\Delta P_{A_e}
=\frac{A_{\mathrm{probe}}}{A_e}\Delta P_{\mathrm{probe}}
$$

最终公式为：

$$
IOP_{\mathrm{calc}}
=K_{\mathrm{geo},5^\circ}
\frac{A_{\mathrm{probe}}}{A_e}
\Delta P_{\mathrm{probe}}
$$

等效地：

$$
IOP_{\mathrm{calc}}
=\frac{A_{\mathrm{probe}}}{A_{c,5^\circ}}
\Delta P_{\mathrm{probe}}
$$

因此，不允许直接计算
`Kgeo,5° × 完整探头基线扣除压强`，因为两者的面积分母不同。

## 4. 1.25 mm 独立验证

### 4.1 输入数据

| 项目 | 数值 |
|---|---:|
| 眼睑厚度 | `1.25 mm` |
| 推进量 | `0.28 mm` |
| 实际施加 IOP | `20.0000 mmHg` |
| $A_e$ | `12.9564434 mm²` |
| $A_{c,5^\circ}$ | `5.3448420 mm²` |
| $K_{\mathrm{geo},5^\circ}$ | `2.4241022` |
| 20 mmHg 探头反力 | `0.175734300 N` |
| 0 mmHg 材料基线反力 | `0.161914097 N` |
| 20 mmHg 完整探头等效压强 | `89.9284981 mmHg` |
| 0 mmHg 完整探头材料基线 | `82.8562867 mmHg` |

0 mmHg 基线来自提交 `447b349f` 的独立 8 核求解：

`/home/xuanyu/PROJECT/ziyu/blueknow-data/zero_iop/20260729T070038Z_447b349f_geometry_zero_t1p25_mesh0p30_np8/run/run_manifest.csv`

该算例三个载荷步全部收敛、返回码为 0、无 ANSYS 错误。

### 4.2 去除材料基线

完整探头面积口径下：

$$
\Delta P_{\mathrm{probe}}
=89.9284981-82.8562867
=7.0722114\ \mathrm{mmHg}
$$

转换到 $A_e$ 口径：

$$
\Delta P_{A_e}
=7.0722114\times\frac{14.6574147}{12.9564434}
=8.0006783\ \mathrm{mmHg}
$$

### 4.3 使用 Kgeo,5° 换算 IOP

$$
IOP_{\mathrm{calc}}
=2.4241022\times8.0006783
=19.3944621\ \mathrm{mmHg}
$$

### 4.4 与实际 20 mmHg 对比

$$
\mathrm{error}
=19.3944621-20
=-0.6055379\ \mathrm{mmHg}
$$

$$
\mathrm{relative\ error}
=\frac{-0.6055379}{20}\times100\%
=-3.0277\%
$$

| 指标 | 结果 |
|---|---:|
| 换算 IOP | `19.3945 mmHg` |
| 实际 IOP | `20.0000 mmHg` |
| 有符号误差 | `-0.6055 mmHg` |
| 绝对误差 | `0.6055 mmHg` |
| 相对误差 | `-3.0277%` |
| 当前判定 | `通过初步单点验证` |

## 5. 与旧的直接乘法对比

如果错误地直接计算：

$$
K_{\mathrm{geo},5^\circ}\times\Delta P_{\mathrm{probe}}
$$

则得到：

$$
2.4241022\times7.0722114=17.1438\ \mathrm{mmHg}
$$

该结果偏低的原因不是 K 本身失效，而是 `Kgeo,5°` 使用 $A_e$，而 `P_probe` 使用完整探头面积；二者分母不一致。完成面积口径转换后，结果由 `17.14 mmHg` 修正为 `19.39 mmHg`。

## 6. 独立九点验证要求

正式九点验证厚度固定为：

`0.80、1.00、1.20、1.25、1.40、1.50、1.60、1.80、2.00 mm`。

每个厚度必须具备相互独立的：

1. 20 mmHg 几何初接触结果；
2. 0 mmHg 几何初接触材料基线结果；
3. 相同 `0.28 mm` 推进量；
4. 相同 `0.30 mm` 初始间隙；
5. 相同 `0.30 mm` 网格；
6. 相同眼睑和角膜材料倍率；
7. 相同接触、粘结和外围边界；
8. 三个载荷步全部收敛；
9. 独立读取 $A_e$、$A_{c,5^\circ}$、$F_{20}$ 和 $F_0$。

禁止使用已知的 20 mmHg 反推 0 mmHg 基线后再验证，否则会构成循环验证。

### 6.1 当前九点状态

| 厚度 | 20 mmHg结果 | 独立0 mmHg基线 | IOP换算状态 |
|---:|---|---|---|
| 0.80 | 已有 | 待补 | 待验证 |
| 1.00 | 已有 | 待补 | 待验证 |
| 1.20 | 已有 | 待补 | 待验证 |
| 1.25 | 已有 | 已有 | `19.3945 mmHg` |
| 1.40 | 已有 | 待补 | 待验证 |
| 1.50 | 已有 | 待补 | 待验证 |
| 1.60 | 已有 | 待补 | 待验证 |
| 1.80 | 已有 | 待补 | 待验证 |
| 2.00 | 已有 | 待补 | 待验证 |

## 7. 自动验证脚本

脚本：

`thick/code/validate_iop_from_kgeo_material_baseline.py`

建议在 5090d 上执行：

```bash
python thick/code/validate_iop_from_kgeo_material_baseline.py \
  --geometry-csv thick/experiments/geometric_observable_5deg/geometry_zero_server_full9.csv \
  --zero-root /home/xuanyu/PROJECT/ziyu/blueknow-data/zero_iop \
  --output-dir thick/experiments/geometric_observable_5deg/iop_from_material_baseline
```

脚本会：

- 自动发现独立的 0 mmHg `run_manifest.csv`；
- 只接受 `status=complete` 且三个载荷步收敛的结果；
- 检查厚度、推进量、材料倍率、初始间隙和网格是否匹配；
- 按 `Kgeo,5° × 去除材料基线后的 Ae 口径压强` 计算 IOP；
- 输出计算 IOP、绝对误差和相对误差；
- 对缺失 0 mmHg 基线的厚度明确标记 `missing_zero_baseline`；
- 在九点没有全部完成前，不给出“九点验证通过”的结论。

## 8. 当前结论

当前 `1.25 mm` 独立结果支持以下换算策略：

$$
\boxed{
IOP_{\mathrm{calc}}
=K_{\mathrm{geo},5^\circ}
\times
\text{去除0眼压材料基线后的 }A_e\text{ 口径压强}
}
$$

在实际输入 `20 mmHg` 时得到 `19.3945 mmHg`，误差为 `-0.6055 mmHg（-3.03%）`。该结论目前只通过一个厚度点验证；最终结论必须等待其余八个独立 0 mmHg 材料基线完成后再冻结。
