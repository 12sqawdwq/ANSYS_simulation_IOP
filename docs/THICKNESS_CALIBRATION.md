# 眼睑厚度材料校准

## 当前运行结果

5090d 批次 `20260721T070542Z_6a75cde2_calibration_0p26` 已完成候选筛选和最终 `0.30 mm` 网格九点扫描。眼睑倍率 `1.00`、角膜倍率 `0.75`、IOP `20 mmHg` 是阶段性参数。该批次的 `0.26 mm` 结果保留为历史对照，完整解释见 [0.26 mm 补充报告](../thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)。正式厚度比较从下一批起统一使用 `0.28 mm` 名义推进。

本批次不能标记为完整校准结束：三个 `0.15 mm` 全局细网格验证均未形成可用结果，控制器随后因索引缺失网格数据触发 `KeyError: 0.8`，没有生成 `selected_parameters.json`、`mesh_validation.csv`、`calibration_report.md` 和 `calibration_status.json`。已经落盘并通过 QC 的 `0.30 mm` 九点结果仍可使用，状态应理解为“粗网格阶段完成、网格验证未完成”。

纯几何弓高随厚度为 `0.241-0.276 mm`，`1.25 mm` 标准眼睑为 `0.2615 mm`。该弓高只作为位移选择依据，不再用于直接生成正式 `Ae`。`0.70-0.75 mm` 只代表有限元闭合接触面积平台。统一 `0.28 mm` 可以覆盖最不利薄眼睑的几何弓高，同时避免进入大位移畸变区。

本流程固定 `20 mmHg` IOP，统一状态为 `0.28 mm`。2026-07-23复核确认：中央连续 `2°` 网格面积只能表示“近水平核心区”，不能表示原几何关系中的完整压平面积 `Ae/Ac`。字段 `ae_over_ac_flat_2deg`、相关红蓝图和角度扫描均降级为灵敏度诊断，不再用于材料选择、实验回归或专利结论。求解得到的位移场、反力、接触状态和表面网格继续有效，无需重新求解后才能修改面积后处理。

## 启动

5090d 的正式仓库必须处于干净 Git 状态：

```bash
cd /home/xuanyu/PROJECT/ziyu/blueknow/simulation
ops/start-thickness-calibration-5090d.sh
```

启动脚本输出 `RUN_ROOT` 和 `CONTROLLER_PID`。控制器通过 `nohup` 独立运行，不依赖
SSH或Codex会话。默认并行度为4个算例、每个算例4个MAPDL核，可通过
`BLUEKNOW_SWEEP_WORKERS` 和 `BLUEKNOW_CASE_NP` 覆盖。

## 状态检查

```bash
python src/postprocess/check_calibration_run.py "$RUN_ROOT"
```

需要保存检查证据时：

```bash
python src/postprocess/check_calibration_run.py "$RUN_ROOT" \
  --write-snapshot "$RUN_ROOT/health_snapshot.json"
```

当控制器仍存活、活动日志持续更新、没有致命/未收敛/高畸变标记，并且已有一个完成
算例或至少三个收敛进度标记时，`healthy_to_leave_unattended` 为 `true`。达到该状态后
不需要持续轮询。

## 0.5°/1°/2°/3°有效形变分布

正式结果完成后生成四组外侧和内侧二值网格图：

```bash
python src/postprocess/plot_flat_region_2deg.py "$RUN_ROOT" --workers 4
```

默认角度为 `0.5°、1°、2°、3°`，也可通过 `--angles` 指定。红色表示满足位移
阈值、中央边连通且平滑面法向夹角不超过当前角度的有效平坦网格；蓝色表示未计入
网格。每个角度输出各厚度俯视图、3D/半剖/中央剖面图、面积与覆盖率 CSV，以及
汇总矩阵。`0.5°、1°、2°、3°` 现在全部只用于灵敏度观察；红色含义是
`θ` 不超过当前阈值，而不是 `θ` 大于当前阈值。

## 面积后处理口径复核

### 当前挂载脚本实际计算的量

