import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from tools.app.services.data_processing.zip_extractor.processors.proactive_processor import ProactiveLogParser
from tools.app.services.data_processing.zip_extractor.processors.return_processor import ReturnLogParser
import re

# 导入共享的数据库管理器
import sys
import os

# 添加 pqat_downloader 的路径到 Python 路径
pqat_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'pqat_downloader', 'db'
)
sys.path.insert(0, pqat_path)
from tools.app.services.data_processing.pqat_downloader.db.db_manager import db_manager

pd.set_option('future.no_silent_downcasting', True)

# =====================
# i18n resources
# =====================
I18N = {
    "zh": {
        "win_title": "Zip压缩日志文件提取",
        "title": "Zip压缩日志文件提取",

        "input_frame": "输入文件设置",
        "btn_add_file": "添加文件",
        "btn_add_folder": "添加文件夹",
        "btn_remove_file": "移除文件",
        "btn_remove_all": "移除所有",

        "btn_db_view": "查看数据库内容",

        "btn_process": "处理ZIP文件",
        "btn_stats": "显示统计图表",
        "btn_export": "导出处理结果",

        "log_frame": "处理日志",

        "dlg_pick_sn_folder": "选择包含ZIP文件的文件夹",
        "dlg_pick_folder": "选择包含ZIP文件的文件夹",

        "warn": "警告",
        "err": "错误",
        "success": "成功",

        "warn_need_input": "请至少添加一个输入路径或文件夹",
        "warn_sn_invalid": "输入文件的文件夹名称必须以有效的SN号结尾，例如：CN3A023818",
        "warn_no_data_export": "没有可导出的数据",
        "warn_no_data_stats": "请先处理ZIP文件或数据库中没有数据",

        "log_welcome": "欢迎使用Zip压缩日志文件提取工具",
        "log_note1": "注意：输入路径应以 SN 号结尾（如：CN3A023818）",
        "log_note2": "或者选择文件夹，程序会自动搜索其中的ZIP文件",
        "log_db": "使用共享数据库: {path}",

        "log_add_file": "添加文件: {path}",
        "log_add_folder": "添加文件夹: {path}",
        "log_auto_search": "程序将自动搜索该文件夹中的所有ZIP文件",
        "log_remove_file": "移除文件: {path}",
        "log_clear": "已清空所有文件",

        "log_path_parse": "路径解析: Platform={platform}, Model={model}, Issue={issue}",
        "log_path_parse_err": "路径解析错误: {msg}",
        "log_zip_parse": "从ZIP路径解析: Platform={platform}, Model={model}, Issue={issue}",
        "log_zip_parse_err": "ZIP路径解析错误: {msg}",

        "log_detect_return": "检测到Return格式文件: {name}",
        "log_detect_proactive": "检测到Proactive格式文件: {name}",
        "log_detect_unknown": "警告: 无法识别文件格式，默认使用Proactive解析器: {name}",

        "log_processing_path": "处理路径: {path}",
        "log_sn_mode": "SN路径 - Platform: {platform}, Model: {model}, Issue: {issue}",
        "log_folder_mode": "普通文件夹模式，将尝试从ZIP文件路径提取信息",
        "log_found_zip": "找到 {n} 个ZIP文件",
        "log_processing_file": "正在处理: {name}",
        "log_skip_done": "文件已处理过，跳过: {name}",
        "log_parsed_ok": "使用 {parser} 成功解析文件",
        "log_saved_to": "结果已保存到: {path}",
        "log_failed": "处理失败 {name}: {msg}",
        "log_done": "处理完成！共处理 {n} 个ZIP文件",
        "log_total_rows": "总数据量: {n} 行",
        "log_none": "没有成功处理任何文件",

        "log_db_saved": "成功保存到共享数据库: {name}",
        "log_db_exists": "文件已存在于共享数据库: {name}",
        "log_db_save_err": "数据库保存错误: {msg}",

        "db_stats_title": "=== 数据库统计 ===",
        "db_stats_units": "Radio Units 总数: {n}",
        "db_stats_files": "日志文件总数: {n}",
        "db_stats_types": "各类型文件数量:",
        "db_type_extlog": " - ExtLog: {n}",
        "db_type_sfn": " - Site Failure Note: {n}",
        "db_type_proactive": " - Proactive Logs: {n}",
        "db_type_pics": " - HWS Scrap Pictures: {n}",
        "db_type_xlsx": " - Processed XLSX: {n}",

        "stats_win": "统计图表",
        "tab_serial": "序列号分布",
        "chart_title": "序列号分布（Top 10）",
        "others": "其他",
        "no_serial_data": "没有序列号数据可用",

        "export_title": "导出处理结果",
        "export_ok": "数据已成功导出到:\n{path}",
        "export_fail": "导出失败: {msg}",
        "sheet_all": "所有数据",
        "sheet_summary": "统计摘要",

        "summary_item": "统计项",
        "summary_value": "数值",
        "summary_total_rows": "总数据行数",
        "summary_unique_serials": "唯一序列号数量",

        "db_win": "共享数据库内容",
        "tab_units": "Radio Units",
        "tab_logs": "日志文件",
        "search": "搜索:",
        "btn_search": "搜索",
        "btn_show_all": "显示全部",

        "col_serial": "序列号",
        "col_model": "型号",
        "col_platform": "平台",
        "col_issue": "问题描述",
        "col_created": "创建日期",

        "col_log_type": "日志类型",
        "col_file_name": "文件名",
        "col_file_path": "文件路径",
        "col_download": "下载日期",

        "log_loaded_db": "从数据库加载了 {n} 条记录",
        "load_db_fail": "从数据库加载数据失败: {msg}",

        "log_type_unknown": "未知",

        # language toggle button label (shows the target language)
        "lang_btn": "EN",
    },

    "en": {
        "win_title": "ZIP Log Extractor",
        "title": "ZIP Log Extractor",

        "input_frame": "Input Settings",
        "btn_add_file": "Add SN Folder",
        "btn_add_folder": "Add Folder",
        "btn_remove_file": "Remove Selected",
        "btn_remove_all": "Remove All",

        "btn_db_view": "View Database",

        "btn_process": "Process ZIP Files",
        "btn_stats": "Show Charts",
        "btn_export": "Export Results",

        "log_frame": "Logs",

        "dlg_pick_sn_folder": "Select SN folder that contains ZIP files",
        "dlg_pick_folder": "Select a folder that contains ZIP files",

        "warn": "Warning",
        "err": "Error",
        "success": "Success",

        "warn_need_input": "Please add at least one input path or folder.",
        "warn_sn_invalid": "The folder name must end with a valid SN, e.g., CN3A023818",
        "warn_no_data_export": "No data to export.",
        "warn_no_data_stats": "Please process ZIP files first, or there is no data in the database.",

        "log_welcome": "Welcome to the ZIP log extraction tool",
        "log_note1": "Note: input path should end with a valid SN (e.g., CN3A023818)",
        "log_note2": "Or choose a folder and the program will search ZIP files automatically",
        "log_db": "Using shared database: {path}",

        "log_add_file": "Added: {path}",
        "log_add_folder": "Added folder: {path}",
        "log_auto_search": "The program will search all ZIP files under this folder",
        "log_remove_file": "Removed: {path}",
        "log_clear": "Cleared all inputs",

        "log_path_parse": "Path parsed: Platform={platform}, Model={model}, Issue={issue}",
        "log_path_parse_err": "Path parse error: {msg}",
        "log_zip_parse": "Parsed from ZIP path: Platform={platform}, Model={model}, Issue={issue}",
        "log_zip_parse_err": "ZIP path parse error: {msg}",

        "log_detect_return": "Detected Return format: {name}",
        "log_detect_proactive": "Detected Proactive format: {name}",
        "log_detect_unknown": "Warning: unknown filename pattern, defaulting to Proactive parser: {name}",

        "log_processing_path": "Processing path: {path}",
        "log_sn_mode": "SN mode - Platform: {platform}, Model: {model}, Issue: {issue}",
        "log_folder_mode": "Folder mode: will try to infer info from ZIP path",
        "log_found_zip": "Found {n} ZIP files",
        "log_processing_file": "Processing: {name}",
        "log_skip_done": "Already processed, skipped: {name}",
        "log_parsed_ok": "Parsed successfully with {parser}",
        "log_saved_to": "Saved to: {path}",
        "log_failed": "Failed {name}: {msg}",
        "log_done": "Done! Processed {n} ZIP files",
        "log_total_rows": "Total rows: {n}",
        "log_none": "No files were processed successfully",

        "log_db_saved": "Saved to shared database: {name}",
        "log_db_exists": "Already exists in shared database: {name}",
        "log_db_save_err": "Database save error: {msg}",

        "db_stats_title": "=== Database Stats ===",
        "db_stats_units": "Total Radio Units: {n}",
        "db_stats_files": "Total log files: {n}",
        "db_stats_types": "Counts by type:",
        "db_type_extlog": " - ExtLog: {n}",
        "db_type_sfn": " - Site Failure Note: {n}",
        "db_type_proactive": " - Proactive Logs: {n}",
        "db_type_pics": " - HWS Scrap Pictures: {n}",
        "db_type_xlsx": " - Processed XLSX: {n}",

        "stats_win": "Charts",
        "tab_serial": "Serial Distribution",
        "chart_title": "Distribution of Radio Serials (Top 10)",
        "others": "Others",
        "no_serial_data": "No serial data available",

        "export_title": "Export Results",
        "export_ok": "Export completed:\n{path}",
        "export_fail": "Export failed: {msg}",
        "sheet_all": "All Data",
        "sheet_summary": "Summary",

        "summary_item": "Metric",
        "summary_value": "Value",
        "summary_total_rows": "Total rows",
        "summary_unique_serials": "Unique serial count",

        "db_win": "Shared Database",
        "tab_units": "Radio Units",
        "tab_logs": "Log Files",
        "search": "Search:",
        "btn_search": "Search",
        "btn_show_all": "Show All",

        "col_serial": "Serial",
        "col_model": "Model",
        "col_platform": "Platform",
        "col_issue": "Issue",
        "col_created": "Created Date",

        "col_log_type": "Log Type",
        "col_file_name": "File Name",
        "col_file_path": "File Path",
        "col_download": "Download Date",

        "log_loaded_db": "Loaded {n} records from database",
        "load_db_fail": "Failed to load from database: {msg}",

        "log_type_unknown": "Unknown",

        # language toggle button label (shows the target language)
        "lang_btn": "中文",
    }
}


