# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

from tools.app.services.data_processing.pqat_downloader.downloader_gui import PQATDownloaderGUI
from tools.app.services.data_processing.zip_extractor.extractor_gui import ZipExtractorGUI
from tools.app.services.data_processing.log_parser.parser_gui import ExcelParserGUI
from tools.app.services.data_processing.data_processor.processor_gui import DataProcessorGUI

# === 新增：路径相关工具（统一默认目录，不干扰主流程） ===
from tools.Common.path_utils import (
    resolve_download_dir,
    get_sn_list_path,
    ensure_dir,
)

APP_NAME = "DeepLogOffline"  # 与 path_utils 中保持一致即可

# =========================
# i18n 资源（Processing）
# =========================
_I18N = {
    "zh": {
        "tab_down": "数据下载",
        "tab_extract": "数据提取",
        "tab_parse": "日志解析",
        "tab_sample": "生成样本数据",
        "status_ready": "就绪",
        "status_init": "正在初始化模块...",
        "status_init_extract": "初始化数据提取模块...",
        "status_init_parse": "初始化日志解析模块...",
        "status_init_sample": "初始化生成样本数据模块...",
        "status_init_done": "所有模块初始化完成",
        "status_init_fail": "模块初始化失败: {err}",
        "status_current": "当前模块: {name}",
        "info_text": "数据处理流程: 下载 → 提取 → 解析 → 生成样本数据\n请按顺序使用各个工具完成数据处理工作流",
        "dl_title": "PQAT日志下载管理",
        "cfg_title": "配置设置",
        "download_path": "下载路径:",
        "sn_file": "序列号文件:",
        "browse": "浏览",
        "btn_download": "下载日志",
        "btn_db": "管理数据库",
        "dlg_init_error": "初始化错误",
        "dlg_download_error": "下载错误",
        "dlg_db_error": "数据库错误",
        "dlg_select_sn_title": "选择序列号文件",
        "err_download": "下载过程中出错: {err}",
        "err_db": "数据库管理出错: {err}",
        "tabnames": ["数据下载", "数据提取", "日志解析", "生成样本数据"],
        "filetype_txt": "文本文件",
        "filetype_all": "所有文件",
    },
    "en": {
        "tab_down": "Download",
        "tab_extract": "Extract",
        "tab_parse": "Parse Logs",
        "tab_sample": "Build Samples",
        "status_ready": "Ready",
        "status_init": "Initializing modules...",
        "status_init_extract": "Initializing extractor...",
        "status_init_parse": "Initializing parser...",
        "status_init_sample": "Initializing sample builder...",
        "status_init_done": "All modules initialized",
        "status_init_fail": "Module initialization failed: {err}",
        "status_current": "Current module: {name}",
        "info_text": "Workflow: Download → Extract → Parse → Build Samples\nPlease follow the order to complete the data processing workflow",
        "dl_title": "PQAT Log Download Manager",
        "cfg_title": "Configuration",
        "download_path": "Download folder:",
        "sn_file": "SN list file:",
        "browse": "Browse",
        "btn_download": "Download Logs",
        "btn_db": "Manage Database",
        "dlg_init_error": "Initialization Error",
        "dlg_download_error": "Download Error",
        "dlg_db_error": "Database Error",
        "dlg_select_sn_title": "Select SN list file",
        "err_download": "Error during downloading: {err}",
        "err_db": "Database management error: {err}",
        "tabnames": ["Download", "Extract", "Parse Logs", "Build Samples"],
        "filetype_txt": "Text files",
        "filetype_all": "All files",
    },
}


