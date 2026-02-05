# AI标注审查系统

面向视频 clips 与单帧 frames 的标注审核工具，统一展示窗口帧、bbox 与 MOT 追踪结果，并提供高效的审核、编辑与批量修正能力。

## 核心特性
- 支持 clips / frames 双形态数据，并可同时查看窗口帧、bbox、MOT 追踪。
- 全键盘驱动的巡检、编辑、审核流，跨文件跳转前自动尝试保存。
- 鼠标拖拽式 bbox 编辑，自动写入 `retrack=True` 并保留历史 Scoreboard 拟合工具。
- VS Code 集成：左侧文本区域双击可直接打开对应 JSON，再按 **L** 重新载入。

> ⚙️ 启动步骤集中在 `quickstart.md`，README 仅保留工作流与功能说明。

## 使用流程
1. **载入数据**：在界面选择 sport/event → clips|frames → ID 后按 **L**；若手动修改 JSON 也需重新按 **L**。
2. **浏览验证**：clips 使用 **Space/B/W/R** 控制播放、窗口帧与 bbox 跳转；frames 直接对静态图巡检。
3. **编辑修正**：按 **E** 进入/轮换 bbox 编辑目标，鼠标拖拽即可写入；必要时用 **X**、**C** 或 `Delete` 处理批量情况。
4. **审核与保存**：确认无误后按 **M** 标记 reviewed，再按 **S** 将内存改动落盘。
5. **切换对象**：同文件用 **N/P**，跨文件用 `Shift+N/P` 或 **U** / `Shift+U`，所有跳转都会先尝试保存当前修改。

## 快捷键一览
| 按键 | 作用域 | 功能 |
|------|--------|------|
| `Space` / `Enter` | clips | 播放/暂停。 |
| `B` | clips | 依次跳到含 bbox 的帧并暂停；再次按键恢复播放并重置 W。 |
| `W` | clips | 按 Q→A 顺序浏览窗口帧，结束后恢复播放并重置 B。 |
| `R` | clips | 从 `Q_window_frame` 起始帧重新播放当前片段。 |
| `L` | 全局 | 根据当前下拉框选择重新载入 JSON。 |
| `P` / `Shift+P` | 全局 | 上一条标注 / 上一个文件（循环，跳转前尝试保存）。 |
| `N` / `Shift+N` | 全局 | 下一条标注 / 下一个文件。 |
| `U` / `Shift+U` | 全局 | 下一份仍含未审核标注的文件；`Shift` 仅筛 `Spatial_Temporal_Grounding`、`Continuous_Actions_Caption`。 |
| `M` | 全局 | 将当前标注标记为已审核。 |
| `S` | 全局 | 将所有内存改动写回 JSON。 |
| `E` | 编辑 | 进入 bbox 编辑；重复按可在 `first_bounding_box` 与各 `bounding_box[i]` 间轮换，遍历完自动退出。 |
| 鼠标左键拖拽 | 编辑 | 在编辑模式下绘制/修改 bbox，松开即写入并自动设置 `retrack=True`。 |
| `C` | ScoreboardSingle | 复制同运动前序文件的 Scoreboard bbox，并按 IOU 匹配到当前文件。 |
| `X` | bbox | 交换当前标注前两个 `bounding_box` 的 `label` 字段。 |
| `Delete` | 全局 | 删除当前 annotation，静默保存并重新载入文件。 |

## 操作分组

### Clips 播放 / 帧定位
- `Space` / `Enter`：播放/暂停，进度条拖拽会自动暂停，方便逐帧查看。
- `B`：逐个跳到含 bbox 的帧并暂停；再次按键恢复播放并清空 W 状态。
- `W`：按 Q→A 顺序跳窗口帧，遍历完自动恢复播放并清空 B 状态。
- `R`：从 `Q_window_frame` 起始帧重新播放当前片段。

### 标注 / 文件导航
- `L`：重新载入当前所选 JSON。
- `P` / `Shift+P`、`N` / `Shift+N`：在标注与文件间切换，跳转前自动尝试保存。
- `U` / `Shift+U`：按是否已审核筛选下一份文件，`Shift` 仅检查指定任务。
- `Delete`：删除当前 annotation 并立即重新载入文件以保持索引。

