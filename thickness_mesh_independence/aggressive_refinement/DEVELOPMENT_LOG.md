# 激进网格方案开发记录

本文件记录正式 commit 冻结前的资源探索。除 `results/development_preflight/` 保存的最终 mesh-only 轻量证据外，所有临时 DB、求解矩阵和试验目录均已清理。这里的任何状态都不是可接收的 \(q\) 端点。

## 2026-08-10

### 既有 DB 上的 `EREFINE` 语法检查

- 在既有 0.20 mm DB 副本上选择中央实体单元并调用 `EREFINE`；
- MAPDL 明确报错：已有节点载荷和约束必须先删除；
- 没有单元被细化，error count 1；
- 由此确定正式实现必须放在体网格完成后、节点约束和接触元素创建前；
- 临时目录已删除，不进入数值比较。

### 参数传递失败与普通 0.20 mm 资源诊断

- 初版开发宏错误地尝试使用 `ARG10–ARG12`；当前 `*USE` 调用实际只可靠传递九个参数，额外参数未生效；
- mesh-only 标志因此没有生效，MAPDL 对普通 0.20 mm、2.00 mm 模型进入了载荷步 1；
- 发现后主动中止，未形成完整载荷步、未接收任何端点；
- 中止前报告 2,198,547 方程、总 solver/non-solver 分配 49.473 GB、in-core equation solver 需求 41.896 GB；
- 约 2.1 GB 临时 `esav` 和其他 scratch 已清理；
- 该事件只用于内存风险审计，不能作为速度标定或数值结果。

### 执行模式编码修复

为保持九参数接口，`ARG3` 改为十进制编码：

- 个位：retry mode；
- 十位：局部 `EREFINE` 次数；
- 百位：mesh-only 标志。

生产默认 `ARG3=0/1` 的行为保持不变。runner 根据 `--local-refine-level` 生成编码值。

### 局部区域收缩过程

| 开发区域 | 局部目标 | 父单元选择 | 细化后实体单元 | 细化后节点 | mesh-only 墙钟 | 最大 RSS | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| 2.70 mm 半宽、贯穿中央组织/下探头 | 0.10 mm | 150,027 | 1,555,348 | 2,164,450 | 45.32 s | 9,187,204 KiB | 规模过大，放弃 |
| 1.80 mm 半宽、贯穿中央组织/下探头 | 0.10 mm | 84,400 | 1,110,155 | 1,544,397 | 29.01 s | 5,487,332 KiB | 仍偏大 |
| 1.80 mm 半宽、两个 1.10 mm 界面带 | 0.10 mm | 58,380 | 900,975 | 1,284,886 | 23.39 s | 4,202,076 KiB | 可行但仍可收缩 |
| 1.80 mm 半宽、两个 0.80 mm 界面带 | 0.10 mm | 44,812 | 817,237 | 1,160,408 | 25.82 s | 3,001,248 KiB | 选为 L010 |
| 同一区域显式连续细化两次 | 0.05 mm | 累计 351,312 | 2,880,653 | 3,986,139 | 96.08 s | 17,659,084 KiB | mesh-only 可行，拒绝非线性求解 |

前几档临时文件已清理。L010 和 L005 的宏哈希、driver、inventory、归档为 `mesh_log.txt` 的 MAPDL 输出和 `resource_time.txt` 记录保存在 `results/development_preflight/manifest.json`。

### 0.05 mm 语义修复

- 单次 `EREFINE,all,2,1` 只执行了一次拓扑细分，不能把它当作 0.05 mm；
- 正式实现改为显式循环：一级调用一次，二级调用两次，并在每次细分后重新建立几何选择；
- 早期“level=2 但计数与 level=1 相同”的试验不登记为 L005 结果；
- 真正 L005 的开发期 mesh-only 已完成：约 288 万实体单元、399 万节点、最大 RSS 16.84 GiB；
- 按节点比投影约 1139 万方程、63.13 GiB RST/端点，当前资源下拒绝非线性求解；
- committed P0 仍可通过 `RUN_EXTREME=1` 复核 mesh-only 可重复性，但不得自动升级为求解。

## 状态边界

开发期最终 L010 证明代码能够在约 26 s 内生成预期局部网格，并将节点增长限制在约 1.51×。它没有证明：

- 完整接触元素生成后规模一定符合投影；
- 稀疏直接求解内存一定足够；
- 三个非线性载荷步会收敛；
- \(q\) 会满足 2% 判据；
- L005 在当前服务器可求解。

以上问题必须由 clean-commit P0/P1 依次回答。

## 2026-08-11

### 首次 P1 资源中止

在 clean commit `d334fd124b768cbb53365fb19f383fa34ec9dbf7` 上启动 L010、2.00 mm、0 mmHg、4 ranks。模型为 817,237 个实体单元、1,160,408 个节点、3,370,950 个方程。MAPDL 报告四 ranks 合计 in-core 需求 73.775 GB、out-of-core 需求 14.499 GB、总 solver/non-solver 分配 26.041 GB，并选择 out-of-core。

