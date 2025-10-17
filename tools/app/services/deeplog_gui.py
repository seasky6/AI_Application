import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk  # 添加图片处理支持
from tools.app.services.model_training.training_gui import TrainingGUI
from tools.app.services.model_prediction.inference_gui import InferenceGUI
from tools.app.services.data_processing.processing_gui import ProcessingGUI


class DeepLogGUI:
    """主GUI - 通过模块化方式集成各子GUI"""
    def __init__(self, root):
        self.root = root
        self.root.title("Deeplog Offline")
        self.root.geometry("1400x1000")

        # 设置深色主题颜色
        self.bg_color = "#1e1e1e"            # 深灰色背景
        self.fg_color = "#ffffff"            # 白色前景
        self.accent_color = "#007acc"        # 蓝色强调色
        self.tab_hover_color = "#3d3d3d"     # 选项卡悬停颜色
        self.tab_selected_color = "#005a9e"  # 选项卡选中颜色（比主强调色稍深）
        self.tab_border_color = "#555555"    # 选项卡边框颜色

        # 配置根窗口背景
        self.root.configure(bg=self.bg_color)

        # 设置深色主题样式
        self.setup_dark_theme()

        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建标题和logo框架 - 修改为水平布局
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        self.create_header_with_logo(header_frame)

        # 创建主标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 创建各功能标签页
        self.create_processing_tab()
        self.create_training_tab()
        self.create_inference_tab()

        # 存储选项卡状态
        self.current_tab = 0

    def setup_dark_theme(self):
        """设置深色主题样式"""
        style = ttk.Style()

        # 配置不同组件的样式
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("TButton",
                        background=self.accent_color,
                        foreground=self.fg_color,
                        focuscolor="none")
        style.configure("TNotebook", background=self.bg_color)

        # 设置 Notebook 选项卡的字体样式
        style.configure("TNotebook.Tab",
                        background="#2d2d2d",
                        foreground="#000000",          # 黑色字体
                        padding=[15, 8],               # 选项卡内边距
                        font=("楷体", 12, "bold"),      # 字体设置
                        relief="raised",               # 添加3D凸起效果
                        borderwidth=2,                 # 边框宽度
                        focusthickness=0,              # 移除焦点厚度
                        focuscolor="none")             # 移除焦点颜色

        # 增强选项卡状态映射
        style.map("TNotebook.Tab",
                  background=[("selected", self.tab_selected_color),  # 选中时使用深蓝色
                              ("active", self.tab_hover_color),  # 悬停时使用悬停颜色
                              ("!selected", "#2d2d2d")],  # 未选中时使用深灰色
                  foreground=[("selected", "#ffffff"),  # 选中时白色字体
                              ("active", "#ffffff"),  # 悬停时白色字体
                              ("!selected", "#000000")],  # 未选中时黑色字体
                  relief=[("selected", "sunken"),  # 选中时凹陷效果
                          ("active", "raised"),  # 悬停时凸起效果
                          ("!selected", "raised")],  # 未选中时凸起效果
                  borderwidth=[("selected", 2),  # 选中时边框宽度
                               ("active", 2),  # 悬停时边框宽度
                               ("!selected", 2)])  # 未选中时边框宽度

        # 配置进度条样式
        style.configure("Horizontal.TProgressbar",
                        background=self.accent_color,
                        troughcolor="#2d2d2d")

    def create_header_with_logo(self, parent):
        """创建包含标题和Logo的头部 - 标题居中版本"""
        # 左侧占位（为了平衡布局）
        left_space = ttk.Frame(parent, width=100)  # 与Logo宽度匹配
        left_space.pack(side=tk.LEFT, fill=tk.Y)

        # 中间标题
        title_frame = ttk.Frame(parent)
        title_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        title_label = ttk.Label(title_frame,
                                text="DeepLog Offline (AI日志诊断系统离线版)",
                                font=("Arial", 18, "bold"),
                                foreground=self.fg_color,
                                background=self.bg_color)
        title_label.pack(anchor=tk.CENTER, pady=10)  # 居中对齐

        # 右侧Logo
        logo_frame = ttk.Frame(parent)
        logo_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.add_ericsson_logo(logo_frame)

    def add_ericsson_logo(self, parent):
        """添加爱立信logo"""
        try:
            # 创建logo框架
            logo_frame = ttk.Frame(parent)
            logo_frame.pack(side=tk.RIGHT, padx=10)

            # 成功创建框架后再保存到实例变量
            self.logo_frame = logo_frame

            # 获取当前脚本所在目录的绝对路径
            logo_path = os.path.join(os.path.dirname(__file__), "ericsson_logo.png")

            # 加载图片
            logo_image = Image.open(logo_path)
            logo_image = logo_image.resize((50, 50), Image.Resampling.LANCZOS)

            # 关键：多重引用保护
            # 1. 实例变量引用
            self.logo_photo_image = ImageTk.PhotoImage(logo_image)

            # 2. 全局字典引用
            if not hasattr(self, '_image_registry'):
                self._image_registry = {}
            self._image_registry['logo'] = self.logo_photo_image

            # 3. Label组件自身引用
            self.logo_label = ttk.Label(self.logo_frame,
                                        image=self.logo_photo_image,
                                        background=self.bg_color)

            # 4. 在Label上直接保存引用（重要！）
            self.logo_label.image_reference = self.logo_photo_image

            self.logo_label.pack()

            # 立即强制界面更新
            self.root.update_idletasks()
            self.root.update()

        except Exception as e:
            import traceback
            traceback.print_exc()

            # 使用文字logo
            fallback_logo = ttk.Label(parent,
                                      text="Ericsson",
                                      font=("Arial", 12, "bold"),
                                      foreground=self.fg_color,
                                      background=self.bg_color)
            fallback_logo.pack(side=tk.RIGHT, padx=10)

    def create_processing_tab(self):
        """创建数据处理标签页 - 后续添加"""
        processing_frame = ttk.Frame(self.notebook)
        self.notebook.add(processing_frame, text="数据处理")

        # 实例化数据处理GUI
        self.processing_gui = ProcessingGUI(processing_frame)

    def create_training_tab(self):
        """创建模型训练标签页"""
        training_frame = ttk.Frame(self.notebook)
        self.notebook.add(training_frame, text="模型训练")

        # 实例化训练GUI
        self.training_gui = TrainingGUI(training_frame)

    def create_inference_tab(self):
        """创建模型推理标签页"""
        inference_frame = ttk.Frame(self.notebook)
        self.notebook.add(inference_frame, text="样本推理")

        # 实例化推理GUI
        self.inference_gui = InferenceGUI(inference_frame)


def main():
    root = tk.Tk()
    DeepLogGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
