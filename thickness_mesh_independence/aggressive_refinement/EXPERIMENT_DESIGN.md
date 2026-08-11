# 激进接触区网格实验设计

## 1. 目的与当前状态

本实验在独立 Git 分支 `aggressive-contact-mesh-experiment-20260810` 上设计，用于回答：在 5090d 当前资源条件下，能否在约 2–3 天墙钟预算内，把决定探头反力的中央接触与界面区域从 0.20 mm 进一步细化到名义 0.10 mm，并判断绝对零基线输出 \(q\) 是否开始收敛。

当前状态是 **正式 clean-commit P0 mesh-only 已完成；首次 P1 的 0 mmHg 算例因资源保护中止并被拒绝；20 mmHg 未启动；cgroup session guard 已在 clean commit `c62987d...` 上正式验证**。P0 不包含非线性求解。失败 P1 没有完整端点，也不产生可进入 \(q\) 比较的数据。现在只允许在实时资源门再次通过后，从新 root 重算 0 mmHg。

本实验不把“局部目标尺寸 0.10 mm”自动等同于网格无关。`EREFINE` 给出的是父四面体的一次局部细分，正式后处理仍必须审计实际边长分布、单元质量、接触表面密度和求解器规模。

## 2. 为什么不直接全局缩到 0.10 mm

使用 2.00 mm、20 mmHg 三个已接收全局网格的实测规模做对数—对数拟合，得到近似指数：

- 单元数：\(N_e\propto h^{-2.905}\)；
- 节点数：\(N_n\propto h^{-2.886}\)；
- 方程数：\(N_{eq}\propto h^{-2.896}\)；
- RST 大小：\(S_{rst}\propto h^{-2.948}\)。

资源投影为：

| 策略 | 预计单元 | 预计节点 | 预计方程 | 单端点 RST | 2.00 mm 压力对墙钟范围 | 六端点墙钟范围 |
|---|---:|---:|---:|---:|---:|---:|
| 全局 0.15 mm | 1,333,685 | 1,773,865 | 5,072,090 | 28.64 GiB | 25.7–42.4 h | 69.6–115.0 h |
| 全局 0.12 mm | 2,550,342 | 3,377,700 | 9,679,965 | 55.30 GiB | 49.0–119.2 h | 132.9–323.4 h |
| 全局 0.10 mm | 4,331,492 | 5,716,800 | 16,413,895 | 94.66 GiB | 83.1–277.5 h | 225.3–752.8 h |
| 分层局部 0.10 mm | 817,237 个实体单元 | 1,160,408 | 约 3,314,954 | 约 18.38 GiB | 16.8–21.5 h | 45.5–58.2 h |
| 分层局部 0.05 mm | 2,880,653 个实体单元 | 3,986,139 | 约 11,387,259 | 约 63.13 GiB | 57.6–154.6 h | 156.3–419.4 h |

墙钟上限只是按方程增长施加超线性惩罚后的规划范围，不是受控速度标定。0.30/0.24/0.20 mm 历史算例使用了不同 ranks 和 I/O 条件，因此不能把该表当作 MAPDL 性能保证。

初始服务器评估快照为 16 个物理核、123 GiB 总内存、约 78 GiB 可用内存、8 GiB swap 和约 148 GiB可用数据盘。全局 0.10 mm 的单个 RST 就预计接近 95 GiB，且方程数超过现有 0.20 mm 的七倍；它不满足当前内存、存储或 72 h 预算，应在求解前拒绝。2026-08-11 清理后 `/home` 空闲约 450 GiB；临时将 ZFS ARC 限制为 16 GiB 后 `MemAvailable` 约 100.33 GiB。后者只是运行时管理员调优，不是资源预留或持久配置。

开发期间一次未形成端点的普通 0.20 mm 资源诊断显示，约 219.9 万方程的单 rank 稀疏直接解法报告总分配 49.473 GB、in-core 需求 41.896 GB。该诊断被主动中止并清理，不能作为数值结果，但进一步说明 1641 万方程的全局 0.10 mm 不宜直接启动。

