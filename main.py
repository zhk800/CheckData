#!/usr/bin/env python3
"""
AI标注审查程序 (macOS 终极修复版 v3)
1. 修复 'update_video_display' 缺失导致的崩溃
2. 修复 Cmd+Right 跳转文件逻辑
3. 恢复进度条拖拽功能
4. 包含 Cmd+B (Mark) 和 Cmd+X (Swap) 功能
"""

import os
import json
import copy
import cv2
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from pathlib import Path
import numpy as np
import platform

class AnnotationReviewer:
    def __init__(self, root):
        self.root = root
        
        # --- 系统检测 ---
        self.is_mac = platform.system() == "Darwin"
        self.mod_key = "Command" if self.is_mac else "Control" 
        self.mod_txt = "Cmd" if self.is_mac else "Ctrl"
        
        self.root.title(f"AI Annotation Review System - {self.mod_txt} Mode")
        self.root.geometry("1200x800")
        
        # Data paths
        self.output_path = Path("../output")
        self.dataset_path = Path("../Dataset")
        self.old_output_path = Path("../../data/output")
        self.old_cache = {}
        self.current_json_path = None
        self.current_old_annotation = None
        self.last_transfer = None
        
        # 当前状态
        self.current_sport = None
        self.current_event = None
        self.current_type = None
        self.current_id = None
        self.current_annotations = []
        self.current_annotation_index = 0
        
        # 视频播放相关
        self.video_cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.play_after_id = None
        self.bbox_paused = False
        self.bbox_frames = []
        self.current_bbox_index = 0
        self.w_paused = False
        self.window_frames = []
        self.current_window_index = 0
        
        # bbox编辑模式相关
        self.bbox_edit_mode = False
        self.editing_bbox = None
        self.bbox_start_point = None
        self.temp_bbox = None
        self.editable_bboxes = []
        self.current_edit_bbox_index = 0
        self.edit_annotation_key = None
        self.active_edit_target = None
        
        # 图像显示相关
        self.current_image = None

        # Cmd+1 撤销：最近一次删除的 annotation 可被 Cmd+Z 恢复
        self.undo_deleted_annotation = None
        self.undo_json_path = None
        self.undo_index = 0

        self.setup_ui()
        self.load_events()
        
    def setup_ui(self):
        """设置用户界面"""
        default_font = ('Arial', 12)
        button_font = ('Arial', 14, 'bold')
        
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 左侧控制面板
        control_frame = ttk.Frame(main_frame, width=350)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        control_frame.pack_propagate(False)
        
        # Event selection
        ttk.Label(control_frame, text="Select Event:", font=default_font).pack(pady=8)
        self.event_var = tk.StringVar()
        self.event_combo = ttk.Combobox(control_frame, textvariable=self.event_var, 
                                       state="readonly", width=35, font=default_font)
        self.event_combo.pack(pady=8)
        self.event_combo.bind("<<ComboboxSelected>>", self.on_event_selected)
        self.event_combo.bind("<Left>", lambda e: "break")
        self.event_combo.bind("<Right>", lambda e: "break")
        
        # Type selection
        ttk.Label(control_frame, text="Data Type:", font=default_font).pack(pady=8)
        self.type_var = tk.StringVar()
        type_frame = ttk.Frame(control_frame)
        type_frame.pack(pady=8)
        ttk.Radiobutton(type_frame, text="Clips", variable=self.type_var, 
                       value="clips", takefocus=False).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="Frames", variable=self.type_var, 
                       value="frames", takefocus=False).pack(side=tk.LEFT, padx=10)
        self.type_var.set("clips")
        
        # ID selection + Load button (same row)
        ttk.Label(control_frame, text="Select ID:", font=default_font).pack(pady=8)
        id_row = ttk.Frame(control_frame)
        id_row.pack(pady=8, fill=tk.X)
        self.id_var = tk.StringVar()
        self.id_combo = ttk.Combobox(id_row, textvariable=self.id_var,
                                    state="readonly", width=28, font=default_font)
        self.id_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.id_combo.bind("<<ComboboxSelected>>", self.on_id_selected)
        self.id_combo.bind("<Left>", lambda e: "break")
        self.id_combo.bind("<Right>", lambda e: "break")
        load_btn = tk.Button(id_row, text="Load (L)", command=self.load_data,
                            font=('Arial', 10), bg='#4CAF50', fg='white',
                            relief='raised', bd=2, height=1, width=8, takefocus=False)
        load_btn.pack(side=tk.LEFT)

        # Annotation info display (uses remaining space)
        ttk.Label(control_frame, text="Current Annotation:", font=('Arial', 14, 'bold')).pack(pady=(15, 8))
        self.annotation_text = tk.Text(control_frame, height=28, wrap=tk.WORD,
                                     font=('Arial', 14), relief='sunken', bd=2, state=tk.DISABLED)
        self.annotation_text.pack(fill=tk.BOTH, expand=True, pady=8)
        self.annotation_text.bind("<Double-Button-1>", self.on_text_double_click)

        # Video frame
        video_frame = ttk.Frame(main_frame)
        video_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.video_canvas = tk.Canvas(video_frame, bg='black')
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        self.video_canvas.bind("<Button-1>", self.on_canvas_click)
        self.video_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.video_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Controls
        controls_frame = ttk.Frame(video_frame)
        controls_frame.pack(fill=tk.X, pady=8)
        
        play_btn = tk.Button(controls_frame, text="▶ Play/Pause", command=self.toggle_play,
                            font=button_font, bg='#4CAF50', fg='white', 
                            relief='raised', bd=2, height=2, width=14, takefocus=False)
        play_btn.pack(side=tk.LEFT, padx=8)
        
        replay_btn = tk.Button(controls_frame, text="🔄 Replay (R)", command=self.replay,
                              font=button_font, bg='#607D8B', fg='white', 
                              relief='raised', bd=2, height=2, width=12, takefocus=False)
        replay_btn.pack(side=tk.LEFT, padx=8)
        
        hint_label = tk.Label(controls_frame, 
                            text=f"💡 Space: Play | ←/→: Nav | {self.mod_txt}+S: Save | {self.mod_txt}+B: Review | {self.mod_txt}+X: Swap Label", 
                            font=('Arial', 10), fg='#666666')
        hint_label.pack(side=tk.LEFT, padx=10)
        
        # Progress
        progress_frame = ttk.Frame(video_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        self.progress_var = tk.DoubleVar()
        self.progress_scale = ttk.Scale(progress_frame, from_=0, to=100, 
                                       orient=tk.HORIZONTAL, variable=self.progress_var,
                                       length=400)
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_progress_change)
        self.progress_scale.bind("<B1-Motion>", self.on_progress_drag)
        self.frame_label = tk.Label(progress_frame, text="0/0", font=('Arial', 12, 'bold'))
        self.frame_label.pack(side=tk.RIGHT, padx=10)

        # ------------------------
        # 快捷键绑定
        # ------------------------
        
        self.root.bind('<space>', self.on_space_key) 
        self.root.bind('<Return>', self.on_enter_key)
        self.root.bind('<r>', self.on_r_key)
        self.root.bind('<R>', self.on_r_key)

        # 导航
        self.root.bind('<Left>', self.on_prev_key)       
        self.root.bind('<Right>', self.on_next_key)      
        self.root.bind(f'<{self.mod_key}-Left>', self.on_prev_file_key)
        self.root.bind(f'<{self.mod_key}-Right>', self.on_next_file_key)
        
        # 功能键
        self.root.bind(f'<{self.mod_key}-s>', self.on_s_key)
        self.root.bind(f'<{self.mod_key}-S>', self.on_s_key)
        
        # Mark Reviewed (Cmd+B)
        self.root.bind(f'<{self.mod_key}-b>', self.on_m_key)
        self.root.bind(f'<{self.mod_key}-B>', self.on_m_key)
        
        # Swap Labels (Cmd+X)
        self.root.bind(f'<{self.mod_key}-x>', self.on_swap_labels_key)
        self.root.bind(f'<{self.mod_key}-X>', self.on_swap_labels_key)
        
        self.root.bind(f'<{self.mod_key}-e>', self.on_e_key)
        self.root.bind(f'<{self.mod_key}-E>', self.on_e_key)
        
        self.root.bind(f'<{self.mod_key}-t>', self.on_t_key)
        self.root.bind(f'<{self.mod_key}-T>', self.on_t_key)
        self.root.bind(f'<{self.mod_key}-Key-1>', self.on_cmd1_key)
        self.root.bind(f'<{self.mod_key}-Key-2>', self.on_cmd2_key)
        self.root.bind(f'<{self.mod_key}-Key-z>', self.on_cmdz_key)
        self.root.bind(f'<{self.mod_key}-Key-Z>', self.on_cmdz_key)
        
        self.root.bind('<F5>', self.on_f5_key)           
        self.root.bind('<Delete>', self.on_delete_key)
        if self.is_mac:
             self.root.bind('<BackSpace>', self.on_delete_key)
        self.root.bind('<l>', self.on_l_key)             
        
        self.root.bind('<b>', self.on_b_key)
        self.root.bind('<B>', self.on_b_key)
        self.root.bind('<w>', self.on_w_key)
        self.root.bind('<W>', self.on_w_key)

        self.root.focus_set()

    # --- 核心逻辑 ---

    def update_video_display(self):
        """更新视频显示with标注 (之前缺失的函数已找回)"""
        if not self.video_cap:
            return
            
        annotation = self.current_annotations[self.current_annotation_index]
        
        # 获取窗口帧范围
        window_start = 0
        if 'Q_window_frame' in annotation:
            window_start = annotation['Q_window_frame'][0]
        elif 'A_window_frame' in annotation and isinstance(annotation['A_window_frame'], list):
            if len(annotation['A_window_frame']) > 0:
                first_window = annotation['A_window_frame'][0]
                if isinstance(first_window, str) and '-' in first_window:
                    window_start = int(first_window.split('-')[0])
                elif isinstance(first_window, (int, float)):
                    window_start = int(first_window)
                    
        # 设置视频到窗口开始帧
        self.current_frame = window_start
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        
        # 开始播放
        if not self.is_playing:
            self.is_playing = True
            self.play_video_with_annotations()

    def _get_ordered_files(self):
        """获取按顺序排列的 (sport, event, data_type, id) 列表，供下一个/上一个文件使用"""
        events = list(self.event_combo['values']) if self.event_combo['values'] is not None else []
        if not events:
            return []

        preferred_type = (self.current_type or self.type_var.get() or 'clips')
        fallback_type = 'frames' if preferred_type == 'clips' else 'clips'
        types_order = [preferred_type, fallback_type]

        ordered_files = []
        for ev in events:
            try:
                sport, event = ev.split('/')
            except Exception:
                continue
            for data_type in types_order:
                type_path = self.output_path / sport / event / data_type
                if not type_path.exists():
                    continue
                ids = []
                for json_file in type_path.glob("*.json"):
                    ids.append(json_file.stem)
                ids.sort(key=lambda x: (0, int(x)) if x.isdigit() else (1, x))
                for _id in ids:
                    ordered_files.append((sport, event, data_type, _id))
        return ordered_files

    def find_next_file(self):
        """切换到下一个 json 文件（不区分 reviewed 状态）"""
        ordered_files = self._get_ordered_files()
        if not ordered_files:
            messagebox.showinfo("Info", "No files found in output")
            return

        try:
            cur_tuple = (self.current_sport, self.current_event, (self.current_type or self.type_var.get()), self.current_id)
        except Exception:
            cur_tuple = None

        start_index = 0
        if cur_tuple and cur_tuple in ordered_files:
            start_index = (ordered_files.index(cur_tuple) + 1) % len(ordered_files)
        target = ordered_files[start_index]

        # 自动保存当前
        try:
            if all([self.current_sport, self.current_event, self.current_id]):
                self.save_data(silent=True)
        except Exception:
            pass

        sport, event, data_type, _id = target
        self.type_var.set(data_type)
        self.event_var.set(f"{sport}/{event}")
        self.on_event_selected()
        self.id_var.set(_id)
        self.on_id_selected()
        self.current_annotation_index = 0
        self.display_current_annotation()

    def find_prev_file(self):
        """切换到上一个 json 文件（不区分 reviewed 状态）"""
        ordered_files = self._get_ordered_files()
        if not ordered_files:
            messagebox.showinfo("Info", "No files found in output")
            return

        try:
            cur_tuple = (self.current_sport, self.current_event, (self.current_type or self.type_var.get()), self.current_id)
        except Exception:
            cur_tuple = None

        start_index = len(ordered_files) - 1
        if cur_tuple and cur_tuple in ordered_files:
            start_index = (ordered_files.index(cur_tuple) - 1) % len(ordered_files)
        target = ordered_files[start_index]

        try:
            if all([self.current_sport, self.current_event, self.current_id]):
                self.save_data(silent=True)
        except Exception:
            pass

        sport, event, data_type, _id = target
        self.type_var.set(data_type)
        self.event_var.set(f"{sport}/{event}")
        self.on_event_selected()
        self.id_var.set(_id)
        self.on_id_selected()
        self.current_annotation_index = 0
        self.display_current_annotation()

    def find_next_unreviewed_file(self, task_filter=None):
        """查找下一个未审核文件"""
        ordered_files = self._get_ordered_files()
        if not ordered_files:
            messagebox.showinfo("Info", "No events available")
            return

        try:
            cur_tuple = (self.current_sport, self.current_event, (self.current_type or self.type_var.get()), self.current_id)
        except Exception:
            cur_tuple = None

        start_index = 0
        if cur_tuple and cur_tuple in ordered_files:
            start_index = ordered_files.index(cur_tuple) + 1

        n = len(ordered_files)
        found = False
        target = None

        def annotation_matches_filter(ann):
            if task_filter and ann.get('task_L2') not in task_filter:
                return False
            return not ann.get('reviewed', False)

        for i in range(n):
            idx = (start_index + i) % n
            sport, event, data_type, _id = ordered_files[idx]
            json_path = self.output_path / sport / event / data_type / f"{_id}.json"
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    annotations = data.get('annotations', [])
                    if any(annotation_matches_filter(ann) for ann in annotations):
                        found = True
                        target = (sport, event, data_type, _id)
                        break
            except Exception:
                continue

        if not found or not target:
            messagebox.showinfo("Info", "No more unreviewed files found")
            return

        try:
            if all([self.current_sport, self.current_event, self.current_id]):
                self.save_data(silent=True)
        except Exception:
            pass

        sport, event, data_type, _id = target
        self.type_var.set(data_type)
        self.event_var.set(f"{sport}/{event}")
        self.on_event_selected()
        self.id_var.set(_id)
        self.on_id_selected()

        for idx, ann in enumerate(self.current_annotations):
            if annotation_matches_filter(ann):
                self.current_annotation_index = idx
                break
        self.display_current_annotation()

    def on_swap_labels_key(self, event):
        """Cmd+X: 交换两个bbox的标签"""
        if not self.current_annotations: return
        
        ann = self.current_annotations[self.current_annotation_index]
        if 'bounding_box' in ann and isinstance(ann['bounding_box'], list) and len(ann['bounding_box']) == 2:
            box1 = ann['bounding_box'][0]
            box2 = ann['bounding_box'][1]
            if isinstance(box1, dict) and isinstance(box2, dict):
                label1 = box1.get('label', '')
                label2 = box2.get('label', '')
                box1['label'] = label2
                box2['label'] = label1
                ann['retrack'] = True
                self.display_current_annotation(refresh_media=False)
                self.refresh_visual()
                messagebox.showinfo("Success", f"Swapped Labels:\nBox 1: {label2}\nBox 2: {label1}")
                return "break"
        
        messagebox.showinfo("Info", "Swap requires exactly 2 bounding boxes")
        return "break"

    # --- 显示逻辑 ---
    def display_current_annotation(self, refresh_media=True):
        if not self.current_annotations:
            self.annotation_text.config(state=tk.NORMAL)
            self.annotation_text.delete(1.0, tk.END)
            self.annotation_text.insert(1.0, "No annotation data")
            self.annotation_text.config(state=tk.DISABLED)
            return
            
        if self.current_annotation_index >= len(self.current_annotations):
            self.current_annotation_index = 0
            
        annotation = self.current_annotations[self.current_annotation_index]
        annotation_key = (self.current_json_path, self.current_annotation_index)
        
        if self.bbox_edit_mode and annotation_key != self.edit_annotation_key:
            self.exit_bbox_edit_mode(notify=False, refresh=False)
        if not self.bbox_edit_mode:
            self.edit_annotation_key = None
            self.active_edit_target = None
            
        self.current_old_annotation = self.find_old_annotation(annotation)
        current_key = (self.current_json_path, self.current_annotation_index)
        if self.last_transfer and self.last_transfer.get('key') != current_key:
            self.last_transfer = None
        
        info_text = f"Annotation {self.current_annotation_index + 1}/{len(self.current_annotations)}\n\n"
        info_text += f"ID: {annotation.get('annotation_id', 'N/A')}\n"
        info_text += f"Task Type: {annotation.get('task_L1', 'N/A')}/{annotation.get('task_L2', 'N/A')}\n"
        info_text += f"Reviewed: {'Yes ✅' if annotation.get('reviewed', False) else 'No ❌'}\n"
        
        if self.bbox_edit_mode and self.active_edit_target:
            info_text += f"🔧 EDITING: {self.describe_edit_target(self.active_edit_target)}\n"
        
        if annotation.get('retrack', False):
            info_text += f"Retrack: 🔄 Yes (bbox modified)\n\n"
        
        if 'question' in annotation:
            info_text += f"Q: {annotation['question']}\n\n"
        elif 'query' in annotation:
            info_text += f"Query: {annotation['query']}\n\n"
            
        if 'answer' in annotation:
            answer = annotation['answer']
            if isinstance(answer, list):
                info_text += f"A: {', '.join(answer)}\n\n"
            else:
                info_text += f"A: {answer}\n\n"
        
        if 'bounding_box' in annotation:
            boxes = annotation['bounding_box']
            if isinstance(boxes, list) and len(boxes) > 0 and isinstance(boxes[0], dict):
                 info_text += "\nLabels:\n"
                 for i, b in enumerate(boxes):
                     info_text += f"  Box {i+1}: {b.get('label', 'N/A')}\n"

        if 'Q_window_frame' in annotation:
            q_window = annotation['Q_window_frame']
            info_text += f"\nQ Window: {q_window[0]}-{q_window[1]}\n"
        if 'A_window_frame' in annotation:
            a_window = annotation['A_window_frame']
            info_text += f"A Window: {a_window}\n"
            
        self.annotation_text.config(state=tk.NORMAL)
        self.annotation_text.delete(1.0, tk.END)
        self.annotation_text.insert(1.0, info_text)
        self.annotation_text.config(state=tk.DISABLED)
        
        if refresh_media:
            if self.current_type == "clips":
                self.find_bbox_frames()
                self.find_window_frames()
                self.update_video_display()
            else:
                self.display_frame_with_annotations()

    # --- 快捷键回调 ---
    def on_space_key(self, event):
        if self.current_type == "clips" and self.video_cap:
            self.toggle_play()
        return "break"
    def on_prev_key(self, event):
        self.prev_annotation()
        return "break"
    def on_next_key(self, event):
        self.next_annotation()
        return "break"
    def on_next_file_key(self, event):
        self.find_next_file()
        return "break"
    def on_prev_file_key(self, event):
        self.find_prev_file()
        return "break"
    def on_cmd1_key(self, event):
        """Cmd+1: 删除当前 annotation"""
        self.delete_current_annotation()
        return "break"
    def on_cmd2_key(self, event):
        """Cmd+2: 删除当前 json 文件"""
        self.delete_current_json_file()
        return "break"
    def on_cmdz_key(self, event):
        """Cmd+Z: 撤销上一次 Cmd+1 删除的 annotation"""
        self.undo_delete_annotation()
        return "break"
    def on_s_key(self, event):
        self.save_data()
        return "break"
    def on_m_key(self, event):
        self.mark_reviewed()
        return "break"
    def on_e_key(self, event):
        self.toggle_bbox_edit_mode() 
        return "break"
    def toggle_bbox_edit_mode(self):
        if not self.current_annotations:
            return
        current_annotation = self.current_annotations[self.current_annotation_index]
        entries = self.build_editable_bbox_list(current_annotation)
        if not entries:
            messagebox.showinfo("Edit Mode", "No editable bounding boxes found.")
            return
        annotation_key = (self.current_json_path, self.current_annotation_index)
        if not self.bbox_edit_mode or annotation_key != self.edit_annotation_key:
            self.stop_playback()
            self.bbox_edit_mode = True
            self.video_canvas.config(cursor="crosshair")
            self.editable_bboxes = entries
            self.current_edit_bbox_index = 0
            self.editing_bbox = self.editable_bboxes[0]
            self.active_edit_target = self.editing_bbox
            self.edit_annotation_key = annotation_key
            self.display_current_annotation(refresh_media=False)
            self.refresh_visual()
            return
        self.current_edit_bbox_index += 1
        if self.current_edit_bbox_index >= len(self.editable_bboxes):
            self.exit_bbox_edit_mode(notify=True)
            self.display_current_annotation(refresh_media=False)
            return
        self.editing_bbox = self.editable_bboxes[self.current_edit_bbox_index]
        self.active_edit_target = self.editing_bbox
        self.temp_bbox = None
        self.refresh_visual()
        self.display_current_annotation(refresh_media=False)

    # --- 辅助方法 ---
    def load_events(self):
        events = []
        if self.output_path.exists():
            for sport_dir in self.output_path.iterdir():
                if sport_dir.is_dir():
                    for event_dir in sport_dir.iterdir():
                        if event_dir.is_dir():
                            events.append(f"{sport_dir.name}/{event_dir.name}")
        self.event_combo['values'] = events

    def on_event_selected(self, event=None):
        selected = self.event_var.get()
        if selected:
            self.current_sport, self.current_event = selected.split('/')
            self.load_ids()
            self.root.focus_set()

    def on_id_selected(self, event=None):
        self.current_id = self.id_var.get()
        try:
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {str(e)}")
        self.root.focus_set()

    def load_ids(self):
        if not self.current_sport or not self.current_event: return
        data_type = self.type_var.get()
        type_path = self.output_path / self.current_sport / self.current_event / data_type
        ids = []
        if type_path.exists():
            for json_file in type_path.glob("*.json"):
                ids.append(json_file.stem)
        ids.sort(key=lambda x: int(x) if x.isdigit() else x)
        self.id_combo['values'] = ids

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing and self.current_type == "clips":
            self.play_video_with_annotations()
        self.root.focus_set()

    def mark_reviewed(self):
        if self.current_annotations and self.current_annotation_index < len(self.current_annotations):
            self.current_annotations[self.current_annotation_index]['reviewed'] = True
            self.display_current_annotation()
            print(f"Marked annotation {self.current_annotation_index} as reviewed.")
        self.root.focus_set()

    def canvas_to_video_coords(self, x, y):
        if not hasattr(self, 'last_frame_info'): return None, None
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        frame_info = getattr(self, 'last_frame_info', {})
        frame_width = frame_info.get('width', 1)
        frame_height = frame_info.get('height', 1)
        display_x = frame_info.get('x', 0)
        display_y = frame_info.get('y', 0)
        display_width = frame_info.get('display_width', canvas_width)
        display_height = frame_info.get('display_height', canvas_height)
        if (x < display_x or x > display_x + display_width or y < display_y or y > display_y + display_height):
            return None, None
        return int((x - display_x) / display_width * frame_width), int((y - display_y) / display_height * frame_height)

    def load_data(self, silent=False):
        if not all([self.current_sport, self.current_event, self.current_id]):
            if not silent: messagebox.showwarning("Warning", "Please select event and ID first")
            return
        self.current_type = self.type_var.get()
        self.stop_playback()
        if self.video_cap: self.video_cap.release(); self.video_cap = None
        self.current_image = None
        json_path = (self.output_path / self.current_sport / self.current_event / self.current_type / f"{self.current_id}.json")
        self.current_json_path = json_path
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_annotations = data.get('annotations', [])
                self.current_annotation_index = 0
            if self.current_type == "clips": self.load_video()
            else: self.load_frame()
            self.display_current_annotation()
            self.find_bbox_frames()
            self.find_window_frames()
        except Exception as e:
            if not silent: messagebox.showerror("Error", f"Failed to load: {str(e)}")

    def load_video(self):
        video_path = None
        for ext in ['.mp4', '.avi', '.mov', '.mkv']:
            candidate_path = (self.dataset_path / self.current_sport / self.current_event / "clips" / f"{self.current_id}{ext}")
            if candidate_path.exists():
                video_path = candidate_path; break
        if not video_path:
            messagebox.showerror("Error", f"Video file not found")
            return
        if self.video_cap: self.video_cap.release()
        self.video_cap = cv2.VideoCapture(str(video_path))
        if not self.video_cap.isOpened():
            messagebox.showerror("Error", f"Cannot open video")
            return
        self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30
        self.current_frame = 0
        self.update_frame_display()

    def load_frame(self):
        frame_path = None
        for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            candidate_path = (self.dataset_path / self.current_sport / self.current_event / "frames" / f"{self.current_id}{ext}")
            if candidate_path.exists():
                frame_path = candidate_path; break
        # Try debug path fallback
        if not frame_path and self.current_annotations:
            try:
                debug_path_str = self.current_annotations[self.current_annotation_index].get('_debug', {}).get('frame_path')
                if debug_path_str:
                    dp = Path(debug_path_str).expanduser()
                    if dp.is_file(): frame_path = dp
            except Exception: pass
        if not frame_path:
            messagebox.showerror("Error", "Image not found")
            return
        self.current_image = cv2.imread(str(frame_path))
        if self.current_image is None:
            messagebox.showerror("Error", "Cannot load image")
            return
        self.display_frame_with_annotations()

    def stop_playback(self):
        self.is_playing = False
        if self.play_after_id:
            self.root.after_cancel(self.play_after_id)
            self.play_after_id = None

    def prev_annotation(self):
        if self.current_annotations and self.current_annotation_index > 0:
            self.current_annotation_index -= 1
            self.display_current_annotation()

    def next_annotation(self):
        if self.current_annotations and self.current_annotation_index < len(self.current_annotations) - 1:
            self.current_annotation_index += 1
            self.display_current_annotation()

    def on_enter_key(self, event):
        if self.current_type == "clips": self.toggle_play()
        return "break"
    def on_r_key(self, event):
        if self.current_type == "clips": self.replay()
        return "break"
    def on_f5_key(self, event):
        self.on_f5()
        return "break"
    def on_delete_key(self, event):
        self.delete_current_annotation()
        return "break"
    def on_l_key(self, event):
        self.load_data()
        return "break"
    def on_b_key(self, event):
        if self.current_type != "clips" or not self.video_cap or not self.bbox_frames: return
        if self.w_paused: self.w_paused = False; self.current_window_index = 0
        if self.bbox_paused:
            self.bbox_paused = False; self.is_playing = True; self.play_video_with_annotations()
        else:
            if self.current_bbox_index < len(self.bbox_frames):
                self.current_frame = self.bbox_frames[self.current_bbox_index]
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                self.update_frame_display()
                self.is_playing = False; self.bbox_paused = True
                self.current_bbox_index = (self.current_bbox_index + 1) % len(self.bbox_frames)
        return "break"
    def on_w_key(self, event):
        if self.current_type != "clips" or not self.video_cap: return
        if self.bbox_paused: self.bbox_paused = False; self.current_bbox_index = 0
        if not self.window_frames: return
        if self.current_window_index < len(self.window_frames):
            target_frame, frame_label = self.window_frames[self.current_window_index]
            self.current_frame = target_frame
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            self.is_playing = False; self.w_paused = True; self.current_w_label = frame_label
            self.update_frame_display()
            self.current_window_index += 1
        else:
            self.w_paused = False; self.current_window_index = 0; self.current_w_label = None
            self.is_playing = True; self.play_video_with_annotations()
        return "break"
    def on_t_key(self, event):
        self.toggle_old_transfer()
        return "break"
    def on_text_double_click(self, event):
        if not all([self.current_sport, self.current_event, self.current_id, self.current_type]): return
        json_path = self.current_json_path
        try:
            import subprocess
            if self.is_mac: subprocess.Popen(["open", str(json_path)]) 
            elif os.name == 'nt': os.startfile(str(json_path))
            else: subprocess.Popen(["xdg-open", str(json_path)])
        except Exception: pass

    def save_data(self, silent=False):
        if not self.current_json_path: return
        try:
            with open(self.current_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['annotations'] = self.current_annotations
            with open(self.current_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if not silent: messagebox.showinfo("Success", "Data saved")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_canvas_click(self, event):
        if not self.bbox_edit_mode: return
        self.stop_playback()
        video_x, video_y = self.canvas_to_video_coords(event.x, event.y)
        if video_x is not None:
            self.bbox_start_point = (video_x, video_y)

    def on_canvas_drag(self, event):
        if not self.bbox_edit_mode or not self.bbox_start_point: return
        video_x, video_y = self.canvas_to_video_coords(event.x, event.y)
        if video_x is not None:
            x1, y1 = self.bbox_start_point
            self.temp_bbox = [min(x1, video_x), min(y1, video_y), max(x1, video_x), max(y1, video_y)]
            self.refresh_visual()

    def on_canvas_release(self, event):
        if not self.bbox_edit_mode or not self.bbox_start_point: return
        video_x, video_y = self.canvas_to_video_coords(event.x, event.y)
        if video_x is not None:
            x1, y1 = self.bbox_start_point
            new_bbox = [min(x1, video_x), min(y1, video_y), max(x1, video_x), max(y1, video_y)]
            if abs(new_bbox[2]-new_bbox[0]) > 5:
                # Update logic
                if self.active_edit_target:
                    tgt_type, idx, _ = self.active_edit_target
                    ann = self.current_annotations[self.current_annotation_index]
                    if tgt_type == 'first': 
                        ann['first_bounding_box'] = new_bbox
                    elif tgt_type == 'bbox_scalar': 
                        ann['bounding_box'] = new_bbox
                    elif tgt_type == 'bbox_dict':
                         ann['bounding_box'][idx]['box'] = new_bbox
                    elif tgt_type == 'bbox_list':
                         ann['bounding_box'][idx] = new_bbox
                    ann['retrack'] = True
                    messagebox.showinfo("Success", f"Bbox updated! Press {self.mod_txt}+S to save.")
            self.bbox_start_point = None; self.temp_bbox = None; self.refresh_visual()

    def update_frame_display(self):
        """更新帧显示 (修复版：防止编辑时视频自动快进)"""
        if self.video_cap:
            # [关键修复]：读取前强制定位到 self.current_frame
            # 否则每次 read() 都会自动跳到下一帧，导致编辑时视频"会动"
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            
            ret, frame = self.video_cap.read()
            if ret:
                annotated_frame = self.draw_annotations_on_frame(frame)
                self.display_frame_on_canvas(annotated_frame)
                
                # 更新界面显示
                progress = (self.current_frame / self.total_frames) * 100 if self.total_frames > 0 else 0
                self.progress_var.set(progress)
                self.frame_label.config(text=f"{self.current_frame}/{self.total_frames}")

    def play_video_with_annotations(self):
        if not self.is_playing or not self.video_cap: return
        ret, frame = self.video_cap.read()
        if not ret or self.current_frame >= self.total_frames:
            self.replay(); return
        annotated_frame = self.draw_annotations_on_frame(frame)
        self.display_frame_on_canvas(annotated_frame)
        progress = (self.current_frame / self.total_frames) * 100 if self.total_frames > 0 else 0
        self.progress_var.set(progress)
        self.frame_label.config(text=f"{self.current_frame}/{self.total_frames}")
        self.current_frame += 1
        if self.is_playing:
            delay = int(1000 / self.fps) if self.fps else 33
            self.play_after_id = self.root.after(delay, self.play_video_with_annotations)

    def draw_annotations_on_frame(self, frame):
        """在帧上绘制标注"""
        if not self.current_annotations: return frame
        annotated_frame = frame.copy()
        annotation = self.current_annotations[self.current_annotation_index]
        self.draw_window_markers(annotated_frame, annotation)
        self.draw_bounding_boxes(annotated_frame, annotation)
        return annotated_frame

    def draw_window_markers(self, frame, annotation):
        """绘制窗口开始和结束标记"""
        if self.w_paused and hasattr(self, 'current_w_label') and self.current_w_label:
            display_text = self.current_w_label.replace("_", " ")
            if "BEGIN" in self.current_w_label or "POINT" in self.current_w_label:
                cv2.rectangle(frame, (15, 15), (400, 120), (0, 255, 0), -1)
                cv2.rectangle(frame, (10, 10), (405, 125), (0, 200, 0), 8)
                cv2.putText(frame, display_text, (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 0), 4)
                if (self.current_frame // 2) % 2 == 0:
                    cv2.rectangle(frame, (12, 12), (403, 123), (255, 255, 255), 3)
            elif "END" in self.current_w_label:
                cv2.rectangle(frame, (15, 15), (350, 120), (0, 0, 255), -1)
                cv2.rectangle(frame, (10, 10), (355, 125), (0, 0, 200), 8)
                cv2.putText(frame, display_text, (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 4)
                if (self.current_frame // 2) % 2 == 0:
                    cv2.rectangle(frame, (12, 12), (353, 123), (255, 255, 255), 3)
        else:
            if 'Q_window_frame' in annotation:
                start, end = annotation['Q_window_frame']
                if self.current_frame == start:
                    cv2.rectangle(frame, (15, 15), (350, 120), (0, 255, 0), -1)
                    cv2.rectangle(frame, (10, 10), (355, 125), (0, 200, 0), 8)
                    cv2.putText(frame, "Q BEGIN", (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 0), 4)
                elif self.current_frame == end:
                    cv2.rectangle(frame, (15, 15), (320, 120), (0, 0, 255), -1)
                    cv2.rectangle(frame, (10, 10), (325, 125), (0, 0, 200), 8)
                    cv2.putText(frame, "Q END", (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 4)

    def draw_bounding_boxes(self, frame, annotation):
        """绘制各种类型的边界框"""
        if 'bounding_box' in annotation:
            boxes = annotation['bounding_box']
            if isinstance(boxes, list):
                if len(boxes) == 4 and all(isinstance(coord, (int, float)) for coord in boxes):
                    self.draw_single_bbox(frame, boxes, 'Object 1', (0, 255, 255))
                else:
                    for i, box_info in enumerate(boxes):
                        if isinstance(box_info, dict) and 'box' in box_info:
                            box = box_info['box']
                            label = box_info.get('label', f'Object {i+1}')
                            self.draw_single_bbox(frame, box, label, (0, 255, 255))
                        elif isinstance(box_info, list) and len(box_info) == 4:
                            self.draw_single_bbox(frame, box_info, f'Object {i+1}', (0, 255, 255))
        if 'first_bounding_box' in annotation:
            box = annotation['first_bounding_box']
            self.draw_single_bbox(frame, box, 'Tracked Object', (255, 0, 0))
        if 'tracking_bboxes' in annotation and 'mot_file' in annotation['tracking_bboxes']:
            self.draw_mot_boxes(frame, annotation['tracking_bboxes']['mot_file'])

    def draw_single_bbox(self, frame, box, label, color):
        try:
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        except Exception: pass

    def draw_mot_boxes(self, frame, mot_file):
        mot_path = Path(mot_file)
        if mot_path.exists():
            try:
                with open(mot_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) >= 6:
                            frame_id = int(parts[0])
                            if frame_id == self.current_frame + 1:
                                x, y, w, h = map(float, parts[2:6])
                                x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                                cv2.putText(frame, f"ID:{parts[1]}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            except Exception: pass

    def display_frame_on_canvas(self, frame):
        cw = self.video_canvas.winfo_width()
        ch = self.video_canvas.winfo_height()
        if cw <= 1: return
        h, w = frame.shape[:2]
        scale = min(cw/w, ch/h)
        nw, nh = int(w*scale), int(h*scale)
        resized = cv2.resize(frame, (nw, nh))
        if self.bbox_edit_mode and self.temp_bbox:
             t = self.temp_bbox
             ts = [int(c * scale) for c in t]
             cv2.rectangle(resized, (ts[0], ts[1]), (ts[2], ts[3]), (255, 255, 0), 3)
             cv2.putText(resized, "EDITING...", (ts[0], ts[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        frame_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        from PIL import Image, ImageTk
        image = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(image)
        self.video_canvas.delete("all")
        x, y = (cw-nw)//2, (ch-nh)//2
        self.video_canvas.create_image(x, y, anchor=tk.NW, image=photo)
        self.video_canvas.image = photo
        self.last_frame_info = {'width':w, 'height':h, 'x':x, 'y':y, 'display_width':nw, 'display_height':nh}

    # --- 恢复的功能 ---
    def on_progress_change(self, event):
        """恢复进度条点击跳转"""
        if self.video_cap and self.total_frames > 0:
            progress = self.progress_var.get()
            new_frame = int((progress / 100) * self.total_frames)
            self.current_frame = new_frame
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            self.update_frame_display()

    def on_progress_drag(self, event):
        """恢复进度条拖拽"""
        if self.video_cap and self.total_frames > 0:
            progress = self.progress_var.get()
            new_frame = int((progress / 100) * self.total_frames)
            self.current_frame = new_frame
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            if self.is_playing: self.is_playing = False
            self.update_frame_display()

    def replay(self): 
        if self.current_type=="clips": 
            self.current_frame=0; self.video_cap.set(cv2.CAP_PROP_POS_FRAMES,0); 
            if self.is_playing: self.play_video_with_annotations()
    def on_f5(self): self.load_data()
    def delete_current_annotation(self):
        if not self.current_annotations:
            messagebox.showinfo("Info", "No annotation to delete")
            return
        self.undo_deleted_annotation = copy.deepcopy(self.current_annotations[self.current_annotation_index])
        self.undo_json_path = self.current_json_path
        self.undo_index = self.current_annotation_index
        self.current_annotations.pop(self.current_annotation_index)
        self.save_data(silent=True)
        self.load_data()

    def undo_delete_annotation(self):
        """恢复上一次 Cmd+1 删除的 annotation（仅当当前仍是同一文件时有效）"""
        if self.undo_deleted_annotation is None or self.undo_json_path is None:
            messagebox.showinfo("Info", "Nothing to undo")
            return
        if self.current_json_path != self.undo_json_path:
            messagebox.showinfo("Info", "Undo only works in the same file. Please switch back to that file.")
            return
        if not self.undo_json_path.exists():
            messagebox.showinfo("Info", "The file was removed, cannot undo.")
            return
        try:
            with open(self.undo_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            annotations = data.get('annotations', [])
            idx = min(self.undo_index, len(annotations))
            annotations.insert(idx, self.undo_deleted_annotation)
            data['annotations'] = annotations
            with open(self.undo_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.undo_deleted_annotation = None
        self.undo_json_path = None
        self.undo_index = 0
        self.load_data()
        self.current_annotation_index = idx
        self.display_current_annotation()
        messagebox.showinfo("Success", "Annotation restored")

    def delete_current_json_file(self):
        """删除当前打开的 json 文件，并切换到下一个文件。"""
        if not self.current_json_path or not self.current_json_path.exists():
            messagebox.showinfo("Info", "No JSON file loaded")
            return
        if not messagebox.askyesno("Confirm", f"Delete this file?\n{self.current_json_path.name}\nThis cannot be undone."):
            return
        path = self.current_json_path
        self.find_next_file()
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        if self.current_json_path == path:
            self.load_events()
            events = list(self.event_combo['values']) if self.event_combo['values'] else []
            if events:
                self.event_var.set(events[0])
                self.on_event_selected()
                ids = list(self.id_combo['values']) if self.id_combo['values'] else []
                if ids:
                    self.id_var.set(ids[0])
                    self.on_id_selected()

    def toggle_old_transfer(self): pass
    def find_bbox_frames(self): 
        self.bbox_frames = []
        if not self.current_annotations or self.current_type != "clips": return
        ann = self.current_annotations[self.current_annotation_index]
        if 'first_bounding_box' in ann:
             start = ann.get('Q_window_frame', [0])[0]
             self.bbox_frames.append(start)
        self.bbox_frames.sort()
    def find_window_frames(self): 
        self.window_frames = []
        if not self.current_annotations: return
        ann = self.current_annotations[self.current_annotation_index]
        if 'Q_window_frame' in ann:
            s, e = ann['Q_window_frame']
            self.window_frames.extend([(s, "Q_BEGIN"), (e, "Q_END")])
    def build_editable_bbox_list(self, ann):
        entries = []
        if 'first_bounding_box' in ann: entries.append(('first', None, 'first_bounding_box'))
        if 'bounding_box' in ann: 
            if isinstance(ann['bounding_box'], list) and len(ann['bounding_box'])==4 and isinstance(ann['bounding_box'][0], (int, float)):
                 entries.append(('bbox_scalar', None, 'bounding_box'))
            elif isinstance(ann['bounding_box'], list):
                 for i, b in enumerate(ann['bounding_box']):
                     entries.append(('bbox_dict' if isinstance(b, dict) else 'bbox_list', i, f'bbox[{i}]'))
        return entries
    def describe_edit_target(self, t): return t[2]
    def exit_bbox_edit_mode(self, notify, refresh): 
        self.bbox_edit_mode=False; self.video_canvas.config(cursor="")
    def find_old_annotation(self, ann): return None
    def refresh_visual(self): 
        if self.current_type=="clips": self.update_frame_display()
        else: self.display_frame_with_annotations()
    def display_frame_with_annotations(self):
        if self.current_image is not None: self.display_frame_on_canvas(self.draw_annotations_on_frame(self.current_image))

def main():
    root = tk.Tk()
    app = AnnotationReviewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()