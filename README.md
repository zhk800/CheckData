# AI标注审查系统

面向视频 clips 与单帧 frames 的标注审核工具，统一展示窗口帧、bbox 与 MOT 追踪结果，并提供审核、编辑与批量修正能力。

## 核心特性
- **多模式审核支持**：支持 "Default" 和 "Spatial Imagination" 两种审核模式，适配不同任务的数据路径结构。
- **上游 Question/Query 小窗**：在 Spatial Imagination 等模式下，左侧会显示对应 Dataset 文件中 `source_annotation.annotation` 的 `question` 与 `query` 内容，便于对照审核。
- 支持 clips / frames 双形态数据，并可同时查看窗口帧、bbox、MOT 追踪。
- 鼠标拖拽式 bbox 编辑，自动写入 `retrack=True`；保留 Scoreboard 复制、交换 label 等按钮。
- VS Code 集成：左侧「Current Annotation」区域双击可打开对应 JSON；加载/保存/播放等通过左侧与底部按钮完成。

> ⚙️ 启动步骤集中在 `quickstart.md`，README 仅保留工作流与功能说明。

## 使用流程
1. **模式与数据载入**：
    - **Review Mode**：在左侧选择 "Default" 或 "Spatial Imag."。
    - **选择数据**：选择 sport/event → data type (clips/frames) → ID。
    - **加载**：点击 **Load Data (L)** 载入；若在外部修改了 JSON，点击 **Reload** 重新载入。
2. **浏览验证**：clips 通过底部 **Play/Pause**、**Replay** 与进度条控制播放；frames 为静态图。
3. **编辑修正**：通过左侧与底部按钮进行 bbox 编辑、Scoreboard 复制、交换 label、删除标注等（无键盘快捷键，仅按钮）。
4. **审核与保存**：确认无误后按 **Cmd/Ctrl+B** 或将当前标注标记为已审核，再点击 **Save (S)** 写回 JSON。
5. **切换对象**：**← / →** 在同一 JSON 内切换 annotation；**Cmd/Ctrl+← / →** 在不同 JSON 文件间切换；跨文件跳转前会尝试保存当前修改。

## 快捷键一览（仅保留以下 5 个）
- **macOS** 使用 **Cmd**，**Windows / Linux** 使用 **Ctrl**。
| 按键 | 功能 |
|------|------|
| `Cmd/Ctrl+B` | 将当前标注的 `reviewed` 设为 `true`（标记已审核） |
| `←` | 同一 JSON 内：上一条 annotation |
| `→` | 同一 JSON 内：下一条 annotation |
| `Cmd/Ctrl+←` | 上一个 JSON 文件（跳转前尝试保存） |
| `Cmd/Ctrl+→` | 下一个 JSON 文件（跳转前尝试保存） |

其余操作（加载、保存、播放、重播、标记已审核、上一/下一标注、上一/下一文件、下一未审核文件、复制 Scoreboard、交换 label、删除标注等）均通过界面按钮完成，无键盘快捷键。

## 界面说明
- **Source question / query (Dataset)**：显示当前 clip 对应上游 JSON（`Dataset/{sport}/{event}/clips/{id}.json`）中的 `source_annotation.annotation.question` 与 `query`，无则显示 N/A。
- **Current Annotation**：当前选中 annotation 的详情；双击该区域可在 VS Code 中打开对应 JSON，编辑后点击 Reload 重新载入。
- 底部提示条：`←/→` 同文件标注，`Cmd/Ctrl+←/→` 切换文件，`Cmd/Ctrl+B` 标记已审核（macOS 为 Cmd，Windows/Linux 为 Ctrl）。

## 数据路径与格式
工具支持两种模式，数据路径有所不同，请确保目录结构符合以下规范：

### 1. Default Mode (标准模式)
适用于常规 OlympicVMBench 任务。
- **Dataset (视频/图片)**: `../Dataset/{sport}/{event}/clips|frames/{id}.{mp4|jpg}`
- **Output (标注 JSON)**: `../output/{sport}/{event}/clips|frames/{id}.json`
- **Reference (旧数据)**: `../../data/output/...`

### 2. Spatial Imagination Mode (任务 L2: Spatial_Imagination)
适用于空间想象力相关任务，数据存储在独立的 `Spatial_Imagination` 文件夹中。
- **Dataset (视频)**: `../Spatial_Imagination/Dataset/{sport}/{event}/clips/{id}.mp4`
- **Output (标注 JSON)**: `../Spatial_Imagination/output/{sport}/{event}/clips/{id}.json`
- *注意：此模式下的 Dataset 和 output 文件夹位于 `Spatial_Imagination` 子目录下。*

### 通用说明
- **工作目录**: 运行 `main.py` 时，当前工作目录必须是 `CheckData/`。
- **目录层级**: `Dataset`, `output`, `Spatial_Imagination` 文件夹应与 `CheckData` 文件夹同级。

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

若需安装/运行指引，请参阅 `quickstart.md`。

### 窗口标记
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
6. **外部编辑**: 使用 VSCode 等编辑器修改 JSON 后，点击左侧 **Reload** 重新加载
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
3. **键盘快捷键无响应**: 确保窗口获得焦点（仅支持 Cmd/Ctrl+B、←、→、Cmd/Ctrl+←、Cmd/Ctrl+→）
4. **bbox 编辑无效果**: 通过左侧/底部对应按钮进入编辑与保存
5. **外部编辑不生效**: 点击 **Reload** 重新加载文件