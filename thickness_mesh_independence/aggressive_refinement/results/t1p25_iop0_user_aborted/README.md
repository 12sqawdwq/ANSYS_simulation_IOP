# 1.25 mm L010 IOP0主动中止记录

该campaign于2026-08-13T02:54:18Z从clean commit `011c77e74e08fd7619cb9cda3d834cfe3b8506dd`启动，并于2026-08-13T03:29:59Z根据用户“停止0 mmHg、优先运行20 mmHg”的明确要求向外层launcher发送TERM：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260813T025418Z_011c77e7_L010_h1p25_iop0_guarded_np4
```

launcher通过session guard终止完整内层cgroup；内层unit最终为inactive/dead，campaign token残留、求解器/MPI进程和运行中的Blueknow unit均为0。中止时MAPDL error为0并已完成8个子步，但没有`RUN COMPLETED`或完整端点。因此该记录不是数值失败，也不是可接收的0 mmHg基线，不得用于压力配对或计算$q$。

清理前保存了全部文件清单，以及待删二进制的路径、大小、mtime、分类和SHA-256。随后仅删除失败`attempt_1`中的不完整RST/DB及求解scratch，共46项、表观9,372,703,404 bytes，manifest残留0。Git保留轻量输入、日志、资源曲线、停止审计和哈希；完整口径见`manifest.json`。