class ZipExtractorGUI:
    def __init__(self, parent):
        self.root = parent

        # i18n
        self.lang = "zh"  # 默认中文；如需默认英文可改为 "en"

        # 设置深色主题
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#007acc"
        self.frame_bg = "#2d2d2d"
        self.entry_bg = "#3d3d3d"
        self.setup_dark_theme()
        self.setup_ui()

        # 存储处理结果的DataFrame
        self.processed_data = pd.DataFrame()

        # 输入路径
        self.input_paths = []

        # 定义文件名格式
        self.proactive_formats = [
            r".*_(\d{8})_(\d{6})_Logfiles\.zip$",
            r".*_(\d{8})_(\d{6})_logfiles\.zip$"
        ]
        self.return_formats = [
            r"^(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})-.*\.zip$",
            r"^.*_(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})-.*\.zip$",
            r"^.*_(\d{4}-\d{2}-\d{2}) (\d{2}\.\d{2}\.\d{2})\s*-\s*.*\.zip$"
        ]

        # 设置窗口标题（如果 parent 是 Tk/Toplevel）
        try:
            self.root.title(self.t("win_title"))
        except Exception:
            pass

    # ---------------------
    # i18n helpers
    # ---------------------
    def t(self, key, **kwargs):
        text = I18N.get(self.lang, I18N["en"]).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.apply_language()

    def apply_language(self):
        try:
            self.root.title(self.t("win_title"))
        except Exception:
            pass

        # title bar
        if hasattr(self, "title_label"):
            self.title_label.configure(text=self.t("title"))
        if hasattr(self, "lang_btn"):
            self.lang_btn.configure(text=self.t("lang_btn"))

        # frames
        if hasattr(self, "input_frame"):
            self.input_frame.configure(text=self.t("input_frame"))
        if hasattr(self, "log_frame"):
            self.log_frame.configure(text=self.t("log_frame"))

        # buttons
        mapping = [
            ("btn_add_file", "btn_add_file"),
            ("btn_add_folder", "btn_add_folder"),
            ("btn_remove_file", "btn_remove_file"),
            ("btn_remove_all", "btn_remove_all"),
            ("btn_db_view", "btn_db_view"),
            ("btn_process", "btn_process"),
            ("btn_stats", "btn_stats"),
            ("btn_export", "btn_export"),
        ]
        for attr, key in mapping:
            if hasattr(self, attr):
                getattr(self, attr).configure(text=self.t(key))

    def setup_dark_theme(self):
        """设置深色主题"""
        style = ttk.Style()

        # 配置黑色文字样式（若你有需要用黑色文字的 Entry/Combobox）
        style.configure("Black.TEntry", fieldbackground=self.entry_bg, foreground="#000000")
        style.configure("Black.TCombobox", fieldbackground=self.entry_bg, foreground="#000000")

        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)

        style.configure("TButton", background=self.accent_color, foreground="#000000")
        style.map(
            "TButton",
            background=[("active", self.accent_color), ("pressed", self.accent_color)],
            foreground=[("active", "#000000"), ("pressed", "#000000")]
        )

        style.configure("TEntry", fieldbackground=self.entry_bg, foreground=self.fg_color)
        style.configure("TCombobox", fieldbackground=self.entry_bg, foreground=self.fg_color)

        # 白色文字的 LabelFrame 样式
        style.configure("White.TLabelframe", background=self.bg_color, foreground=self.fg_color)
        style.configure("White.TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)

        style.configure("TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)

        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", background=self.frame_bg, foreground=self.fg_color)
        style.map("TNotebook.Tab", background=[("selected", self.accent_color)])

    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题栏：左侧标题 + 右侧 EN/中文 切换按钮
        title_bar = ttk.Frame(main_frame)
        title_bar.pack(fill=tk.X, pady=10)

        self.title_label = ttk.Label(
            title_bar,
            text=self.t("title"),
            font=("Arial", 16, "bold"),
            foreground=self.fg_color,
            background=self.bg_color
        )
        self.title_label.pack(side=tk.LEFT)

        self.lang_btn = ttk.Button(
            title_bar,
            text=self.t("lang_btn"),
            command=self.toggle_language
        )
        self.lang_btn.pack(side=tk.RIGHT, padx=5)

        # 输入路径设置框架
        self.input_frame = ttk.LabelFrame(
            main_frame, text=self.t("input_frame"), padding="10", style="White.TLabelframe"
        )
        self.input_frame.pack(fill=tk.X, pady=5)

        # 输入路径列表和按钮
        self.input_listbox = tk.Listbox(
            self.input_frame, height=4, bg=self.entry_bg, fg=self.fg_color,
            selectbackground=self.accent_color
        )
        self.input_listbox.pack(fill=tk.X, pady=5)

        input_button_frame = ttk.Frame(self.input_frame)
        input_button_frame.pack(fill=tk.X)

        self.btn_add_file = ttk.Button(input_button_frame, text=self.t("btn_add_file"), command=self.add_input_path)
        self.btn_add_file.pack(side=tk.LEFT, padx=5)

        self.btn_add_folder = ttk.Button(input_button_frame, text=self.t("btn_add_folder"), command=self.add_folder)
        self.btn_add_folder.pack(side=tk.LEFT, padx=5)

        self.btn_remove_file = ttk.Button(input_button_frame, text=self.t("btn_remove_file"), command=self.remove_input_path)
        self.btn_remove_file.pack(side=tk.LEFT, padx=5)

        self.btn_remove_all = ttk.Button(input_button_frame, text=self.t("btn_remove_all"), command=self.clear_input_paths)
        self.btn_remove_all.pack(side=tk.LEFT, padx=5)

        # 数据库管理按钮框架
        db_frame = ttk.Frame(main_frame)
        db_frame.pack(fill=tk.X, pady=5)

        self.btn_db_view = ttk.Button(db_frame, text=self.t("btn_db_view"), command=self.show_database_content)
        self.btn_db_view.pack(side=tk.LEFT, padx=5)

        # 处理按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.btn_process = ttk.Button(button_frame, text=self.t("btn_process"), command=self.process_all_zips)
        self.btn_process.pack(side=tk.LEFT, padx=5)

        self.btn_stats = ttk.Button(button_frame, text=self.t("btn_stats"), command=self.show_statistics)
        self.btn_stats.pack(side=tk.LEFT, padx=5)

        self.btn_export = ttk.Button(button_frame, text=self.t("btn_export"), command=self.export_results)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        # 日志显示框架
        self.log_frame = ttk.LabelFrame(main_frame, text=self.t("log_frame"), padding="10", style="White.TLabelframe")
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(self.log_frame, height=15, bg=self.entry_bg, fg=self.fg_color,
                                insertbackground=self.fg_color)
        scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 初始日志
        self.log(self.t("log_welcome"))
        self.log(self.t("log_note1"))
        self.log(self.t("log_note2"))
        self.log(self.t("log_db", path=db_manager.db_path))

    def log(self, message):
        """添加日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    def add_input_path(self):
        """添加输入路径（SN 文件夹）"""
        path = filedialog.askdirectory(title=self.t("dlg_pick_sn_folder"))
        if path:
            # 修正：正确的 SN 正则（10位字母数字）
            sn_pattern = re.compile(r"[A-Z0-9]{10}$", re.IGNORECASE)
            last_part = os.path.basename(path)
            if not sn_pattern.match(last_part):
                messagebox.showwarning(self.t("warn"), self.t("warn_sn_invalid"))
                return

            if path not in self.input_paths:
                self.input_paths.append(path)
                self.input_listbox.insert(tk.END, path)
                self.log(self.t("log_add_file", path=path))

    def add_folder(self):
        """添加文件夹，自动搜索其中的ZIP文件"""
        folder = filedialog.askdirectory(title=self.t("dlg_pick_folder"))
        if folder:
            if folder not in self.input_paths:
                self.input_paths.append(folder)
                self.input_listbox.insert(tk.END, folder)
                self.log(self.t("log_add_folder", path=folder))
                self.log(self.t("log_auto_search"))

    def remove_input_path(self):
        """移除选中的输入路径"""
        selection = self.input_listbox.curselection()
        if selection:
            index = selection[0]
            path = self.input_paths.pop(index)
            self.input_listbox.delete(index)
            self.log(self.t("log_remove_file", path=path))

    def clear_input_paths(self):
        """清空所有输入路径"""
        self.input_paths.clear()
        self.input_listbox.delete(0, tk.END)
        self.log(self.t("log_clear"))

    def extract_path_info(self, input_path):
        """
        从输入路径中提取 Platform, Model, Issue 信息
        路径格式: .../Platform/Model/xxx_issues/SN
        """
        try:
            normalized_path = os.path.normpath(input_path)
            path_parts = normalized_path.split(os.sep)

            base_index = -1
            for i, part in enumerate(path_parts):
                if "files_to_be_processed" in part.lower():
                    base_index = i
                    break

            if base_index == -1:
                if len(path_parts) >= 3:
                    issue = path_parts[-1]
                    model = path_parts[-2]
                    platform = path_parts[-3]
                else:
                    platform, model, issue = "Unknown", "Unknown", "Unknown"
            else:
                relevant_parts = path_parts[base_index + 1:]
                if len(relevant_parts) >= 3:
                    platform = relevant_parts[0]
                    model = relevant_parts[1]
                    issue = relevant_parts[2]
                elif len(relevant_parts) == 2:
                    platform = relevant_parts[0]
                    model = relevant_parts[1]
                    issue = "Unknown"
                elif len(relevant_parts) == 1:
                    platform = relevant_parts[0]
                    model, issue = "Unknown", "Unknown"
                else:
                    platform, model, issue = "Unknown", "Unknown", "Unknown"

            self.log(self.t("log_path_parse", platform=platform, model=model, issue=issue))
            return platform, model, issue
        except Exception as e:
            self.log(self.t("log_path_parse_err", msg=str(e)))
            return "Unknown", "Unknown", "Unknown"

    def extract_info_from_zip_path(self, zip_path):
        """
        从ZIP文件路径中提取 Platform, Model, Issue 信息
        适用于文件夹模式，从ZIP文件所在目录结构推断信息
        """
        try:
            normalized_path = os.path.normpath(zip_path)
            path_parts = normalized_path.split(os.sep)
            dir_parts = path_parts[:-1]  # 去掉文件名部分

            platform, model, issue = "Unknown", "Unknown", "Unknown"

            sn_pattern = re.compile(r"[A-Z0-9]{10}$", re.IGNORECASE)
            for part in reversed(dir_parts):
                if sn_pattern.match(part):
                    issue = part
                    break

            for i, part in enumerate(dir_parts):
                if "platform" in part.lower():
                    platform = part
                elif "model" in part.lower():
                    model = part
                elif "issue" in part.lower() and i > 0:
                    issue = dir_parts[i - 1] if i > 0 else "Unknown"

            self.log(self.t("log_zip_parse", platform=platform, model=model, issue=issue))
            return platform, model, issue
        except Exception as e:
            self.log(self.t("log_zip_parse_err", msg=str(e)))
            return "Unknown", "Unknown", "Unknown"

    def determine_parser_type(self, zip_filename):
        """根据文件名判断应该使用哪个解析器"""
        for pattern in self.return_formats:
            if re.match(pattern, zip_filename, re.IGNORECASE):
                self.log(self.t("log_detect_return", name=zip_filename))
                return "return"

        for pattern in self.proactive_formats:
            if re.match(pattern, zip_filename, re.IGNORECASE):
                self.log(self.t("log_detect_proactive", name=zip_filename))
                return "proactive"

        self.log(self.t("log_detect_unknown", name=zip_filename))
        return "proactive"

    def parse_zip_file(self, input_zip, input_path, platform, model, issue):
        """
        解析ZIP文件并提取平台、型号、Issue信息
        """
        zip_filename = os.path.basename(input_zip)
        parser_type = self.determine_parser_type(zip_filename)

        if parser_type == "return":
            self.log("DEBUG: 根据文件名判断，使用ReturnLogParser...")
            try:
                df = ReturnLogParser.parse(input_zip)
                self.log("DEBUG: ReturnLogParser succeeded")
                return "ReturnLogParser", df
            except Exception as e:
                self.log(f"DEBUG: ReturnLogParser failed: {str(e)}")
                self.log("DEBUG: 尝试备用解析器ProactiveLogParser...")
                try:
                    df = ProactiveLogParser.parse(input_zip)
                    self.log("DEBUG: ProactiveLogParser succeeded")
                    return "ProactiveLogParser", df
                except Exception as e2:
                    self.log(f"DEBUG: ProactiveLogParser also failed: {str(e2)}")
                    raise Exception(f"两种解析器都无法处理文件: Return错误: {str(e)}, Proactive错误: {str(e2)}")

        else:
            self.log("DEBUG: 根据文件名判断，使用ProactiveLogParser...")
            try:
                df = ProactiveLogParser.parse(input_zip)
                self.log("DEBUG: ProactiveLogParser succeeded")
                return "ProactiveLogParser", df
            except Exception as e:
                self.log(f"DEBUG: ProactiveLogParser failed: {str(e)}")
                self.log("DEBUG: 尝试备用解析器ReturnLogParser...")
                try:
                    df = ReturnLogParser.parse(input_zip)
                    self.log("DEBUG: ReturnLogParser succeeded")
                    return "ReturnLogParser", df
                except Exception as e2:
                    self.log(f"DEBUG: ReturnLogParser also failed: {str(e2)}")
                    raise Exception(f"两种解析器都无法处理文件: Proactive错误: {str(e)}, Return错误: {str(e2)}")

    def save_to_database(self, zip_file_path, xlsx_file_path, platform, model, issue, file_size, df):
        """将处理结果保存到共享数据库"""
        try:
            serial_number = "Unknown"
            if 'Serial' in df.columns and not df['Serial'].empty:
                valid_serials = df[df['Serial'].notna()]['Serial']
                if not valid_serials.empty:
                    serial_number = valid_serials.iloc[0]

            success = db_manager.add_log_file(
                serial_number=serial_number,
                log_type=5,  # 5 表示处理后的XLSX文件
                file_name=os.path.basename(xlsx_file_path),
                file_path=xlsx_file_path,
                file_size=file_size,
                model=model,
                platform=platform,
                issue_description=issue
            )

            if success:
                self.log(self.t("log_db_saved", name=os.path.basename(xlsx_file_path)))
            else:
                self.log(self.t("log_db_exists", name=os.path.basename(xlsx_file_path)))

            return success
        except Exception as e:
            self.log(self.t("log_db_save_err", msg=str(e)))
            return False

    def process_all_zips(self):
        """处理所有输入路径下的ZIP文件"""
        if not self.input_paths:
            messagebox.showwarning(self.t("warn"), self.t("warn_need_input"))
            return

        all_data = []
        total_processed = 0

        for input_path in self.input_paths:
            self.log(self.t("log_processing_path", path=input_path))

            is_sn_path = False
            sn_pattern = re.compile(r"[A-Z0-9]{10}$", re.IGNORECASE)
            last_part = os.path.basename(input_path)

            if sn_pattern.match(last_part):
                is_sn_path = True
                platform, model, issue = self.extract_path_info(input_path)
                self.log(self.t("log_sn_mode", platform=platform, model=model, issue=issue))
            else:
                platform, model, issue = "Unknown", "Unknown", "Unknown"
                self.log(self.t("log_folder_mode"))

            zip_files = []
            for root_dir, _, files in os.walk(input_path):
                for file in files:
                    if file.lower().endswith('.zip'):
                        full_path = os.path.join(root_dir, file)
                        zip_files.append(full_path)

            self.log(self.t("log_found_zip", n=len(zip_files)))

            for zip_path in zip_files:
                try:
                    filename = os.path.basename(zip_path)
                    self.log(self.t("log_processing_file", name=filename))

                    xlsx_filename = f"{os.path.splitext(filename)[0]}_extracted.xlsx"
                    existing_records = db_manager.search_radio_units(xlsx_filename)
                    if existing_records:
                        self.log(self.t("log_skip_done", name=filename))
                        continue

                    if not is_sn_path:
                        zip_platform, zip_model, zip_issue = self.extract_info_from_zip_path(zip_path)
                        if zip_platform != "Unknown":
                            platform = zip_platform
                        if zip_model != "Unknown":
                            model = zip_model
                        if zip_issue != "Unknown":
                            issue = zip_issue

                    parser_name, df = self.parse_zip_file(zip_path, input_path, platform, model, issue)
                    self.log(self.t("log_parsed_ok", parser=parser_name))

                    output_excel = os.path.join(os.path.dirname(zip_path), xlsx_filename)

                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name="Submit Pattern Lines", index=False)

                    file_size = os.path.getsize(output_excel)
                    self.save_to_database(zip_path, output_excel, platform, model, issue, file_size, df)

                    all_data.append(df)
                    total_processed += 1
                    self.log(self.t("log_saved_to", path=output_excel))

                except Exception as e:
                    self.log(self.t("log_failed", name=os.path.basename(zip_path), msg=str(e)))
                    continue

        if all_data:
            self.processed_data = pd.concat(all_data, ignore_index=True)
            self.log(self.t("log_done", n=total_processed))
            self.log(self.t("log_total_rows", n=len(self.processed_data)))
            self.show_database_stats()
        else:
            self.log(self.t("log_none"))

    def show_database_content(self):
        """显示数据库内容"""
        try:
            db_window = tk.Toplevel(self.root)
            db_window.title(self.t("db_win"))
            db_window.geometry("1200x600")

            notebook = ttk.Notebook(db_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Radio Units tab
            units_frame = ttk.Frame(notebook, padding="10")
            notebook.add(units_frame, text=self.t("tab_units"))

            search_frame = ttk.Frame(units_frame)
            search_frame.pack(fill=tk.X, pady=5)

            ttk.Label(search_frame, text=self.t("search")).pack(side=tk.LEFT, padx=5)
            search_var = tk.StringVar()
            ttk.Entry(search_frame, textvariable=search_var, width=30).pack(side=tk.LEFT, padx=5)

            units_columns = ("serial_number", "model", "platform", "issue_description", "created_date")
            units_tree = ttk.Treeview(units_frame, columns=units_columns, show="headings", height=15)

            units_tree.heading("serial_number", text=self.t("col_serial"))
            units_tree.heading("model", text=self.t("col_model"))
            units_tree.heading("platform", text=self.t("col_platform"))
            units_tree.heading("issue_description", text=self.t("col_issue"))
            units_tree.heading("created_date", text=self.t("col_created"))

            units_tree.column("serial_number", width=150)
            units_tree.column("model", width=150)
            units_tree.column("platform", width=100)
            units_tree.column("issue_description", width=200)
            units_tree.column("created_date", width=150)

            scrollbar = ttk.Scrollbar(units_frame, orient=tk.VERTICAL, command=units_tree.yview)
            units_tree.configure(yscrollcommand=scrollbar.set)
            units_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            def perform_search():
                search_term = search_var.get()
                for item in units_tree.get_children():
                    units_tree.delete(item)
                results = db_manager.search_radio_units(search_term)
                for result in results:
                    units_tree.insert("", "end", values=(
                        result["serial_number"],
                        result["model"] or "",
                        result["platform"] or "",
                        result["issue_description"] or "",
                        result["created_date"]
                    ))

            ttk.Button(search_frame, text=self.t("btn_search"), command=perform_search).pack(side=tk.LEFT, padx=5)
            ttk.Button(
                search_frame,
                text=self.t("btn_show_all"),
                command=lambda: [search_var.set(""), perform_search()]
            ).pack(side=tk.LEFT, padx=5)

            # Log Files tab
            logs_frame = ttk.Frame(notebook, padding="10")
            notebook.add(logs_frame, text=self.t("tab_logs"))

            logs_columns = ("serial_number", "log_type", "file_name", "file_path", "download_date")
            logs_tree = ttk.Treeview(logs_frame, columns=logs_columns, show="headings", height=15)

            logs_tree.heading("serial_number", text=self.t("col_serial"))
            logs_tree.heading("log_type", text=self.t("col_log_type"))
            logs_tree.heading("file_name", text=self.t("col_file_name"))
            logs_tree.heading("file_path", text=self.t("col_file_path"))
            logs_tree.heading("download_date", text=self.t("col_download"))

            logs_tree.column("serial_number", width=150)
            logs_tree.column("log_type", width=100)
            logs_tree.column("file_name", width=200)
            logs_tree.column("file_path", width=300)
            logs_tree.column("download_date", width=150)

            logs_scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=logs_tree.yview)
            logs_tree.configure(yscrollcommand=logs_scrollbar.set)
            logs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            logs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            perform_search()
            self.load_log_files(logs_tree)

        except Exception as e:
            messagebox.showerror(self.t("err"), f"{self.t('load_db_fail', msg=str(e))}")

    def load_log_files(self, tree):
        """加载日志文件数据"""
        for item in tree.get_children():
            tree.delete(item)

        units = db_manager.search_radio_units("")
        for unit in units:
            log_files = db_manager.get_log_files(unit["serial_number"])
            for log_file in log_files:
                log_type_map = {
                    1: "ExtLog", 2: "Site Failure Note", 3: "Proactive Logs",
                    4: "HWS Scrap Pictures", 5: "Processed XLSX"
                }
                log_type_name = log_type_map.get(log_file["log_type"], self.t("log_type_unknown"))
                tree.insert("", "end", values=(
                    unit["serial_number"],
                    log_type_name,
                    log_file["file_name"],
                    log_file["file_path"],
                    log_file["download_date"]
                ))

    def show_database_stats(self):
        """显示数据库统计信息"""
        try:
            units = db_manager.search_radio_units("")
            total_files = 0
            file_types = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

            for unit in units:
                log_files = db_manager.get_log_files(unit["serial_number"])
                total_files += len(log_files)
                for log_file in log_files:
                    if log_file["log_type"] in file_types:
                        file_types[log_file["log_type"]] += 1

            self.log(self.t("db_stats_title"))
            self.log(self.t("db_stats_units", n=len(units)))
            self.log(self.t("db_stats_files", n=total_files))
            self.log(self.t("db_stats_types"))
            self.log(self.t("db_type_extlog", n=file_types[1]))
            self.log(self.t("db_type_sfn", n=file_types[2]))
            self.log(self.t("db_type_proactive", n=file_types[3]))
            self.log(self.t("db_type_pics", n=file_types[4]))
            self.log(self.t("db_type_xlsx", n=file_types[5]))
        except Exception as e:
            self.log(self.t("log_db_save_err", msg=str(e)))

    def show_statistics(self):
        """显示统计图表"""
        if self.processed_data.empty:
            try:
                self.load_data_from_database()
            except Exception:
                messagebox.showwarning(self.t("warn"), self.t("warn_no_data_stats"))
                return

        stats_window = tk.Toplevel(self.root)
        stats_window.title(self.t("stats_win"))
        stats_window.geometry("1000x800")

        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        serial_frame = ttk.Frame(notebook)
        notebook.add(serial_frame, text=self.t("tab_serial"))

        self.create_serial_chart(serial_frame)

    def load_data_from_database(self):
        """从数据库加载数据到processed_data"""
        try:
            all_data = []
            units = db_manager.search_radio_units("")
            for unit in units:
                temp_df = pd.DataFrame({
                    "Serial": [unit["serial_number"]]
                })
                all_data.append(temp_df)

            if all_data:
                self.processed_data = pd.concat(all_data, ignore_index=True)
                self.log(self.t("log_loaded_db", n=len(self.processed_data)))
            else:
                raise Exception("no data")
        except Exception as e:
            raise Exception(self.t("load_db_fail", msg=str(e)))

    def create_serial_chart(self, parent):
        """创建序列号分布饼图（显示前10个最常见的序列号）"""
        if 'Serial' in self.processed_data.columns:
            serial_counts = self.processed_data['Serial'].value_counts()

            if len(serial_counts) > 10:
                top_serials = serial_counts.head(10)
                other_count = serial_counts[10:].sum()
                top_serials[self.t("others")] = other_count
                serial_counts = top_serials

            fig, ax = plt.subplots(figsize=(8, 6))
            colors = sns.color_palette('pastel', len(serial_counts))
            wedges, texts, autotexts = ax.pie(
                serial_counts.values,
                labels=serial_counts.index,
                autopct='%1.1f%%',
                colors=colors,
                startangle=90
            )

            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontsize(8)

            ax.set_title(self.t("chart_title"), fontsize=14, fontweight='bold')

            canvas = FigureCanvasTkAgg(fig, parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(parent, text=self.t("no_serial_data"), font=("Arial", 12)).pack(expand=True)

    def export_results(self):
        """导出处理结果"""
        if self.processed_data.empty:
            messagebox.showwarning(self.t("warn"), self.t("warn_no_data_export"))
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title=self.t("export_title")
        )

        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    self.processed_data.to_excel(writer, sheet_name=self.t("sheet_all"), index=False)
                    summary_data = self.create_summary()
                    summary_data.to_excel(writer, sheet_name=self.t("sheet_summary"), index=False)

                self.log(self.t("log_saved_to", path=file_path))
                messagebox.showinfo(self.t("success"), self.t("export_ok", path=file_path))
            except Exception as e:
                messagebox.showerror(self.t("err"), self.t("export_fail", msg=str(e)))

    def create_summary(self):
        """创建统计摘要"""
        summary = {
            self.t('summary_item'): [self.t('summary_total_rows'), self.t('summary_unique_serials')],
            self.t('summary_value'): [
                len(self.processed_data),
                self.processed_data['Serial'].nunique() if 'Serial' in self.processed_data.columns else 0
            ]
        }
        return pd.DataFrame(summary)


def main():
    """主函数"""
    root = tk.Tk()
    ZipExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()