正式 `0.28 mm` 求解进程基于提交 `973a834`。MAPDL在IOP预载结束和探头推进结束时，
分别导出两层变形三角面：

- 外层：探头—眼睑接触侧的 `CONTA174` 面；
- 内层：眼睑—角膜完全粘结界面的 `CONTA174` 面。

设第 $i$ 个三角面三个节点在预载和最终状态下的纵向坐标平均值分别为
$\bar y_{i,\mathrm{pre}}$ 和 $\bar y_{i,\mathrm{final}}$，当前算法首先计算相对预载状态的
向下位移：

$$
d_i = \bar y_{i,\mathrm{pre}} - \bar y_{i,\mathrm{final}}.
$$

使用远端外环面片的位移中位数 $b$ 消除整体漂移：

$$
b = \operatorname{median}_{r_i \ge 0.8r_{\max}}(d_i),
\qquad
\tilde d_i = \max(d_i-b,0).
$$

外环残差的稳健噪声估计为：

$$
\sigma_{\mathrm{MAD}}
= 1.4826\,\operatorname{median}
\left(\left|(d_i-b)-\operatorname{median}(d_i-b)\right|\right).
$$

参与形变的位移门槛为：

$$
T = \max\left(3\sigma_{\mathrm{MAD}},\ 0.05\tilde d_{\max},\ 1\ \mu\mathrm{m}\right).
$$

对最终变形网格进行节点法向平滑后，第 $i$ 个面片与探头轴之间的夹角为：

$$
\theta_i = \cos^{-1}
\left(\frac{|n_{y,i}|}{\|\mathbf n_i\|}\right).
$$

给定角度阈值 $\theta_0$，候选面片集合为：

$$
\mathcal S(\theta_0)
= \left\{i\;\middle|\;
\tilde d_i \ge T,\;
\theta_i \le \theta_0,\;
r_i \le a
\right\},
\qquad a=2.16\ \mathrm{mm}.
$$

随后只保留与探头轴最近面片相连的中央边连通分量 $\mathcal C(\theta_0)$，删除其他
离散小岛。设最终状态三角面的两条边为 $\mathbf e_{1,i}$ 和 $\mathbf e_{2,i}$，
$\alpha_i$ 是三角面落在探头圆内的面积比例，则当前外层面积为：

$$
A_e^{(\theta_0)}
= \sum_{i\in\mathcal C_{\mathrm{outer}}(\theta_0)}
\alpha_i\,
\frac{\left|\left(\mathbf e_{1,i}\times\mathbf e_{2,i}\right)_y\right|}{2}.
$$

内层使用相同算法：

$$
A_c^{(\theta_0)}
= \sum_{i\in\mathcal C_{\mathrm{inner}}(\theta_0)}
\alpha_i\,
\frac{\left|\left(\mathbf e_{1,i}\times\mathbf e_{2,i}\right)_y\right|}{2}.
$$

当前角度面积比和外层覆盖率分别为：

$$
K_{\theta_0}=\frac{A_e^{(\theta_0)}}{A_c^{(\theta_0)}},
\qquad
\eta_{\theta_0}=\frac{A_e^{(\theta_0)}}{\pi a^2}.
$$

探头圆裁切和面片部分裁切只提供上界：

$$
0\le A_e^{(\theta_0)}\le \pi a^2,
\qquad
0\le\eta_{\theta_0}\le1.
$$

它们只能防止面积越出探头投影，不能保证 $\eta_{\theta_0}$ 接近 $1$。因此这里的
“覆盖率”是一个待检查的结果，不是算法保证条件；中央连通筛选还可能继续降低该数值。

其中原计划采用 $\theta_0=2^\circ$，而 `0.5°、1°、3°` 用于阈值敏感性检查。

### 与原几何压平公式的差异

原几何关系使用眼睑外表面半径 $R$、探头半径 $a$ 和名义推进 $\delta$。球面与推进
平面的交线半径和参考面积为：

$$
r_g = \min\left(a,\sqrt{2R\delta-\delta^2}\right),
\qquad
A_{\mathrm{geom}}=\pi r_g^2.
$$

达到探头边缘所需的球面弓高为：

