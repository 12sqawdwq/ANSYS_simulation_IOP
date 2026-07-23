# 眼睑厚度材料校准

## 当前运行结果

5090d 批次 `20260721T070542Z_6a75cde2_calibration_0p26` 已完成候选筛选和最终 `0.30 mm` 网格九点扫描。眼睑倍率 `1.00`、角膜倍率 `0.75`、IOP `20 mmHg` 是阶段性参数。该批次的 `0.26 mm` 结果保留为历史对照，完整解释见 [0.26 mm 补充报告](../thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)。正式厚度比较从下一批起统一使用 `0.28 mm` 名义推进。

本批次不能标记为完整校准结束：三个 `0.15 mm` 全局细网格验证均未形成可用结果，控制器随后因索引缺失网格数据触发 `KeyError: 0.8`，没有生成 `selected_parameters.json`、`mesh_validation.csv`、`calibration_report.md` 和 `calibration_status.json`。已经落盘并通过 QC 的 `0.30 mm` 九点结果仍可使用，状态应理解为“粗网格阶段完成、网格验证未完成”。

纯几何弓高随厚度为 `0.241-0.276 mm`，`1.25 mm` 标准眼睑为 `0.2615 mm`。该弓高只作为位移选择依据，不再用于直接生成正式 `Ae`。`0.70-0.75 mm` 只代表有限元闭合接触面积平台。统一 `0.28 mm` 可以覆盖最不利薄眼睑的几何弓高，同时避免进入大位移畸变区。

本流程固定 `20 mmHg` IOP，正式状态为 `0.28 mm`。`Ae` 和 `Ac` 均由 IOP 预载状态到最终状态之间的变形网格计算：选择探头半径内、压入位移超过外环噪声阈值、平滑面法向与探头轴夹角不超过 `2°` 的中央边连通区域，并积分其轴向投影面积。后续材料选择优先使用 `ae_over_ac_flat_2deg`。

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
汇总矩阵。正式面积仍固定使用 `2°`，其余角度用于灵敏度观察。

## 校准判据

- 正式位移固定为 `0.28 mm`，总探头位移为 `0.33 mm`，其中包含 `0.05 mm` 初始间隙闭合。
- 正式 `Ae` 为外侧中央连续 `2°` 平坦区投影面积，正式 `Ac` 使用相同算法处理内侧表面。
- 覆盖率为 `Ae/14.6574 mm²`。探头面积只作分母和上限质检，不把 `Ae` 强制设为探头面积。
- `1°/3°` 面积用于阈值灵敏度；闭合接触面积、径向折点面积和球面弓高面积均作为独立诊断。
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
