# Thickness Data Contract

## 目录状态

- `placeholder/`：当前参数扫描结果，只作占位。
- `raw/`：原始仪器导出、双相机图片和视频；默认 Git 忽略，仅跟踪其 README、清单和校验值。
- `processed/`：从原始 CSV 可复算得到的汇总、图表和正式报告。
- `manifest.csv`：每次数据导入的版本、路径、校验值、脚本提交和状态。

## 原始 CSV 必需字段

| 字段 | 单位/格式 | 含义 |
|---|---|---|
| `run_id` | string | 单次加载记录唯一 ID |
| `assembly_id` | string | 独立仿体装配 ID |
| `repeat_id` | integer | 同一装配体的重复编号 |
| `eyelid_thickness_mm` | mm | 实测眼睑厚度 |
| `cornea_thickness_mm` | mm | 实测角膜厚度 |
| `reference_iop_mmhg` | mmHg | 腔内压力传感器真值 |
| `probe_advance_mm` | mm | 探头推进位移 |
| `probe_force_n` | N | 探头轴向力 |
| `outer_area_mm2` | mm2 | 外侧相机测得压平面积 Ae |
| `inner_area_mm2` | mm2 | 内侧相机测得有效面积 Ac |
| `image_id_outer` | string | 外侧相机原始文件 ID |
| `image_id_inner` | string | 内侧相机原始文件 ID |
| `qc_status` | `pass`/`fail` | 数据质量判定 |
| `operator` | string | 采集操作者 |
| `timestamp` | ISO 8601 | 采集时间 |

处理脚本仅使用 `qc_status=pass` 的记录。面积比例定义为 `Ae/Ac`；`Ac/Ae` 仅作为面积传递效率输出。