$$
\delta_g = R-\sqrt{R^2-a^2}.
$$

当前厚度范围的 $\delta_g$ 为 `0.241-0.276 mm`，因此统一 `0.28 mm` 已经达到或超过
几何参考弓高。几何参考面积由此接近探头面积：

$$
A_{\mathrm{probe}}=\pi(2.16\ \mathrm{mm})^2=14.6574\ \mathrm{mm}^2.
$$

但是当前 `2°` 外层红区覆盖率仅约为 `41%-49%`。这不是材料参数造成的小偏差，而是
两个面积定义回答了不同问题：

- 几何公式描述探头尺度内应参与整体压平的范围；
- 角度算法只描述最终表面中局部坡度接近零的中央核心。

### 为什么不能把角度面积作为正式 Ae/Ac

1. $\theta_i\le\theta_0$ 是局部坡度条件，不是压平量、曲率降低量或压缩贡献条件。
2. 初始球面的中心区域本身接近水平，小角度不必然由探头压平产生。
3. 厚度改变会使内表面法向略微跨过阈值，导致整片网格突然进入或退出 `Ac`。
4. 当前 `0.30 mm` 网格采用整面片二值分类，角度边界存在明显离散跳变。
5. 严格阈值下内层面积收缩快于外层；当前 `0.5°` 面积比可达到约 `1.8-10.2`，
   主要反映阈值和网格敏感性，而不是稳定的生物力学比例。

因此，当前 $A_e^{(\theta_0)}$、$A_c^{(\theta_0)}$ 和 $K_{\theta_0}$ 只能用于显示局部
平坦核心与网格敏感性。它们不得进入正式 `Ae/Ac` 曲线、材料反演评分、实验区间比较
或专利汇报。

### 仍然有效的结果

- IOP预载与 `0.28 mm` 推进后的位移场；
- 探头反力、接触状态、接触压力和闭合接触单元；
- 外层和内层的完整预载/最终变形三角面；
- 应力、应变、穿透量和多视角结果；
- `0.5°/1°/2°/3°` 红蓝图，限于阈值敏感性诊断。

当前求解不需要因面积口径问题停止或重算。下一版面积应根据相对预载状态的曲率降低量、
到探头平面的距离和连续压缩贡献进行积分，使几何压平点附近的结果能够接近探头尺度，
但不通过归一化强制等于探头面积。

## 后续校准约束

- 正式位移固定为 `0.28 mm`，总探头位移为 `0.33 mm`，其中包含 `0.05 mm` 初始间隙闭合。
- `Ae/Ac` 新口径完成前暂停材料参数自动评分，禁止使用 `ae_over_ac_flat_2deg` 选择材料。
- 角度面积、闭合接触面积、径向折点面积和球面弓高面积均作为独立诊断，不作为正式面积。
- 新面积必须同时报告探头面积覆盖率、网格敏感性和与球面弓高尺度的偏差，但不得强制归一化。
- 主厚度：`0.8、1.0、1.2、1.25 mm`，目标区间 `1.5-2.0`。
- 至少3个主厚度点相对区间误差不超过20%，四点平均误差不超过20%。
- `1.5 mm` 的次要范围为 `2.0-3.0`；`2.0 mm` 为 `4.0-8.0`。
- 第一轮为眼睑倍率 `0.5/1/2` 与角膜倍率 `0.75/1/1.25` 的完整组合。
- 第一轮不足时，控制器只在最优参数附近执行一次细化；再次失败即报告模型形式不足。

## 输出和存储

控制器在运行目录写入：

- `candidate_scores.csv`：候选评分；
- `selected_parameters.json`：最终材料参数；
- `mesh_validation.csv`：0.15 mm网格验证；
- `calibration_report.md`：最终结果表；
- `calibration_status.json`：最终状态。

筛选算例在0.28 mm结果提取完成后删除主 `.db/.rst`，保留指标、面数据和日志。最终
计算只为 `0.8、1.2、2.0 mm` 保留主结果文件；所有最终厚度保留0.8 mm和0.28 mm
状态图片。
