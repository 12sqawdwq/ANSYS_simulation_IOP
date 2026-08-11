# 激进接触区网格实验

本目录是独立实验分支 `aggressive-contact-mesh-experiment-20260810` 的入口。目标是在 72 h 墙钟预算内优先细化决定探头积分反力的两条中央界面，而不是直接启动资源上不可接受的全局 0.10 mm 矩阵。仓库全局眼睑厚度基线为 1.25 mm；本实验的 2.00 mm 锚点及可选 1.60/1.80 mm 工况属于厚端网格问题的显式覆盖，不能作为 1.25 mm 基线结果解释。

## 当前决策

- **拒绝直接求解全局 0.10 mm**：预计约 433 万单元、1641 万方程、单端点约 94.7 GiB RST；
- **主方案 L010**：0.20 mm 背景 + 1.80 mm 中央半宽 + 两个 0.80 mm 界面带 + 一级 `EREFINE`，局部名义目标 0.10 mm；
- **极限方案 L005**：同一区域二级细化至名义 0.05 mm；开发期 mesh-only 得到约 288 万实体单元、399 万节点，预计约 1139 万方程和 63.13 GiB RST/端点，因此当前服务器只保留构网格证据并拒绝非线性求解；
- **先锚点、后扩展**：先做 2.00 mm 的 0/20 mmHg 压力对，资源和 QC 通过后才考虑 1.60/1.80 mm；
- **正式 P0 已完成**：commit `8768e6ec...` 上的 G015/L010 mesh-only 均通过；
- **首次 P1 已被拒绝**：commit `d334fd1...` 上的 0 mmHg 算例因资源保护中止，20 mmHg 未启动；没有完整端点，也不能计算 \(q\)。旧 launcher 只终止 runner process group，MAPDL/MPI 独立 session 一度残留；失败二进制经审计后已清理；
- **重启保护已正式验证**：新 launcher 使用 user-systemd cgroup、随机 campaign token、TERM→KILL 升级和零残留核验；clean commit `c62987d...` 上的 helper 与完整 launcher 信号测试均通过且未调用 ANSYS。默认每个 campaign 只允许一个压力，0 mmHg 人工 QC 通过前不得启动 20 mmHg。

详尽依据、资源表、阶段矩阵和判据见 [`EXPERIMENT_DESIGN.md`](EXPERIMENT_DESIGN.md)。

## 正式 P0 mesh-only 预检

首次正式 P0 已完成，结论见 [`results/formal_preflight/CONCLUSION.md`](results/formal_preflight/CONCLUSION.md)。以下命令用于在新的 commit 或服务器状态下重跑；必须先提交本分支并在 5090d 检出同一 commit：

```bash
export EXPECTED_COMMIT='<full-commit-sha>'
export CAMPAIGN_ROOT="/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/$(date -u +%Y%m%dT%H%M%SZ)_${EXPECTED_COMMIT:0:8}_aggressive_mesh_preflight"
bash thickness_mesh_independence/aggressive_refinement/scripts/server/launch_mesh_preflight_5090d.sh
```

默认只构建 G015 和 L010。若只想评估 0.05 mm 二级局部网格规模，可另行设置：

```bash
export RUN_EXTREME=1
```

这不会启动 L005 非线性求解；当前资源快照下该求解已被明确拒绝。

## 正式 P1 锚点压力对

失败尝试与资源包络见 [`results/failed_p1_resource_guard/README.md`](results/failed_p1_resource_guard/README.md)。旧 campaign 不可续算；重启必须使用新 commit、新 root，并先单独运行 0 mmHg：

```bash
export EXPECTED_COMMIT='<full-commit-sha>'
export CAMPAIGN_ROOT="/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/$(date -u +%Y%m%dT%H%M%SZ)_${EXPECTED_COMMIT:0:8}_L010_h2p00_iop0"
export THICKNESSES='2.0'
export PRESSURES='0'
export NP_PER_CASE=4
bash thickness_mesh_independence/aggressive_refinement/scripts/server/launch_aggressive_anchor_5090d.sh
```

启动器要求 `MemAvailable>=90 GiB`、空闲磁盘 `>=150 GiB`，每 10 s 监测；30 GiB 内存或 100 GiB 磁盘保护线触发时终止完整 cgroup/token process set。只有 0 mmHg 的三个载荷步、`RUN COMPLETED`、ANSYS error 0、资源和零残留人工 QC 均通过后，才可另建 root、设置 `PRESSURES='20'` 并单独授权。

不涉及 ANSYS 的 session-tree 回归测试入口为：

```bash
bash thickness_mesh_independence/aggressive_refinement/scripts/server/test_session_guard_5090d.sh
bash thickness_mesh_independence/aggressive_refinement/scripts/server/test_anchor_launcher_signal_5090d.sh
```

第二项使用假 solver 驱动完整 launcher 并向其发送 TERM，不调用 ANSYS。

## 评估

```bash
python thickness_mesh_independence/aggressive_refinement/scripts/analysis/evaluate_aggressive_refinement.py \
  --campaign-root "$CAMPAIGN_ROOT" \
  --reference thickness_mesh_independence/results/confirmation/mesh_comparison.csv \
  --output-dir /tmp/aggressive_mesh_evaluation
```

资源估算可重复生成：

```bash
python thickness_mesh_independence/aggressive_refinement/scripts/analysis/estimate_resource_envelope.py \
  --output-dir thickness_mesh_independence/aggressive_refinement/results
```

## 目录

- `config/experiment.json`：冻结的设计、阶段门限和 claim boundary；
- `results/resource_projection.*`：基于既有三级网格与开发期 mesh-only 计数的规划投影；
- `results/development_preflight/`：不作为正式端点的开发期构网格证据；
- `results/formal_preflight/`：commit `8768e6ec...` 上 G015/L010 的正式 P0 轻量结果、外部 DB 哈希和结论；
- `results/failed_p1_resource_guard/`：首次 P1 资源中止、孤儿 session 和失败二进制清理的轻量审计；
- `results/session_guard_validation/`：clean commit 上 helper 与完整 launcher TERM→KILL正式验证、进程快照和外部哈希；
- `scripts/server/`：5090d 启动器、cgroup session guard 及其回归测试；
- `scripts/analysis/`：资源收集、估算和压力对评估。

大体积 DB/RST 只能保存在新建的 5090d campaign root，不进入 Git。
