#!/usr/bin/env python3
"""Sync selected annotations across sports from the old dataset into the new one."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

TASK_FIELD_RULES: Dict[str, Tuple[str, ...]] = {
    "ScoreboardMultiple": ("question", "answer"),
    "Spatial_Temporal_Grounding": ("question",),
    "Continuous_Actions_Caption": ("question",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync annotations across sports")
    parser.add_argument(
        "--new-root",
        default="/media/zhanghongkai/Data/data-new/output",
        type=Path,
        help="Root of the new dataset (will be modified)",
    )
    parser.add_argument(
        "--old-root",
        default="/media/zhanghongkai/Data/data/output",
        type=Path,
        help="Root of the old dataset (read-only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report changes without writing files",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def normalize_text(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) else str(value) if value is not None else ""


def serialize_answer(value: Any) -> str:
    if isinstance(value, list):
        return "|||".join(normalize_text(item) for item in value)
    if isinstance(value, dict):
        try:
            return json.dumps(value, sort_keys=True)
        except (TypeError, ValueError):
            return str(value)
    return normalize_text(value)


def build_key(annotation: Dict[str, Any], fields: Iterable[str]) -> Tuple[str, ...]:
    key_parts: List[str] = []
    for field in fields:
        if field == "answer":
            key_parts.append(serialize_answer(annotation.get(field)))
        else:
            key_parts.append(normalize_text(annotation.get(field)))
    return tuple(key_parts)


def build_annotation_index(annotations: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]]:
    index: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]] = {}
    for ann in annotations:
        task = ann.get("task_L2")
        fields = TASK_FIELD_RULES.get(task)
        if not fields:
            continue
        key = build_key(ann, fields)
        index[(task, key)] = ann
    return index


def process_annotations(
    new_annotations: List[Dict[str, Any]],
    index: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]],
) -> int:
    """Apply updates in-place and return number of modified annotations."""
    modified = 0
    for idx, ann in enumerate(new_annotations):
        task = ann.get("task_L2")
        fields = TASK_FIELD_RULES.get(task)
        if not fields:
            continue
        key = build_key(ann, fields)
        match = index.get((task, key))
        if not match:
            continue
        updated = json.loads(json.dumps(match))
        updated["reviewed"] = False
        if updated != ann:
            new_annotations[idx] = updated
            modified += 1
    return modified


def process_file(
    new_path: Path,
    new_root: Path,
    old_root: Path,
    dry_run: bool,
) -> Tuple[int, Path | None]:
    """Return (num_annotations_modified, Path when file modified)."""
    rel_path = new_path.relative_to(new_root)
    old_path = old_root / rel_path
    if not old_path.exists():
        return (0, None)

    try:
        new_data = load_json(new_path)
        old_data = load_json(old_path)
    except Exception:
        return (0, None)

    annotations = new_data.get("annotations")
    old_annotations = old_data.get("annotations")
    if not isinstance(annotations, list) or not isinstance(old_annotations, list):
        return (0, None)

    index = build_annotation_index(old_annotations)
    changed = process_annotations(annotations, index)

    if changed and not dry_run:
        dump_json(new_path, new_data)

    return (changed, new_path if changed else None)


if __name__ == "__main__":
    args = parse_args()
    total_ann = 0
    matched_files: List[Path] = []
    for root, _dirs, files in os.walk(args.new_root):
        for filename in files:
            if not filename.endswith(".json"):
                continue
            new_file_path = Path(root) / filename
            ann_count, file_path = process_file(
                new_file_path, args.new_root, args.old_root, args.dry_run
            )
            total_ann += ann_count
            if file_path:
                matched_files.append(file_path)
    suffix = " (dry-run, no files written)" if args.dry_run else ""
    total_files = len(matched_files)
    print(f"Done. Updated {total_ann} annotations across {total_files} files{suffix}.")
    if matched_files:
        print("Matched files:")
        for path in matched_files:
            rel = path.relative_to(args.new_root)
            print(f" - {rel}")
