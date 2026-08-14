# 1.25 mm L010完整压力对

本目录配对同一clean commit `6ef45199bec06139538c5a68a1538ae683ea1c3b`、同一1.25 mm几何、材料、0.28 mm推进、L010网格、4 MPI ranks、out-of-core和last-only结果策略下的两个已接收端点：

- IOP0：`../accepted_iop0_t1p25_ooc/`；
- IOP20：`../accepted_iop20_t1p25_ooc/`。

配对QC确认只有IOP不同；网格inventory、APDL哈希、全局基线、材料、几何、并行度、载荷步末态和源码commit均一致。两端点均为29个已收敛子步、三个载荷步、`RUN COMPLETED`、MAPDL error 0和零残留。

按探头Y反力幅值定义

\[
q_{20}=\frac{|F_{y,20}|-|F_{y,0}|}{A_{\mathrm{probe}}},
\qquad A_{\mathrm{probe}}=14.65741468458854\ \mathrm{mm^2},
\]

得到：

- \(|F_{y,0}|=0.17134016405785\ \mathrm{N}\)；
- \(|F_{y,20}|=0.18100135590385\ \mathrm{N}\)；
- \(\Delta F=0.009661191846000006\ \mathrm{N}\)；
- \(\Delta p=659.1334184027838\ \mathrm{Pa}\)；
- **\(q_{20}=4.9439072093374365\ \mathrm{mmHg}\)**。

IOP20相对IOP0的接触面积、峰值接触压力和最大穿透分别增加0.107464 mm²、1.938835 kPa和0.001711 mm。

`field_qc/`保存两端点载荷步3、`time=3.0`、实际比例中央剖面`007`。原生自动色标最大值分别为40.366和44.488 kPa；两图均居中且场连续，IOP20呈一致的场重分布。完整18张原生视图及源文件哈希保存在5090d：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260814T085004Z_6ef45199_L010_h1p25_iop0_iop20_field_qc
```

完成上述场QC后，两份成功RST已按用户授权删除；删除前再次核对路径、大小、mtime和SHA-256，共删除2项、表观3,498,967,040 bytes、实际分配2,637,785,088 bytes。两份DB继续保留，删除审计见`field_qc/rst_cleanup/`。

## 结论边界

该数值是**1.25 mm、L010离散、0.28 mm推进下的已接收压力对结果**，不是网格无关值。它相对既有全局0.30 mm结果7.072211 mmHg低30.09%；这只是方向性网格敏感性比较，不满足“最新两级相差不超过2%”的正式收敛设计，也不能升级为真实组织阈值、生产标定或算法独立验证。
