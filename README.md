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
| **Space / Enter** | 播放/暂停 | 仅clips：切换视频播放状态 |
| **B** | bbox帧跳转/循环 | 仅clips：依次跳到含bbox的帧并暂停，再次按键恢复播放并重置W状态 |
| **W** | 窗口帧导航 | 仅clips：按Q→A顺序跳转窗口帧，完成一轮后自动恢复播放并重置B状态 |
| **R** | 重播视频 | 从当前标注的Q窗口起始帧重新播放并开始循环 |
| **L** | 加载数据 | 根据当前选择的事件/类型/ID重新载入JSON |
| **F5** | 重新加载文件 | 不变更选择，直接从磁盘刷新当前JSON内容 |
| **P** | 上一标注 | 切换到上一条标注记录 |
| **N** | 下一标注 | 切换到下一条标注记录 |
| **M** | 标记已审核 | 将当前标注设置为reviewed状态 |
| **S** | 保存数据 | 将当前内存中的标注全部写回JSON文件 |
| **E** | bbox编辑模式 | 进入后可按E循环切换可编辑目标，完成一轮后自动退出 |
| **T** | 旧数据一键替换 | 将当前标注替换为旧数据同任务的内容，再按一次撤销替换 |
| **U** | 下一个未审核文件 | 自动保存当前修改后，跳转到下一份包含未审核标注的文件 |
| **Shift + U** | 过滤跳转 | 仅在`Spatial_Temporal_Grounding`/`Continuous_Actions_Caption`任务中查找未审核文件 |
| **X** | 交换前两个bbox标签 | 同一标注中前两个bbox的label字段互换，并自动标记retrack |
| **Delete** | 删除当前标注 | 移除当前annotation、静默保存并重新加载文件以保持索引正确 |

## bbox编辑模式使用

1. **进入编辑模式**: 按 **E** 键；若同一标注有多个目标，重复按 **E** 可在 `first_bounding_box` 与各个 `bounding_box[i]` 之间轮换。
2. **创建/修改bbox**: 鼠标左键拖拽绘制，松开后立即写入当前标注并自动添加 `retrack` 标记（仍需按 **S** 手动保存到文件）。
3. **实时预览**: 拖拽过程中显示黄色虚线框和 "EDITING..." 提示。
4. **退出编辑**: 连续按 **E** 直至循环结束或手动切换其它标注，模式会自动关闭，光标恢复常规状态。

**编辑模式特性**:
- 视频播放自动暂停，避免干扰编辑
- 鼠标光标变为十字形，并在角落提示当前目标
- 拖拽过小的框会被忽略

## 标注维护快捷键

- **X 交换标签**: 当前标注中前两个 `bounding_box` 的 `label` 字段互换，可用于快速修正目标描述的顺序，操作后会自动添加 `retrack` 提示。
- **Delete 删除标注**: 直接移除当前 annotation，静默保存文件并自动重新加载，方便清除无效任务。
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