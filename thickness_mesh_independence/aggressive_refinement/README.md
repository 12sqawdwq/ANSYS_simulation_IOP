# 激进接触区网格实验

本目录是独立实验分支 `aggressive-contact-mesh-experiment-20260810` 的入口。目标是在 72 h 墙钟预算内优先细化决定探头积分反力的两条中央界面，而不是直接启动资源上不可接受的全局 0.10 mm 矩阵。仓库全局眼睑厚度基线为 1.25 mm；本实验的 2.00 mm 锚点及可选 1.60/1.80 mm 工况属于厚端网格问题的显式覆盖，不能作为 1.25 mm 基线结果解释。

## 当前决策

- **拒绝直接求解全局 0.10 mm**：预计约 433 万单元、1641 万方程、单端点约 94.7 GiB RST；
- **主方案 L010**：0.20 mm 背景 + 1.80 mm 中央半宽 + 两个 0.80 mm 界面带 + 一级 `EREFINE`，局部名义目标 0.10 mm；
- **极限方案 L005**：同一区域二级细化至名义 0.05 mm；开发期 mesh-only 得到约 288 万实体单元、399 万节点，预计约 1139 万方程和 63.13 GiB RST/端点，因此当前服务器只保留构网格证据并拒绝非线性求解；
- **先锚点、后扩展**：先做 2.00 mm 的 0/20 mmHg 压力对，资源和 QC 通过后才考虑 1.60/1.80 mm；
- **正式 P0 已完成**：commit `8768e6ec...` 上的 G015/L010 mesh-only 均通过；
- **首次 P1 已被拒绝**：commit `d334fd1...` 上的 0 mmHg 算例因资源保护中止，20 mmHg 未启动；没有完整端点，也不能计算 \(q\)。旧 launcher 只终止 runner process group，MAPDL/MPI 独立 session 一度残留；失败二进制经审计后已清理；
- **重启保护已正式验证**：新 launcher 使用 user-systemd cgroup、随机 campaign token、TERM→KILL 升级和零残留核验；clean commit `c62987d...` 上的 helper 与完整 launcher 信号测试均通过且未调用 ANSYS。默认每个 campaign 只允许一个压力，0 mmHg 人工 QC 通过前不得启动 20 mmHg；
- **2.00 mm、0 mmHg端点已接收**：commit `abf4175...` 的新campaign在约10.67 h后自然完成，三个载荷步、返回码、ANSYS error、穿透、资源和零残留均通过；轻量证据见 [`results/accepted_iop0_h2p00/`](results/accepted_iop0_h2p00/)。该端点是2.00 mm显式厚度覆盖，不是1.25 mm基线；
- **当前新阶段为1.25 mm全局基线**：launcher默认从 `config/model_baseline.json` 读取1.25 mm；1.25 mm L010 mesh-only预检已通过。按用户优先级切换后，0 mmHg主动中止，第一次20 mmHg在伪时间2.928125、压入0.259875 mm后因30 GiB内存保护线中止。28个已完成子步均收敛，但没有正式端点；轻量证据见 [`results/t1p25_iop20_resource_aborted/`](results/t1p25_iop20_resource_aborted/)；
- **IOP20重跑已以显式out-of-core完成并接收**：全新root通过runner参数冻结`out-of-core`与每载荷步末态输出，launcher运行早期确认实际模式；29个子步、三个载荷步、`RUN COMPLETED`、MAPDL error 0、资源和零残留全部通过。正式$F_{20}=-0.18100135590385$ N，轻量证据见 [`results/accepted_iop20_t1p25_ooc/`](results/accepted_iop20_t1p25_ooc/)；
- **IOP0重跑已完成并接收**：同一源码commit和out-of-core/last-only策略下完成29个子步、三个载荷步，`RUN COMPLETED`、MAPDL error 0、资源、warning、接触边界与零残留QC全部通过；正式$|F_0|=0.17134016405785$ N，证据见 [`results/accepted_iop0_t1p25_ooc/`](results/accepted_iop0_t1p25_ooc/)；
- **1.25 mm L010压力对已接收**：同配置配对得到$q_{20}=4.9439072093374365$ mmHg；末态中央剖面`007`与完整配对证据见 [`results/t1p25_l010_pressure_pair/`](results/t1p25_l010_pressure_pair/)。该值相对既有全局0.30 mm结果低30.09%，只能作为L010离散结果，不能宣称绝对网格无关。

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

## 1.25 mm全局基线阶段

本阶段保持L010网格策略、材料、0.28 mm推进、0.30 mm初始间隙、4 ranks、1 worker和资源门不变，只把眼睑厚度切换为机器可读全局基线1.25 mm。由于几何变化会改变实际单元/节点数，非线性求解前必须先运行同一commit上的1.25 mm mesh-only预检；预检只验证构网格和shape error，不产生力学端点。

每个campaign仍严格只含一个压力。0和20 mmHg均已从独立新root自然完成，并通过三个载荷步、`RUN COMPLETED`、ANSYS error、穿透、资源、out-of-core实际模式和残留人工QC；同配置压力对现可计算$q$。

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

启动器要求 `MemAvailable>=90 GiB`、空闲磁盘 `>=150 GiB`，每 10 s 监测；30 GiB 内存或 100 GiB 磁盘保护线触发时终止完整 cgroup/token process set。已完成的1.25 mm压力对严格按两个独立新root运行，并在30 min内从`solve.out`核实out-of-core；两端点均完成人工QC。

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
- `results/t1p25_iop20_resource_aborted/`：1.25 mm IOP20近终点资源中止、数值状态和失败二进制清理的轻量审计；
- `results/accepted_iop20_t1p25_ooc/`：已接收1.25 mm IOP20 out-of-core端点的标量、资源、warning、外部哈希和QC；
- `results/t1p25_iop0_ooc_launch/`：1.25 mm IOP0独立out-of-core重跑的授权、资源门、driver和实际solver模式证据；
- `results/accepted_iop0_t1p25_ooc/`：已接收1.25 mm IOP0端点的标量、资源、warning、边界图、外部哈希和QC；
- `results/t1p25_l010_pressure_pair/`：同配置0/20 mmHg压力对、$q_{20}$、中央剖面`007`和claim边界；
- `scripts/server/`：5090d 启动器、cgroup session guard 及其回归测试；
- `scripts/analysis/`：资源收集、估算和压力对评估。

大体积 DB/RST 只能保存在新建的 5090d campaign root，不进入 Git。
