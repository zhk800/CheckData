# AI标注审查系统

基于 Tkinter + OpenCV 的 **AI 标注审查桌面工具**，用于可视化和审核视频片段（clips）与单帧图像（frames）的标注数据。支持边界框绘制与编辑、时间窗口与 MOT 追踪可视化，以及按标注/按文件快速导航与批量审核。

> **平台说明**：macOS 下修饰键为 **Cmd**，Windows/Linux 下为 **Ctrl**，下文统一写作「修饰键+S」等形式。

## 项目结构

```
CheckData-master/
├── main.py           # 主程序入口，启动审查界面
├── requirements.txt  # Python 依赖
├── README.md         # 本说明
├── USAGE.md          # 详细使用与数据结构说明
└── sync_output.py    # 输出目录同步脚本（若存在）
```

## 功能特点

1. **多格式支持**：支持视频片段（clips）和单帧图像（frames）的标注审核。
2. **可视化显示**：
   - 边界框（bounding box）、Q/A 窗口帧标记（window_frame）
   - MOT 追踪数据（MOTChallenge 格式）可视化
3. **交互式审核**：按条浏览标注、标记已审核、保存到原始 JSON。
4. **视频播放**：播放/暂停、进度条拖拽/点击跳帧、从首帧重播。
5. **bbox 编辑**：修饰键+E 进入编辑模式，鼠标拖拽修改框，支持 `first_bounding_box` 与多目标 `bounding_box`。
6. **文件级操作**：修饰键+←/→ 切换上一/下一个 JSON 文件；修饰键+1 删除当前条、修饰键+Z 撤销删除；修饰键+2 删除当前 JSON 文件。

## 键盘快捷键

以下与 `main.py` 中实际绑定一致。

| 按键 | 功能 | 说明 |
|------|------|------|
| **Space / Enter** | 播放/暂停 | 仅 clips：切换视频播放 |
| **R** | 重播 | 仅 clips：从第 0 帧重新播放 |
| **B** | bbox 帧跳转 | 仅 clips：依次跳到含 bbox 的帧并暂停，再按恢复播放并重置 W 状态 |
| **W** | 窗口帧导航 | 仅 clips：按 Q BEGIN→Q END 顺序跳转，一轮结束后恢复播放并重置 B 状态 |
| **L** | 加载数据 | 按当前事件/类型/ID 重新载入 JSON 与媒体 |
| **F5** | 重新加载 | 不改变选择，从磁盘刷新当前 JSON |
| **← (Left)** | 上一条标注 | 在当前文件内切换到上一条 annotation |
| **→ (Right)** | 下一条标注 | 在当前文件内切换到下一条 annotation |
| **修饰键+←** | 上一个文件 | 切换到上一个 JSON 文件（自动保存当前） |
| **修饰键+→** | 下一个文件 | 切换到下一个 JSON 文件（自动保存当前） |
| **修饰键+S** | 保存 | 将当前内存中的标注写回当前 JSON 文件 |
| **修饰键+B** | 标记已审核 | 将当前标注设为 `reviewed: true` |
| **修饰键+X** | 交换标签 | 当且仅当当前条有 2 个 `bounding_box` 时，交换两框的 `label` |
| **修饰键+E** | bbox 编辑模式 | 进入/切换可编辑 bbox；进入时暂停视频，支持拖拽绘制/修改 |
| **修饰键+T** | 旧数据替换 | 预留（当前实现为空） |
| **修饰键+1** | 删除当前条 | 删除当前 annotation 并保存；可用修饰键+Z 撤销 |
| **修饰键+2** | 删除当前文件 | 确认后删除当前 JSON 文件并切换到下一个文件 |
| **修饰键+Z** | 撤销删除 | 仅恢复上一次修饰键+1 删除的 annotation（须在同一文件内） |
| **Delete / BackSpace** | 删除当前条 | 与修饰键+1 相同（Mac 上为 BackSpace） |

## bbox 编辑模式使用

1. **进入编辑模式**：按 **修饰键+E**（如 Cmd+E / Ctrl+E）
2. **创建/修改 bbox**：在画面上鼠标左键拖拽绘制或修改边界框
3. **实时预览**：拖拽时显示黄色框与 "EDITING..." 提示
4. **写入与保存**：松开鼠标后更新内存中的标注；需再按 **修饰键+S** 写回 JSON 文件
5. **切换目标 / 退出**：再次按 **修饰键+E** 在多个可编辑 bbox 间切换，全部切换完一轮后退出编辑模式