### 审核与数据维护
- `M`：标记当前 annotation 已审核。
- `S`：显式保存所有改动（唯一真正写回 JSON 的动作）。
- `C`：从历史文件复制 ScoreboardSingle bbox，并按 IOU 自动匹配。

### bbox 编辑
- `E`：进入/轮换编辑目标，完成一圈后自动退出并恢复光标。
- 鼠标拖拽：写入或替换 bbox，并自动添加 `retrack=True`。
- `X`：交换前两个 bbox 的 label，方便快速修正描述顺序。

## 工作技巧
- 左侧文本区域双击可在 VS Code 打开对应 JSON，编辑后按 **L** 回读最新结果。
- `B` 与 `W` 互斥：触发其一会清空另一方的暂停与索引，避免状态乱套。
- 所有跨文件跳转（`Shift+N/P`、`U` 系列）都会尝试保存当前更改；若尚未按 **S** 也不会丢失。
- 进度条拖动可与 `B/W` 组合使用：先精准定位再触发快捷键做系统巡检。

## 数据路径与格式
- 媒体：`../Dataset/{sport}/{event}/clips|frames/{id}.{mp4|jpg}`。
- 标注：`../output/{sport}/{event}/clips|frames/{id}.json`，旧版本可参考 `../../data/output/...`。

**Clips JSON 示例**
```json
{
  "id": "1",
  "origin": { "sport": "3x3_Basketball", "event": "Men" },
  "annotations": [
    {
      "annotation_id": "1",
      "task_L2": "Spatial_Temporal_Grounding",
      "Q_window_frame": [0, 76],
      "A_window_frame": [11, 30],
      "first_bounding_box": [x1, y1, x2, y2],
      "tracking_bboxes": { "mot_file": "path/to/mot.txt" },
      "reviewed": false
    }
  ]
}
```

**Frames JSON 示例**
```json
{
  "id": "1",
  "origin": { "sport": "Cycling", "event": "Women's_Cross-Country" },
  "annotations": [
    {
      "annotation_id": "1",
      "task_L2": "Objects_Spatial_Relationships",
      "timestamp_frame": 1,
      "bounding_box": [ { "label": "cyclist", "box": [x1, y1, x2, y2] } ],
      "reviewed": false
    }
  ]
}
```

若需安装/运行指引，请参阅 `quickstart.md`；本文件保持为操作指南与数据说明的唯一入口。

### 窗口标记:
- **绿色 "Q BEGIN/END"**: Q窗口开始/结束帧
- **蓝色 "A1/A2/A3... BEGIN/END"**: A窗口开始/结束帧  
- **紫色 "A1/A2... POINT"**: A窗口关键点帧

### 状态显示:
- **帧计数器**: 当前帧/总帧数
- **进度条**: 视频播放进度
- **任务信息**: 显示任务类型和查询内容
- **"EDITING..."**: bbox编辑模式提示

## 注意事项

1. **数据路径**: 确保数据路径正确，程序会在当前目录的上级目录中查找Dataset和output文件夹
2. **媒体文件**: 视频和图片文件必须存在，否则无法加载
3. **MOT格式**: MOT文件格式应符合MOTChallenge标准
4. **自动保存**: bbox编辑和审核状态会自动保存到原始JSON文件中
5. **编辑模式**: 在bbox编辑模式下视频会自动暂停，避免编辑干扰
6. **外部编辑**: 使用VSCode等编辑器修改JSON文件后，按F5重新加载
7. **坐标精度**: bbox坐标会自动转换为视频原始分辨率坐标

## 技术要求

### 依赖环境
```bash
pip install opencv-python pillow tkinter
```

### 系统支持
- Python 3.7+
- Windows/Linux/macOS
- OpenCV 4.0+
- VSCode (可选，用于外部编辑)

## 故障排除

1. **视频无法播放**: 检查视频文件路径和格式
2. **JSON文件报错**: 验证JSON格式是否正确
3. **键盘快捷键无响应**: 确保窗口获得焦点
4. **bbox编辑无效果**: 检查是否正确进入编辑模式(E键)
5. **外部编辑不生效**: 使用F5重新加载文件