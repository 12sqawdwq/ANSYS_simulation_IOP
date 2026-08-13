# 1.25 mm全局基线 L010 IOP0启动记录

已于2026-08-13T02:54:18Z只启动1.25 mm、0 mmHg端点：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T025418Z_011c77e7_L010_h1p25_iop0_guarded_np4
```

源commit为`011c77e74e08fd7619cb9cda3d834cfe3b8506dd`，服务器工作树启动时干净。launcher从`config/model_baseline.json`读取1.25 mm，campaign状态记录`thickness_mode=global_baseline`；4 MPI ranks、1 worker、无重试、24 h单例超时，采用90/30 GiB内存门和150/100 GiB磁盘门。

启动后确认外层和内层systemd service均为`active/running`，runner元数据实际厚度为1.25 mm、IOP为0 mmHg，模型有2,711,583个方程，采用in-core稀疏求解。该记录只证明受控启动，不是完整端点或科学结论。20 mmHg未启动，也未授权。
