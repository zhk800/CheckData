# 标注自动修复工具

## 功能

自动修复体育赛事视频帧标注数据中的两个问题：

1. **删除无效的ScoreboardSingle标注** - 当画面中没有计分板时
2. **修复空间关系问题** - 移除问题中的冗余位置描述（如"on the left", "on the right"）

## 技术特点

- ✅ 仅传输关键信息（question/answer/labels），token消耗减少85%
- ✅ 支持超大批处理（默认100个文件/批）
- ✅ 一次API调用处理多个文件，效率提升50倍

## 前置要求

1. **设置API密钥**
```bash
export GEMINI_API_KEY='你的Gemini API密钥'
```

## 用法

### 1. 处理单个运动项目

```bash
# 处理Artistic_Swimming
python fix.py Artistic_Swimming

# 处理Badminton
python fix.py Badminton

# 处理Basketball
python fix.py Basketball
```

### 2. 处理所有运动项目（默认）

```bash
python fix.py
```

### 3. 自定义参数

```bash
# 指定批处理大小
python fix.py Badminton --batch-size 50

# 指定批次间延迟
python fix.py Basketball --delay 2.0

# 使用API密钥参数（而非环境变量）
python fix.py --api-key 'your-key-here'
```

## 输出示例

```
🏅 Artistic_Swimming
📁 找到 100 个JSON文件
📦 批处理大小: 100 个文件/批次
================================================================================

================================================================================
📦 批次 1/1 - 处理 100 个文件
================================================================================
  📦 [1/4] 读取文件...
  �� [2/4] 打包数据... (47个文件，24886字符)
  🚀 [3/4] 调用API处理...
  ✅ API响应成功
  📝 [4/4] 应用修复...
  ✅ 8.json: 2 -> 1 annotations
  ✅ 10.json: Updated
  ⚪ 15.json: No changes

================================================================================
📊 修复统计:
  总文件数: 47
  总标注数: 89
  删除标注: 21
  更新标注: 27
  错误: 0
================================================================================
```

## 修复规则

### 规则1: ScoreboardSingle标注
- **检测**: answer包含"no scoreboard visible"
- **操作**: 删除整个标注

### 规则2: Objects_Spatial_Relationships标注
- **检测**: 
  - bounding_box中有"Swimmer A"和"Swimmer B"标签
  - question/answer中包含位置描述（如"on the left", "on the right"）
- **操作**: 移除位置描述，只保留"Swimmer A"/"Swimmer B"

**示例**:
- 修复前: "In which direction is the swimmer on the left (Swimmer A) relative to..."
- 修复后: "In which direction is Swimmer A relative to Swimmer B?"

## 文件结构

```
CheckData/
├── fix.py          # 主程序
├── prompt.md       # API提示词
└── README.md       # 本文档
```

## 性能数据

处理100个Artistic_Swimming文件的实测效果：
- API调用: 1次（传统方式需100次）
- Token消耗: ~25K字符（传统方式需~100K字符）
- 处理时间: <10秒（传统方式需200+秒）
- 成本节省: ~98%

## 注意事项

1. 程序会**直接修改原文件**，建议先备份
2. 仅处理`frames/`目录下的JSON文件
3. API调用有配额限制，注意控制频率
4. 批处理大小建议100（文件较小时可增大到200）
