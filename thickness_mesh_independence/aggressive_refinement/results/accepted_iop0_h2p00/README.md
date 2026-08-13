# 已接收的 L010 H2.00 IOP0 端点

该目录保存 5090d campaign

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260811T064031Z_abf4175d_L010_h2p00_iop0_guarded_np4
```

的轻量QC与溯源证据。源提交为 `abf4175de29eb2237f84b4151e362559d5634b85`。算例使用 2.00 mm眼睑、0 mmHg、0.20 mm背景网格、一级局部细化至名义0.10 mm、0.28 mm正式推进、4 MPI ranks、1 worker、无重试。

人工审计确认三个载荷步全部收敛、`RUN COMPLETED`、ANSYS error 0、返回码0、最大穿透0.007125 mm、无资源中止、无MAPDL/MPI或campaign token残留。该端点因此被接收为**2.00 mm显式厚度覆盖下的0 mmHg端点**。

它不是1.25 mm全局基线端点，也不提供20 mmHg或 \(q\)。新的1.25 mm实验必须使用新的clean commit、新campaign root，并先完成1.25 mm mesh-only预检。

大体积DB/RST与完整求解日志留在上述5090d目录；`external_artifacts.csv`保存路径、大小、mtime和SHA-256，`manifest.json`保存机器可读验收结论。
