# OlympicVM Annotation Check & Clean Tools

本工具集包含两个主要脚本，用于对 `Dataset` 和 `output` 目录下的标注数据进行批量清理、统计以及可视化审查。

## 功能总览

| 脚本文件 | 用途 | 主要功能 |
| :--- | :--- | :--- |
| **1. `find_relations_and_scoreboard.py`** | **批量处理/清洗** | 自动删除无效的 Scoreboard 标注，统计并检索 Spatial 标注。 |
| **2. `view_spatial_relations.py`** | **可视化审查** | 图形化查看检索到的 Spatial 标注，支持双击跳转 VS Code 修改。 |

---

## 步骤一：批量清洗与检索

运行 `find_relations_and_scoreboard.py` 脚本，它会扫描指定目录下的所有 JSON 文件。

### 执行逻辑
1.  **删除 ScoreboardSingle**:
    -   如果 `task_L2` 为 `ScoreboardSingle` **且** `answer` 包含 "no"，该条目会被**自动删除**。
    -   文件会被原地修改保存。
2.  **检索 Objects_Spatial_Relationships**:
    -   如果 `task_L2` 为 `Objects_Spatial_Relationships` **且** `question` 包含 "right" 或 "left"，该条目会被**记录**（不删除）。
    -   符合条件的文件路径会被保存到 `spatial_results.json`，供后续 GUI 使用。

### 使用方法

**默认运行**（搜索上两级目录的 `output`）：
```bash
python3 find_relations_and_scoreboard.py
```

**指定路径运行**：
```bash
python3 find_relations_and_scoreboard.py --base /path/to/your/output
```

**输出示例**：
```text
[Objects_Spatial_Relationships] .../Athletics/.../1.json
[Objects_Spatial_Relationships] .../Swimming/.../5.json
----------------------------------------
Total Found Objects_Spatial_Relationships (occurrences, KEPT): 150
Total Deleted ScoreboardSingle (occurrences, DELETED): 42
Total Files Processed: 500
Results saved to .../spatial_results.json
```

---

## 步骤二：GUI 可视化审查

在步骤一运行完成后，会生成 `spatial_results.json` 文件。此时运行 `view_spatial_relations.py` 启动可视化界面。

### 启动方式
```bash
python3 view_spatial_relations.py
```

### 界面功能
-   **图片预览**：左侧自动加载与 JSON 对应的图片（脚本会尝试在同级或 `Dataset` 目录下查找）。
-   **标注详情**：右侧显示当前文件的 Question 和 Answer。
-   **文件导航**：
    -   `Prev File` / `Next File`: 切换上一个/下一个包含 Spatial 标注的文件。
    -   `Prev Ann` / `Next Ann`: 在当前文件中切换多个标注条目。
-   **快捷编辑**：
    -   **双击右侧文本区域**，脚本会尝试调用 VS Code 打开当前 JSON 文件，方便你直接进行修改或查看上下文。

---

## 配置说明

如果你的目录结构与默认设置不同，可以在脚本头部修改以下变量：

**在 `find_relations_and_scoreboard.py` 中**：
```python
# 默认搜索的 output 根目录
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'output'
```

**在 `view_spatial_relations.py` 中**：
```python
# 图片 Dataset 的根目录（用于查找图片）
DATASET_ROOT = Path(__file__).resolve().parent.parent / 'Dataset'
```

