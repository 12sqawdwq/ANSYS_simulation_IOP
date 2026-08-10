# 正式 P0 mesh-only 预检结论

## 状态

- 状态：`formal_committed_mesh_only_preflight_complete`
- 源 commit：`8768e6ec6afb41225d729c21aac80b467c266897`
- 外部根：`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260810T152200Z_8768e6ec_aggressive_mesh_preflight`
- 开始：2026-08-10 15:23:50 UTC
- 结束：2026-08-10 15:24:30 UTC
- 非线性求解：未启动
- 力、\(q\) 或收敛端点：无

## 结果

| 策略 | 背景/局部目标 | 实体单元 | 节点 | mesh-only 墙钟 | 最大 RSS | DB | MAPDL error | shape warning/error |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| G015 | 0.15/0.15 mm | 1,292,705 | 1,813,547 | 18.9 s | 3,983,120 KiB | 880,214,016 B | 0 | 14/0 |
| L010 | 0.20/0.10 mm | 817,237 | 1,160,408 | 20.6 s | 3,001,528 KiB | 559,546,368 B | 0 | 32/0 |

两例均有 `RUN COMPLETED`、return code 0 和 MAPDL error 0。shape warning 比例均很低且 shape error 为 0；正式非线性算例仍必须重新检查接触、穿透和三个载荷步。

## 决策

1. **G015 不进入优先非线性求解**：它比 L010 多约 58.2% 实体单元、56.3% 节点，但目标界面尺寸只有 0.15 mm；
2. **L010 通过构网格 P0**：正式 clean-commit 结果复现了开发期 817,237 个实体单元和 1,160,408 个节点；
3. **L010 只获得 P1 资格，不是求解授权**：2.00 mm 的 0/20 mmHg 压力对尚未启动，稀疏直接解法的实际内存、RST 和墙钟仍未知；
4. **L005 不进入本服务器非线性求解**：开发期两次细化已投影约 1139 万方程和 63.13 GiB RST/端点；
5. P1 若获授权，必须保持单任务、压力串行、36 h 阶段上限和运行中内存/磁盘保护。

## Claim boundary

P0 只证明指定 commit 可以构造 G015 和 L010 网格，并给出可靠的前处理规模。它不能证明接触求解会收敛，不能计算 \(q\)，也不能改变现有“绝对幅值尚未网格无关”的结论。

机器可读来源见 `preflight_manifest.csv` 和 `manifest.json`；外部 DB 的大小与 SHA-256 已登记，但 DB 不进入 Git。
