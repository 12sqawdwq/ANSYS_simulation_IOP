# 1.25 mm L010 IOP20 out-of-core重跑启动记录

用户明确授权重新求解后，campaign于`2026-08-13T14:08:38Z`从clean commit `6ef45199bec06139538c5a68a1538ae683ea1c3b`启动：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T140838Z_6ef45199_L010_h1p25_iop20_ooc_last_np4
```

实时启动门为：solver 0、运行中Blueknow unit 0、`MemAvailable=119,194,160 KiB`、空闲磁盘456,861,824 KiB、ZFS ARC上限17,179,869,184 bytes。物理与网格条件保持1.25 mm、20 mmHg、0.28 mm推进、L010、4 MPI ranks、1 worker、retry 0；每个campaign仍只有一个压力。

实际driver冻结`solver_out_of_core=1`、`result_last_only=1`和`encoded_mode=11010`。MAPDL早期日志明确报告2,711,583方程、四rank合计solver/non-solver内存分配17.776 GB，并实际进入`out-of-core memory mode`；launcher的运行时模式门已记录`solver_mode_verified,out-of-core`。与失败的in-core attempt的60.353 GB相比，报告分配降低约70.5%。

本目录只冻结启动和模式确认时的轻量证据，不是完整端点。求解完成前不存在正式`F20`；即使本端点完成，在0 mmHg从全新root重跑并接收前仍不能计算$q$。大体积DB/RST留在上述5090d root，成功端点的RST在后处理和人工QC完成前不会删除。
