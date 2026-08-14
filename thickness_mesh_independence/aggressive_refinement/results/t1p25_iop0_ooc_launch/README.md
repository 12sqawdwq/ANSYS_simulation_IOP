# 1.25 mm L010 IOP0 out-of-core重跑启动记录

用户在IOP20端点接收并被告知IOP0仍缺失后明确要求“继续”。IOP0于`2026-08-14T02:53:31Z`作为独立单压力campaign从同一clean commit `6ef45199bec06139538c5a68a1538ae683ea1c3b`启动：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260814T025331Z_6ef45199_L010_h1p25_iop0_ooc_last_np4
```

启动门为：solver 0、运行中Blueknow unit 0、`MemAvailable=120,271,980 KiB`、空闲磁盘455,449,472 KiB、ZFS ARC上限17,179,869,184 bytes。条件保持1.25 mm、0 mmHg、0.28 mm推进、L010、4 MPI ranks、1 worker和retry 0；未复用此前用户主动中止的IOP0 root。

实际driver冻结`solver_out_of_core=1`、`result_last_only=1`与`encoded_mode=11010`。MAPDL首次矩阵初始化报告2,711,583方程、四rank合计solver/non-solver分配17.776 GB，并实际进入`out-of-core memory mode`；launcher已记录`solver_mode_verified,out-of-core`。

本目录仅冻结授权、启动门和运行时策略验证证据，不是端点。只有本campaign自然完成并通过完整QC，才能与已接收IOP20端点配对计算$q_{20}$。
