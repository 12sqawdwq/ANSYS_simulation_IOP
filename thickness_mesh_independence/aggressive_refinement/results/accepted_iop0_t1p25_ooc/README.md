# 已接收的1.25 mm L010 IOP0 out-of-core端点

正式campaign：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260814T025331Z_6ef45199_L010_h1p25_iop0_ooc_last_np4
```

求解源码为clean commit `6ef45199bec06139538c5a68a1538ae683ea1c3b`。条件为1.25 mm、0 mmHg、0.28 mm推进、0.20 mm背景网格、一级局部细化（名义0.10 mm）、4 MPI ranks、显式out-of-core和每个载荷步末态输出。

## 接收结论

- campaign和runner返回0，`CAMPAIGN_COMPLETE`与`RUN COMPLETED`存在；
- 三个载荷步分别完成8/8/13个子步，共29个子步、累计48次平衡迭代；
- 三个收敛状态均为1，最终结果为载荷步3、`time=3.0`；
- MAPDL error、非收敛、二分、cutback、负主元、shape error和残留solver/session均为0；
- 实际solver模式为out-of-core，四rank总solver/non-solver分配17.776 GB；
- 最低可用内存70.07 GiB、最低空闲磁盘364.29 GiB，未接近30/100 GiB中止线；
- warning经分类审计可接收：9个shape warning单元但无shape error、既有接触节点/初始offset、小参考力判据，以及预期的out-of-core I/O性能提示；
- `applanation_boundary_qc.png`显示内外边界居中、近圆且无离散旁瓣，外/内拟合断点半径分别为1.5007/1.3923 mm。

正式端点标量：

- 探头Y反力：`-0.17134016405785 N`，力幅值`0.17134016405785 N`；
- 接触面积：`5.7508535621642 mm²`；
- 峰值接触压力：`44.899486979167 kPa`；
- 最大穿透：`0.004724236077891 mm`；
- 角膜峰值等效应力：`40.366186799206 kPa`；
- 眼睑峰值等效应力：`33.932100176185 kPa`；
- MAPDL子进程墙钟：`20793.338 s`（约5.78 h）。

本端点已与同一commit的IOP20端点完成配对和中央剖面场QC。源RST在保存路径、大小、mtime和SHA-256后按授权删除；DB继续保存在5090d。完整机器可读接收口径见`manifest.json`，删除审计见`../t1p25_l010_pressure_pair/field_qc/rst_cleanup/`。