## 3. 选定的局部方案

### 3.1 背景与目标尺寸

- 背景网格：0.20 mm；
- 一级局部细化：每个被选 SOLID187 父单元细分一次，名义目标 0.10 mm；
- 二级局部细化：重复两次，名义目标 0.05 mm；只允许 mesh-only 预检，默认不允许非线性求解；
- 局部细化发生在创建节点约束、接触单元和持久 node component 之前。

### 3.2 空间范围

0.20 mm 六个已接收状态的最终等效接触半径为 1.4391–1.5308 mm。实验冻结中央半宽为 1.80 mm，比最大等效半径大 17.58%。该范围与两个 0.80 mm 厚的轴向带相交：

1. 眼睑—角膜界面带：\(y=-0.40\sim+0.40\) mm；
2. 探头—眼睑路径带：以眼睑顶点和初始探头底面为基准，覆盖界面两侧各约 0.40 mm。

选择区是确定性的 Cartesian 方盒，不是把等效圆半径冒充真实接触边界。`EREFINE` 的一层过渡还会在选择区外增加相容单元。

### 3.3 开发期 mesh-only 结果

2.00 mm 几何的开发期 L010 预检得到：

- 细化前实体单元 538,725、节点 769,607；
- 首次选择父单元 44,812；
- 细化后实体单元 817,237、节点 1,160,408；
- 元素增长 1.517×，节点增长 1.508×；
- mesh-only 墙钟 25.82 s，最大 RSS 3,001,248 KiB；
- MAPDL error 0，初始自由网格形状 warning 涉及 32/393,079 个新建或修改单元，没有 shape error；局部细化阶段未新增 warning；
- 没有创建接触单元、没有施加载荷、没有启动非线性求解。

同一开发源对 L005 连续执行两次细化后，实体单元增至 2,880,653、节点增至 3,986,139；mesh-only 墙钟 96.08 s、最大 RSS 17,659,084 KiB、MAPDL error 0。初始自由网格有 32 个 shape warning 单元，第二次细化有 18/2,373,301 个新建或修改单元触及 warning 限制，shape error 为 0。按节点比投影约为 1139 万方程和 63.13 GiB RST/端点，仅 2.00 mm 压力对就需要约 126 GiB RST，尚未包含 DB、scratch 和求解内存。因此 L005 **构网格可行，但当前服务器上非线性求解不可接受**。

证据位于 `results/development_preflight/`。由于运行时工作树尚未提交，它只能用于资源评估；正式 P0 必须在 clean commit 上重跑。

## 4. 分阶段实验矩阵

### P0：正式 mesh-only 预检

| 策略 | 背景 | 局部目标 | 2.00 mm | 非线性求解 |
|---|---:|---:|---:|---:|
| G015 | 0.15 mm | 0.15 mm | 1 个 mesh-only | 否 |
| L010 | 0.20 mm | 0.10 mm | 1 个 mesh-only | 否 |
| L005 | 0.20 mm | 0.05 mm | 默认关闭 | 否 |

P0 必须保存实际单元/节点增长、DB 大小、MAPDL warning/error、墙钟、最大 RSS、源 commit 和宏 SHA-256。L005 只有设置 `RUN_EXTREME=1` 才会构网格；即使成功，也不会自动进入求解。

commit `8768e6ec6afb41225d729c21aac80b467c266897` 上的正式 P0 已完成：G015 为 1,292,705 个实体单元、1,813,547 个节点，L010 为 817,237 个实体单元、1,160,408 个节点；两者均 `RUN COMPLETED`、MAPDL error 0、shape error 0。G015 比 L010 多约 58.2% 实体单元和 56.3% 节点，同时目标界面更粗，因此不进入优先求解；L010 获得 P1 资源审查资格。详见 `results/formal_preflight/CONCLUSION.md`。

### P1：2.00 mm 锚点压力对

在 P0 通过后，仅运行：

- 2.00 mm × 0 mmHg × L010；
- 2.00 mm × 20 mmHg × L010。

