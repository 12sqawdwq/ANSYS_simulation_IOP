# 1.25 mm全局基线 L010 mesh-only预检

该P0预检在clean commit `011c77e74e08fd7619cb9cda3d834cfe3b8506dd` 上完成，外部根为：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T025229Z_011c77e7_L010_h1p25_mesh_preflight
```

`driver.dat`明确传入0.00125 m眼睑厚度，且campaign复制并冻结了`config/model_baseline.json`。L010实际得到655,574个实体单元和940,688个节点，MAPDL error 0、shape error 0、`RUN COMPLETED`；因此获得单独运行1.25 mm、0 mmHg端点的构网格资格。

该目录仅为mesh-only证据，不含非线性力学端点。G015是同一launcher保留的比较性构网格点，不获批非线性求解。大体积DB留在5090d，路径、大小和SHA-256记录在`manifest.json`。