**编辑模式特性**：
- 视频自动暂停，光标为十字形
- 支持修改 `first_bounding_box` 及当前条内的 `bounding_box` 列表
- 过小的框会被忽略；修改后会自动设置 `retrack: true`

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本操作流程
1. 启动程序：`python main.py`
2. 在左侧选择事件（sport/event）、数据类型（clips 或 frames）和 ID
3. 点击「Load (L)」或按 **L** 加载数据
4. 使用 **← / →** 切换标注条，**修饰键+← / 修饰键+→** 切换文件
5. 需要时按 **修饰键+E** 进入 bbox 编辑，拖拽修改后 **修饰键+S** 保存
6. 审核完成后 **修饰键+B** 标记已审核，再 **修饰键+S** 保存

### 高效审核工作流
1. **快速导航**：用 **W** 按 Q BEGIN/END 顺序查看窗口关键帧
2. **精确定位**：用 **B** 跳转到含 bbox 的帧
3. **编辑修正**：按 **修饰键+E** 进入编辑模式，拖拽修正边界框后 **修饰键+S** 保存
4. **标记完成**：按 **修饰键+B** 将当前条标为已审核
5. **继续下一条/下一个文件**：**→** 切下一条标注，**修饰键+→** 切下一个 JSON 文件

### 外部编辑集成
- **双击左侧标注信息区域**：用系统默认应用（如 VSCode）打开当前 JSON 文件
- **F5**：在外部修改 JSON 后按 F5 从磁盘重新加载当前文件

## 数据结构要求

### 原始数据路径:
- 视频: `../Dataset/{sport}/{event}/clips/{id}.mp4`
- 图片: `../Dataset/{sport}/{event}/frames/{id}.jpg`

### 标注数据路径:
- 视频标注: `../output/{sport}/{event}/clips/{id}.json`
- 图片标注: `../output/{sport}/{event}/frames/{id}.json`

### 标注格式:

#### Clips标注格式:
```json
{
  "id": "1",
  "origin": {
    "sport": "3x3_Basketball",
    "event": "Men"
  },
  "annotations": [
    {
      "annotation_id": "1",
      "task_L1": "Understanding",
      "task_L2": "Spatial_Temporal_Grounding",
      "Q_window_frame": [0, 76],
      "A_window_frame": [11, 30],
      "first_bounding_box": [x1, y1, x2, y2],
      "tracking_bboxes": {
        "mot_file": "path/to/mot/file.txt",
        "format": "MOTChallenge"
      },
      "reviewed": false
    }
  ]
}
```

#### Frames标注格式:
```json
{
  "id": "1",
  "origin": {
    "sport": "Cycling_Mountain_Bike",
    "event": "Women's_Cross-Country"
  },
  "annotations": [
    {
      "annotation_id": "1",
      "task_L1": "Understanding",
      "task_L2": "Objects_Spatial_Relationships",
      "timestamp_frame": 1,
      "bounding_box": [
        {
          "label": "cyclist in black jersey",
          "box": [x1, y1, x2, y2]
        }
      ],
      "reviewed": false
    }
  ]
}
```

## 可视化说明

### 边界框颜色:
- **黄色**: 静态标注框 (first_bounding_box)
- **红色**: 第一帧追踪框  
- **青色**: MOT追踪框
- **黄色虚线**: 编辑模式中的临时边界框

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

1. **数据路径**：程序从当前工作目录的 `../Dataset` 与 `../output` 读取媒体和标注，请保证目录结构符合下文「数据结构要求」。
2. **媒体文件**：视频（如 .mp4）和图片（如 .jpg）需存在，否则无法加载。
3. **MOT 格式**：若使用追踪，MOT 文件需符合 MOTChallenge 格式。
4. **保存**：修改标注或 bbox 后需按 **修饰键+S** 才会写回 JSON；切换文件前会自动保存当前文件。
5. **编辑模式**：进入 bbox 编辑时视频会暂停，避免拖拽时画面跳动。
6. **外部编辑**：在别处修改 JSON 后，按 **F5** 重新加载当前文件。
7. **坐标**：bbox 在画布上的拖拽会按当前帧分辨率换算后写回原始坐标。

## 技术要求

### 依赖环境
```bash
pip install -r requirements.txt
```
主要依赖：`opencv-python`、`Pillow`；界面使用 Python 标准库 `tkinter`（一般随 Python 安装）。

### 系统支持
- Python 3.7+
- Windows / Linux / macOS（程序会根据系统自动使用 Cmd 或 Ctrl）
- VSCode 等编辑器可选，用于双击打开 JSON 后配合 F5 重载

## 故障排除

1. **视频无法播放**: 检查视频文件路径和格式
2. **JSON文件报错**: 验证JSON格式是否正确
3. **键盘快捷键无响应**: 确保窗口获得焦点
4. **bbox 编辑无效果**：确认已按修饰键+E 进入编辑模式，且当前条存在可编辑的 bbox
5. **外部编辑不生效**: 使用F5重新加载文件