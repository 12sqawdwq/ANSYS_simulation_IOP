# Blueknow 眼压计仿真

本仓库统一管理经眼睑眼压测量的可复现模型、运行代码、分析文档和轻量结果。原始 ANSYS 求解文件保存在 5090d 外部数据区，不进入 Git 历史。

## 当前核心结论

- 7 点三维厚度扫描已完成：眼睑厚度从 0.80 mm 增加到 2.00 mm 时，固定 0.80 mm 推进的探头反力从 0.6127 N 增至 1.4253 N，外侧接触面积基本不变。严格几何 `Ae/Ac` 对角度和粗网格敏感，未复现旧占位资料的单调上升曲线。
- 旧厚度参数扫描仍保留用于追溯实验假设；真实仿体完成后将以受控内压、力/位移和双相机内外面积数据形成正式 IOP 修正。
- 偏心量在 0-1 mm 时半经验面积比变化较小；2 mm 时内部有效面积和三维接触范围明显下降。3D 模型的接触单元代理从 351 降至 180，眼睑峰值应力从 27.15 kPa 增至 37.83 kPa。
- `Kgeo,5°=Ae/Ac,5°`只用于冻结的几何材料筛选；最终IOP修正必须区分面积项 `KA=Ap/Ac` 与力传递项，不得将面积比直接当作传感器标定系数。
- 当前全局算法方向为 `PIOP=ηeff(PIOP)·KA(PIOP)·Pprobe`。只有在力传递修正近似常数通过验证后，才简化为 `PIOP=bPprobe/(1-aPprobe)`；旧经验线性 `Ksensor(PIOP)`不再作为最终算法解释。
- 高眼压固定配置的 0–50 mmHg 分式模型样本内 RMSE 约 0.954 mmHg，但冻结参数后的 52.5–60 mmHg 独立外推 RMSE 约 4.782 mmHg，60 mmHg 高估约 6.964 mmHg；当前不构成生产硬件标定。
- 厚度敏感性分析表明，除 1.25 mm 外只有 0/20 mmHg 端点，不能逐厚度识别分式参数；20 mmHg 组合增益稳定只能作为代理结论。

## 目录

- `algorithms/`：IOP 修正算法的代际分类、历史来源、当前框架和机器可读文件清单。
- `baseline/`：无偏心基线图表、说明与本地 Workbench 工程入口。
- `offset/`：偏心研究的报告、轻量数据、图表与本地 Workbench 工程入口。
- `thick/`：厚度项目的实验协议、占位结果、真实实验数据契约、处理脚本与报告。
- `high_iop_mechanical_transfer_t1p25_c0p60/`：0–60 mmHg 高眼压实验的分层配置、脚本、结论和无损实验记录。
- `analysis/`：厚度敏感性与参数可识别性分析管线及可复现输出。
- `models/apdl/`：参数化 APDL 模型、后处理宏和测试输入。
- `src/runners/`：当前可复现的批量运行入口。
- `src/postprocess/`：共享状态提取、汇总、面积/接触/力学分析和绘图工具。
- `docs/analysis/`：共享分析说明；项目报告分别位于各模块 `docs/`。
- `docs/DATA_PROVENANCE.md`：模型层级、参数差异和结论适用范围。
- `docs/INDENTATION_SWEEP.md`：连续三载荷步扫描、状态判定、质检和分阶段运行协议。
- `docs/IOP修正算法全局方向.md`：面积变化、力传递分解和分式 IOP 反演的全局方向。
- `algorithms/README.md`：明确历史经验 `Ksensor` 与当前机制框架的边界，并逐文件标注归属。
- `docs/SCRIPT_INDEX.md`：全仓库脚本职责索引。
- `docs/CHANGELOG.md`：按 Git 提交记录时间和完整文件清单的系统日志。
- `docs/DOCUMENTATION_POLICY.md`：主要结论、工程配置、索引、日志和中间结论的治理规则。
- `results/summary/`：机器可读汇总和外部结果校验清单。
- `ops/`：本地、5090d 和 arch 的仓库初始化与同步脚本。

## 三端角色

- 本地：完整开发副本。
- 5090d：中心 bare 仓库、完整工作副本和外部求解数据区。
- arch：`blob:none` 部分克隆，只检出文档、汇总、图和报告脚本。

详细同步命令见 [docs/SYNC_GUIDE.md](docs/SYNC_GUIDE.md)。数据解释和限制见 [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md)。

## 版本管理

- 工作树只保留一套当前模型、运行入口和后处理脚本。
- 历史实现通过 Git commit、branch 或 tag 查询；工作树不保留历史代码目录，也不在流程脚本名中添加版本数字、`final`、`old` 或 `backup` 后缀。
- 每次批量求解在 `run_manifest.csv` 中记录 Git commit 和工作区是否有未提交修改；未提交状态只用于调试，不作为正式结果来源。
- 大型实验按主要结论、系统工程、脚本索引、更改日志、完整实验记录和中间结论分层；规范见 [docs/DOCUMENTATION_POLICY.md](docs/DOCUMENTATION_POLICY.md)。

## 扫描入口

5090d 上使用 `ops/launch-indentation-sweep-5090d.sh smoke` 启动四个代表性算例。当前名义压入上限为 0.8 mm；只有 smoke 质检通过并人工确认后，才依次使用 `coarse` 和 `full`，脚本不会自动跨阶段推进。

眼睑厚度有限元实验使用 `ops/launch-thickness-sweep-5090d.sh`，固定中心推进 0.8 mm，扫描眼睑厚度 0.8-2.0 mm、步长 0.2 mm。当前正式模型采用 IOP 预载、几何初接触和正式压入的连续三载荷步，并使用自动产物保留策略。

当前正式 smoke 的 manifest、汇总、QC、元数据和趋势图使用 `results/summary/indentation_smoke*` 这一组固定名称更新；历史版本只通过 Git 提交查询。
