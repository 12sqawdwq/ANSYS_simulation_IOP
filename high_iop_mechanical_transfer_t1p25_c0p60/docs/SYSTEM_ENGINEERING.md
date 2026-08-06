# 高眼压实验系统工程配置

> 状态：当前运行配置
> 最后核对：2026-08-06
> 配套入口：[`SCRIPT_INDEX.md`](SCRIPT_INDEX.md)

## 1. 目录与职责

```text
high_iop_mechanical_transfer_t1p25_c0p60/
├── README.md                 # 模块入口和状态
├── config/                   # 当前可执行 JSON 规格
├── docs/                     # 主要结论、系统配置、索引、日志和完整记录
│   └── intermediate/         # 未定型探索路径
├── scripts/
│   ├── analysis/             # 回归、机理推导、评估和绘图
│   ├── postprocess/          # 运行结果/RST 汇总
│   └── server/               # 5090d 正式入口
├── results/                  # 已提交的轻量机器可读证据
└── figures/                  # 已提交图件
```

大体积 DB、RST、FULL、ESAV 和运行日志不进入 Git，权威副本位于 5090d：

```text
/home/xuanyu/PROJECT/ziyu/blueknow-data/high_iop_mechanical_transfer_t1p25_c0p60
```

仓库服务器工作树：

```text
/home/xuanyu/PROJECT/ziyu/blueknow/simulation
```

## 2. 软件环境

### 2.1 5090d 正式环境

|组件|路径/版本|
|---|---|
|主机短名|`xuanyu`|
|ANSYS MAPDL|2025 R2|
|ANSYS 可执行文件|`/ansys_inc/v252/ansys/bin/ansys252`|
|Python|`/home/xuanyu/miniconda3/envs/grs-pilot/bin/python`|
|正式并发|最多 2 个工况|
|每工况首轮核数|8|
|单次超时|3600 s|
|失败重试|1 次，即最多 2 次尝试|

启动器会检查主机、可执行文件、源结果、Git 工作树清洁度和磁盘余量。正式运行不允许脏工作树。

### 2.2 本地分析环境

当前已验证测试环境：

```text
E:\SOFTWARE\annaconda\annaconda_evn\python.exe
Python 3.12.4
```

绘图脚本同时支持 Linux Noto CJK 和 Windows `C:/Windows/Fonts` 中的 Noto Sans SC、微软雅黑、微软正黑或黑体回退字体。

## 3. 固定几何、材料与加载路径

### 3.1 几何

|参数|冻结值|
|---|---:|
|眼睑厚度|1.25 mm|
|角膜厚度|0.60 mm|
|探头半径|2.16 mm|
|探头面积|14.65741468458854 mm²|
|初始安全间隙|0.30 mm|
|网格尺寸|0.30 mm|
|求解终点|0.28 mm|
|主目标推进|0.26 mm|
|实际主结果集|0.259875 mm|
|主结果最大允许偏差|0.001 mm|

### 3.2 绝对材料参数

眼睑：

```text
model = two_parameter_mooney_rivlin
C10 = 0.076 MPa
C01 = 0.010 MPa
D1  = 1e-7 Pa^-1
```

角膜：

```text
model = two_parameter_mooney_rivlin
C10 = 0.0825 MPa
C01 = 0.01875 MPa
D1  = 1e-7 Pa^-1
```

正式规格保存绝对参数，不依赖容易误解的相对材料版本名。

### 3.3 三载荷步

统一模型 `models/apdl/param_eye_sweep.mac` 使用连续三载荷步：

1. 保持 0.30 mm 安全间隙施加 IOP 预载，要求探头接触数为零；
2. 根据预载后顶点位置推进到几何初接触，要求接近终点反力近零；
3. 从几何初接触继续正式推进到 0.28 mm。

禁止把不同载荷路径生成的数据直接拼接成同一标定曲线。

## 4. 当前配置文件

### 4.1 `config/calibration_0_to_50.json`

用途：0–50 mmHg、2.5 mmHg 间隔的正式校准/诊断网格。

- 最终 21 点：0、2.5、…、50 mmHg；
- 新求解十个半步点：2.5、7.5、…、47.5 mmHg；
- 复用已验收 0、5、…、50 mmHg 点；
- 两工况并行，按低/高压力配对平衡墙钟时间；
- 输出保留 0.259875 和 0.28 mm 两个状态。

### 4.2 `config/extrapolation_50_to_60.json`

用途：冻结 0–50 参数后，对 52.5、55、57.5、60 mmHg 做未见外推检验。

- 第一闸门先单独求解 60 mmHg；
- 通过后并行求解 52.5/57.5，再求解 55；
- 复用完整 0–50 密集结果；
- 三组分式参数在启动前冻结；
- 评估完成前不重新拟合。

### 4.3 `config/interface_force_integrals.json`

用途：读取 0–50 mmHg 已保留 RST，积分探头—眼睑和眼睑—角膜接触力矢量。

