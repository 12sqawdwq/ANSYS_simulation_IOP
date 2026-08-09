# 论文稿件目录

本目录保存基于仓库当前有限元、后处理和算法审计结果形成的论文草稿。论文版本由 Git 管理，不创建 `final`、`latest` 或数字后缀副本。

## 当前稿件

- [`MANUSCRIPT.md`](MANUSCRIPT.md)：以第二版本的正向形式 $q=p/(a+bp)$ 及等价反演 $p=aq/(1-bq)$ 为唯一拟合 claim 的中文完整初稿；RESULTS 按“耦合等效刚度—有限元场变量—角膜至探头载荷路径—非线性输出”展示。
- [`build_figures.py`](build_figures.py)：从冻结 CSV/JSON 生成耦合割线刚度、角膜压力合力、面积修正、接口/探头传力及第二版本正向响应四联图，校验并组装代表性 MAPDL 中央剖面应力云图，同时生成厚度直接响应与参数可识别性图。

## 稿件状态

```text
status: internal_complete_draft
scientific_scope: finite-element evidence only
paper_algorithm_claim: second-version empirical rational fitting
latest_mechanistic_algorithm_used_as_claim: false
production_calibration_claim: false
clinical_validation_claim: false
external_literature_review: pending
```

正文数值来自仓库中的冻结 CSV/JSON、网格审计轻量结果和结论文档。论文从眼睑—角膜串联近似、球面小压平几何、压力相关角膜刚度和 $p=\eta K_Aq$ 详细推导分式结构，但只采用第二版本经验分式进行参数识别、冻结和外推；RESULTS 首先用两个相邻推进状态量化 IOP 相关耦合割线刚度，再展示既有 RST 中探头—眼睑—角膜中央剖面的应力场重分布，随后正向推进至角膜压力合力、面积修正、眼睑—角膜接口力、眼睑介导的探头反力和 $q(p)$ 响应。最新的力学传递框架仅作为辅助边界解释，不作为本文算法 claim。正文没有把同源重参数化描述为独立验证，也没有把第二版本公式称为真实硬件生产标定。

投稿前仍需作者完成：

1. 确定目标期刊及篇幅、图表、参考文献格式；
2. 补充并核验外部文献，替换正文中的“参考文献待补”标记；
3. 填写作者、单位、基金、利益冲突和作者贡献；
4. 确认是否保留厚度可识别性作为第二研究问题；
5. 根据期刊要求生成 Word 或 LaTeX 稿件；
6. 如使用新增仿真或硬件数据，先冻结分析方案并更新机器可读结果。

## 图件再生成

```powershell
E:\SOFTWARE\annaconda\annaconda_evn\python.exe paper/build_figures.py
```

输出：

- `paper/figures/forward_mechanical_response.png`
- `paper/figures/forward_mechanical_response.svg`
- `paper/figures/central_section_stress_contours.png`
- `paper/figures/thickness_response_identifiability.png`
- `paper/figures/thickness_response_identifiability.svg`

稿件图 6 直接引用 `thickness_mesh_independence/results/confirmation/mesh_independence_screening.png`；该图由网格评估脚本和冻结三级比较表生成，不在论文目录复制平行副本。

中央剖面应力云图的 4 张轻量原始 PNG 和 provenance manifest 位于 `paper/figures/mechanical_contours_raw/`。它们由 5090d 外部数据区中的既有收敛 RST 后处理得到，包含探头、眼睑和角膜，并按变形后实际比例显示；构图脚本会先按 manifest 校验 SHA-256。各 MAPDL 子图保留原生自动色标，因此不可仅按颜色跨压力定量比较。

## 主要数据入口

- `high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop_0_to_60_step2p5_summary.csv`
- `high_iop_mechanical_transfer_t1p25_c0p60/results/20260730_rational_regression_0_to_50_step2p5.json`
- `high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_5017b619_iop60_frozen_model_extrapolation.json`
- `high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_forward_rational_parameters_ac5_proxy.json`
- `high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_3ce7c957_interface_force_integrals_summary.csv`
- `high_iop_mechanical_transfer_t1p25_c0p60/results/20260731_global_load_share_derivation.json`
- `paper/figures/mechanical_contours_raw/manifest.json`
- `thickness_mesh_independence/results/confirmation/mesh_comparison.csv`
- `thickness_mesh_independence/results/confirmation/screening_summary.json`
- `thickness_mesh_independence/results/confirmation/CONCLUSION.md`
- `analysis/outputs/report.md`
- `analysis/outputs/fitted_parameters.csv`
- `analysis/outputs/thickness_iop_predictions.csv`
- `analysis/outputs/sensitivity_results.csv`
