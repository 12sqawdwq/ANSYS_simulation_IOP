# Thick Study

眼睑厚度为主变量、角膜厚度为分层变量的独立研究项目。

`data/placeholder/` 和 `figures/placeholder/` 保存当前参数扫描占位资料；它们用于实验设计，不是正式实验结论。真实仿体实验完成后，原始采集记录进入 `data/raw/` 的外部数据区，处理结果进入 `data/processed/`，并由 `code/process_experiment.py` 重新生成统计表、图和正式报告。

完整实验设计见 [真实仿体实验方案](protocol/真实仿体实验方案.md)，字段及文件治理见 [数据说明](data/README.md)。

当前三维有限元厚度先行实验使用 `0.80、1.00、1.20、1.40、1.60、1.80、2.00 mm` 七个眼睑厚度点，固定中心推进 `0.80 mm`。5090d 通过 `ops/launch-thickness-sweep-5090d.sh` 运行，轻量结果完成质检后汇总到 `thick/data/processed/fe_sweep/`。

7 个状态已全部完成并通过 QC。报告见 [眼睑厚度有限元实验报告](docs/眼睑厚度有限元实验报告.md)，机器可读结果见 [fe_sweep 数据](data/processed/fe_sweep/README.md)，每个状态的 9 张图片见 [完整视图索引](figures/fe_sweep/views/README.md)。

仓库继续保留 `0.26 mm` 九点推进数据作为历史对照，见 [fe_sweep_indent_0p26](data/processed/fe_sweep_indent_0p26/README.md) 和 [0.26 mm 视图索引](figures/fe_sweep_indent_0p26/views/README.md)。当前面积分析统一使用已完成的七个 `0.28 mm` 状态，见 [Ae/Ac 0.28 mm 推进报告](docs/眼睑厚度Ae_Ac推进0.28mm补充报告.md)。

正式厚度工况现统一为 `0.28 mm` 名义推进。球面相交面积已从活动数据链删除；`0.5°-10°` 法向夹角面积只表示局部近水平核心，不能作为正式 `Ae/Ac`，完整扫描见[Flat Region 角度灵敏度实验](experiments/flat_region_angle_sweep/README.md)。当前外侧使用位移参与区的保守网格下界，内侧使用 bonded 界面的增量压力参与面积；公式、合理性和限制见[眼睑厚度 Ae/Ac 计算与校准](../docs/THICKNESS_CALIBRATION.md#两种面积定义)。内外两侧统一按压力分布计算的诊断结果见[统一力学有效面积对照](experiments/mechanical_area_comparison/README.md)。

利用已收敛 `0.80 mm` 加载路径逐状态提取的探头反力曲线见[探头反力与拐点检查](experiments/probe_force_curve_0p8/README.md)。七个厚度均在约 `0.325-0.375 mm` 出现平滑增刚区间，但没有达到局部斜率突跳判据，当前不支持将其解释为明确机械拐点或完全压平终点。

按 `1 mN` 首次稳定承载接触重新定义零点后的有效 `0.26/0.28 mm` 面积见[接触归零面积对照](experiments/contact_rezeroed_0p26_0p28/README.md)。外侧位移覆盖约为 `88.3%-89.8%`，实际承载接触覆盖仅为 `29.7%-43.4%`；混合面积比仍随厚度下降。该分析还发现薄眼睑工况在 IOP 预载末端已经接触探头，正式零点模型需要增大初始间隙并增加独立接近阶段。

提交 `371ed27` 已将正式模型改为连续三载荷步：使用 `0.30 mm` 安全初始间隙建立无探头接触的 IOP 预载，再按预载顶点抬升计算几何初接触位置，最后推进 `0.26/0.28 mm`。完整九厚度的 0/20 mmHg 几何初接触状态已经完成；代表工况确认预载接触面积为零且三个载荷步连续收敛。当前接触重归零面积仍标记为 `candidate_not_approved`，不替换历史面积结论。具体定义和审计值见[眼睑厚度 Ae/Ac 计算与校准](../docs/THICKNESS_CALIBRATION.md#几何初接触重算)。