class ProcessingGUI:
    """数据处理主GUI - 数据处理工具集成界面"""

    def __init__(self, parent):
        self.root = parent

        # 默认语言（主界面会通过 apply_language 覆盖）
        self.lang = "zh"
        self._external_t = None  # 来自主界面的 t(key)

        # 设置深色主题颜色 - 与主GUI保持一致
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#007acc"
        self.frame_bg = "#2d2d2d"
        self.entry_bg = "#3d3d3d"

        # 设置样式
        self.setup_styles()

        # 创建界面
        self.setup_ui()

        # 解析默认下载目录与 SN 列表路径（优先 OneDrive - Ericsson 模板）
        self.download_dir = resolve_download_dir(ask_if_missing=False, app_name=APP_NAME)
        ensure_dir(self.download_dir)
        self.sn_list_path = get_sn_list_path(app_name=APP_NAME)

        # 初始化各个模块
        self.setup_modules()

        # ✅ 初始化结束后，确保子模块语言与当前一致（避免启动瞬间不一致）
        self._apply_child_language()

    # -------------------------
    # i18n helper
    # -------------------------
    def _t(self, key: str, **fmt) -> str:
        """
        优先使用主界面传入的 t(key)（如果它认识这个 key）。
        如果主界面返回的仍是 key，则回退到本文件内置 _I18N。
        """
        text = key
        if callable(self._external_t):
            v = self._external_t(key)
            if v != key:
                text = v
            else:
                text = _I18N.get(self.lang, _I18N["en"]).get(key, key)
        else:
            text = _I18N.get(self.lang, _I18N["en"]).get(key, key)

        if fmt:
            try:
                return text.format(**fmt)
            except Exception:
                return text
        return text

    def _apply_child_language(self):
        """
        ✅ 核心：把当前语言下发给子模块（数据提取/日志解析/生成样本数据）
        - 优先调用子模块 apply_language(lang, t_func)
        - 若子模块还是旧签名 apply_language()，做 TypeError 兼容
        """
        for child_attr in ("extractor_gui", "parser_gui", "processor_gui"):
            child = getattr(self, child_attr, None)
            if child is None:
                continue

            if hasattr(child, "apply_language"):
                try:
                    child.apply_language(self.lang, self._external_t)
                except TypeError:
                    # 兼容旧版本无参 apply_language()
                    try:
                        child.lang = self.lang
                        child.apply_language()
                    except Exception:
                        pass

    def apply_language(self, lang: str, t_func=None):
        """供主界面调用：切换语言并刷新可见UI文本 + 无条件联动子模块"""
        self.lang = lang or "zh"
        self._external_t = t_func

        # notebook tabs
        if hasattr(self, "notebook"):
            self.notebook.tab(self.downloader_frame, text=self._t("tab_down"))
            self.notebook.tab(self.extractor_frame, text=self._t("tab_extract"))
            self.notebook.tab(self.parser_frame, text=self._t("tab_parse"))
            self.notebook.tab(self.processor_frame, text=self._t("tab_sample"))

        # 下载页组件
        if hasattr(self, "dl_title_label"):
            self.dl_title_label.configure(text=self._t("dl_title"))
        if hasattr(self, "config_frame"):
            self.config_frame.configure(text=self._t("cfg_title"))
        if hasattr(self, "folder_label"):
            self.folder_label.configure(text=self._t("download_path"))
        if hasattr(self, "snfile_label"):
            self.snfile_label.configure(text=self._t("sn_file"))
        if hasattr(self, "folder_button"):
            self.folder_button.configure(text=self._t("browse"))
        if hasattr(self, "snfile_button"):
            self.snfile_button.configure(text=self._t("browse"))
        if hasattr(self, "download_button"):
            self.download_button.configure(text=self._t("btn_download"))
        if hasattr(self, "manage_button"):
            self.manage_button.configure(text=self._t("btn_db"))

        # 底部说明
        if hasattr(self, "info_label"):
            self.info_label.configure(text=self._t("info_text"))

        # 状态：如果当前正显示 ready，就翻译；否则不强行覆盖正在进行的状态文本
        if hasattr(self, "status_label"):
            current = self.status_label.cget("text")
            if current in ("就绪", "Ready"):
                self.status_label.configure(text=self._t("status_ready"))

        # ✅ 最关键：无条件联动子模块（不要放在任何 if 条件里）
        self._apply_child_language()

    # -------------------------
    # styles & UI
    # -------------------------
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()

        style.configure(
            "Title.TLabel",
            font=("Arial", 16, "bold"),
            background=self.bg_color,
            foreground="#000000",
        )
        style.configure(
            "Subtitle.TLabel",
            font=("Arial", 12, "bold"),
            background=self.bg_color,
            foreground="#000000",
        )
        style.configure(
            "Status.TLabel",
            font=("Arial", 10),
            foreground=self.accent_color,
            background=self.bg_color,
        )

        style.configure("TFrame", background=self.bg_color)

        style.configure(
            "TLabelframe",
            background=self.bg_color,
            foreground="#000000",
        )
        style.configure(
            "TLabelframe.Label",
            background=self.frame_bg,
            foreground="#000000",
        )

        style.configure(
            "White.TLabelframe",
            background=self.bg_color,
            foreground=self.fg_color,
        )
        style.configure(
            "White.TLabelframe.Label",
            background=self.frame_bg,
            foreground=self.fg_color,
        )

        style.configure("TLabel", background=self.bg_color, foreground="#000000")

        style.configure(
            "TButton",
            background=self.accent_color,
            foreground="#000000",
            focuscolor="none",
        )
        style.map(
            "TButton",
            background=[("active", self.accent_color), ("pressed", self.accent_color)],
            foreground=[("active", "#000000"), ("pressed", "#000000")],
        )

        style.configure("TProgressbar", background=self.accent_color, troughcolor=self.frame_bg)

        style.configure("TNotebook", background=self.bg_color)
        style.configure(
            "TNotebook.Tab",
            background=self.frame_bg,
            foreground="#000000",
            padding=[10, 5],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.accent_color), ("active", "#3d3d3d")],
            foreground=[
                ("selected", "#000000"),
                ("active", "#000000"),
                ("!selected", "#000000"),
                ("!active", "#000000"),
            ],
        )

        style.configure(
            "Treeview",
            background=self.entry_bg,
            foreground="#000000",
            fieldbackground=self.entry_bg,
        )
        style.configure("Treeview.Heading", background=self.frame_bg, foreground="#000000")
        style.map("Treeview", background=[("selected", self.accent_color)])

    def setup_ui(self):
        """设置主界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.downloader_frame = ttk.Frame(self.notebook, padding="10")
        self.extractor_frame = ttk.Frame(self.notebook, padding="10")
        self.parser_frame = ttk.Frame(self.notebook, padding="10")
        self.processor_frame = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.downloader_frame, text=self._t("tab_down"))
        self.notebook.add(self.extractor_frame, text=self._t("tab_extract"))
        self.notebook.add(self.parser_frame, text=self._t("tab_parse"))
        self.notebook.add(self.processor_frame, text=self._t("tab_sample"))

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.status_label = ttk.Label(main_frame, text=self._t("status_ready"), style="Status.TLabel")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        self.info_label = ttk.Label(
            info_frame,
            text=self._t("info_text"),
            justify=tk.CENTER,
            foreground="#888888",
            background=self.bg_color,
        )
        self.info_label.pack()

    def setup_modules(self):
        """初始化各个模块"""
        try:
            self.update_status(self._t("status_init"))

            # 数据下载模块
            self.setup_downloader_module()

            # 数据提取模块
            self.update_status(self._t("status_init_extract"))
            self.setup_extractor_module()

            # 日志解析模块
            self.update_status(self._t("status_init_parse"))
            self.setup_parser_module()

            # 生成样本数据模块
            self.update_status(self._t("status_init_sample"))
            self.setup_processor_module()

            self.update_status(self._t("status_init_done"))

        except Exception as e:
            self.update_status(self._t("status_init_fail", err=str(e)))
            messagebox.showerror(self._t("dlg_init_error"), self._t("status_init_fail", err=str(e)))

    def setup_downloader_module(self):
        """设置下载器模块到选项卡中"""
        self.update_status(self._t("status_init"))

        self.downloader_gui = PQATDownloaderGUI()

        downloader_main_frame = ttk.Frame(self.downloader_frame)
        downloader_main_frame.pack(fill=tk.BOTH, expand=True)

        self.dl_title_label = ttk.Label(
            downloader_main_frame,
            text=self._t("dl_title"),
            font=("Arial", 16, "bold"),
            foreground=self.fg_color,
            background=self.bg_color,
        )
        self.dl_title_label.pack(pady=10)

        self.config_frame = ttk.LabelFrame(
            downloader_main_frame,
            text=self._t("cfg_title"),
            padding="10",
            style="White.TLabelframe",
        )
        self.config_frame.pack(fill=tk.X, pady=10)

        # 下载路径
        self.folder_label = ttk.Label(self.config_frame, text=self._t("download_path"), foreground=self.fg_color)
        self.folder_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.folder_var = tk.StringVar(value=str(self.download_dir))
        folder_entry = ttk.Entry(self.config_frame, textvariable=self.folder_var, width=50)
        folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        folder_entry.configure(style="Black.TEntry")

        self.folder_button = ttk.Button(self.config_frame, text=self._t("browse"), command=self.browse_download_folder)
        self.folder_button.grid(row=0, column=2, pady=5, padx=5)

        # SN 文件
        self.snfile_label = ttk.Label(self.config_frame, text=self._t("sn_file"), foreground=self.fg_color)
        self.snfile_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.snfile_var = tk.StringVar(value=str(self.sn_list_path))
        snfile_entry = ttk.Entry(self.config_frame, textvariable=self.snfile_var, width=50)
        snfile_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        snfile_entry.configure(style="Black.TEntry")

        self.snfile_button = ttk.Button(self.config_frame, text=self._t("browse"), command=self.browse_sn_file)
        self.snfile_button.grid(row=1, column=2, pady=5, padx=5)

        button_frame = ttk.Frame(downloader_main_frame)
        button_frame.pack(pady=20)

        self.download_button = ttk.Button(button_frame, text=self._t("btn_download"), command=self.start_download)
        self.download_button.grid(row=0, column=0, padx=10)

        self.manage_button = ttk.Button(button_frame, text=self._t("btn_db"), command=self.manage_database)
        self.manage_button.grid(row=0, column=1, padx=10)

        self.config_frame.columnconfigure(1, weight=1)
        downloader_main_frame.columnconfigure(0, weight=1)

    def setup_extractor_module(self):
        """设置数据提取模块到选项卡中"""
        self.extractor_gui = ZipExtractorGUI(self.extractor_frame)

        # ✅ 初始化后同步一次语言（保证首次展示就一致）
        try:
            self.extractor_gui.apply_language(self.lang, self._external_t)
        except TypeError:
            try:
                self.extractor_gui.lang = self.lang
                self.extractor_gui.apply_language()
            except Exception:
                pass

        self.extractor_frame.update_idletasks()

    def setup_parser_module(self):
        """设置日志解析模块到选项卡中"""
        self.parser_gui = ExcelParserGUI(self.parser_frame)

        # ✅ 初始化后同步一次语言（保证首次展示就一致）
        try:
            self.parser_gui.apply_language(self.lang, self._external_t)
        except TypeError:
            try:
                self.parser_gui.lang = self.lang
                self.parser_gui.apply_language()
            except Exception:
                pass

        self.parser_frame.update_idletasks()

    def setup_processor_module(self):
        """设置生成样本数据模块到选项卡中"""
        self.processor_gui = DataProcessorGUI(self.processor_frame)

        # ✅ 初始化后同步一次语言（保证首次展示就一致）
        try:
            self.processor_gui.apply_language(self.lang, self._external_t)
        except TypeError:
            try:
                self.processor_gui.lang = self.lang
                self.processor_gui.apply_language()
            except Exception:
                pass

        self.processor_frame.update_idletasks()

    def browse_download_folder(self):
        """浏览下载文件夹"""
        initial_dir = self.folder_var.get() or str(self.download_dir)
        folder_path = filedialog.askdirectory(initialdir=initial_dir)
        if folder_path:
            self.folder_var.set(folder_path)

    def browse_sn_file(self):
        """浏览序列号文件"""
        initial_file_dir = os.path.dirname(self.snfile_var.get()) or str(self.download_dir)
        file_path = filedialog.askopenfilename(
            initialdir=initial_file_dir,
            title=self._t("dlg_select_sn_title"),
            filetypes=((self._t("filetype_txt"), "*.txt"), (self._t("filetype_all"), "*.*")),
        )
        if file_path:
            self.snfile_var.set(file_path)

    def start_download(self):
        """开始下载"""
        try:
            self.downloader_gui.download_logs(
                self.snfile_var.get(),
                self.folder_var.get(),
                self.downloader_frame,
            )
        except Exception as e:
            messagebox.showerror(self._t("dlg_download_error"), self._t("err_download", err=str(e)))

    def manage_database(self):
        """管理数据库"""
        try:
            self.downloader_gui.manage_database()
        except Exception as e:
            messagebox.showerror(self._t("dlg_db_error"), self._t("err_db", err=str(e)))

    def on_tab_changed(self, event):
        """选项卡切换事件处理"""
        current_tab = self.notebook.index(self.notebook.select())
        names = _I18N.get(self.lang, _I18N["en"]).get("tabnames", ["Tab1", "Tab2", "Tab3", "Tab4"])
        if 0 <= current_tab < len(names):
            self.update_status(self._t("status_current", name=names[current_tab]))

    def update_status(self, message):
        """更新状态信息"""
        self.status_label.config(text=message)
        try:
            self.root.update_idletasks()
        except Exception:
            pass


def main():
    """主函数（独立运行时）"""
    root = tk.Tk()
    ProcessingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()