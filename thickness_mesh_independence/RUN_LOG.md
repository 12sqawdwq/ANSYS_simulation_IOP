# 网格无关性运行日志

## 2026-08-07：0.24 mm 快速筛查

### 资源预检（未接收结果）

- 外部目录：`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260807T091651Z_cef09f9_mesh0p24_screening`
- 启动：2026-08-07 09:19:50 UTC
- 中止：2026-08-07 11:31:27 UTC
- 参数：每个压力 `workers=2`、每个算例 `np=4`，最多 4 个算例同时运行，单算例超时 14400 s。
- 观察：四个首批算例在约 2 h 后仍主要位于载荷步 1；单个 0.24 mm 模型约 29 万单元、39 万节点、109 万方程，四算例临时文件约 85 GB。
- 决策：根据载荷步 2/3 的最小子步数，原超时设置存在明确的完成前超时风险，因此主动中止，不等待超时重试。
- 证据边界：中止发生在完整三载荷步结果形成前；不得从中止算例读取终点反力，也不得把它视为非收敛或网格失败。
- 清理：保留 `driver.dat`、`solve.out`、run manifest、run metadata、状态和 SHA-256；删除可再生的 DMP/MAPDL 临时文件，目录由约 85 GB 降至约 110 KB。

### 有界并行正式筛查

- 外部目录：`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260807T113236Z_cef09f9_mesh0p24_screening_bounded`
- 参数：每个压力 `workers=1`、每个算例 `np=8`，0/20 mmHg 配对并行，最多 2 个算例同时运行；单算例超时 28800 s，不自动重试。
- 原因：限制并发以降低内存和并行文件系统竞争，同时使同一厚度的 0/20 mmHg 配对同步推进。
- 状态：6/6 算例完成，全部配对 QC 通过；2026-08-07 16:09:22 UTC 结束。
- 筛查结果：厚端次序 `1.60 > 1.80 > 2.00 mm` 保留；0.24 mm 的 \(q\) 分别为 `6.6048、6.3904、5.9892 mmHg`，相对 0.30 mm 改变 `-10.41%、-11.50%、-11.92%`；1.60→2.00 mm 降幅由 `7.76%` 增至 `9.32%`。
- 决策：方向保留但幅值未满足 2% 判据，按预案启动 0.20 mm 三级确认。

### 0.20 mm 三级确认

#### MPI 资源预检（未接收结果）

- 外部目录：`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260807T161926Z_cef09f9_mesh0p20_confirmation`
- 参数：每个压力 `workers=1`、每个算例 `np=8`，最多 2 个配对算例同时运行；单算例超时 43200 s。
- 观察：1.60 mm 模型约 48.4 万单元、64.7 万节点、183 万方程；16 个 rank 的进程 RSS 约 35 GB，但合计 CPU 吞吐仅约 7 核，外部目录一度约 79 GB。
- 决策：2026-08-07 17:15 UTC 主动中止，未形成完整三载荷步结果，不接收任何数值；保留轻量诊断并清理可再生临时文件。

#### 有界 MPI 正式确认

- 外部目录：`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260807T171738Z_cef09f9_mesh0p20_confirmation_bounded_np4`
- 参数：每个压力 `workers=1`、每个算例 `np=4`，最多 2 个配对算例同时运行；单算例超时 43200 s，不自动重试。
- 原因：总 rank 由 16 降至 8，以降低内存和 DMP 文件系统竞争；模型、网格尺寸和物理参数不变。
- 结果：并行阶段的 20 mmHg 在形成任何完整终点前于 2026-08-08 01:43 UTC 中止；0 mmHg 获得独占资源后完成 1.60、1.80、2.00 mm 三个工况，三者均通过 runner QC。

#### 压力串行补充

- 20 mmHg 外部目录：`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260808T084727Z_cef09f9_mesh0p20_iop20_sequential`
- 参数：仅运行 20 mmHg，`workers=1`、`np=4`、单算例超时 43200 s、不自动重试；任一时刻仅一个 MAPDL 工况。
- 配对原则：最终评估将该目录的 20 mmHg 终点与上一目录已完成的 0 mmHg 终点按厚度配对；二者 Git SHA、APDL 哈希、网格和全部固定参数必须一致。
- 完成：2026-08-08 23:46:40 UTC，3/3 端点完成，runner return code 为 0。

