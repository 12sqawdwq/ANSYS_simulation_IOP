# Thick Study

眼睑厚度为主变量、角膜厚度为分层变量的独立研究项目。

`data/placeholder/` 和 `figures/placeholder/` 保存当前参数扫描占位资料；它们用于实验设计，不是正式实验结论。真实仿体实验完成后，原始采集记录进入 `data/raw/` 的外部数据区，处理结果进入 `data/processed/`，并由 `code/process_experiment.py` 重新生成统计表、图和正式报告。

完整实验设计见 [真实仿体实验方案](protocol/真实仿体实验方案.md)，字段及文件治理见 [数据说明](data/README.md)。

当前三维有限元厚度先行实验使用 `0.80、1.00、1.20、1.40、1.60、1.80、2.00 mm` 七个眼睑厚度点，固定中心推进 `0.80 mm`。5090d 通过 `ops/launch-thickness-sweep-5090d.sh` 运行，轻量结果完成质检后汇总到 `thick/data/processed/fe_sweep/`。

7 个状态已全部完成并通过 QC。报告见 [眼睑厚度有限元实验报告](docs/眼睑厚度有限元实验报告.md)，机器可读结果见 [fe_sweep 数据](data/processed/fe_sweep/README.md)，每个状态的 9 张图片见 [完整视图索引](figures/fe_sweep/views/README.md)。

在不覆盖上述 `0.80 mm` 结果的前提下，仓库另保存从相同加载路径提取的 `0.26 mm` 推进状态。补充分析见 [Ae/Ac(2°) 0.26 mm 推进报告](docs/眼睑厚度Ae_Ac推进0.26mm补充报告.md)，数据见 [fe_sweep_indent_0p26](data/processed/fe_sweep_indent_0p26/README.md)，63 张图片见 [0.26 mm 视图索引](figures/fe_sweep_indent_0p26/views/README.md)。
