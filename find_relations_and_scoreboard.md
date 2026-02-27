# find_relations_and_scoreboard.py 使用说明

这个脚本用于在指定的 `output` 目录下扫描包含 `frames` 文件夹的 JSON 文件，并根据特定的 `task_L2` 类型和内容进行清理和统计。

## 功能概述

脚本会遍历目标文件夹下的所有 JSON 文件，对每个文件执行以下两类操作：

1.  **删除 ScoreboardSingle**:
    -   **条件**: `task_L2` 为 `ScoreboardSingle` **且** `answer` 中包含 "no" (不区分大小写)。
    -   **操作**: 从 JSON 文件中**删除**该 Annotation 条目。
    -   **统计**: 计入 "Total Deleted ScoreboardSingle"。
    -   **文件修改**: 如果有删除操作，文件会被直接修改并保存。

2.  **保留并统计 Objects_Spatial_Relationships**:
    -   **条件**: `task_L2` 为 `Objects_Spatial_Relationships` **且** `question` 中包含 "right" 或 "left" (不区分大小写)。
    -   **操作**: **保留**该条目（不删除）。
    -   **统计**: 计入 "Total Found Objects_Spatial_Relationships"。
    -   **输出**: 只要文件中包含至少一个满足此条件的条目，就会在终端打印该文件的路径。

## 使用方法

### 1. 默认运行
脚本默认会在其**上两级目录的同级目录**下的 `output` 文件夹中进行搜索（以及脚本顶部的 `OUTPUT_DIR` 变量所指定的路径）。

```bash
python3 find_relations_and_scoreboard.py
```

### 2. 指定搜索路径
如果你想搜索自定义的 `output` 目录，可以使用 `--base` 或 `-b` 参数：

```bash
python3 find_relations_and_scoreboard.py --base /path/to/your/custom/output
```

## 输出示例

终端输出只会显示包含 `Objects_Spatial_Relationships` 的文件路径，而不会显示只删除了 `ScoreboardSingle` 的文件路径。

```text
[Objects_Spatial_Relationships] /home/user/project/output/Athletics/frames/video1.json
[Objects_Spatial_Relationships] /home/user/project/output/Swimming/frames/video5.json
...
----------------------------------------
Total Found Objects_Spatial_Relationships (occurrences, KEPT): 150
Total Deleted ScoreboardSingle (occurrences, DELETED): 42
Total Files Processed: 500
```

## 配置
你可以直接修改脚本开头的 `OUTPUT_DIR` 变量来更改默认的搜索根目录：

```python
# find_relations_and_scoreboard.py
# ...
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'output'
# ...
```
