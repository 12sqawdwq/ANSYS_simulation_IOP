# IOP20启动包装器失败记录

首次20 mmHg调度root：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T034039Z_5d3ece4b_L010_h1p25_iop20_guarded_np4
```

外层systemd unit因调度包装器直接执行没有Git executable bit的launcher而返回126（permission denied）。launcher、ANSYS和MPI均未启动，活动solver和Blueknow unit均为0；root只含调度元数据和审计文件，不是数值attempt，也没有可接收结果。修正方式是通过`/bin/bash <launcher>`调用，并让launcher自行创建另一个全新root；未复用本目录。