#### 三级评估

- 评估生成：2026-08-09 11:44:37 UTC。
- QC：六个 0.20 mm 端点全部完成，三个载荷步全部收敛，ANSYS error 为 0，同厚度配对离散一致；最大穿透 0.009760 mm。
- 0.20 mm 的 $q(1.60,1.80,2.00)$：`5.8586、5.6457、5.2518 mmHg`。
- 0.24→0.20 mm 最大绝对变化：`12.31%`，超过冻结的 `2%` 判据。
- 厚端 1.60→2.00 mm 降幅：0.30/0.24/0.20 mm 依次为 `7.76%、9.32%、10.36%`。
- 事后形状诊断：0.24→0.20 mm 的三个厚度 $q$ 偏移约为 `-0.74 mmHg`，偏移极差 `0.0088 mmHg`；1.60–2.00 mm 对比差变化 `-1.43%`。该项不替代预设绝对 $q$ 判据。
- 判定：`thick_end_order_robust_but_amplitude_not_mesh_independent`。下降方向和次序在三个测试网格上一致，但绝对幅值未收敛，1.60 mm 不得称为真实物理阈值。

## 2026-08-11：L010首次 P1 资源中止与保护器修订

- 外部目录：`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260811T022100Z_d334fd1_L010_t2p00_iop0_20_anchor_serial_np4`。
- 源 commit：`d334fd124b768cbb53365fb19f383fa34ec9dbf7`；L010、2.00 mm、0 mmHg、0.28 mm、`np=4`、`workers=1`；20 mmHg 未启动。
- 实测规模：817,237 个实体单元、1,160,408 个节点、3,370,950 个方程；MAPDL 采用 out-of-core，四 ranks 合计 in-core 需求 73.775 GB、out-of-core 需求 14.499 GB、总分配 26.041 GB。
- 资源：`MemAvailable` 从 77,680,088 KiB 降至 12,058,648 KiB；旧 15 GiB 保护线于 `2026-08-11T02:26:03Z` 触发。
- 数值边界：载荷步 1 的 8 个子步完成，载荷步 2 已开始；载荷步 3、`RUN COMPLETED` 和完整端点均不存在；中止前未发现 MAPDL error。该事件是资源/进程包含失败，不是数值不收敛结论。
- 进程缺陷：旧 launcher 只终止 runner process group，`SID=439551` 的 MAPDL/MPI 树继续运行；完整 session 于 `2026-08-11T04:24:15Z` 停止。
- 清理：按文件清单和哈希删除失败 attempt 的 47 个 DB/RST/scratch，表观 90,442,977,929 bytes、实际 83,147,467,776 bytes；没有删除接收结果。
- 判定：`resource_guard_abort_with_orphan_process_cleanup`；0 mmHg 不接收，不能计算 $q$，旧二进制不可续算。
- 修订：launcher 改用 user-systemd cgroup + 随机 campaign token，强制每 campaign 只运行一个压力，启动/中止门限改为内存 90/30 GiB、磁盘 150/100 GiB，监控间隔 10 s，并执行 TERM→KILL及零残留核验。
- 开发期保护器测试：三个不同 SID/PGID 的嵌套进程中，模拟 MAPDL/Hydra 的进程忽略 TERM；2 s 后 KILL，最终残留 0。
- 正式保护器验证：clean commit `c62987d795711052170f3538517e38fff5c0aa18` 上同时通过 helper 和完整 launcher TERM 路径；完整 launcher 预期 return code 143、campaign incomplete、TERM→KILL、fixture残留 0、活动测试 unit 0，且未调用 ANSYS。外部根为 `/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260811T063315Z_c62987d7_session_guard_validation`。
- 当前边界：旧失败二进制不可续算；只允许在新 commit、新 campaign root 和实时资源门通过后重算 0 mmHg。20 mmHg 仍未授权。
