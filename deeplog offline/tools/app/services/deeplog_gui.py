import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk  # 添加图片处理支持

from tools.app.services.model_training.training_gui import TrainingGUI
from tools.app.services.model_prediction.inference_gui import InferenceGUI
from tools.app.services.data_processing.processing_gui import ProcessingGUI


# =========================
# I18N 语言资源（可继续扩展到子页面）
# =========================
I18N = {
    "zh": {
        "app_title": "Deeplog Offline",
        "header_title": "DeepLog Offline (AI日志诊断系统离线版)",
        "tab_processing": "数据处理",
        "tab_training": "模型训练",
        "tab_inference": "样本推理",
        # 语言切换按钮显示：中文状态下显示“EN”（表示点它切到英文）
        "btn_toggle_to_en": "EN",
        "btn_toggle_to_zh": "中文",
    },
    "en": {
        "app_title": "Deeplog Offline",
        "header_title": "DeepLog Offline (Offline AI Log Diagnosis System)",
        "tab_processing": "Data Processing",
        "tab_training": "Model Training",
        "tab_inference": "Inference",
        "btn_toggle_to_en": "EN",
        "btn_toggle_to_zh": "中文",
    },
}


class ScrollableFrame(ttk.Frame):
    """可滚动的Frame组件"""

    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        # 创建Canvas和滚动条
        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # 配置Canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # 在Canvas中创建窗口
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # 配置Canvas的滚动
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 布局
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 绑定鼠标滚轮事件
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux向上滚动
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux向下滚动

    def _on_canvas_configure(self, event):
        """当Canvas大小改变时调整内部框架宽度"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _on_frame_configure(self, event):
        """当内部框架大小改变时更新滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            # Linux系统
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")


