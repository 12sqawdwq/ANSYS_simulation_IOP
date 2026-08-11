# 高眼压机械传递实验（1.25 mm 眼睑 / 0.60 mm 角膜）

本目录保存 0–60 mmHg 高眼压机械传递实验的当前配置、可执行脚本、轻量证据、图件及无损实验记录。其 1.25 mm 眼睑与仓库级统一基线一致，基线规则见 [`../docs/GLOBAL_BASELINE.md`](../docs/GLOBAL_BASELINE.md)。

## 从这里开始

1. **当前主要结论**：[`docs/MAIN_CONCLUSIONS.md`](docs/MAIN_CONCLUSIONS.md)
2. **算法代际与文件归属**：[`../algorithms/README.md`](../algorithms/README.md)
3. **系统与运行配置**：[`docs/SYSTEM_ENGINEERING.md`](docs/SYSTEM_ENGINEERING.md)
4. **模块脚本索引**：[`docs/SCRIPT_INDEX.md`](docs/SCRIPT_INDEX.md)
5. **系统/更改日志**：[`docs/CHANGELOG.md`](docs/CHANGELOG.md)
6. **14 份原文无损合并记录**：[`docs/EXPERIMENT_RECORD.md`](docs/EXPERIMENT_RECORD.md)
7. **中间结论生命周期**：[`docs/intermediate/README.md`](docs/intermediate/README.md)

## 当前状态

- 0–50 mmHg、步长 2.5 mmHg：21 个实际 FE 点完成；
- 52.5–60 mmHg：4 个冻结参数后的独立外推点完成；
- 0–50 mmHg RST 直接界面力积分：21/21 完成；
- 主工作点：0.259875 mm；0.28 mm 仅作敏感性对照；
- 0–50 逆向分式样本内 RMSE 约 0.954 mmHg；
- 52.5–60 冻结外推 RMSE 约 4.782 mmHg，60 mmHg 高估约 6.964 mmHg；
- 当前结论不支持把固定参数公式称为独立验证的生产标定。

## 当前目录

```text
config/              当前 JSON 规格
scripts/analysis/    回归、机理分析、评估和绘图
scripts/postprocess/ 运行结果与 RST 后处理
scripts/server/      5090d 正式入口
docs/                结论、工程配置、索引、日志和实验记录
results/             轻量 JSON/CSV/metadata/SHA-256 证据
figures/             已提交图件
```

大体积求解文件位于：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/high_iop_mechanical_transfer_t1p25_c0p60
```

## 当前正式入口

```bash
# 0–50 mmHg 校准/诊断网格
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_calibration_0_to_50_5090d.sh --detach

# 50–60 mmHg 冻结模型外推
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_extrapolation_50_to_60_5090d.sh --detach

# 0–50 mmHg RST 界面力积分
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_interface_force_integrals_5090d.sh --detach
```

运行前必须阅读系统工程文档；正式服务器工作树必须清洁，输出目录必须全新。

## 文档完整性

原先根目录中的 14 份实验文档已全文合并到 `docs/EXPERIMENT_RECORD.md`。`docs/SOURCE_DOCUMENT_MANIFEST.json` 保存每个原文件的 SHA-256、Git blob、行数和合并段落哈希；自动测试验证合并后段落未丢失。原文件也可从 Git 提交 `e70b506` 恢复。