- 压力点：21 个；
- 每点只读后处理，单线程串行执行；
- 40 mmHg 使用预检保留状态覆盖；
- APDL 接触积分：`models/apdl/post_contact_force_integrals.mac`；
- 接触积分解析：`src/postprocess/extract_contact_force_integrals.py`。

## 5. 正式运行命令

所有命令都应在 5090d 的清洁、已同步工作树中执行。

### 5.1 0–50 mmHg

```bash
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_calibration_0_to_50_5090d.sh --detach
```

也可指定全新输出目录：

```bash
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_calibration_0_to_50_5090d.sh \
  --detach /home/xuanyu/PROJECT/ziyu/blueknow-data/high_iop_mechanical_transfer_t1p25_c0p60/<new-run>
```

### 5.2 50–60 mmHg 独立外推

```bash
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_extrapolation_50_to_60_5090d.sh --detach
```

### 5.3 RST 界面力积分

```bash
high_iop_mechanical_transfer_t1p25_c0p60/scripts/server/launch_interface_force_integrals_5090d.sh --detach
```

`--run RUN_ROOT` 是启动器内部/前台模式；日常正式运行优先使用 `--detach`。

## 6. 运行链

### 6.1 求解链

```text
server launcher
  -> src/runners/run_indentation_sweep.py
  -> models/apdl/param_eye_sweep.mac
  -> run_manifest.csv + run_metadata.json + retained RST/DB
  -> src/postprocess/extract_geometry_zero_state.py
  -> scripts/postprocess/postprocess_pressure_sweep.py
  -> scripts/analysis/plot_pressure_sweep.py
  -> （外推任务）scripts/analysis/evaluate_iop60_extrapolation.py
```

### 6.2 界面力链

```text
server launcher
  -> scripts/postprocess/postprocess_interface_force_integrals.py
  -> src/postprocess/extract_contact_force_integrals.py
  -> models/apdl/post_contact_force_integrals.mac
  -> per-pressure contact_force_integrals*.csv
  -> interface_force_integrals_summary.json/csv
```

### 6.3 分析链

```text
pressure summary
  -> fit_rational_piop_vs_pprobe.py
  -> derive_forward_rational_parameters.py
  -> direct RST interface integration
  -> derive_global_load_share_model.py
  -> plots and frozen extrapolation evaluation
```

脚本的逐项输入、输出和状态见 [`SCRIPT_INDEX.md`](SCRIPT_INDEX.md)。

## 7. QC 与验收

每个新求解工况至少满足：

- runner 状态 `complete`；
- 返回码 0；
- ANSYS 错误数 0；
- 三载荷步全部收敛；
- IOP 预载探头接触数 0；
- 几何接近阶段轴向力绝对值不超过 0.001 N；
- 最大接触穿透不超过 0.03 mm；
- 主结果推进偏差不超过 0.001 mm；
- 压力序列中的探头总力和扣除后读数严格单调。

界面力积分另要求：

- 全压力点存在；
- MAPDL 后处理错误数为 0；
- 探头接触积分合力与 FE 探头反力相对差小于 1%；
- $\eta_{eff}=\tau_{interface}\chi$ 数值恒等检查通过。

## 8. 数据与溯源

### 8.1 Git 中保存

- 当前配置和运行脚本；
- 轻量 JSON/CSV 汇总；
- controller state、launch metadata；
- artifact SHA-256；
- 结论文档、完整实验记录和图件。

### 8.2 5090d 外部数据中保存

- RST、DB、FULL、ESAV；
- 完整 runner 尝试目录；
- MAPDL stdout/stderr；
- 大体积状态提取工作目录。

不得将外部大文件复制回 Git。运行根必须唯一且不能覆盖已有目录。

### 8.3 关键权威运行

|任务|运行/提交标识|外部数据说明|
|---|---|---|
|40 mmHg 收敛预检|`bdca48fe`|历史证据，当前入口已被正式密集矩阵替代|
|首轮完整矩阵|`23d4f22f`|历史 0/20/25/30/35/40 数据源|
|5 mmHg 补点|`440e44e5`|当前密集规格仍复用其已验收点|
|0–50、2.5 mmHg 网格|`290d0544`|当前 0–50 权威曲线|
|RST 界面力积分|`3ce7c957`|当前 0–50 直接界面力证据|
|50–60 外推|`5017b619`|当前 0–60 权威曲线和独立外推集|

## 9. 已移除的旧入口

2026-08-06 整理中移除了仅用于已完成阶段的当前工作树入口：

- 40 mmHg 预检启动器、规格和专用后处理；
- 首轮完整矩阵启动器、规格和专用后处理；
- 5 mmHg 补点启动器、规格和专用散点绘图；
- 早期 0.259875 mm 六点散点专用绘图。

删除原因不是实验无效，而是它们已被 0–50 的 2.5 mmHg 当前链替代。历史结果、校验文件和完整文字仍保留；源脚本可从 Git 提交 `e70b506` 或对应实验提交恢复。禁止复制旧脚本并改名为 `v2/final/latest`；需要修改当前入口时直接提交 Git，必要时建立实验分支。
