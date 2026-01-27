#!/usr/bin/env python3
"""
AI标注审查程序
用于可视化和审核AI标注数据中的bbox和window_frame
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

class AnnotationReviewer:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Annotation Review System")
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
        self.current_type = None  # "clips" or "frames"
        self.current_id = None
        self.current_annotations = []
        self.current_annotation_index = 0
        
        # 视频播放相关
        self.video_cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.play_after_id = None  # 存储定时器ID
        self.bbox_paused = False   # B键暂停状态
        self.bbox_frames = []      # 包含bbox的帧列表
        self.current_bbox_index = 0  # 当前bbox帧索引
        self.w_paused = False      # W键暂停状态
        self.window_frames = []    # 窗口帧列表（开始和结束帧）
        self.current_window_index = 0  # 当前窗口帧索引
        
        # bbox编辑模式相关变量
        self.bbox_edit_mode = False    # 是否在bbox编辑模式
        self.editing_bbox = None       # 当前编辑的bbox（'first_bounding_box' 或 ('bounding_box', index)）
        self.bbox_start_point = None   # bbox绘制的起始点
        self.temp_bbox = None          # 临时bbox坐标
        self.editable_bboxes = []      # 可编辑bbox目标列表
        self.current_edit_bbox_index = 0
        self.edit_annotation_key = None
        self.active_edit_target = None
        
        # 图像显示相关
        self.current_image = None
        
        self.setup_ui()
        self.load_events()
        
    def setup_ui(self):
        """设置用户界面"""
        # 设置默认字体
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
        
        # Type selection
        ttk.Label(control_frame, text="Data Type:", font=default_font).pack(pady=8)
        self.type_var = tk.StringVar()
        type_frame = ttk.Frame(control_frame)
        type_frame.pack(pady=8)
        ttk.Radiobutton(type_frame, text="Clips", variable=self.type_var, 
                   value="clips", style="Large.TRadiobutton", command=self.on_type_changed).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="Frames", variable=self.type_var, 
                   value="frames", style="Large.TRadiobutton", command=self.on_type_changed).pack(side=tk.LEFT, padx=10)
        self.type_var.set("clips")
        
        # ID selection
        ttk.Label(control_frame, text="Select ID:", font=default_font).pack(pady=8)
        self.id_var = tk.StringVar()
        self.id_combo = ttk.Combobox(control_frame, textvariable=self.id_var, 
                                    state="readonly", width=35, font=default_font)
        self.id_combo.pack(pady=8)
        self.id_combo.bind("<<ComboboxSelected>>", self.on_id_selected)
        
        # Load button
        load_btn = tk.Button(control_frame, text="Load Data (L)", command=self.load_data,
                            font=button_font, bg='#4CAF50', fg='white', 
                            relief='raised', bd=3, height=2, width=14)
        load_btn.pack(pady=15)
        
        # Reload button
        reload_btn = tk.Button(control_frame, text="🔄 Reload (F5)", command=self.on_f5,
                              font=button_font, bg='#2196F3', fg='white', 
                              relief='raised', bd=3, height=2, width=14)
        reload_btn.pack(pady=5)
        
        # Annotation info display
        ttk.Label(control_frame, text="Current Annotation:", font=('Arial', 14, 'bold')).pack(pady=(25, 8))
        self.annotation_text = tk.Text(control_frame, height=12, wrap=tk.WORD, 
                                     font=('Arial', 14), relief='sunken', bd=2)
        self.annotation_text.pack(fill=tk.BOTH, expand=True, pady=8)
        
        # 绑定双击事件打开VSCode编辑
        self.annotation_text.bind("<Double-Button-1>", self.on_text_double_click)
        
        # Annotation navigation
        nav_frame = ttk.Frame(control_frame)
        nav_frame.pack(pady=15)
        prev_btn = tk.Button(nav_frame, text="← Previous (P)", command=self.prev_annotation,
                            font=button_font, bg='#2196F3', fg='white', 
                            relief='raised', bd=2, height=2, width=14)
        prev_btn.pack(side=tk.LEFT, padx=8)
        next_btn = tk.Button(nav_frame, text="Next (N) →", command=self.next_annotation,
                            font=button_font, bg='#2196F3', fg='white', 
                            relief='raised', bd=2, height=2, width=14)
        next_btn.pack(side=tk.LEFT, padx=8)
        
        # Review status
        review_frame = ttk.Frame(control_frame)
        review_frame.pack(pady=15)
        review_btn = tk.Button(review_frame, text="✓ Mark Reviewed (M)", command=self.mark_reviewed,
                              font=button_font, bg='#FF9800', fg='white', 
                              relief='raised', bd=2, height=2, width=18)
        review_btn.pack(side=tk.LEFT, padx=5)
        save_btn = tk.Button(review_frame, text="💾 Save (S)", command=self.save_data,
                            font=button_font, bg='#9C27B0', fg='white', 
                            relief='raised', bd=2, height=2, width=12)
        save_btn.pack(side=tk.LEFT, padx=5)
        # Next unreviewed button
        next_unreviewed_btn = tk.Button(review_frame, text="➡ Next Unreviewed (U)", command=self.find_next_unreviewed_file,
                         font=button_font, bg='#E91E63', fg='white',
                         relief='raised', bd=2, height=2, width=18)
        next_unreviewed_btn.pack(side=tk.LEFT, padx=5)
        
        # 右侧视频显示区域
        video_frame = ttk.Frame(main_frame)
        video_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 视频画布
        self.video_canvas = tk.Canvas(video_frame, bg='black')
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标事件用于bbox编辑
        self.video_canvas.bind("<Button-1>", self.on_canvas_click)
        self.video_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.video_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # 视频控制
        controls_frame = ttk.Frame(video_frame)
        controls_frame.pack(fill=tk.X, pady=8)
        
        play_btn = tk.Button(controls_frame, text="▶ Play/Pause (Enter)", command=self.toggle_play,
                            font=button_font, bg='#4CAF50', fg='white', 
                            relief='raised', bd=2, height=2, width=18)
        play_btn.pack(side=tk.LEFT, padx=8)
        
        replay_btn = tk.Button(controls_frame, text="🔄 Replay (R)", command=self.replay,
                              font=button_font, bg='#607D8B', fg='white', 
                              relief='raised', bd=2, height=2, width=14)
        replay_btn.pack(side=tk.LEFT, padx=8)
        
        # Keyboard shortcuts hint
        hint_label = tk.Label(controls_frame, text="💡 Space: Play/Pause | B: bbox | W: window | E: Edit bbox | F5: Reload | Del: Delete annotation", 
                              font=('Arial', 11), fg='#666666')
        hint_label.pack(side=tk.LEFT, padx=20)
        
        # 绑定键盘事件
        self.root.bind('<KeyPress-space>', self.on_space_key)  # 空格键播放/暂停
        self.root.bind('<KeyPress-b>', self.on_b_key)  # B键跳转bbox帧
        self.root.bind('<KeyPress-B>', self.on_b_key)
        self.root.bind('<KeyPress-w>', self.on_w_key)
        self.root.bind('<KeyPress-W>', self.on_w_key)  # 大写W也支持
        self.root.bind('<KeyPress-u>', self.on_u_key)  # U键跳到下一个未审核文件（Shift+U 过滤特定任务）
        self.root.bind('<KeyPress-U>', self.on_u_key)
        self.root.bind('<F5>', self.on_f5_key)  # F5键重新加载数据
        self.root.bind('<KeyPress-e>', self.on_e_key)  # E键切换bbox编辑模式
        self.root.bind('<KeyPress-E>', self.on_e_key)
        self.root.bind('<KeyPress-l>', self.on_l_key)  # L键加载数据
        self.root.bind('<KeyPress-L>', self.on_l_key)
        self.root.bind('<KeyPress-p>', self.on_p_key)  # P键上一个标注
        self.root.bind('<KeyPress-P>', self.on_p_key)
        self.root.bind('<KeyPress-n>', self.on_n_key)  # N键下一个标注
        self.root.bind('<KeyPress-N>', self.on_n_key)
        self.root.bind('<KeyPress-m>', self.on_m_key)  # M键标记已审核
        self.root.bind('<KeyPress-M>', self.on_m_key)
        self.root.bind('<KeyPress-r>', self.on_r_key)  # R键重播视频
        self.root.bind('<KeyPress-R>', self.on_r_key)
        self.root.bind('<KeyPress-s>', self.on_s_key)  # S键保存
        self.root.bind('<KeyPress-S>', self.on_s_key)
        self.root.bind('<KeyPress-t>', self.on_t_key)  # T键同步旧数据
        self.root.bind('<KeyPress-T>', self.on_t_key)
        self.root.bind('<Return>', self.on_enter_key)  # Enter键播放/暂停
        self.root.bind('<Delete>', self.on_delete_key)  # Delete键删除当前标注并重新加载
        self.root.focus_set()
        
        # 进度条
        progress_frame = ttk.Frame(video_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_scale = ttk.Scale(progress_frame, from_=0, to=100, 
                                       orient=tk.HORIZONTAL, variable=self.progress_var,
                                       length=400)
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_progress_change)
        self.progress_scale.bind("<B1-Motion>", self.on_progress_drag)  # 拖拽时实时更新
        
        self.frame_label = tk.Label(progress_frame, text="0/0", font=('Arial', 12, 'bold'))
        self.frame_label.pack(side=tk.RIGHT, padx=10)
        
    def load_events(self):
        """加载可用的事件列表"""
        events = []
        if self.output_path.exists():
            for sport_dir in self.output_path.iterdir():
                if sport_dir.is_dir():
                    for event_dir in sport_dir.iterdir():
                        if event_dir.is_dir():
                            events.append(f"{sport_dir.name}/{event_dir.name}")
        
        self.event_combo['values'] = events
        
    def on_event_selected(self, event=None):
        """事件选择回调"""
        selected = self.event_var.get()
        if selected:
            self.current_sport, self.current_event = selected.split('/')
            self.load_ids()

    def on_type_changed(self):
        """数据类型切换回调：刷新当前事件的ID列表"""
        self.load_ids()
            
    def load_ids(self):
        """加载当前事件下的ID列表"""
        if not self.current_sport or not self.current_event:
            return
            
        data_type = self.type_var.get()
        type_path = self.output_path / self.current_sport / self.current_event / data_type
        
        ids = []
        if type_path.exists():
            for json_file in type_path.glob("*.json"):
                ids.append(json_file.stem)
        
        ids.sort(key=lambda x: int(x) if x.isdigit() else x)
        self.id_combo['values'] = ids

        # 当切换类型时，尝试保留当前ID，否则默认选中第一个
        current_id = self.id_var.get()
        if current_id in ids:
            self.id_var.set(current_id)
        elif ids:
            self.id_var.set(ids[0])
        else:
            self.id_var.set("")
        
    def on_id_selected(self, event=None):
        """ID选择回调"""
        self.current_id = self.id_var.get()
        # 当用户选择了ID后，自动加载并显示数据
        try:
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load selected ID: {str(e)}")
        
    def on_canvas_click(self, event):
        """鼠标点击事件处理"""
        if not self.bbox_edit_mode or not self.current_annotations:
            return
            
        # 确保视频暂停
        self.stop_playback()
            
        # 转换鼠标坐标到视频坐标
        video_x, video_y = self.canvas_to_video_coords(event.x, event.y)
        if video_x is None:
            return
            
        self.bbox_start_point = (video_x, video_y)
        print(f"Start bbox at: ({video_x}, {video_y})")
        if self.bbox_edit_mode and self.editing_bbox:
            self.editing_bbox = self.editable_bboxes[self.current_edit_bbox_index]
            self.display_current_annotation(refresh_media=False)
        
    def on_canvas_drag(self, event):
        """鼠标拖拽事件处理"""
        if not self.bbox_edit_mode or not self.bbox_start_point:
            return

        self.stop_playback()
        video_x, video_y = self.canvas_to_video_coords(event.x, event.y)
        if video_x is None:
            return

        x1, y1 = self.bbox_start_point
        self.temp_bbox = [min(x1, video_x), min(y1, video_y), max(x1, video_x), max(y1, video_y)]
        self.refresh_visual()

    def on_canvas_release(self, event):
        """鼠标释放事件处理"""
        if not self.bbox_edit_mode or not self.bbox_start_point:
            return

        video_x, video_y = self.canvas_to_video_coords(event.x, event.y)
        if video_x is None:
            return

        x1, y1 = self.bbox_start_point
        new_bbox = [min(x1, video_x), min(y1, video_y), max(x1, video_x), max(y1, video_y)]

        if abs(new_bbox[2] - new_bbox[0]) < 10 or abs(new_bbox[3] - new_bbox[1]) < 10:
            print("Bbox too small, ignoring")
            self.bbox_start_point = None
            self.temp_bbox = None
            return

        annotation = self.current_annotations[self.current_annotation_index]
        target_entry = None
        if self.bbox_edit_mode and self.active_edit_target:
            target_entry = self.active_edit_target
        updated_label = None

        if target_entry:
            target_type, idx, label = target_entry
            if target_type == 'first':
                annotation['first_bounding_box'] = new_bbox
            elif target_type == 'bbox_scalar':
                annotation['bounding_box'] = new_bbox
            elif target_type == 'bbox_dict':
                boxes = annotation.get('bounding_box')
                if isinstance(boxes, list) and idx is not None and idx < len(boxes):
                    boxes[idx]['box'] = new_bbox
            elif target_type == 'bbox_list':
                boxes = annotation.get('bounding_box')
                if isinstance(boxes, list) and idx is not None and idx < len(boxes):
                    boxes[idx] = new_bbox
            updated_label = label
            annotation['retrack'] = True
        else:
            if 'first_bounding_box' in annotation:
                annotation['first_bounding_box'] = new_bbox
                updated_label = 'first_bounding_box'
            elif 'bounding_box' in annotation and annotation['bounding_box']:
                boxes = annotation['bounding_box']
                if isinstance(boxes[0], dict):
                    boxes[0]['box'] = new_bbox
                else:
                    boxes[0] = new_bbox
                updated_label = 'bounding_box[0]'
            else:
                annotation['first_bounding_box'] = new_bbox
                updated_label = 'first_bounding_box'
            annotation['retrack'] = True

        self.bbox_start_point = None
        self.temp_bbox = None
        self.refresh_visual()

        label_text = updated_label or 'bounding_box'
        messagebox.showinfo(
            "Success",
            f"Updated {label_text}!\nNew bbox: {new_bbox}\nRetrack flag added: true\n\nDon't forget to save (S key)",
        )

    def on_e_key(self, event):
        """E键事件处理 - 轮换bbox编辑目标"""
        if not self.current_annotations:
            return

        current_annotation = self.current_annotations[self.current_annotation_index]
        entries = self.build_editable_bbox_list(current_annotation)

        if not entries:
            messagebox.showinfo(
                "Edit Mode",
                "Current annotation has no editable bounding boxes.\nAdd 'first_bounding_box' or 'bounding_box' before using E.",
            )
            return

        annotation_key = (self.current_json_path, self.current_annotation_index)

        if not self.bbox_edit_mode or annotation_key != self.edit_annotation_key:
            # 进入编辑模式或重新定位到当前标注
            self.stop_playback()
            self.bbox_edit_mode = True
            self.video_canvas.config(cursor="crosshair")
            self.editable_bboxes = entries
            self.current_edit_bbox_index = 0
            self.editing_bbox = self.editable_bboxes[0]
            self.active_edit_target = self.editing_bbox
            self.edit_annotation_key = annotation_key
            label = self.describe_edit_target(self.editing_bbox)
            messagebox.showinfo(
                "Edit Mode",
                f"Bbox Edit Mode ON\nCurrent target: {label}\n\nUse mouse drag to edit. Press E again to jump to the next target; after the last target, E will exit.",
            )
            self.refresh_visual()
            self.display_current_annotation(refresh_media=False)
            return

        # 已在编辑模式下，切换到下一个目标或退出
        self.current_edit_bbox_index += 1
        if self.current_edit_bbox_index >= len(self.editable_bboxes):
            self.exit_bbox_edit_mode(notify=True)
            self.display_current_annotation(refresh_media=False)
            return

        self.editing_bbox = self.editable_bboxes[self.current_edit_bbox_index]
        self.active_edit_target = self.editing_bbox
        label = self.describe_edit_target(self.editing_bbox)
        self.temp_bbox = None
        self.refresh_visual()

        label_text = updated_label or 'bounding_box'
        messagebox.showinfo(
            "Success",
            f"Updated {label_text}!\nNew bbox: {new_bbox}\nRetrack flag added: true\n\nDon't forget to save (S key)",
        )
        
    def canvas_to_video_coords(self, canvas_x, canvas_y):
        """将画布坐标转换为视频坐标"""
        if not hasattr(self, 'last_frame_info'):
            return None, None
            
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return None, None
            
        # 获取上次显示的帧信息
        frame_info = getattr(self, 'last_frame_info', {})
        frame_width = frame_info.get('width', 1)
        frame_height = frame_info.get('height', 1)
        display_x = frame_info.get('x', 0)
        display_y = frame_info.get('y', 0)
        display_width = frame_info.get('display_width', canvas_width)
        display_height = frame_info.get('display_height', canvas_height)
        
        # 检查点击是否在视频区域内
        if (canvas_x < display_x or canvas_x > display_x + display_width or
            canvas_y < display_y or canvas_y > display_y + display_height):
            return None, None
            
        # 转换坐标
        relative_x = canvas_x - display_x
        relative_y = canvas_y - display_y
        
        video_x = int((relative_x / display_width) * frame_width)
        video_y = int((relative_y / display_height) * frame_height)
        
        return video_x, video_y
        """重新加载当前文件的最新数据"""
        if not all([self.current_sport, self.current_event, self.current_id, self.current_type]):
            messagebox.showwarning("Warning", "No file currently loaded to reload")
            return
            
        # 保存当前标注索引
        current_index = self.current_annotation_index
        
        try:
            # 重新加载数据
            self.load_data()
            
            # 恢复到之前的标注索引（如果可能）
            if current_index < len(self.current_annotations):
                self.current_annotation_index = current_index
                self.display_current_annotation()
            
            print(f"Reloaded: {self.current_sport}/{self.current_event}/{self.current_type}/{self.current_id}.json")
            messagebox.showinfo("Success", f"Data reloaded successfully!\nFile: {self.current_sport}/{self.current_event}/{self.current_type}/{self.current_id}.json")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload data: {str(e)}")
            
    def load_data(self):
        """加载标注数据"""
        if not all([self.current_sport, self.current_event, self.current_id]):
            messagebox.showwarning("Warning", "Please select event and ID first")
            return
            
        self.current_type = self.type_var.get()

        # 切换文件前确保停止播放并释放资源
        self.stop_playback()
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self.current_image = None
        
        # 加载JSON标注数据
        json_path = (self.output_path / self.current_sport / 
                    self.current_event / self.current_type / f"{self.current_id}.json")
        self.current_json_path = json_path
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_annotations = data.get('annotations', [])
                self.current_annotation_index = 0
                
            # 加载对应的媒体文件
            if self.current_type == "clips":
                self.load_video()
            else:
                self.load_frame()
                
            self.display_current_annotation()
            self.find_bbox_frames()  # 查找包含bbox的帧
            self.find_window_frames()  # 查找窗口帧
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
            
    def load_video(self):
        """加载视频文件"""
        video_path = None
        
        # 尝试不同的视频格式
        for ext in ['.mp4', '.avi', '.mov', '.mkv']:
            candidate_path = (self.dataset_path / self.current_sport / 
                            self.current_event / "clips" / f"{self.current_id}{ext}")
            if candidate_path.exists():
                video_path = candidate_path
                break
                
        if not video_path:
            messagebox.showerror("Error", f"Video file not found: {self.current_sport}/{self.current_event}/clips/{self.current_id}")
            return
            
        if self.video_cap:
            self.video_cap.release()
            
        self.video_cap = cv2.VideoCapture(str(video_path))
        if not self.video_cap.isOpened():
            messagebox.showerror("Error", f"Cannot open video file: {video_path}")
            return
            
        self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30
        self.current_frame = 0
        
        self.update_frame_display()
        
    def load_frame(self):
        """加载单帧图片"""
        frame_path = None
        
        # 尝试不同的图片格式
        for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            candidate_path = (self.dataset_path / self.current_sport / 
                            self.current_event / "frames" / f"{self.current_id}{ext}")
            if candidate_path.exists():
                frame_path = candidate_path
                break
                
        # 如果默认路径不存在，尝试从标注中的 _debug.frame_path 读取
        if not frame_path and self.current_annotations:
            try:
                current_annotation = self.current_annotations[self.current_annotation_index]
                debug_info = current_annotation.get('_debug', {})
                debug_path_str = debug_info.get('frame_path')
                if debug_path_str:
                    debug_path = Path(debug_path_str).expanduser()
                    if debug_path.is_file():
                        frame_path = debug_path
            except Exception as e:
                print(f"Failed to use debug frame path: {e}")

        if not frame_path:
            messagebox.showerror("Error", f"Image file not found: {self.current_sport}/{self.current_event}/frames/{self.current_id}")
            return
            
        self.current_image = cv2.imread(str(frame_path))
        if self.current_image is None:
            messagebox.showerror("Error", f"Cannot load image: {frame_path}")
            return
            
        self.display_frame_with_annotations()

    def get_old_json_path(self):
        """构造旧数据集中对应文件的路径"""
        if not all([self.current_sport, self.current_event, self.current_id, self.current_type]):
            return None
        return (self.old_output_path / self.current_sport /
                self.current_event / self.current_type / f"{self.current_id}.json")

    def load_old_annotations(self):
        """加载旧数据中的annotations并执行缓存"""
        old_json_path = self.get_old_json_path()
        if old_json_path is None or not old_json_path.exists():
            return None
        if old_json_path in self.old_cache:
            return self.old_cache[old_json_path]
        try:
            with open(old_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.old_cache[old_json_path] = data
                return data
        except Exception:
            self.old_cache[old_json_path] = None
            return None

    def find_old_annotation(self, annotation):
        """在旧数据中查找同任务且已审核的annotation"""
        old_data = self.load_old_annotations()
        if not old_data:
            return None
        annotations = old_data.get('annotations', [])
        target_task = annotation.get('task_L2')
        if not target_task:
            return None
        candidates = [
            ann for ann in annotations
            if ann.get('task_L2') == target_task and ann.get('reviewed', False)
        ]
        if not candidates:
            return None

        target_id = annotation.get('annotation_id')
        if target_id is not None:
            for ann in candidates:
                if ann.get('annotation_id') == target_id:
                    return ann

        target_question = str(annotation.get('question', '')).strip()
        if target_question:
            for ann in candidates:
                if str(ann.get('question', '')).strip() == target_question:
                    return ann

        return candidates[0]
        
    def display_current_annotation(self, refresh_media=True):
        """显示当前标注信息"""
        if not self.current_annotations:
            self.annotation_text.delete(1.0, tk.END)
            self.annotation_text.insert(1.0, "No annotation data")
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
        
        # Display annotation info
        info_text = f"Annotation {self.current_annotation_index + 1}/{len(self.current_annotations)}\n\n"
        info_text += f"ID: {annotation.get('annotation_id', 'N/A')}\n"
        info_text += f"Task Type: {annotation.get('task_L1', 'N/A')}/{annotation.get('task_L2', 'N/A')}\n"
        info_text += f"Reviewed: {'Yes' if annotation.get('reviewed', False) else 'No'}\n"
        info_text += f"exist_old: {'true' if self.current_old_annotation else 'false'}\n"
        if self.bbox_edit_mode and self.active_edit_target:
            info_text += f"Editing Target: {self.describe_edit_target(self.active_edit_target)}\n"
        
        # 显示retrack状态
        if annotation.get('retrack', False):
            info_text += f"Retrack: 🔄 Yes (bbox modified)\n\n"
        else:
            info_text += f"Retrack: No\n\n"
        
        if 'question' in annotation:
            info_text += f"Question: {annotation['question']}\n\n"
        elif 'query' in annotation:
            info_text += f"Query: {annotation['query']}\n\n"
            
        if 'answer' in annotation:
            answer = annotation['answer']
            if isinstance(answer, list):
                info_text += f"Answer: {', '.join(answer)}\n\n"
            else:
                info_text += f"Answer: {answer}\n\n"
                
        # Window frame info
        if 'Q_window_frame' in annotation:
            q_window = annotation['Q_window_frame']
            info_text += f"Question Window: {q_window[0]}-{q_window[1]}\n"
        if 'A_window_frame' in annotation:
            a_window = annotation['A_window_frame']
            info_text += f"Answer Window: {a_window}\n"
            
        self.annotation_text.delete(1.0, tk.END)
        self.annotation_text.insert(1.0, info_text)
        
        if refresh_media:
            # 更新可视化
            if self.current_type == "clips":
                self.find_bbox_frames()  # 重新查找bbox帧
                self.find_window_frames()  # 重新查找窗口帧
                self.update_video_display()
            else:
                self.display_frame_with_annotations()

    def toggle_old_transfer(self):
        """切换是否应用旧数据中的annotation内容"""
        if not self.current_annotations:
            messagebox.showinfo("Info", "当前无可用标注")
            return

        idx = self.current_annotation_index
        current_annotation = self.current_annotations[idx]

        current_key = (self.current_json_path, idx)

        # 若已经应用过旧数据，则撤销到原始内容
        if self.last_transfer and self.last_transfer.get('key') == current_key and self.last_transfer.get('applied'):
            self.current_annotations[idx] = copy.deepcopy(self.last_transfer['original'])
            self.last_transfer['applied'] = False
            messagebox.showinfo("Undo", "已撤销本次一键替换")
            self.display_current_annotation()
            return

        old_annotation = self.current_old_annotation or self.find_old_annotation(current_annotation)
        if not old_annotation:
            messagebox.showinfo("Info", "旧数据不存在同任务且已审核的标注")
            return

        self.last_transfer = {
            'key': current_key,
            'annotation_idx': idx,
            'original': copy.deepcopy(current_annotation),
            'applied': False,
        }

        new_annotation = copy.deepcopy(old_annotation)
        new_annotation['reviewed'] = current_annotation.get('reviewed', False)
        self.current_annotations[idx] = new_annotation
        self.last_transfer['applied'] = True
        messagebox.showinfo("Success", "已应用旧数据内容（按 T 再次撤销）")
        self.display_current_annotation()
            
    def update_video_display(self):
        """更新视频显示with标注"""
        if not self.video_cap:
            return
            
        annotation = self.current_annotations[self.current_annotation_index]
        
        # 获取窗口帧范围
        window_start, window_end = 0, self.total_frames - 1
        if 'Q_window_frame' in annotation:
            window_start, window_end = annotation['Q_window_frame']
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
            
    def play_video_with_annotations(self):
        """播放视频并显示标注"""
        if not self.is_playing or not self.video_cap:
            return
            
        ret, frame = self.video_cap.read()
        if not ret or self.current_frame >= self.total_frames:
            if self.is_playing:  # 只有在播放状态下才循环播放
                self.replay()  # 循环播放
            return
            
        # 绘制标注
        annotated_frame = self.draw_annotations_on_frame(frame)
        
        # 显示帧
        self.display_frame_on_canvas(annotated_frame)

        # 更新播放状态
        progress = (self.current_frame / self.total_frames) * 100 if self.total_frames > 0 else 0
        self.progress_var.set(progress)
        self.frame_label.config(text=f"{self.current_frame}/{self.total_frames}")

        self.current_frame += 1

        if self.is_playing:
            delay = int(1000 / self.fps) if self.fps else 33
            self.play_after_id = self.root.after(delay, self.play_video_with_annotations)
        
    def refresh_visual(self):
        """根据当前数据类型刷新画面"""
        if self.current_type == "clips":
            self.redraw_current_frame()
        else:
            self.display_frame_with_annotations()

    def build_editable_bbox_list(self, annotation):
        """生成当前标注中可编辑bbox的列表"""
        entries = []
        first_box = annotation.get('first_bounding_box')
        if isinstance(first_box, (list, tuple)) and len(first_box) == 4:
            entries.append(('first', None, 'first_bounding_box'))

        boxes = annotation.get('bounding_box')
        if isinstance(boxes, list):
            if len(boxes) == 4 and all(isinstance(coord, (int, float)) for coord in boxes):
                entries.append(('bbox_scalar', None, 'bounding_box'))
            else:
                for idx, box in enumerate(boxes):
                    if isinstance(box, dict) and isinstance(box.get('box'), list):
                        entries.append(('bbox_dict', idx, f'bounding_box[{idx}]'))
                    elif isinstance(box, list) and len(box) == 4 and all(isinstance(coord, (int, float)) for coord in box):
                        entries.append(('bbox_list', idx, f'bounding_box[{idx}]'))
        return entries

    def describe_edit_target(self, entry):
        return entry[2] if entry else 'N/A'

    def exit_bbox_edit_mode(self, notify=False, refresh=True):
        """退出bbox编辑模式并清理状态"""
        self.bbox_edit_mode = False
        self.editable_bboxes = []
        self.current_edit_bbox_index = 0
        self.edit_annotation_key = None
        self.active_edit_target = None
        self.bbox_start_point = None
        self.temp_bbox = None
        self.video_canvas.config(cursor="")

        if notify:
            messagebox.showinfo("Edit Mode", "Bbox Edit Mode OFF")
        if refresh:
            self.refresh_visual()
    
    def stop_playback(self):
        """停止视频播放并取消定时器"""
        self.is_playing = False
        if self.play_after_id:
            self.root.after_cancel(self.play_after_id)
            self.play_after_id = None
    
    def redraw_current_frame(self):
        """重新绘制当前帧（不推进视频）"""
        if not self.video_cap:
            return
            
        # 保存当前位置
        current_pos = self.video_cap.get(cv2.CAP_PROP_POS_FRAMES)
        
        # 回到当前帧位置并读取
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.video_cap.read()
        
        if ret:
            # 绘制标注
            annotated_frame = self.draw_annotations_on_frame(frame)
            # 显示帧
            self.display_frame_on_canvas(annotated_frame)
        
        # 恢复位置
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
        
    def draw_annotations_on_frame(self, frame):
        """在帧上绘制标注"""
        annotated_frame = frame.copy()
        
        if not self.current_annotations:
            return annotated_frame
            
        annotation = self.current_annotations[self.current_annotation_index]
        
        # 绘制窗口标记
        self.draw_window_markers(annotated_frame, annotation)
        
        # 绘制bounding boxes
        self.draw_bounding_boxes(annotated_frame, annotation)
        
        return annotated_frame
        
    def draw_window_markers(self, frame, annotation):
        """绘制窗口开始和结束标记"""
        # 如果在W键导航模式，显示当前导航的标签
        if self.w_paused and hasattr(self, 'current_w_label') and self.current_w_label:
            # 显示当前W键导航要显示的标签
            display_text = self.current_w_label.replace("_", " ")
            print(f"Drawing marker: frame={self.current_frame}, label={display_text}")
            
            if "BEGIN" in self.current_w_label or "POINT" in self.current_w_label:
                # 绿色开始标记
                cv2.rectangle(frame, (15, 15), (400, 120), (0, 255, 0), -1)
                cv2.rectangle(frame, (10, 10), (405, 125), (0, 200, 0), 8)
                cv2.putText(frame, display_text, (25, 75), 
                           cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 0), 4)
                # 闪烁效果
                if (self.current_frame // 2) % 2 == 0:
                    cv2.rectangle(frame, (12, 12), (403, 123), (255, 255, 255), 3)
            elif "END" in self.current_w_label:
                # 红色结束标记
                cv2.rectangle(frame, (15, 15), (350, 120), (0, 0, 255), -1)
                cv2.rectangle(frame, (10, 10), (355, 125), (0, 0, 200), 8)
                cv2.putText(frame, display_text, (25, 75), 
                           cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 4)
                # 闪烁效果
                if (self.current_frame // 2) % 2 == 0:
                    cv2.rectangle(frame, (12, 12), (353, 123), (255, 255, 255), 3)
        else:
            # 非W键导航模式：显示常规的窗口标记
            if 'Q_window_frame' in annotation:
                start, end = annotation['Q_window_frame']
                if self.current_frame == start:
                    cv2.rectangle(frame, (15, 15), (350, 120), (0, 255, 0), -1)
                    cv2.rectangle(frame, (10, 10), (355, 125), (0, 200, 0), 8)
                    cv2.putText(frame, "Q BEGIN", (25, 75), 
                               cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 0), 4)
                elif self.current_frame == end:
                    cv2.rectangle(frame, (15, 15), (320, 120), (0, 0, 255), -1)
                    cv2.rectangle(frame, (10, 10), (325, 125), (0, 0, 200), 8)
                    cv2.putText(frame, "Q END", (25, 75), 
                               cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 4)
                           
    def draw_bounding_boxes(self, frame, annotation):
        """绘制边界框"""
        # 静态边界框
        if 'bounding_box' in annotation:
            boxes = annotation['bounding_box']
            if (
                isinstance(boxes, list)
                and len(boxes) == 4
                and all(isinstance(coord, (int, float)) for coord in boxes)
            ):
                self.draw_single_bbox(frame, boxes, 'Object 1', (0, 255, 255))
            else:
                for i, box_info in enumerate(boxes):
                    if isinstance(box_info, dict) and 'box' in box_info:
                        box = box_info['box']
                        label = box_info.get('label', f'Object {i+1}')
                        self.draw_single_bbox(frame, box, label, (0, 255, 255))
                    elif isinstance(box_info, list) and len(box_info) == 4:
                        self.draw_single_bbox(frame, box_info, f'Object {i+1}', (0, 255, 255))
                    
        # 第一帧边界框
        if 'first_bounding_box' in annotation:
            box = annotation['first_bounding_box']
            self.draw_single_bbox(frame, box, 'Tracked Object', (255, 0, 0))
            
        # MOT追踪框
        if 'tracking_bboxes' in annotation and 'mot_file' in annotation['tracking_bboxes']:
            self.draw_mot_boxes(frame, annotation['tracking_bboxes']['mot_file'])
            
    def draw_single_bbox(self, frame, box, label, color):
        """绘制单个边界框"""
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                   
    def draw_mot_boxes(self, frame, mot_file):
        """绘制MOT追踪框"""
        mot_path = Path(mot_file)
        if mot_path.exists():
            try:
                with open(mot_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) >= 6:
                            frame_id = int(parts[0])
                            if frame_id == self.current_frame + 1:  # MOT格式帧从1开始
                                x, y, w, h = map(float, parts[2:6])
                                x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                                cv2.putText(frame, f"ID:{parts[1]}", (x1, y1 - 10),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            except Exception as e:
                print(f"读取MOT文件失败: {e}")
                
    def display_frame_with_annotations(self):
        """显示带标注的单帧图片"""
        if self.current_image is None:
            return
            
        annotated_frame = self.current_image.copy()
        
        if self.current_annotations:
            annotation = self.current_annotations[self.current_annotation_index]
            
            # 绘制边界框
            if 'bounding_box' in annotation:
                boxes = annotation['bounding_box']
                if (
                    isinstance(boxes, list)
                    and len(boxes) == 4
                    and all(isinstance(coord, (int, float)) for coord in boxes)
                ):
                    self.draw_single_bbox(annotated_frame, boxes, 'Object 1', (0, 255, 255))
                else:
                    for i, box_info in enumerate(boxes):
                        if isinstance(box_info, dict) and 'box' in box_info:
                            box = box_info['box']
                            label = box_info.get('label', f'Object {i+1}')
                            self.draw_single_bbox(annotated_frame, box, label, (0, 255, 255))
                        elif isinstance(box_info, list) and len(box_info) == 4:
                            self.draw_single_bbox(annotated_frame, box_info, f'Object {i+1}', (0, 255, 255))
            if 'first_bounding_box' in annotation:
                self.draw_single_bbox(annotated_frame, annotation['first_bounding_box'], 'Tracked Object', (255, 0, 0))
                        
        self.display_frame_on_canvas(annotated_frame)
        
    def display_frame_on_canvas(self, frame):
        """在画布上显示帧"""
        # 获取画布尺寸
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
            
        # 调整帧尺寸以适应画布
        frame_height, frame_width = frame.shape[:2]
        scale = min(canvas_width / frame_width, canvas_height / frame_height)
        
        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)
        
        resized_frame = cv2.resize(frame, (new_width, new_height))
        
        # 在编辑模式下绘制临时bbox
        if self.bbox_edit_mode and self.temp_bbox:
            temp_bbox_scaled = [
                int(self.temp_bbox[0] * scale),
                int(self.temp_bbox[1] * scale),
                int(self.temp_bbox[2] * scale),
                int(self.temp_bbox[3] * scale)
            ]
            cv2.rectangle(resized_frame, (temp_bbox_scaled[0], temp_bbox_scaled[1]), 
                         (temp_bbox_scaled[2], temp_bbox_scaled[3]), (255, 255, 0), 3)
            cv2.putText(resized_frame, "EDITING...", (temp_bbox_scaled[0], temp_bbox_scaled[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        
        # 转换颜色空间并显示
        frame_rgb = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        from PIL import Image, ImageTk
        image = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(image)
        
        self.video_canvas.delete("all")
        
        # 居中显示
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        self.video_canvas.create_image(x, y, anchor=tk.NW, image=photo)
        self.video_canvas.image = photo  # 保持引用
        
        # 保存帧信息用于坐标转换
        self.last_frame_info = {
            'width': frame_width,
            'height': frame_height,
            'x': x,
            'y': y,
            'display_width': new_width,
            'display_height': new_height
        }
        
    def toggle_play(self):
        """切换播放/暂停"""
        self.is_playing = not self.is_playing
        if self.is_playing and self.current_type == "clips":
            self.play_video_with_annotations()
            
    def replay(self):
        """重新播放"""
        if self.current_type == "clips" and self.video_cap:
            annotation = self.current_annotations[self.current_annotation_index] if self.current_annotations else {}
            window_start = 0
            if 'Q_window_frame' in annotation:
                window_start = annotation['Q_window_frame'][0]
                
            self.current_frame = window_start
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            # 只有当前已经在播放状态时才继续播放
            if self.is_playing:
                self.play_video_with_annotations()
            
    def on_progress_drag(self, event):
        """进度条拖拽时实时更新"""
        if self.video_cap and self.total_frames > 0:
            progress = self.progress_var.get()
            new_frame = int((progress / 100) * self.total_frames)
            self.current_frame = new_frame
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            # 暂停播放以便用户查看当前帧
            if self.is_playing:
                self.is_playing = False
            self.update_frame_display()
            
    def on_progress_change(self, event):
        """进度条变化回调"""
        if self.video_cap and self.total_frames > 0:
            progress = self.progress_var.get()
            new_frame = int((progress / 100) * self.total_frames)
            self.current_frame = new_frame
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            self.update_frame_display()
            
    def update_frame_display(self):
        """更新帧显示"""
        if self.video_cap:
            ret, frame = self.video_cap.read()
            if ret:
                annotated_frame = self.draw_annotations_on_frame(frame)
                self.display_frame_on_canvas(annotated_frame)
                
                progress = (self.current_frame / self.total_frames) * 100 if self.total_frames > 0 else 0
                self.progress_var.set(progress)
                self.frame_label.config(text=f"{self.current_frame}/{self.total_frames}")
                
    def prev_annotation(self):
        """上一个标注"""
        if self.current_annotations and self.current_annotation_index > 0:
            self.current_annotation_index -= 1
            self.display_current_annotation()
            
    def next_annotation(self):
        """下一个标注"""
        if self.current_annotations and self.current_annotation_index < len(self.current_annotations) - 1:
            self.current_annotation_index += 1
            self.display_current_annotation()
            
    def mark_reviewed(self):
        """标记当前标注为已审核"""
        if self.current_annotations and self.current_annotation_index < len(self.current_annotations):
            self.current_annotations[self.current_annotation_index]['reviewed'] = True
            self.display_current_annotation()
            messagebox.showinfo("Info", "Marked as reviewed")
            
    def save_data(self, silent=False):
        """保存标注数据"""
        if not all([self.current_sport, self.current_event, self.current_id, self.current_type]):
            messagebox.showwarning("Warning", "No data to save")
            return
            
        json_path = (self.output_path / self.current_sport / 
                    self.current_event / self.current_type / f"{self.current_id}.json")
        
        try:
            # Read original data
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Update annotation data
            data['annotations'] = self.current_annotations
            
            # Save data
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            if not silent:
                messagebox.showinfo("Success", "Data saved")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def delete_current_annotation(self):
        """删除当前标注并重新加载当前文件"""
        if not self.current_annotations:
            messagebox.showwarning("Warning", "No annotation to delete")
            return

        idx = self.current_annotation_index
        total = len(self.current_annotations)
        self.current_annotations.pop(idx)

        # 持久化更改但不弹出保存成功提示
        self.save_data(silent=True)

        # 重新加载数据，相当于按下L键
        self.load_data()

        messagebox.showinfo(
            "Deleted",
            f"Deleted annotation {min(idx + 1, total)}/{total}. File reloaded.",
        )
    
    def find_bbox_frames(self):
        """查找当前标注中包含bbox的帧"""
        self.bbox_frames = []
        self.current_bbox_index = 0
        
        if not self.current_annotations or self.current_type != "clips":
            return
            
        annotation = self.current_annotations[self.current_annotation_index]
        
        # 检查first_bounding_box对应的第一帧
        if 'first_bounding_box' in annotation:
            window_start = 0
            # 优先使用Q_window_frame的开始帧
            if 'Q_window_frame' in annotation:
                window_start = annotation['Q_window_frame'][0]
            # 如果没有Q_window_frame但有A_window_frame，使用A_window_frame的第一个窗口开始帧
            elif 'A_window_frame' in annotation:
                a_windows = annotation['A_window_frame']
                if isinstance(a_windows, list) and len(a_windows) > 0:
                    first_window = a_windows[0]
                    if isinstance(first_window, str) and '-' in first_window:
                        window_start = int(first_window.split('-')[0])
                    elif isinstance(first_window, (int, float)):
                        window_start = int(first_window)
            self.bbox_frames.append(window_start)
        
        # 检查MOT文件中的帧
        if 'tracking_bboxes' in annotation and 'mot_file' in annotation['tracking_bboxes']:
            mot_path = Path(annotation['tracking_bboxes']['mot_file'])
            if mot_path.exists():
                try:
                    with open(mot_path, 'r') as f:
                        frames_with_bbox = set()
                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) >= 6:
                                frame_id = int(parts[0]) - 1  # MOT格式从1开始，转换为0开始
                                frames_with_bbox.add(frame_id)
                        
                        # 添加到bbox_frames列表（去重并排序）
                        for frame_id in sorted(frames_with_bbox):
                            if frame_id not in self.bbox_frames:
                                self.bbox_frames.append(frame_id)
                except Exception as e:
                    print(f"Failed to read MOT file: {e}")
        
        # Sort bbox frames
        self.bbox_frames.sort()
        print(f"Found bbox frames: {self.bbox_frames}")
    
    def find_window_frames(self):
        """查找当前标注中的窗口帧（开始和结束帧）"""
        self.window_frames = []
        self.current_window_index = 0
        
        if not self.current_annotations or self.current_type != "clips":
            return
            
        annotation = self.current_annotations[self.current_annotation_index]
        
        # 1. 检查Q窗口
        if 'Q_window_frame' in annotation:
            start, end = annotation['Q_window_frame']
            self.window_frames.append((start, "Q_BEGIN"))
            if start != end:
                self.window_frames.append((end, "Q_END"))
            
        # 2. 检查A窗口
        if 'A_window_frame' in annotation:
            a_windows = annotation['A_window_frame']
            if isinstance(a_windows, list):
                for i, window in enumerate(a_windows):
                    if isinstance(window, str) and '-' in window:
                        start, end = map(int, window.split('-'))
                        self.window_frames.append((start, f"A{i+1}_BEGIN"))
                        if start != end:
                            self.window_frames.append((end, f"A{i+1}_END"))
                    elif isinstance(window, (int, float)):
                        frame_num = int(window)
                        self.window_frames.append((frame_num, f"A{i+1}_POINT"))
        
        print(f"Window frames sequence: {self.window_frames}")
    
    def on_space_key(self, event):
        """空格键事件处理 - 播放/暂停"""
        if self.current_type == "clips" and self.video_cap:
            self.toggle_play()
    
    def on_b_key(self, event):
        """B键事件处理 - 跳转bbox帧"""
        if self.current_type != "clips" or not self.video_cap or not self.bbox_frames:
            return
        
        # 重置W键状态
        if self.w_paused:
            self.w_paused = False
            self.current_window_index = 0
        
        if self.bbox_paused:
            # Resume playback
            self.bbox_paused = False
            self.is_playing = True
            self.play_video_with_annotations()
            print("Resume loop playback (B key)")
        else:
            # Jump to next bbox frame and pause
            if self.current_bbox_index < len(self.bbox_frames):
                target_frame = self.bbox_frames[self.current_bbox_index]
                self.current_frame = target_frame
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                self.update_frame_display()
                
                # Pause playback
                self.is_playing = False
                self.bbox_paused = True
                
                print(f"Jump to frame {target_frame} (bbox frame {self.current_bbox_index + 1}/{len(self.bbox_frames)})")
                
                # Move to next bbox frame index
                self.current_bbox_index = (self.current_bbox_index + 1) % len(self.bbox_frames)
    
    def on_w_key(self, event):
        """W键事件处理 - 跳转窗口帧"""
        if self.current_type != "clips" or not self.video_cap:
            return
        
        # 重置B键状态
        if self.bbox_paused:
            self.bbox_paused = False
            self.current_bbox_index = 0
        
        if not self.window_frames:
            return
            
        if self.current_window_index < len(self.window_frames):
            # 跳转到当前索引对应的窗口帧
            target_frame, frame_label = self.window_frames[self.current_window_index]
            self.current_frame = target_frame
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            
            # 暂停播放
            self.is_playing = False
            self.w_paused = True
            
            # 设置当前要显示的标签（供draw_window_markers使用）
            self.current_w_label = frame_label
            
            print(f"W key: Jump to frame {target_frame} ({frame_label}) - step {self.current_window_index + 1}/{len(self.window_frames)}")
            
            # 更新显示
            self.update_frame_display()
            
            # 移动到下一步
            self.current_window_index += 1
        else:
            # 所有窗口帧都访问完了，恢复播放
            self.w_paused = False
            self.current_window_index = 0
            self.current_w_label = None
            self.is_playing = True
            self.play_video_with_annotations()
            print("W key: All frames visited, resume playback")
    
    def on_l_key(self, event):
        """L键事件处理 - 加载数据"""
        self.load_data()
    
    def on_f5_key(self, event):
        """F5键事件处理 - 重新加载数据"""
        self.on_f5()
    
    def on_f5(self, event=None):
        """F5: 重新加载当前文件"""
        print(f"Reloaded: {self.get_relative_path(self.json_path)}")
        self.load_data(self.json_path)
        
    def on_p_key(self, event):
        """P键事件处理 - 上一个标注"""
        self.prev_annotation()
    
    def on_n_key(self, event):
        """N键事件处理 - 下一个标注"""
        self.next_annotation()
    
    def on_r_key(self, event):
        """R键事件处理 - 重播视频"""
        if self.current_type == "clips" and self.video_cap:
            self.is_playing = True  # 手动重播时开始播放
            self.replay()
    
    def on_m_key(self, event):
        """M键事件处理 - 标记已审核"""
        self.mark_reviewed()
    
    def on_s_key(self, event):
        """S键事件处理 - 保存数据"""
        self.save_data()

    def on_delete_key(self, event):
        """Delete键事件处理 - 删除当前标注并重新加载文件"""
        self.delete_current_annotation()

    def on_t_key(self, event):
        """T键事件处理 - 同步旧版annotation"""
        self.toggle_old_transfer()
    
    def on_enter_key(self, event):
        """Enter键事件处理 - 播放/暂停"""
        if self.current_type == "clips" and self.video_cap:
            self.toggle_play()

    def on_text_double_click(self, event):
        """双击文本区域事件处理 - 打开VSCode编辑JSON文件"""
        if not all([self.current_sport, self.current_event, self.current_id, self.current_type]):
            messagebox.showwarning("Warning", "No file loaded to edit")
            return
            
        # 构建当前JSON文件路径
        json_path = (self.output_path / self.current_sport / 
                    self.current_event / self.current_type / f"{self.current_id}.json")
        
        if not json_path.exists():
            messagebox.showerror("Error", f"File not found: {json_path}")
            return
            
        try:
            import subprocess
            import os
            
            # 尝试使用VSCode打开文件
            if os.name == 'nt':  # Windows
                subprocess.Popen(["code", str(json_path)], shell=True)
            else:  # Linux/Mac
                subprocess.Popen(["code", str(json_path)])
            
            print(f"Opening {json_path} in VSCode...")
            
            # 显示提示信息
            messagebox.showinfo("VSCode", f"Opening file in VSCode:\n{json_path}\n\nAfter editing, you can reload the data with 'L' key.")
            
        except FileNotFoundError:
            # VSCode未安装或不在PATH中
            try:
                # 尝试使用系统默认的文本编辑器
                if os.name == 'nt':  # Windows
                    os.startfile(str(json_path))
                else:  # Linux/Mac
                    subprocess.Popen(["xdg-open", str(json_path)])
                    
                messagebox.showinfo("Editor", f"Opening file with system default editor:\n{json_path}\n\nAfter editing, you can reload the data with 'L' key.")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}\n\nYou can manually open: {json_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open VSCode: {str(e)}")

    def on_u_key(self, event):
        """U键事件处理 - 跳转到下一个包含未审核标注的文件"""
        shift_pressed = bool(event.state & 0x1) if event else False
        if shift_pressed:
            task_filter = {"Spatial_Temporal_Grounding", "Continuous_Actions_Caption"}
            self.find_next_unreviewed_file(task_filter=task_filter)
        else:
            self.find_next_unreviewed_file()

    def annotation_matches_filter(self, annotation, task_filter):
        if task_filter and annotation.get('task_L2') not in task_filter:
            return False
        return not annotation.get('reviewed', False)

    def find_next_unreviewed_file(self, task_filter=None):
        """查找并跳转到下一个未审核文件（支持 clips 与 frames 自动回退）

        - 优先使用当前选择的数据类型（`self.current_type` 或单选框）。
        - 如果当前类型在某事件下没有文件，自动回退到另一类型。
        - 载入目标文件时，先设置数据类型，再设置事件与ID，保证列表联动正常。
        """
        events = list(self.event_combo['values']) if self.event_combo['values'] is not None else []
        if not events:
            messagebox.showinfo("Info", "没有可用事件")
            return

        # 当前首选类型与备用类型
        preferred_type = (self.current_type or self.type_var.get() or 'clips')
        fallback_type = 'frames' if preferred_type == 'clips' else 'clips'
        types_order = [preferred_type, fallback_type]

        # 构建有序文件列表：(sport, event, data_type, id)
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
                # Sort numeric IDs numerically and fallback to lexicographic for mixed cases
                ids.sort(key=lambda x: (0, int(x)) if x.isdigit() else (1, x))
                for _id in ids:
                    ordered_files.append((sport, event, data_type, _id))

        if not ordered_files:
            messagebox.showinfo("Info", "在输出目录未找到任何文件")
            return

        # 确定当前位置（如果当前文件在列表中，则从其后一个开始）
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

        # 从当前位置循环查找未审核文件
        for i in range(n):
            idx = (start_index + i) % n
            sport, event, data_type, _id = ordered_files[idx]
            json_path = self.output_path / sport / event / data_type / f"{_id}.json"
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    annotations = data.get('annotations', [])
                    if any(self.annotation_matches_filter(ann, task_filter) for ann in annotations):
                        found = True
                        target = (sport, event, data_type, _id)
                        break
            except Exception:
                # 忽略不可读文件
                continue

        if not found or not target:
            messagebox.showinfo("Info", "没有下一个未审核文件")
            return

        # 静默保存当前数据（若当前选择完整）
        try:
            if all([self.current_sport, self.current_event, self.current_id, (self.current_type or self.type_var.get())]):
                self.save_data()
        except Exception:
            pass

        # 加载目标文件：先设置类型，再设置事件与ID
        sport, event, data_type, _id = target
        self.type_var.set(data_type)
        self.event_var.set(f"{sport}/{event}")
        self.on_event_selected()
        self.id_var.set(_id)
        self.on_id_selected()

        # 跳到第一个未审核标注
        for idx, ann in enumerate(self.current_annotations):
            if self.annotation_matches_filter(ann, task_filter):
                self.current_annotation_index = idx
                break
        self.display_current_annotation()
            
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'video_cap') and self.video_cap:
            self.video_cap.release()

def main():
    root = tk.Tk()
    app = AnnotationReviewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