首次 P1 在 commit `d334fd124b768cbb53365fb19f383fa34ec9dbf7` 上启动 0 mmHg 后被资源保护中止。实测模型为 3,370,950 方程；四 ranks 合计 in-core 需求 73.775 GB、out-of-core 需求 14.499 GB，MAPDL 采用 out-of-core。`MemAvailable` 最低 11.50 GiB；旧 launcher 返回 143，但 MAPDL/MPI 的独立 session 未随 runner process group 退出。孤儿 session 停止后，失败 attempt 的 47 个 DB/RST/scratch 经清单和哈希审计删除。载荷步 1 完成、载荷步 2 开始，但载荷步 3 和 `RUN COMPLETED` 不存在，因此不接收端点。

修订后两压力不能在同一 campaign 自动串行：每个 campaign 强制恰好一个压力、每次一个 MAPDL、4 ranks、1 worker、无重试。先从新 root 重算 0 mmHg；只有其三个载荷步、ANSYS error、资源和零残留人工 QC 全部通过后，才允许另建 20 mmHg campaign。单算例上限 24 h。P1 是资源和绝对幅值的共同锚点，不在一开始同时提交六个大算例。

### P2：厚端次序扩展

只有同时满足以下条件，才运行 1.60 和 1.80 mm 的四个 L010 端点：

1. P1 两端点完整且全部 QC 通过；
2. P1 实测墙钟外推后，完整 campaign 可在 72 h 内结束；
3. 至少还有 36 h campaign 预算；
4. 已明确预留足够磁盘，且不删除 P1 的 DB/RST 来腾空间；
5. 当前服务器没有其他高内存或高 I/O MAPDL 任务。

### P3：0.05 mm 二级局部锚点

L005 需要对同一区域连续调用两次 `EREFINE`。开发期 mesh-only 已确认其约 288 万实体单元、399 万节点，资源投影超过当前 72 h、内存和保留压力对 RST 的门限。因此 P3 在本轮中冻结为 **mesh-only 可构建、非线性求解拒绝**。这属于资源不可接受，不得称为数值不收敛。只有迁移到更大内存与存储资源并另行授权，才能重新讨论 L005 压力对。

## 5. 运行资源保护

正式 launcher 具有以下保护：

- 必须显式提供 `EXPECTED_COMMIT`；
- 5090d 工作树必须干净且恰好位于该 commit；
- campaign root 必须预先不存在；
- user systemd manager 和 cgroup v2 必须可用，否则在求解前拒绝；
- 启动前至少 90 GiB `MemAvailable` 和 150 GiB 空闲磁盘；
- 运行中每 10 s 记录可用内存和磁盘；
- 可用内存低于 30 GiB或空闲磁盘低于 100 GiB时，主动终止完整 service cgroup；
- 每个 campaign 强制恰好一个压力，0/20 mmHg 不自动串联；
- MAPDL/MPI 即使创建嵌套 `setsid`，仍由 user-systemd cgroup 包含；随机 `BLUEKNOW_CAMPAIGN_TOKEN` 用于检出任何异常脱离 cgroup的同 campaign 进程；
- 中止先向完整 cgroup/token 集合发 TERM，等待后升级 KILL，并保存 PID、PPID、SID、PGID 与命令快照；
- 信号或 launcher 异常退出通过 EXIT trap 使用同一清理路径；任何残留使 campaign 硬失败；
- 单算例上限 24 h，不能通过重试静默延长；
- 被资源保护中止的部分载荷步不进入数值比较。

清理后磁盘已不再是当前首要阻塞，但正式运行仍保留 150/100 GiB 两级门限，避免约 83.15 GiB 的失败 attempt 临时分配峰值再次耗尽文件系统。P2 仍不是自动阶段；必须按新端点的实际 RST、DB、scratch、墙钟和内存重新评估。

## 6. 数值与物理验收

### 6.1 单算例 QC

每个接收端点必须满足：

