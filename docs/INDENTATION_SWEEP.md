# 偏心压入扫描协议

## 固定物理假设

- 普通压入和偏心实验的眼睑厚度统一采用 1.25 mm 全局基线；只有预注册的厚度变量实验可显式覆盖，并记录实际厚度与原因。基线真源见 [`../config/model_baseline.json`](../config/model_baseline.json)。
- 眼睑—角膜完全 bonded，不考虑滑移、摩擦和黏弹性。
- 主扫描使用 0.3 mm 均匀网格。
- 载荷步 1 将 IOP 从 0 增加到 2666.4 Pa，同时固定探针顶部。
- 载荷步 2 保持 IOP，将探针推进到 `-(0.05 mm + nominal indentation)`。
- 名义压入限制在 0-0.8 mm；Python 和 APDL 两层都拒绝超过上限的工况。
- 力收敛容差为 1%；最终不收敛时终止当前 MAPDL 进程。

## 运行阶段

```bash
ops/launch-indentation-sweep-5090d.sh smoke
ops/launch-indentation-sweep-5090d.sh coarse
ops/launch-indentation-sweep-5090d.sh full
```

`smoke` 为 `(0,0)`、`(0,0.8)`、`(2,0.4)`、`(2,0.8)` 四个代表性工况。`coarse` 为 4 个偏心量乘以 `0/0.4/0.8 mm`，共 12 个工况；`full` 使用 `0/0.2/0.4/0.6/0.8 mm`，共 20 个工况。三种普通 profile 默认都使用 1.25 mm 眼睑；`run_metadata.json` 同时记录全局基线、实际厚度模式和配置哈希。每一阶段结束后人工检查 `qc_report.json`、`summary.csv` 和 `figures/`，不得自动启动下一阶段。

5090d 启动脚本固定使用 `/home/xuanyu/miniconda3/envs/grs-pilot/bin/python`，该环境已包含质量检查曲线所需的 Pillow。只有在明确验证其他兼容 Conda 环境时，才通过 `BLUEKNOW_PYTHON` 覆盖解释器路径。

每个运行目录使用 UTC 时间、Git 短提交号和阶段名称标识。每个算例拥有独立 attempt 目录，不复用旧 `.rst`、指标或图片。单次尝试上限为 7200 秒；仅非收敛或 ANSYS 求解错误重试一次，重试使用 2 MPI 核和更小初始子步。

## 完成判据

`complete` 要求 MAPDL 正常结束、最终结果为载荷步 2/时间 2、两个载荷步均收敛、RST 与结构化指标存在、所有指标有限、探针位移符合命令值，并生成九张非空视图。通用 `*** ERROR ***` 只记录数量；若自动切步后得到有效最终结果，不单独判失败。批次 QC 还要求 manifest 与 `run_metadata.json` 中的预期工况逐一匹配，中断造成的缺行必须判失败。

状态包括 `complete`、`nonconverged`、`ansys_error`、`missing_results`、`invalid_metrics` 和 `timeout`。`run_metadata.json` 保存 Git、ANSYS、命令、主机、并行设置、时间和 APDL SHA-256；`run_manifest.csv` 每完成一个算例即原子更新。

## 求解产物保留

每次 attempt 完成有效性判定后立即执行固定保留策略。成功算例保留主 `job.rst`、`job.db`、九张 PNG、结构化指标、APDL 输入、`solve.out`、启动日志和 attempt 元数据；删除可由主结果或重新求解恢复的 MPI 编号 RST、`*.rNNN`、`*.esav`、`*.full`、`*.rdb`、`*.ldhi`、`*.DSP` 等暂存文件。失败算例额外删除无效的主 RST/DB，但保留日志、指标和已有视图用于诊断。

`run_manifest.csv` 记录每个最终 attempt 清理的文件数、字节数和异常。对旧批次先执行只读预检，再显式应用：

```bash
python src/postprocess/prune_solver_artifacts.py /path/to/run
python src/postprocess/prune_solver_artifacts.py /path/to/run --apply
```

## 结果使用

核心量为探针 `Fx/Fy`、闭合接触面积、面积加权接触中心、最大接触压力、最大数值穿透、闭合单元数、组织峰值应力和探针位移。最大数值穿透超过 0.03 mm 时产生 QC 警告。峰值量只作趋势指标；名义 0 mm 工况只作基线，不要求严格零接触力。

九张固定视图不再包含 5 倍放大变形。几何接触检查使用实际比例 capped 中央变形截面；另输出 `CONT:PENE` 俯视云图，使数值穿透与三维遮挡、未变形轮廓叠加造成的视觉交叉分开判断。

完整扫描通过后，以 0.2 mm 网格复算 `(0,0.8)`、`(2,0.4)`、`(2,0.8)` mm。探针反力和接触面积相对 0.3 mm 结果变化不超过 10% 时，可认为主趋势具备网格稳定性；峰值应力仍不作为精确绝对值。
