#!/usr/bin/env python3
"""
在上级目录同级的 `output` 目录下，递归查找所有名为 `frames` 的文件夹，
对其中的 JSON 文件进行扫描：
- 如果存在 `task_L2` 为 `Objects_Spatial_Relationships` 的 annotation，且其 `question` 中包含 right 或 left；
- 同时存在 `task_L2` 为 `ScoreboardSingle` 的 annotation，且其 `answer` 中包含 no；
则在终端打印该 JSON 文件路径（不修改文件）。
可通过 `--base` 指定不同的 output 根目录。
"""
from pathlib import Path
import argparse
import json
import re
import sys

# 将默认搜索的 output 目录设置为脚本顶部变量，方便手动修改
# 默认指向：脚本所在目录的上级目录的同级目录中的 `output`
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'output'


# 全局计数器
TOTAL_DELETED_SCOREBOARD = 0
TOTAL_FOUND_SPATIAL = 0


def filter_annotations(obj, modified=False, file_path=""):
    """
    递归遍历并过滤 JSON 对象：
    - 删除 ScoreboardSingle 且 answer 含 no 的项
    - 统计 Objects_Spatial_Relationships 且 question 含 right/left 的项（但不删除）
    - 返回 (filtered_obj, changed_flag, found_spatial_in_tree)
    """
    global TOTAL_DELETED_SCOREBOARD, TOTAL_FOUND_SPATIAL

    found_spatial = False
    
    if isinstance(obj, list):
        new_list = []
        is_changed = modified
        for item in obj:
            # 检查当前 item 是否需要删除，或者是否包含需要统计的 spatial
            should_delete = False
            
            if isinstance(item, dict):
                tl = item.get('task_L2') or item.get('task_l2') or item.get('taskL2') or ''
                if isinstance(tl, str):
                    tl = tl.strip()
                    
                    if tl == 'Objects_Spatial_Relationships':
                        q = item.get('question') or item.get('Question') or ''
                        if isinstance(q, str) and re.search(r"\b(right|left)\b", q, re.IGNORECASE):
                            TOTAL_FOUND_SPATIAL += 1
                            found_spatial = True
                            # 不删除，所以 should_delete 保持 False
                    
                    elif tl == 'ScoreboardSingle':
                        a = item.get('answer') or item.get('Answer') or ''
                        if isinstance(a, str) and re.search(r"\bno\b", a, re.IGNORECASE):
                            TOTAL_DELETED_SCOREBOARD += 1
                            should_delete = True
            
            if should_delete:
                is_changed = True
            else:
                # 递归处理子元素
                filtered_item, child_changed, child_found_spatial = filter_annotations(item, False, file_path)
                if child_changed:
                    is_changed = True
                if child_found_spatial:
                    found_spatial = True
                new_list.append(filtered_item)
        return new_list, is_changed, found_spatial

    elif isinstance(obj, dict):
        is_changed = modified
        new_dict = {}
        for k, v in obj.items():
            filtered_v, child_changed, child_found_spatial = filter_annotations(v, False, file_path)
            if child_changed:
                is_changed = True
            if child_found_spatial:
                found_spatial = True
            new_dict[k] = filtered_v
        return new_dict, is_changed, found_spatial

    else:
        return obj, modified, found_spatial


def process_file(path: Path):
    # 此函数在本版本中不再使用，逻辑整合到 main 中
    pass


def find_frames_jsons(base_dir: Path):
    """在 base_dir 下递归查找所有名为 frames 的目录，然后列出其下的 JSON 文件。"""
    for frames in base_dir.rglob('frames'):
        if frames.is_dir():
            for j in frames.rglob('*.json'):
                yield j


def main():
    p = argparse.ArgumentParser(description='查找满足条件的 frames 下 JSON 文件并打印路径')
    p.add_argument('--base', '-b', help='output 根目录（默认: script 的上级目录同级的 output）')
    p.add_argument('--abs', action='store_true', help='打印绝对路径（默认是绝对路径）')
    args = p.parse_args()

    if args.base:
        base = Path(args.base)
    else:
        # 使用顶部变量作为默认 output 目录，方便在脚本内修改
        base = OUTPUT_DIR

    if not base.exists():
        print(f'Base not found: {base}', file=sys.stderr)
        sys.exit(1)

    TOTAL_PROCESSED_FILES = 0
    FOUND_FILES = []

    for j in find_frames_jsons(base):
        
        try:
            # 读取文件
            text = j.read_text(encoding='utf-8')
            data = json.loads(text)
            
            # 过滤/统计
            # 返回: new_data, changed_flag, found_spatial_flag
            new_data, changed, found_spatial_in_file = filter_annotations(data, modified=False, file_path=str(j))

            if changed:
                j.write_text(json.dumps(new_data, indent=4, ensure_ascii=False), encoding='utf-8')
            
            # 如果发现了 Spatial，就只打印这个文件的路径
            if found_spatial_in_file:
                abs_path = str(j.resolve())
                print(f"[Objects_Spatial_Relationships] {abs_path}")
                FOUND_FILES.append(abs_path)
                
            TOTAL_PROCESSED_FILES += 1

        except Exception:
            continue

    # 将找到的文件列表保存到 json，供 GUI 使用
    results_file = Path("spatial_results.json")
    results_file.write_text(json.dumps(FOUND_FILES, indent=4, ensure_ascii=False), encoding='utf-8')
    print(f"Results saved to {results_file.resolve()}")

    print("-" * 40)
    print(f"Total Found Objects_Spatial_Relationships (occurrences, KEPT): {TOTAL_FOUND_SPATIAL}")
    print(f"Total Deleted ScoreboardSingle (occurrences, DELETED): {TOTAL_DELETED_SCOREBOARD}")
    print(f"Total Files Processed: {TOTAL_PROCESSED_FILES}")


if __name__ == '__main__':
    main()
