import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import json
import os
from pathlib import Path

# 配置部分
# 假设 Dataset 目录在 output 的同级目录
DATASET_ROOT = Path(__file__).resolve().parent.parent / 'Dataset'
RESULTS_FILE = Path("spatial_results.json")

class SpatialViewerApp:
    def __init__(self, root, file_list):
        self.root = root
        self.root.title("Spatial Relations Viewer")
        self.root.geometry("1200x800")

        self.file_list = file_list
        self.current_index = 0
        self.current_annotations = []
        self.current_ann_index = 0

        # 主布局
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧图片区域
        self.image_frame = tk.Frame(self.main_frame, width=600, bg='gray')
        self.image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.image_label = tk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)

        # 右侧信息区域
        self.info_frame = tk.Frame(self.main_frame, width=400)
        self.info_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        
        # 顶部导航文件
        self.nav_frame = tk.Frame(self.info_frame)
        self.nav_frame.pack(fill=tk.X, pady=5)
        
        self.prev_file_btn = tk.Button(self.nav_frame, text="<< Prev File", command=self.prev_file)
        self.prev_file_btn.pack(side=tk.LEFT, padx=5)
        
        self.file_label = tk.Label(self.nav_frame, text=f"File: 0 / {len(self.file_list)}")
        self.file_label.pack(side=tk.LEFT, expand=True)
        
        self.next_file_btn = tk.Button(self.nav_frame, text="Next File >>", command=self.next_file)
        self.next_file_btn.pack(side=tk.RIGHT, padx=5)

        # 文本信息
        self.path_label = tk.Label(self.info_frame, text="", wraplength=400, justify=tk.LEFT, fg="blue")
        self.path_label.pack(pady=5, anchor="w", padx=10)

        # Annotation 导航
        self.ann_nav_frame = tk.Frame(self.info_frame)
        self.ann_nav_frame.pack(fill=tk.X, pady=5)

        self.prev_ann_btn = tk.Button(self.ann_nav_frame, text="< Prev Ann", command=self.prev_ann)
        self.prev_ann_btn.pack(side=tk.LEFT, padx=5)

        self.ann_label = tk.Label(self.ann_nav_frame, text="Annotation: 0 / 0")
        self.ann_label.pack(side=tk.LEFT, expand=True)

        self.next_ann_btn = tk.Button(self.ann_nav_frame, text="Next Ann >", command=self.next_ann)
        self.next_ann_btn.pack(side=tk.RIGHT, padx=5)

        # 详细信息显示
        self.detail_text = tk.Text(self.info_frame, wrap=tk.WORD, height=20, font=("Arial", 12))
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 绑定双击事件到 Text 组件
        self.detail_text.bind("<Double-Button-1>", self.open_in_vscode)
        
        # 添加提示标签
        self.hint_label = tk.Label(self.info_frame, text="Double-click above text to open JSON in VS Code", fg="gray", font=("Arial", 9))
        self.hint_label.pack(pady=2)

        # Load first
        self.load_file(0)

    def open_in_vscode(self, event=None):
        if not self.file_list or self.current_index >= len(self.file_list):
            return
            
        file_path = str(self.file_list[self.current_index])
        try:
            # 使用 code 命令打开文件
            # 也可以尝试使用 os.startfile(file_path) 在某些系统上
            # 或者使用 xdg-open 等
            
            # 优先尝试 code 命令
            ret = os.system(f'code "{file_path}"')
            if ret != 0:
                 # 如果 code 命令失败 (例如未在 PATH 中)，打印错误
                 print("Error: 'code' command not found or failed. Please ensure VS Code is in your PATH.")
                 messagebox.showerror("Error", "Could not open in VS Code. Make sure 'code' command is available.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")

    def load_file(self, index):
        if not self.file_list:
            messagebox.showinfo("Info", "No files found in spatial_results.json")
            return

        if index < 0 or index >= len(self.file_list):
            return

        self.current_index = index
        file_path = Path(self.file_list[index])
        
        try:
            data = json.loads(file_path.read_text(encoding='utf-8'))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load json: {e}")
            return

        self.path_label.config(text=str(file_path))
        self.file_label.config(text=f"File: {index + 1} / {len(self.file_list)}")

        # 提取 spatial annotations
        self.current_annotations = self.extract_spatial_annotations(data)
        self.current_ann_index = 0
        
        # 尝试加载图片
        # 假设 output 结构是 .../output/Sport/Event/frames/xx.json
        # 对应的 dataset 可能是 .../Dataset/Sport/Event/frames/xx.jpg
        # 我们根据路径尝试推断
        # 原始：.../output/Athletics_batch_2/Women's_Hammer_Throw/frames/45.json
        # 目标：.../Dataset/Athletics_batch_2/Women's_Hammer_Throw/frames/45.jpg
        
        # 简单的替换策略：把路径中的 'output' 替换为 'Dataset'，并把 .json 换成 .jpg
        # 注意：这取决于你的具体目录结构，可能需要调整
        
        possible_img_path = str(file_path).replace("/output/", "/Dataset/").replace(".json", ".jpg")
        
        # 如果 Dataset 不在 output 同级，或者用了不同的命名，这里可以做更复杂的逻辑
        # 比如使用顶部配置的 DATASET_ROOT
        # 尝试相对路径解析
        try:
            parts = file_path.parts
            if 'output' in parts:
                idx = parts.index('output')
                rel_parts = parts[idx+1:]
                img_path = DATASET_ROOT.joinpath(*rel_parts).with_suffix('.jpg')
                if not img_path.exists():
                     # 尝试 png
                     img_path = img_path.with_suffix('.png')
            else:
                img_path = Path(possible_img_path)
        except:
             img_path = Path(possible_img_path)

        self.show_image(img_path)
        self.show_annotation(0)

    def extract_spatial_annotations(self, obj):
        anns = []
        if isinstance(obj, dict):
            if 'task_L2' in obj or 'task_l2' in obj or 'taskL2' in obj:
                 tl = obj.get('task_L2') or obj.get('task_l2') or obj.get('taskL2') or ''
                 if 'Objects_Spatial_Relationships' in str(tl):
                      anns.append(obj)
            for v in obj.values():
                anns.extend(self.extract_spatial_annotations(v))
        elif isinstance(obj, list):
            for item in obj:
                anns.extend(self.extract_spatial_annotations(item))
        return anns

    def show_image(self, path):
        if not path or not os.path.exists(path):
            self.image_label.config(text=f"Image not found:\n{path}", image='')
            return

        try:
            img = Image.open(path)
            # Resize
            # Get current frame size
            frame_width = self.image_frame.winfo_width() or 800
            frame_height = self.image_frame.winfo_height() or 600
            
            # Keep Aspect Ratio, fit within frame
            img_ratio = img.width / img.height
            frame_ratio = frame_width / frame_height

            if frame_ratio > img_ratio:
                 # Fit to height
                 h_size = frame_height
                 w_size = int(h_size * img_ratio)
            else:
                 # Fit to width
                 w_size = frame_width
                 h_size = int(w_size / img_ratio)
            
            # Avoid error on startup when size is 1
            if w_size <= 0: w_size = 800
            if h_size <= 0: h_size = 600

            img = img.resize((w_size, h_size), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo # Keep reference
        except Exception as e:
            self.image_label.config(text=f"Error loading image:\n{e}", image='')

    def show_annotation(self, index):
        if not self.current_annotations:
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(tk.END, "No Spatial Annotations found.")
            self.ann_label.config(text="Annotation: 0 / 0")
            return
            
        if index < 0 or index >= len(self.current_annotations):
            return

        self.current_ann_index = index
        ann = self.current_annotations[index]
        self.ann_label.config(text=f"Annotation: {index + 1} / {len(self.current_annotations)}")

        content = f"Question:\n{ann.get('question', 'N/A')}\n\n"
        content += f"Answer:\n{ann.get('answer', 'N/A')}\n\n"
        content += f"Task L2: {ann.get('task_L2', 'N/A')}\n"
        
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, content)

    def prev_file(self):
        if self.current_index > 0:
            self.load_file(self.current_index - 1)

    def next_file(self):
        if self.current_index < len(self.file_list) - 1:
            self.load_file(self.current_index + 1)

    def prev_ann(self):
        if self.current_ann_index > 0:
            self.show_annotation(self.current_ann_index - 1)

    def next_ann(self):
        if self.current_ann_index < len(self.current_annotations) - 1:
            self.show_annotation(self.current_ann_index + 1)


if __name__ == "__main__":
    if not RESULTS_FILE.exists():
        print(f"Error: {RESULTS_FILE} not found. Please run find_relations_and_scoreboard.py first.")
    else:
        try:
            files = json.loads(RESULTS_FILE.read_text(encoding='utf-8'))
            root = tk.Tk()
            app = SpatialViewerApp(root, files)
            root.mainloop()
        except Exception as e:
            print(f"Error starting app: {e}")
