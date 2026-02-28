#!/usr/bin/env python3
"""当 bbox 与对应 MOT 帧的 IoU 低于阈值时自动添加 retrack=True。

脚本遍历 Check 根目录下的 `output/**/clips/` 内全部 JSON，取每条标注的
first_bounding_box 与 A 窗口起始帧对应的 MOT bbox（MOT 帧号 = JSON 帧 + 1）
比对，若该帧最佳 IoU 低于阈值则写入 `retrack=True`。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

Box = Tuple[float, float, float, float]
FrameBoxes = Dict[int, List[Box]]
OUTPUT_ROOT = (Path(__file__).resolve().parents[2] / "output").resolve()
THRESHOLD_DEFAULT = 0.90
MARK_LOG_PATH = Path(__file__).with_name("marked_files.txt")


class MotData:
    def __init__(self, lines: List[List[str]], frame_index: Dict[int, List[int]], frames: FrameBoxes):
        self.lines = lines
        self.frame_index = frame_index
        self.frames = frames
        self.dirty = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="比对 bbox 与 MOT 并标记 retrack")
    parser.add_argument(
        "--check-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="包含 output 文件夹的 Check 根目录路径",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=THRESHOLD_DEFAULT,
        help="IoU 阈值，低于此值写入 retrack=True",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅分析不写回 JSON",
    )
    return parser.parse_args()


def parse_a_window_start(a_window_frame) -> Optional[int]:
    """返回起始帧（int），支持整数或 "start-end" 字符串。"""
    if a_window_frame is None:
        return None
    first = a_window_frame[0] if isinstance(a_window_frame, list) else a_window_frame
    if isinstance(first, (int, float)):
        return int(first)
    if isinstance(first, str):
        try:
            token = first.split("-")[0]
            return int(float(token))
        except ValueError:
            return None
    return None


def expand_a_window_frames(a_window_frame) -> List[int]:
    """展开 A 窗口为帧列表，整数向下取整，区间按闭区间处理。"""
    frames: List[int] = []
    if a_window_frame is None:
        return frames

    items = a_window_frame if isinstance(a_window_frame, list) else [a_window_frame]
    for item in items:
        if isinstance(item, (int, float)):
            frames.append(int(item))
            continue
        if isinstance(item, str):
            if "-" in item:
                parts = item.split("-")
                if len(parts) == 2:
                    try:
                        start = int(float(parts[0]))
                        end = int(float(parts[1]))
                        if end < start:
                            start, end = end, start
                        frames.extend(range(start, end + 1))
                        continue
                    except ValueError:
                        pass
            try:
                frames.append(int(float(item)))
            except ValueError:
                continue
    return frames


def iou(box_a: Box, box_b: Box) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def load_mot(path: Path) -> MotData:
    frames: FrameBoxes = {}
    lines: List[List[str]] = []
    frame_index: Dict[int, List[int]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            parts = line.rstrip("\n").split(",")
            if len(parts) < 6:
                lines.append(parts)
                continue
            try:
                frame_id = int(float(parts[0]))
                x = float(parts[2])
                y = float(parts[3])
                w = float(parts[4])
                h = float(parts[5])
            except ValueError:
                lines.append(parts)
                continue
            box = (x, y, x + w, y + h)
            frames.setdefault(frame_id, []).append(box)
            frame_index.setdefault(frame_id, []).append(idx)
            lines.append(parts)
    return MotData(lines=lines, frame_index=frame_index, frames=frames)


def resolve_mot_path(json_path: Path, mot_rel: str, check_root: Path) -> Optional[Path]:
    mot_candidates: List[Path] = []
    mot_rel_path = Path(mot_rel)
    if mot_rel_path.is_absolute():
        mot_candidates.append(mot_rel_path)
    else:
        mot_candidates.append(check_root / mot_rel_path)
    mot_name = mot_rel_path.name
    mot_candidates.append(json_path.parent / "mot" / mot_name)
    for candidate in mot_candidates:
        if candidate.exists():
            return candidate
    return None


def best_iou_with_mot(
    mot_frames: FrameBoxes, frame_id: int, target_box: Box
) -> float:
    boxes = mot_frames.get(frame_id)
    if not boxes:
        return 0.0
    return max(iou(target_box, mot_box) for mot_box in boxes)


def _rebuild_frame_boxes(mot_data: MotData, frame_id: int) -> None:
    indices = mot_data.frame_index.get(frame_id, [])
    boxes: List[Box] = []
    for idx in indices:
        line = mot_data.lines[idx]
        if len(line) < 6:
            continue
        try:
            x = float(line[2])
            y = float(line[3])
            w = float(line[4])
            h = float(line[5])
        except ValueError:
            continue
        boxes.append((x, y, x + w, y + h))
    mot_data.frames[frame_id] = boxes


def update_mot_box(mot_data: MotData, frame_id: int, target_box: Box) -> None:
    indices = mot_data.frame_index.get(frame_id)
    x1, y1, x2, y2 = target_box
    w = max(0.0, x2 - x1)
    h = max(0.0, y2 - y1)

    if indices:
        best_idx = indices[0]
        best_score = -1.0
        for idx in indices:
            line = mot_data.lines[idx]
            if len(line) < 6:
                continue
            try:
                bx = float(line[2])
                by = float(line[3])
                bw = float(line[4])
                bh = float(line[5])
            except ValueError:
                continue
            score = iou(target_box, (bx, by, bx + bw, by + bh))
            if score > best_score:
                best_score = score
                best_idx = idx

        mot_data.lines[best_idx][2] = f"{x1:.2f}"
        mot_data.lines[best_idx][3] = f"{y1:.2f}"
        mot_data.lines[best_idx][4] = f"{w:.2f}"
        mot_data.lines[best_idx][5] = f"{h:.2f}"
    else:
        new_line = [
            str(frame_id),
            "1",
            f"{x1:.2f}",
            f"{y1:.2f}",
            f"{w:.2f}",
            f"{h:.2f}",
            "-1.0",
            "-1.0",
            "-1.0",
            "-1.0",
        ]
        mot_data.lines.append(new_line)
        mot_data.frame_index[frame_id] = mot_data.frame_index.get(frame_id, []) + [len(mot_data.lines) - 1]

    mot_data.dirty = True
    _rebuild_frame_boxes(mot_data, frame_id)


def iter_clip_jsons(check_root: Path) -> Iterable[Path]:
    base = OUTPUT_ROOT
    if not base.exists():
        return
    for json_path in base.rglob("clips/*.json"):
        yield json_path


def main() -> None:
    args = parse_args()
    check_root = args.check_root.resolve()
    mot_cache: Dict[Path, MotData] = {}
    marked_files: Dict[str, set] = {}

    file_count = 0
    ann_checked = 0
    ann_flagged = 0
    missing_mot = 0

    for json_path in iter_clip_jsons(check_root):
        file_count += 1
        try:
            with json_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] 跳过 {json_path}: 读取错误 {exc}")
            continue

        changed = False
        rel_path = str(json_path.relative_to(check_root)) if json_path.is_relative_to(check_root) else str(json_path)
        annotations = data.get("annotations") or []
        for ann in annotations:
            bbox = ann.get("first_bounding_box")
            mot_info = ann.get("tracking_bboxes") or {}
            mot_rel = mot_info.get("mot_file")
            start_frame = parse_a_window_start(ann.get("A_window_frame"))
            if not bbox or mot_rel is None or start_frame is None:
                continue

            mot_path = resolve_mot_path(json_path, mot_rel, check_root)
            if mot_path is None:
                missing_mot += 1
                continue

            if mot_path not in mot_cache:
                mot_cache[mot_path] = load_mot(mot_path)
            mot_data = mot_cache[mot_path]

            # MOT 帧从 1 开始，JSON 用 0 开始。
            frame_id = start_frame + 1
            ann_checked += 1
            target_box = tuple(map(float, bbox))
            iou_score = best_iou_with_mot(mot_data.frames, frame_id, target_box)
            if iou_score < args.threshold:
                if ann.get("retrack") is not True:
                    ann["retrack"] = True
                    changed = True
                    marked_files.setdefault(rel_path, set()).add("retrack")
                ann_flagged += 1
                update_mot_box(mot_data, frame_id, target_box)

            window_frames = expand_a_window_frames(ann.get("A_window_frame"))
            if window_frames:
                json_set = set(window_frames)
                mot_set = {fid - 1 for fid in mot_data.frames.keys()}
                if json_set != mot_set:
                    if ann.get("is_window_consistence") is not False:
                        ann["is_window_consistence"] = False
                        changed = True
                        marked_files.setdefault(rel_path, set()).add("is_window_consistence")

        if changed and not args.dry_run:
            with json_path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=True)
                fh.write("\n")

    if not args.dry_run:
        for mot_path, mot_data in mot_cache.items():
            if not mot_data.dirty:
                continue
            with mot_path.open("w", encoding="utf-8") as fh:
                for line in mot_data.lines:
                    fh.write(",".join(line))
                    fh.write("\n")

    retrack_files = sum(1 for marks in marked_files.values() if "retrack" in marks)
    window_files = sum(1 for marks in marked_files.values() if "is_window_consistence" in marks)

    if not args.dry_run:
        with MARK_LOG_PATH.open("w", encoding="utf-8") as log_f:
            log_f.write("[retrack]\n")
            for path, marks in sorted(marked_files.items()):
                if "retrack" in marks:
                    log_f.write(f"{path}\n")
            log_f.write("\n[is_window_consistence]\n")
            for path, marks in sorted(marked_files.items()):
                if "is_window_consistence" in marks:
                    log_f.write(f"{path}\n")

    print(
        f"扫描 {file_count} 个 JSON；检查 {ann_checked} 条标注；"
        f"标记 {ann_flagged} 条；缺失 MOT 文件 {missing_mot}。"
    )
    print(f"retrack 标记文件数: {retrack_files}")
    print(f"is_window_consistence 标记文件数: {window_files}")


if __name__ == "__main__":
    main()
