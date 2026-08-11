# Blueknow 眼压计仿真

本仓库统一管理经眼睑眼压测量的可复现模型、运行代码、分析文档和轻量结果。原始 ANSYS 求解文件保存在 5090d 外部数据区，不进入 Git 历史。

## 全局实验基线

所有新实验统一以 **1.25 mm 眼睑厚度**为参考基线，机器可读真源为 [`config/model_baseline.json`](config/model_baseline.json)。普通压入、偏心、压力、材料和算法实验默认使用该厚度；厚度扫描和厚端网格实验可显式覆盖，但必须记录实际厚度和覆盖原因。历史 1.00 mm 或其他厚度结果保持原始含义，不追溯改写。完整规则见 [`docs/GLOBAL_BASELINE.md`](docs/GLOBAL_BASELINE.md)。

## 当前核心结论

- 7 点三维厚度扫描已完成：眼睑厚度从 0.80 mm 增加到 2.00 mm 时，固定 0.80 mm 推进的探头反力从 0.6127 N 增至 1.4253 N，外侧接触面积基本不变。严格几何 `Ae/Ac` 对角度和粗网格敏感，未复现旧占位资料的单调上升曲线。
- 旧厚度参数扫描仍保留用于追溯实验假设；真实仿体完成后将以受控内压、力/位移和双相机内外面积数据形成正式 IOP 修正。
- 偏心量在 0-1 mm 时半经验面积比变化较小；2 mm 时内部有效面积和三维接触范围明显下降。3D 模型的接触单元代理从 351 降至 180，眼睑峰值应力从 27.15 kPa 增至 37.83 kPa。
- 算法统一展示为三个版本：版本一按有效压平面积比换算 `PIOP=(Ap/Ac)·Pprobe`，版本二采用经验分式 `PIOP=a·Pprobe/(1-b·Pprobe)`，版本三采用力学传递模型 `PIOP=ηeff·KA·Pprobe=KA·Pprobe/Tmech`。三个版本目前均不是生产硬件标定。
- `Kgeo,5°=Ae/Ac,5°`只用于冻结的几何材料筛选；版本一已因高压系统性低估而关闭为完整算法。当前主方向是版本三，必须区分面积项 `KA=Ap/Ac` 与力学传递比/修正，不得将面积比、直接界面传力或同源重参数化单独包装为生产算法。
- 高眼压固定配置的 0–50 mmHg 分式模型样本内 RMSE 约 0.954 mmHg，但冻结参数后的 52.5–60 mmHg 独立外推 RMSE 约 4.782 mmHg，60 mmHg 高估约 6.964 mmHg；当前不构成生产硬件标定。
- 厚度敏感性分析表明，除 1.25 mm 外只有 0/20 mmHg 端点，不能逐厚度识别分式参数；20 mmHg 组合增益稳定只能作为 0.30 mm 网格上的代理描述。0.30/0.24/0.20 mm 三级审计均保留 1.60→2.00 mm 的下降次序，但最细两级的绝对输出仍变化最多 12.31%，因此方向稳健、幅值未达到网格无关，1.60 mm 不是已验证的物理阈值。

## 目录

- `config/`：全局模型基线的机器可读配置；当前眼睑厚度参考值为 1.25 mm。
- `algorithms/`：IOP 修正算法的三版本分类、历史来源、当前框架和机器可读文件清单。
- `baseline/`：无偏心基线图表、说明与本地 Workbench 工程入口。
- `offset/`：偏心研究的报告、轻量数据、图表与本地 Workbench 工程入口。
- `thick/`：厚度项目的实验协议、占位结果、真实实验数据契约、处理脚本与报告。
- `high_iop_mechanical_transfer_t1p25_c0p60/`：0–60 mmHg 高眼压实验的分层配置、脚本、结论和无损实验记录。
- `analysis/`：厚度敏感性与参数可识别性分析管线及可复现输出。
- `thickness_mesh_independence/`：1.60–2.00 mm 厚端响应的定向网格无关性设计、服务器入口、轻量结果和结论；[`DETAILED_REPORT.md`](thickness_mesh_independence/DETAILED_REPORT.md) 含三级实际网格、原生/统一 0–60 kPa 结果剖面截图和 18 个接收终点的逐项耗时；[`aggressive_refinement/`](thickness_mesh_independence/aggressive_refinement/) 是 2–3 天预算内局部 0.10 mm 及更激进 mesh-only 方案的独立实验入口。
- `paper/`：基于冻结有限元和算法证据形成的论文初稿、投稿前核对项及数据溯源。
- `models/apdl/`：参数化 APDL 模型、后处理宏和测试输入。
- `src/runners/`：当前可复现的批量运行入口。
- `src/postprocess/`：共享状态提取、汇总、面积/接触/力学分析和绘图工具。
- `docs/analysis/`：共享分析说明；项目报告分别位于各模块 `docs/`。
- `docs/DATA_PROVENANCE.md`：模型层级、参数差异和结论适用范围。
- `docs/INDENTATION_SWEEP.md`：连续三载荷步扫描、状态判定、质检和分阶段运行协议。
- `docs/IOP修正算法全局方向.md`：面积变化、力传递分解和分式 IOP 反演的全局方向。
- `algorithms/README.md`：统一展示面积换算、经验分式和力学传递三个版本，并逐文件标注归属。
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
