# AI标注审查系统

这是一个用于审查AI标注数据的可视化工具，支持视频片段(clips)和单帧图像(frames)的标注审核。

## 功能特点

1. **多格式支持**: 支持视频片段和单帧图像的标注审核
2. **可视化显示**: 
   - 显示边界框(bounding box)
   - 显示窗口帧标记(window_frame)
   - 支持MOT追踪数据可视化
3. **交互式审核**: 
   - 逐个审核标注
   - 标记审核状态
   - 保存审核结果
4. **视频播放控制**: 
   - 播放/暂停
   - 进度控制
   - 循环播放
5. **bbox编辑功能**: 
   - 鼠标拖拽创建/修改边界框
   - 实时视觉反馈
   - 自动保存到JSON文件

## 键盘快捷键

| 按键 | 功能 | 说明 |
|-----|------|------|
| **Space** | 播放/暂停 | 切换视频播放状态 |
| **B** | bbox帧跳转 | 在包含bounding box的帧间跳转 |
| **W** | 窗口帧导航 | 按逻辑顺序导航窗口帧 (Q→A sequence) |
| **M** | 标记已审核 | 将当前标注标记为已审核 |
| **R** | 重播视频 | 从窗口开始帧重新播放 |
| **S** | 保存数据 | 保存当前修改到JSON文件 |
| **L** | 加载数据 | 重新加载选中的数据 |
| **P** | 上一标注 | 切换到上一个标注 |
| **N** | 下一标注 | 切换到下一个标注 |
| **U** | 撤销审核 | 取消当前标注的审核状态 |
| **F5** | 重新加载 | 重新加载当前文件 |
| **E** | bbox编辑模式 | 进入/退出边界框编辑模式 |

## bbox编辑模式使用

1. **进入编辑模式**: 按 **E** 键
2. **创建bbox**: 鼠标左键拖拽绘制边界框
3. **实时预览**: 拖拽过程中显示黄色虚线框
4. **自动保存**: 松开鼠标后自动保存到JSON文件
5. **退出编辑**: 再次按 **E** 键退出编辑模式

**编辑模式特性**:
- 视频播放自动暂停，避免干扰编辑
- 鼠标光标变为十字形
- 显示"EDITING..."状态提示
- 支持修改 `first_bounding_box` 字段
- 过小的框会被自动忽略

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本操作流程
1. 启动程序: `python main.py`
2. 选择要审核的事件(sport/event)
3. 选择数据类型(clips或frames)  
4. 选择具体的ID
5. 点击"加载数据"开始审核
6. 使用键盘快捷键进行高效审核
7. 使用bbox编辑功能修改边界框
8. 标记审核状态并保存

### 高效审核工作流
1. **快速导航**: 使用 **W** 键按逻辑顺序查看所有关键帧
2. **精确定位**: 使用 **B** 键跳转到包含bbox的重要帧
3. **编辑修正**: 按 **E** 进入编辑模式，鼠标拖拽修正边界框
4. **标记完成**: 按 **M** 标记当前标注为已审核
5. **下一个标注**: 按 **N** 切换到下一个标注继续审核

### 外部编辑集成
- **双击标注信息**: 在VSCode中打开对应的JSON文件
- **F5重新加载**: 外部修改后按F5刷新显示

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