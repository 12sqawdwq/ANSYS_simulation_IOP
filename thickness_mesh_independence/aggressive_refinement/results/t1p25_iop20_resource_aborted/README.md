# 1.25 mm L010 IOP20近终点资源中止记录

该campaign从clean commit `5d3ece4bccf67e382bdfa639b0da80711c8008b8`启动：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T034259Z_5d3ece4b_L010_h1p25_iop20_guarded_np4
```

条件为1.25 mm、20 mmHg、0.28 mm推进、0.20 mm背景网格、一级局部细化、4 MPI ranks、1 worker、retry 0。模型含2,711,583个方程，MAPDL自动选择in-core模式；四rank合计solver/non-solver分配60.353 GB。

## 中止与数值状态

`2026-08-13T07:39:44Z`，`MemAvailable=30,237,892 KiB`（约28.84 GiB）低于30 GiB保护线，launcher终止完整session tree并返回143。空闲磁盘为442,591,744 KiB，不是中止原因。中止后内层unit为inactive/dead，solver、campaign token及运行中Blueknow unit残留均为0。

中止前的已完成状态全部收敛：

- 载荷步1：8个子步；
- 载荷步2：8个子步；
- 载荷步3：12个子步；
- 共28个完成子步、累计54次平衡迭代；
- MAPDL error、非收敛、二分、cutback、负主元和shape error均为0；
- 9个单元触发shape warning，未触发shape error；
- 最后收敛伪时间为2.928125，对应正式压入0.259875 mm，距0.28 mm终点0.020125 mm。

这些中间状态只证明数值路径稳定，不是0.28 mm正式端点。不存在`RUN COMPLETED`、完整合并RST或正式`F20`，不得外推、续算、进入压力配对或计算$q$。

## 二进制清理与重跑决策

清理前已保存全部文件清单，以及待删文件的路径、大小、allocated bytes、mtime、类别和SHA-256。随后仅删除失败`attempt_1`的不完整DB/RST和可再生求解scratch：共46项，表观21,133,517,890 bytes，实际占用14,760,343,552 bytes；清单残留0。轻量输入、`solve.out`、资源曲线、session guard证据和清理清单保留。

原样in-core重跑未获授权。下一次必须使用全新root，显式强制out-of-core，仅保留每个载荷步末态，并在运行早期从`solve.out`确认实际模式为out-of-core；90/30 GiB内存门、150/100 GiB磁盘门、4 ranks和单压力策略保持不变。完整机器可读口径见`manifest.json`。