- runner `status=complete`、return code 0；
- 三个载荷步全部收敛，最终 `result_load_step=3`；
- ANSYS error count 0；
- 初始接触前探头力绝对值不超过 0.001 N；
- 最大穿透不超过 0.03 mm；
- 同厚度 0/20 mmHg 的 Git SHA、APDL 哈希、ANSYS 版本、背景网格、局部级别、节点数、单元数和全部固定物理参数一致。

### 6.2 正式输出

保持原定义：

\[
q_{20}(h)=\frac{F(h,20,0.28)-F(h,0,0.28)}{A_{probe}},
\qquad A_{probe}=14.65741468458854\ \mathrm{mm^2}.
\]

不得混入 \(K_{geo}\)、\(A_e\) 或 \(A_{c,5^\circ}\)。除 \(q\) 外还记录两压力总力、接触面积、峰值接触压力、穿透、活跃接触节点、单元/节点/方程、墙钟、RSS 和 RST 大小。

### 6.3 判定层级

1. **策略筛查**：L010 相对现有全局 0.20 mm 的 \(|\Delta q|\le2\%\)；这只是两种离散策略的差异筛查；
2. **厚端次序**：如果 P2 完整，检查 \(q(1.60)>q(1.80)>q(2.00)\)；
3. **绝对幅值收敛**：必须有 L005 与 L010 的完整同厚度压力对，且最新变化不超过 2%，才能支持锚点的绝对幅值收敛；
4. **网格无关**：即使 2.00 mm 锚点通过，也不能自动外推到其他厚度；三个厚度均需相应证据；
5. **物理外推**：任何通过都只适用于当前有限元模型，不建立真实组织阈值或临床标定。

## 7. 推荐执行顺序

1. G015 和 L010 的正式 P0 已完成；
2. 首次 P1 失败 attempt 已归档为资源中止，没有接收端点；
3. cgroup session guard 已在 clean commit `c62987d...` 上完成不涉及 ANSYS 的嵌套 `setsid` 和完整 launcher TERM→KILL 正式回归测试；
4. 每次正式启动前重新回读临时 ARC 上限、`MemAvailable>=90 GiB`、空闲磁盘、swap和活动求解器；
5. 使用新 root 只运行 L010、2.00 mm、0 mmHg；
6. 人工审核三个载荷步、`RUN COMPLETED`、ANSYS error 0、资源、文件规模和零残留；
7. 只有第 6 步通过后，才另建 root 并单独授权 20 mmHg；
8. P1 压力对完成后运行 `evaluate_aggressive_refinement.py`，在读取 P2 前冻结是否继续；
9. 只有预算和磁盘门限均通过才运行 P2；
10. L005 保持 mesh-only；当前资源快照下明确拒绝非线性求解，除非迁移资源并另行授权；
11. 最终将轻量 CSV/JSON、运行 manifest、配置、源 SHA 和结论纳入 Git，大体积 DB/RST 留在 5090d；
12. 求解全部结束后由管理员把临时 `zfs_arc_max` 恢复为 `0`。

## 8. 入口

- 配置：`config/experiment.json`
- 资源投影：`results/resource_projection.csv`、`resource_projection.json`
- 开发期 mesh-only 证据：`results/development_preflight/manifest.json`
- 正式 P0 结论与 provenance：`results/formal_preflight/CONCLUSION.md`、`results/formal_preflight/manifest.json`
- 失败 P1 轻量证据：`results/failed_p1_resource_guard/README.md`、`results/failed_p1_resource_guard/manifest.json`
- P0 启动器：`scripts/server/launch_mesh_preflight_5090d.sh`
- P1/P2 单压力启动器：`scripts/server/launch_aggressive_anchor_5090d.sh`
- cgroup/session guard：`scripts/server/session_guard.sh`
- session guard 回归测试：`scripts/server/test_session_guard_5090d.sh`
- 完整 launcher 信号回归测试：`scripts/server/test_anchor_launcher_signal_5090d.sh`
- P0 收集器：`scripts/analysis/collect_mesh_preflight.py`
- 资源估算：`scripts/analysis/estimate_resource_envelope.py`
- 压力对评估：`scripts/analysis/evaluate_aggressive_refinement.py`
