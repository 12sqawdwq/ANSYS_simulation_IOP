# 1.25 mm L010 IOP20启动记录

根据用户明确要求，在0 mmHg不完整attempt完成隔离、哈希审计和清理后，只启动20 mmHg：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T034259Z_5d3ece4b_L010_h1p25_iop20_guarded_np4
```

正式源commit为`5d3ece4bccf67e382bdfa639b0da80711c8008b8`，启动时5090d工作树干净，基线为1.25 mm，solver和运行中的Blueknow unit均为0；可用内存112,715,100 KiB、空闲磁盘456,996,224 KiB，临时ZFS ARC上限为16 GiB。实际driver明确记录1.25 mm、20 mmHg对应2666.44736842 Pa、局部细化一级，runner记录4 MPI ranks、1 worker和retry 0。

早期核验时模型为2,711,583个方程，采用in-core求解，MAPDL error为0，外层和内层systemd cgroup均为active/running。该目录只记录受控启动，不是完整端点或科学结论。即使20 mmHg完整完成，在0 mmHg从新root重跑并接收前仍不能计算$q$。
