import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
from tools.app.services.data_processing.pqat_downloader.downloader_gui import PQATDownloaderGUI
from tools.app.services.data_processing.zip_extractor.extractor_gui import ZipExtractorGUI
from tools.app.services.data_processing.log_parser.parser_gui import ExcelParserGUI
from tools.app.services.data_processing.data_processor.processor_gui import DataProcessorGUI


class ProcessingGUI:
    """数据处理主GUI - 数据处理工具集成界面"""
    def __init__(self, parent):
        self.root = parent

        # 设置深色主题颜色 - 与主GUI保持一致
        self.bg_color = "#1e1e1e"  # 深灰色背景
        self.fg_color = "#ffffff"  # 白色前景
        self.accent_color = "#007acc"  # 蓝色强调色
        self.frame_bg = "#2d2d2d"  # 框架背景色
        self.entry_bg = "#3d3d3d"  # 输入框背景色

        # 设置样式
        self.setup_styles()

        # 创建界面
        self.setup_ui()

        # 初始化各个模块
        self.setup_modules()

    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()

        # 配置不同组件(弹窗)的样式 - 修改字体颜色为黑色
        style.configure("Title.TLabel",
                        font=("Arial", 16, "bold"),
                        background=self.bg_color,
                        foreground="#000000")  # 改为黑色字体
        style.configure("Subtitle.TLabel",
                        font=("Arial", 12, "bold"),
                        background=self.bg_color,
                        foreground="#000000")  # 改为黑色字体
        style.configure("Status.TLabel",
                        font=("Arial", 10),
                        foreground=self.accent_color,
                        background=self.bg_color)

        # 配置标签页和框架样式
        style.configure("TFrame", background=self.bg_color)

        # 黑色文字的 LabelFrame 样式
        style.configure("TLabelframe",
                        background=self.bg_color,
                        foreground="#000000")  # 改为黑色字体
        style.configure("TLabelframe.Label",
                        background=self.frame_bg,
                        foreground="#000000")  # 改为黑色字体

        # 白色文字的 LabelFrame 样式
        style.configure("White.TLabelframe",
                        background=self.bg_color,
                        foreground=self.fg_color)  # 白色字体
        style.configure("White.TLabelframe.Label",
                        background=self.frame_bg,
                        foreground=self.fg_color)  # 白色字体

        style.configure("TLabel",
                        background=self.bg_color,
                        foreground="#000000")  # 改为黑色字体
        style.configure("TButton",
                        background=self.accent_color,
                        foreground="#000000",  # 黑色字体
                        focuscolor="none")
        style.map("TButton",
                  background=[("active", self.accent_color),
                              ("pressed", self.accent_color)],
                  foreground=[("active", "#000000"),
                              ("pressed", "#000000")])

        style.configure("TProgressbar",
                        background=self.accent_color,
                        troughcolor=self.frame_bg)

        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab",
                        background=self.frame_bg,
                        foreground="#000000",  # 黑色字体
                        padding=[10, 5])
        style.map("TNotebook.Tab",
                  background=[("selected", self.accent_color),
                              ("active", "#3d3d3d")],
                  foreground=[("selected", "#000000"),
                              ("active", "#000000"),
                              ("!selected", "#000000"),
                              ("!active", "#000000")])

        # 配置 Treeview 样式
        style.configure("Treeview",
                        background=self.entry_bg,
                        foreground="#000000",  # 改为黑色字体
                        fieldbackground=self.entry_bg)
        style.configure("Treeview.Heading",
                        background=self.frame_bg,
                        foreground="#000000")  # 改为黑色字体
        style.map("Treeview",
                  background=[('selected', self.accent_color)])

    def setup_ui(self):
        """设置主界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建选项卡
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 创建各个模块的框架
        self.downloader_frame = ttk.Frame(self.notebook, padding="10")
        self.extractor_frame = ttk.Frame(self.notebook, padding="10")
        self.parser_frame = ttk.Frame(self.notebook, padding="10")
        self.processor_frame = ttk.Frame(self.notebook, padding="10")

        # 添加选项卡
        self.notebook.add(self.downloader_frame, text="数据下载")
        self.notebook.add(self.extractor_frame, text="数据提取")
        self.notebook.add(self.parser_frame, text="日志解析")
        self.notebook.add(self.processor_frame, text="生成样本数据")

        # 绑定选项卡切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 状态标签
        self.status_label = ttk.Label(main_frame, text="就绪", style="Status.TLabel")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        # 底部信息栏
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        info_text = (
            "数据处理流程: 下载 → 提取 → 解析 → 生成样本\n"
            "请按顺序使用各个工具完成数据处理工作流"
        )
        info_label = ttk.Label(info_frame, text=info_text,
                               justify=tk.CENTER,
                               foreground="#888888",
                               background=self.bg_color)
        info_label.pack()

    def setup_modules(self):
        """初始化各个模块"""
        try:
            self.update_status("正在初始化模块...")

            # 数据下载模块 - 需要特殊处理
            self.setup_downloader_module()

            # 数据提取模块
            self.update_status("初始化数据提取模块...")
            self.setup_extractor_module()

            # 日志解析模块
            self.update_status("初始化日志解析模块...")
            self.setup_parser_module()

            # 数据处理模块
            self.update_status("初始化生成样本数据模块...")
            self.setup_processor_module()

            self.update_status("所有模块初始化完成")

        except Exception as e:
            self.update_status(f"模块初始化失败: {str(e)}")
            messagebox.showerror("初始化错误", f"模块初始化失败: {str(e)}")

    def setup_downloader_module(self):
        """设置下载器模块到选项卡中"""
        self.update_status("初始化数据下载模块...")

        # 创建下载器实例
        self.downloader_gui = PQATDownloaderGUI()

        # 由于PQATDownloaderGUI是独立设计的，需要手动重建其界面
        downloader_main_frame = ttk.Frame(self.downloader_frame)
        downloader_main_frame.pack(fill=tk.BOTH, expand=True)

        # 添加标题
        title_label = ttk.Label(
            downloader_main_frame,
            text="PQAT日志下载管理",
            font=("Arial", 16, "bold"),
            foreground=self.fg_color,
            background=self.bg_color
        )
        title_label.pack(pady=10)

        # 添加配置框架 - 修改这里使"配置设置"显示为白色
        config_frame = ttk.LabelFrame(
            downloader_main_frame,
            text="配置设置",
            padding="10",
            style="White.TLabelframe"  # 使用白色文字的样式
        )
        config_frame.pack(fill=tk.X, pady=10)
        #
        # # 添加配置框架 - 修改这里使"输入文件设置"显示为白色
        # config_frame = ttk.LabelFrame(
        #     downloader_main_frame,
        #     text="输入文件设置",
        #     padding="10",
        #     style="White.TLabelframe"  # 使用白色文字的样式
        # )
        # config_frame.pack(fill=tk.X, pady=10)
        #
        # # 添加配置框架 - 修改这里使"处理日志"显示为白色
        # config_frame = ttk.LabelFrame(
        #     downloader_main_frame,
        #     text="处理日志",
        #     padding="10",
        #     style="White.TLabelframe"  # 使用白色文字的样式
        # )
        # config_frame.pack(fill=tk.X, pady=10)
        #
        # # 添加配置框架 - 修改这里使"处理选项"显示为白色
        # config_frame = ttk.LabelFrame(
        #     downloader_main_frame,
        #     text="处理选项",
        #     padding="10",
        #     style="White.TLabelframe"  # 使用白色文字的样式
        # )
        # config_frame.pack(fill=tk.X, pady=10)

        # 下载路径配置
        folder_label = ttk.Label(config_frame, text="下载路径:", foreground=self.fg_color)
        folder_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.folder_var = tk.StringVar(value=getattr(self.downloader_gui, 'default_folder', ""))
        folder_entry = ttk.Entry(config_frame, textvariable=self.folder_var, width=50)
        folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        # 设置输入框样式为黑色文字
        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        folder_entry.configure(style="Black.TEntry")

        folder_button = ttk.Button(
            config_frame,
            text="浏览",
            command=self.browse_download_folder
        )
        folder_button.grid(row=0, column=2, pady=5, padx=5)

        # 序列号文件配置
        snfile_label = ttk.Label(config_frame, text="序列号文件:", foreground=self.fg_color)
        snfile_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.snfile_var = tk.StringVar(value=getattr(self.downloader_gui, 'default_sn_file', ""))
        snfile_entry = ttk.Entry(config_frame, textvariable=self.snfile_var, width=50)
        snfile_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        snfile_entry.configure(style="Black.TEntry")  # 设置黑色文字

        snfile_button = ttk.Button(
            config_frame,
            text="浏览",
            command=self.browse_sn_file
        )
        snfile_button.grid(row=1, column=2, pady=5, padx=5)

        # 按钮框架
        button_frame = ttk.Frame(downloader_main_frame)
        button_frame.pack(pady=20)

        # 添加下载按钮
        download_button = ttk.Button(
            button_frame,
            text="下载日志",
            command=self.start_download
        )
        download_button.grid(row=0, column=0, padx=10)

        # 添加管理按钮
        manage_button = ttk.Button(
            button_frame,
            text="管理数据库",
            command=self.manage_database
        )
        manage_button.grid(row=0, column=1, padx=10)

        # 配置权重
        config_frame.columnconfigure(1, weight=1)
        downloader_main_frame.columnconfigure(0, weight=1)

    def setup_extractor_module(self):
        """设置数据提取模块到选项卡中"""
        # 创建数据提取GUI实例
        self.extractor_gui = ZipExtractorGUI(self.extractor_frame)

        # 由于ZipExtractorGUI已经设计为接受父容器，我们不需要额外设置
        # 但是我们需要确保它的UI正确显示
        self.extractor_frame.update_idletasks()

    def setup_parser_module(self):
        """设置日志解析模块到选项卡中"""
        # 创建日志解析GUI实例
        self.parser_gui = ExcelParserGUI(self.parser_frame)

        # 确保UI正确显示
        self.parser_frame.update_idletasks()

    def setup_processor_module(self):
        """设置数据处理模块到选项卡中"""
        # 创建数据处理GUI实例
        self.processor_gui = DataProcessorGUI(self.processor_frame)

        # 确保UI正确显示
        self.processor_frame.update_idletasks()

    def browse_download_folder(self):
        """浏览下载文件夹"""
        folder_path = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder_path:
            self.folder_var.set(folder_path)

    def browse_sn_file(self):
        """浏览序列号文件"""
        file_path = filedialog.askopenfilename(
            initialdir=os.path.dirname(self.snfile_var.get()) or ".",
            title="选择序列号文件",
            filetypes=(("文本文件", "*.txt"), ("所有文件", "*.*"))
        )
        if file_path:
            self.snfile_var.set(file_path)

    def start_download(self):
        """开始下载"""
        try:
            self.downloader_gui.download_logs(
                self.snfile_var.get(),
                self.folder_var.get(),
                self.downloader_frame
            )
        except Exception as e:
            messagebox.showerror("下载错误", f"下载过程中出错: {str(e)}")

    def manage_database(self):
        """管理数据库"""
        try:
            self.downloader_gui.manage_database()
        except Exception as e:
            messagebox.showerror("数据库错误", f"数据库管理出错: {str(e)}")

    def on_tab_changed(self, event):
        """选项卡切换事件处理"""
        current_tab = self.notebook.index(self.notebook.select())
        tab_names = ["数据下载", "数据提取", "日志解析", "生成样本数据"]
        self.update_status(f"当前模块: {tab_names[current_tab]}")

    def update_status(self, message):
        """更新状态信息"""
        self.status_label.config(text=message)
        self.root.update_idletasks()


def main():
    """主函数"""
    root = tk.Tk()
    ProcessingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