class DeepLogGUI:
    """主GUI - 通过模块化方式集成各子GUI"""

    def __init__(self, root):
        self.root = root

        # ✅ 默认启动中文
        self.lang = "zh"

        # 窗口基础设置（title 会在 apply_language() 里根据语言再设置一次）
        self.root.title("Deeplog Offline")
        self.root.geometry("1400x1000")

        # 设置深色主题颜色
        self.bg_color = "#1e1e1e"  # 深灰色背景
        self.fg_color = "#ffffff"  # 白色前景
        self.accent_color = "#007acc"  # 蓝色强调色
        self.tab_hover_color = "#3d3d3d"  # 选项卡悬停颜色
        self.tab_selected_color = "#005a9e"  # 选项卡选中颜色（比主强调色稍深）
        self.tab_border_color = "#555555"  # 选项卡边框颜色

        # 配置根窗口背景
        self.root.configure(bg=self.bg_color)

        # 设置深色主题样式
        self.setup_dark_theme()

        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建标题和logo框架 - 水平布局
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        self.create_header_with_logo(header_frame)

        # 创建主标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 创建各功能标签页（tab 文案用 t()）
        self.create_processing_tab()
        self.create_training_tab()
        self.create_inference_tab()

        # 存储选项卡状态
        self.current_tab = 0

        # ✅ 初次应用语言（刷新窗口标题、tab 名等）
        self.apply_language()

    # -------------------------
    # i18n helper
    # -------------------------
    def t(self, key: str) -> str:
        """根据当前语言取文本：当前语言 -> 英文回退 -> key"""
        return I18N.get(self.lang, I18N["en"]).get(key, I18N["en"].get(key, key))

    def toggle_language(self):
        """按钮触发：中英互切"""
        self.lang = "en" if self.lang == "zh" else "zh"
        self.apply_language()

    def apply_language(self):
        """把当前语言应用到所有已创建控件"""
        # 窗口标题
        self.root.title(self.t("app_title"))

        # header 标题
        if hasattr(self, "title_label"):
            self.title_label.configure(text=self.t("header_title"))

        # 语言按钮文字：中文状态显示“EN”，英文状态显示“中文”
        if hasattr(self, "lang_btn"):
            self.lang_btn.configure(
                text=self.t("btn_toggle_to_en") if self.lang == "zh" else self.t("btn_toggle_to_zh")
            )

        # Notebook tabs 文案刷新（需要保存每个 tab frame 的引用）
        if hasattr(self, "processing_tab"):
            self.notebook.tab(self.processing_tab, text=self.t("tab_processing"))
        if hasattr(self, "training_tab"):
            self.notebook.tab(self.training_tab, text=self.t("tab_training"))
        if hasattr(self, "inference_tab"):
            self.notebook.tab(self.inference_tab, text=self.t("tab_inference"))

        # （可选）对子GUI下发语言：子GUI实现 apply_language(lang, t) 即可联动
        for child_name in ("processing_gui", "training_gui", "inference_gui"):
            child = getattr(self, child_name, None)
            if child is not None and hasattr(child, "apply_language"):
                child.apply_language(self.lang, self.t)

    # -------------------------
    # theme & UI construction
    # -------------------------
    def setup_dark_theme(self):
        """设置深色主题样式"""
        style = ttk.Style()

        # 配置不同组件的样式
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure(
            "TButton",
            background=self.accent_color,
            foreground=self.fg_color,
            focuscolor="none",
        )
        style.configure("TNotebook", background=self.bg_color)

        # 设置 Notebook 选项卡的字体样式
        style.configure(
            "TNotebook.Tab",
            background="#2d2d2d",
            foreground="#000000",  # 黑色字体
            padding=[15, 8],  # 选项卡内边距
            font=("楷体", 12, "bold"),  # 字体设置（如需英文更好看可后续改为语言自适应）
            relief="raised",  # 添加3D凸起效果
            borderwidth=2,  # 边框宽度
            focusthickness=0,  # 移除焦点厚度
            focuscolor="none",  # 移除焦点颜色
        )

        # 增强选项卡状态映射
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", self.tab_selected_color),  # 选中时使用深蓝色
                ("active", self.tab_hover_color),  # 悬停时使用悬停颜色
                ("!selected", "#2d2d2d"),  # 未选中时使用深灰色
            ],
            foreground=[
                ("selected", "#ffffff"),  # 选中时白色字体
                ("active", "#ffffff"),  # 悬停时白色字体
                ("!selected", "#000000"),  # 未选中时黑色字体
            ],
            relief=[
                ("selected", "sunken"),  # 选中时凹陷效果
                ("active", "raised"),  # 悬停时凸起效果
                ("!selected", "raised"),  # 未选中时凸起效果
            ],
            borderwidth=[
                ("selected", 2),  # 选中时边框宽度
                ("active", 2),  # 悬停时边框宽度
                ("!selected", 2),  # 未选中时边框宽度
            ],
        )

        # 配置进度条样式
        style.configure(
            "Horizontal.TProgressbar",
            background=self.accent_color,
            troughcolor="#2d2d2d",
        )

    def create_header_with_logo(self, parent):
        """创建包含标题和Logo的头部 - 标题居中版本 + 语言切换按钮"""

        # 左侧占位（为了平衡布局）
        left_space = ttk.Frame(parent, width=100)  # 与Logo宽度匹配
        left_space.pack(side=tk.LEFT, fill=tk.Y)

        # 中间标题
        title_frame = ttk.Frame(parent)
        title_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ✅ 保存引用：便于切换语言时更新
        self.title_label = ttk.Label(
            title_frame,
            text=self.t("header_title"),
            font=("Arial", 18, "bold"),
            foreground=self.fg_color,
            background=self.bg_color,
        )
        self.title_label.pack(anchor=tk.CENTER, pady=10)

        # 右侧区域：语言按钮 + Logo
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # ✅ 语言切换按钮：中文状态显示“EN”，英文状态显示“中文”
        self.lang_btn = ttk.Button(
            right_frame,
            text=self.t("btn_toggle_to_en") if self.lang == "zh" else self.t("btn_toggle_to_zh"),
            command=self.toggle_language,
        )
        self.lang_btn.pack(side=tk.TOP, padx=10, pady=(0, 6))

        # Logo
        self.add_ericsson_logo(right_frame)

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
            if not hasattr(self, "_image_registry"):
                self._image_registry = {}
            self._image_registry["logo"] = self.logo_photo_image

            # 3. Label组件自身引用
            self.logo_label = ttk.Label(
                self.logo_frame, image=self.logo_photo_image, background=self.bg_color
            )

            # 4. 在Label上直接保存引用（重要！）
            self.logo_label.image_reference = self.logo_photo_image
            self.logo_label.pack()

            # 立即强制界面更新
            self.root.update_idletasks()
            self.root.update()

        except Exception:
            import traceback
            traceback.print_exc()

            # 使用文字logo
            fallback_logo = ttk.Label(
                parent,
                text="Ericsson",
                font=("Arial", 12, "bold"),
                foreground=self.fg_color,
                background=self.bg_color,
            )
            fallback_logo.pack(side=tk.RIGHT, padx=10)

    def create_processing_tab(self):
        """创建数据处理标签页 - 使用可滚动框架"""
        self.processing_tab = ScrollableFrame(self.notebook)
        self.notebook.add(self.processing_tab, text=self.t("tab_processing"))

        # 实例化数据处理GUI，传入可滚动框架的内部框架
        self.processing_gui = ProcessingGUI(self.processing_tab.scrollable_frame)

    def create_training_tab(self):
        """创建模型训练标签页 - 使用可滚动框架"""
        self.training_tab = ScrollableFrame(self.notebook)
        self.notebook.add(self.training_tab, text=self.t("tab_training"))

        # 实例化训练GUI，传入可滚动框架的内部框架
        self.training_gui = TrainingGUI(self.training_tab.scrollable_frame)

    def create_inference_tab(self):
        """创建模型推理标签页 - 使用可滚动框架"""
        self.inference_tab = ScrollableFrame(self.notebook)
        self.notebook.add(self.inference_tab, text=self.t("tab_inference"))

        # 实例化推理GUI，传入可滚动框架的内部框架
        self.inference_gui = InferenceGUI(self.inference_tab.scrollable_frame)


def main():
    root = tk.Tk()
    DeepLogGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()