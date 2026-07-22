# 眼睑厚度材料校准

## 当前运行结果

5090d 批次 `20260721T070542Z_6a75cde2_calibration_0p26` 已完成候选筛选和最终 `0.30 mm` 网格九点扫描。当前选择眼睑倍率 `1.00`、角膜倍率 `0.75`、IOP `20 mmHg`；主厚度区间达到 3/4 点在 20% 容差内，平均区间误差为 `12.9%`。完整结果解释见 [0.26 mm 补充报告](../thick/docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)。

本批次不能标记为完整校准结束：三个 `0.15 mm` 全局细网格验证均未形成可用结果，控制器随后因索引缺失网格数据触发 `KeyError: 0.8`，没有生成 `selected_parameters.json`、`mesh_validation.csv`、`calibration_report.md` 和 `calibration_status.json`。已经落盘并通过 QC 的 `0.30 mm` 九点结果仍可使用，状态应理解为“粗网格阶段完成、网格验证未完成”。

本流程固定 `20 mmHg` IOP，以完整 `0.8 mm` 加载路径中的 `0.26 mm` 状态校准
眼睑和角膜 Mooney-Rivlin 参数倍率。原始面片 `Ae/Ac(2°)` 继续保留，材料选择使用
一环节点法向平滑后的 `Ae/Ac(2°)`。

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

## 校准判据

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

筛选算例在0.26 mm结果提取完成后删除主 `.db/.rst`，保留指标、面数据和日志。最终
计算只为 `0.8、1.2、2.0 mm` 保留主结果文件；所有最终厚度保留0.8 mm和0.26 mm
状态图片。
