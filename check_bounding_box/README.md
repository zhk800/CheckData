# check_bounding_box 使用说明

## 功能概述
- 扫描 Check/output 下所有 `clips/*.json` 标注。
- 比对首帧 bbox 与 MOT 同帧（MOT 帧号 = JSON 帧 + 1）的 IoU，低于阈值写入 `retrack: true` 并回写 MOT。
- 展开 `A_window_frame` 的帧集合，与对应 MOT 帧集合（减 1 后）比较，不相等则写入 `is_window_consistence: false`。
- 将标记过的文件路径输出到 `marked_files.txt`，分区列出 retrack 与 is_window_consistence。

### MOT 文件定位
脚本从 JSON 的 `tracking_bboxes.mot_file` 取到文件名后，会**优先**在“该 JSON 同级目录的 `mot/` 文件夹”下查找对应的 TXT；只有找不到时才回退到 JSON 中的绝对/相对路径。

## 运行
```bash
cd /home/liuruizhi/Liuruizhi/OlympicVMBench/Check/CheckData
python check_bounding_box/check_bounding_box.py
```
可选参数：
- `--threshold <float>`：IoU 阈值，默认 0.95。
- `--check-root <path>`：Check 根目录，默认脚本自动推算。
- `--dry-run`：仅检测，不写回 JSON/MOT，也不生成日志。

## 输出
- 修改后的 JSON 与 MOT（非 dry-run 时）。
- `marked_files.txt`：标记的文件路径列表，分区展示。
- 终端统计：扫描文件数、检查标注数、标记条数、缺失 MOT 文件数，以及各标记文件数量。