`MemAvailable` 从 77,680,088 KiB 降至 12,058,648 KiB；旧 15 GiB 保护线于 `2026-08-11T02:26:03Z` 触发。载荷步 1 的 8 个子步均完成，载荷步 2 已开始，但载荷步 3、`RUN COMPLETED` 和完整终点均不存在；20 mmHg 未启动。该事件归类为资源失败，不是已证明的数值不收敛。

旧 launcher 只向 runner process group 发 TERM。runner 和 MAPDL 各自使用 `start_new_session`/MPI session，导致 `SID=439551` 的 MAPDL/MPI 树继续运行。完整 session 于 `2026-08-11T04:24:15Z` 停止。随后按清单删除 47 个失败 attempt 的 DB/RST/scratch：表观 90,442,977,929 bytes、实际分配 83,147,467,776 bytes；未删除任何接收端点。轻量证据位于 `results/failed_p1_resource_guard/`。

### 资源和终止策略修订

- 启动门限提高到 `MemAvailable>=90 GiB`、空闲磁盘 `>=150 GiB`；
- 中止线提高到可用内存 30 GiB、空闲磁盘 100 GiB；
- 监控间隔从 60 s 缩短到 10 s；
- 每个 campaign 强制只允许一个压力；0 mmHg 通过人工 QC 后才能另行授权 20 mmHg；
- launcher 改用 user-systemd service/cgroup，并设置随机 `BLUEKNOW_CAMPAIGN_TOKEN`；
- TERM 作用于完整 cgroup 和 token 进程集合，超时后升级 KILL；
- 保存 TERM/KILL 前进程的 PID、PPID、SID、PGID 和命令；任何残留都会把 campaign 判为失败；
- 信号和异常退出也通过 EXIT trap 清理完整 process set。

开发期不涉及 ANSYS 的实机测试构造了三个不同 SID/PGID 的进程，其中模拟 MAPDL/Hydra 的两个子进程忽略 TERM。保护器在 2 s 后升级 KILL并确认残留为 0。另一次完整 launcher 测试以假 solver 通过 commit/resource gate、systemd unit和监控路径，再向 launcher 发 TERM；campaign 正确标记 incomplete，launcher return code 143，TERM→KILL 后 fixture 残留和活动 `blueknow-*` unit 均为 0。

正式验证期间先后修复了两个仅属于测试 harness 的误判：KILL 后被 init 回收前的短暂进程状态，以及 `pgrep -f` 匹配上层 wrapper 命令行中的 fixture 字符串。两次不完整验证均未启动 ANSYS，外部目录保留 `VALIDATION_INCOMPLETE.txt` 和哈希。最终测试改为按 fixture 的精确 `argv[0]` 匹配，并在 clean commit `c62987d795711052170f3538517e38fff5c0aa18` 上完成：helper 和完整 launcher 信号测试均通过，残留进程 0、活动 `blueknow-*` unit 0。正式轻量证据位于 `results/session_guard_validation/`。

### 临时 ZFS ARC 调优

授权后将 `zfs_arc_max` 临时设为 17,179,869,184 bytes（16 GiB）。`2026-08-11T05:55:46Z` 回读 ARC 约 15.68 GiB、`MemAvailable` 约 100.33 GiB、无活动求解器。该系统参数不是 Git 管理的持久配置；正式运行前必须重新回读，求解结束后恢复动态值 `0`。

## 2026-08-13

### 1.25 mm IOP20近终点资源中止

在clean commit `5d3ece4bccf67e382bdfa639b0da80711c8008b8`上运行1.25 mm、20 mmHg L010。模型为655,574个实体单元、940,688个节点、2,711,583个方程。MAPDL自动选择in-core：四rank合计in-core求解器需求48.900 GB、solver/non-solver分配60.353 GB。

载荷步1和2均完成8个子步；载荷步3完成12个子步，累计54次平衡迭代，最后收敛伪时间2.928125（正式压入0.259875 mm）。全部28个完成子步收敛，MAPDL error、非收敛、二分、cutback、负主元和shape error均为0。`2026-08-13T07:39:44Z`可用内存降至30,237,892 KiB，触发30 GiB保护线；此时仍缺0.28 mm终点、`RUN COMPLETED`和完整RST，因此不接收为端点。

session guard将完整树终止为零残留。按用户授权，先冻结路径、大小、allocated bytes、mtime、类别和SHA-256，再删除失败attempt的不完整DB/RST与可再生scratch；轻量证据位于`results/t1p25_iop20_resource_aborted/`。

### 重跑策略

原样in-core重跑被拒绝。runner增加显式solver memory mode和结果输出频率编码；L010 launcher固定请求out-of-core、只保存每个载荷步末态，并在运行早期读取`solve.out`确认实际模式。若观察到in-core或在限定时间内未观察到out-of-core，完整session tree会被受控终止。物理条件、4 ranks、单压力、90/30 GiB内存门和150/100 GiB磁盘门保持不变。
