# 已接收的1.25 mm L010 IOP20 out-of-core端点

正式campaign：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T140838Z_6ef45199_L010_h1p25_iop20_ooc_last_np4
```

求解源码为clean commit `6ef45199bec06139538c5a68a1538ae683ea1c3b`。条件为1.25 mm、20 mmHg、0.28 mm推进、0.20 mm背景网格、一级局部细化（名义0.10 mm）、4 MPI ranks、显式out-of-core和每个载荷步末态输出。

## 接收结论

- campaign和runner返回0，`CAMPAIGN_COMPLETE`与`RUN COMPLETED`存在；
- 三个载荷步分别完成8/8/13个子步，共29个子步、累计56次平衡迭代；
- 三个收敛状态均为1，最终结果为载荷步3、`time=3.0`；
- MAPDL error、非收敛、二分、cutback、负主元、shape error和残留solver/session均为0；
- 实际solver模式为out-of-core，四rank总solver/non-solver分配17.776 GB；
- 最低可用内存70.12 GiB、最低空闲磁盘366.21 GiB，未接近30/100 GiB中止线；
- warning经分类审计可接收：9个shape warning单元但无shape error、既有接触节点/初始offset、小参考力判据，以及预期的out-of-core I/O性能提示。

正式端点标量：

- 探头Y反力：`-0.18100135590385 N`；
- 接触面积：`5.858317222134899 mm²`；
- 峰值接触压力：`46.838321614583 kPa`；
- 最大穿透：`0.0064352781616132 mm`；
- 角膜峰值等效应力：`44.488354090264 kPa`；
- 眼睑峰值等效应力：`27.088741188774 kPa`；
- MAPDL子进程墙钟：`25418.533 s`（约7.06 h）。

本端点提供正式$F_{20}$，但1.25 mm、0 mmHg端点仍缺失，因此不得计算$q_{20}$。DB/RST仍保存在5090d并有SHA-256；在最终场变量和压力对QC完成前暂不删除。完整机器可读接收口径见`manifest.json`。
