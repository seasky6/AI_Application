import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from tools.app.services.data_processing.data_processor.extractor.pa_issue_extractor import PaIssueExtractor
from tools.app.services.data_processing.data_processor.labeler.pa_issue_labeler import PaIssueLabeler

# =====================
# i18n resources (minimal invasive)
# =====================
I18N = {
    "zh": {
        "win_title": "生成样本数据",
        "title": "生成样本数据",

        "input_frame": "输入文件设置",
        "input_hint": "选择输入文件或者文件夹:",
        "btn_add_file": "添加文件",
        "btn_add_folder": "添加文件夹",
        "btn_clear_all": "清除所有",
        "file_count": "已选择 {n} 个文件",

        "output_frame": "输出路径设置",
        "output_hint": "选择输出目录:",
        "btn_browse_dir": "浏览目录",

        "issue_frame": "问题类型设置",
        "issue_type": "问题类型:",

        "extractor_frame": "特征抽取设置",
        "extractor_select": "选择特征抽取器:",
        "extractor_desc_default": "特征抽取器描述",

        "labeler_frame": "打标器设置",
        "labeler_select": "选择打标器:",
        "labeler_desc_default": "打标器描述",

        "method_frame": "打标方法选择",
        "method_pattern1": "Pattern分析方法一",
        "method_pattern2": "Pattern分析方法二",
        "method_repair": "Repair Info方法",

        "logopt_frame": "日志设置",
        "save_repair_logs": "保存Repair Info详细日志",
        "logopt_desc": "如果勾选，repair_info方法的详细调试日志将保存到logs文件夹中",

        "progress_frame": "处理进度",
        "status_ready": "就绪",
        "status_processing": "处理中...",
        "status_done": "完成",
        "status_error": "错误",

        "log_display_frame": "处理日志",

        "btn_start": "开始处理",
        "btn_clear_log": "清空日志",
        "btn_exit": "退出",

        "warn": "警告",
        "error": "错误",

        "warn_need_method": "请至少选择一种打标方法",
        "err_need_input": "请选择输入文件",
        "err_need_output": "请选择输出目录",

        "dlg_select_json": "选择JSON文件",
        "dlg_select_json_folder": "选择包含JSON文件的文件夹(支持多选)",
        "dlg_select_output": "选择输出目录",

        "json_error_title": "JSON错误",
        "json_error_body": "文件不是有效的JSON格式: {path}\n错误: {err}",

        "log_added_files": "已添加 {n} 个文件",
        "log_folder_exists": "文件夹已存在: {folder}",
        "log_scanning": "正在扫描文件夹: {folder}",
        "log_scan_error": "扫描文件夹时出错: {err}",
        "log_file_invalid": "文件验证失败: {name} - {msg}",
        "log_scan_done": "扫描完成: 从 '{name}' 中找到 {total} 个JSON文件",
        "log_scan_stat": "有效文件: {ok} 个, 无效文件: {bad} 个",
        "log_scan_hint": "无效文件可能由于路径格式不正确或JSON格式错误",

        "log_cleared_inputs": "已清除所有输入文件",
        "log_output_set": "输出目录设置为: {dir}",

        "log_start": "开始处理文件...",
        "log_input_count": "输入文件: {n} 个",
        "log_output_dir": "输出目录: {dir}",
        "log_issue_type": "问题类型: {issue}",
        "log_extractor": "特征抽取器: {name}",
        "log_labeler": "打标器: {name}",
        "log_methods": "打标方法: {methods}",

        "log_repair_on": "已启用Repair Info详细日志保存",
        "log_repair_off": "Repair Info详细日志保存已禁用",
        "log_repair_import_fail": "警告: 无法导入 repair_info 模块: {err}",
        "log_repair_unavailable": "Repair Info详细日志功能不可用",

        "log_use_extractor": "使用特征抽取器: {name}",
        "log_extractor_inst_fail": "错误: 无法实例化特征抽取器 {name}: {err}",
        "log_use_default_extractor": "使用默认的PaIssueExtractor",
        "log_unknown_extractor": "警告: 未知的特征抽取器 {name}，使用默认的PaIssueExtractor",

        "log_use_labeler": "使用打标器: {name}",
        "log_labeler_inst_fail": "错误: 无法实例化打标器 {name}: {err}",
        "log_use_default_labeler": "使用默认的PaIssueLabeler",
        "log_unknown_labeler": "警告: 未知的打标器 {name}，使用默认的PaIssueLabeler",

        "log_extracting": "正在提取样本...",
        "log_samples_count": "提取到的样本数量: {n}",
        "log_samples_empty": "警告: 提取到空样本列表!",

        "log_labeling": "正在打标样本...",
        "log_saving": "正在保存结果...",

        "log_repair_saved": "Repair Info详细日志已保存到: {path}",
        "log_repair_path_fail": "无法获取Repair Info日志文件路径",

        "log_done": "处理完成!",
        "log_error": "处理过程中发生错误: {err}",
        "log_trace": "详细错误信息: {trace}",

        # show target language on button
        "lang_btn": "EN",

        # extractor/labeler descriptions (zh)
        "ex_desc": {
            "PaIssueExtractor": "PA问题特征抽取器 - 提取PA相关的电压、电流、功率等特征",
            "DcdcIssueExtractor": "DCDC问题特征抽取器 - 提取DCDC电源相关的电压、电流、效率等特征",
            "DigitalIssueExtractor": "数字问题特征抽取器 - 提取数字电路相关的时序、逻辑状态等特征",
            "DpdIssueExtractor": "DPD问题特征抽取器 - 提取数字预失真相关的参数和性能指标",
            "FuIssueExtractor": "FU问题特征抽取器 - 提取频率单元相关的频率稳定度、相位噪声等特征",
            "LtuIssueExtractor": "LTU问题特征抽取器 - 提取线性化技术单元相关的特征参数",
            "NffIssueExtractor": "NFF问题特征抽取器 - 提取无故障发现相关的测试和诊断特征",
            "SwIssueExtractor": "软件问题特征抽取器 - 提取软件相关的日志、状态、性能指标",
            "TrxIssueExtractor": "TRX问题特征抽取器 - 提取收发器相关的射频性能和配置参数",
        },
        "lb_desc": {
            "PaIssueLabeler": "PA问题打标器 - 使用Pattern分析和Repair Info方法标注PA状态",
            "DcdcIssueLabeler": "DCDC问题打标器 - 使用电压稳定性分析和效率计算方法标注DCDC状态",
            "DigitalIssueLabeler": "数字问题打标器 - 使用时序分析和逻辑状态验证方法标注数字电路状态",
            "DpdIssueLabeler": "DPD问题打标器 - 使用线性度分析和预失真效果评估方法标注DPD状态",
            "FuIssueLabeler": "FU问题打标器 - 使用频率稳定度分析和相位噪声评估方法标注频率单元状态",
            "LtuIssueLabeler": "LTU问题打标器 - 使用线性化性能分析和参数优化方法标注LTU状态",
            "NffIssueLabeler": "NFF问题打标器 - 使用故障诊断和测试验证方法标注NFF状态",
            "SwIssueLabeler": "软件问题打标器 - 使用日志分析和性能监控方法标注软件状态",
            "TrxIssueLabeler": "TRX问题打标器 - 使用射频性能分析和配置验证方法标注收发器状态",
        },
    },

    "en": {
        "win_title": "Sample Generator",
        "title": "Sample Generator",

        "input_frame": "Input Settings",
        "input_hint": "Select input files or folders:",
        "btn_add_file": "Add Files",
        "btn_add_folder": "Add Folder",
        "btn_clear_all": "Clear All",
        "file_count": "{n} file(s) selected",

        "output_frame": "Output Settings",
        "output_hint": "Select output directory:",
        "btn_browse_dir": "Browse",

        "issue_frame": "Issue Type",
        "issue_type": "Issue Type:",

        "extractor_frame": "Extractor Settings",
        "extractor_select": "Select extractor:",
        "extractor_desc_default": "Extractor description",

        "labeler_frame": "Labeler Settings",
        "labeler_select": "Select labeler:",
        "labeler_desc_default": "Labeler description",

        "method_frame": "Labeling Methods",
        "method_pattern1": "Pattern Method 1",
        "method_pattern2": "Pattern Method 2",
        "method_repair": "Repair Info Method",

        "logopt_frame": "Logging Options",
        "save_repair_logs": "Save Repair Info detailed logs",
        "logopt_desc": "If checked, detailed debug logs of repair_info will be saved to the logs folder",

        "progress_frame": "Progress",
        "status_ready": "Ready",
        "status_processing": "Processing...",
        "status_done": "Done",
        "status_error": "Error",

        "log_display_frame": "Logs",

        "btn_start": "Start",
        "btn_clear_log": "Clear Log",
        "btn_exit": "Exit",

        "warn": "Warning",
        "error": "Error",

        "warn_need_method": "Please select at least one labeling method",
        "err_need_input": "Please select input files",
        "err_need_output": "Please select an output directory",

        "dlg_select_json": "Select JSON files",
        "dlg_select_json_folder": "Select a folder containing JSON files",
        "dlg_select_output": "Select output directory",

        "json_error_title": "JSON Error",
        "json_error_body": "Invalid JSON file: {path}\nError: {err}",

        "log_added_files": "Added {n} file(s)",
        "log_folder_exists": "Folder already added: {folder}",
        "log_scanning": "Scanning folder: {folder}",
        "log_scan_error": "Folder scan error: {err}",
        "log_file_invalid": "Invalid file: {name} - {msg}",
        "log_scan_done": "Scan finished: found {total} JSON file(s) in '{name}'",
        "log_scan_stat": "Valid: {ok}, Invalid: {bad}",
        "log_scan_hint": "Invalid files may have incorrect path format or invalid JSON",

        "log_cleared_inputs": "Cleared all input files",
        "log_output_set": "Output directory set to: {dir}",

        "log_start": "Start processing...",
        "log_input_count": "Input files: {n}",
        "log_output_dir": "Output directory: {dir}",
        "log_issue_type": "Issue type: {issue}",
        "log_extractor": "Extractor: {name}",
        "log_labeler": "Labeler: {name}",
        "log_methods": "Methods: {methods}",

        "log_repair_on": "Repair Info detailed logging enabled",
        "log_repair_off": "Repair Info detailed logging disabled",
        "log_repair_import_fail": "Warning: cannot import repair_info module: {err}",
        "log_repair_unavailable": "Repair Info logging feature is unavailable",

        "log_use_extractor": "Using extractor: {name}",
        "log_extractor_inst_fail": "Error: cannot instantiate extractor {name}: {err}",
        "log_use_default_extractor": "Using default PaIssueExtractor",
        "log_unknown_extractor": "Warning: unknown extractor {name}, using default PaIssueExtractor",

        "log_use_labeler": "Using labeler: {name}",
        "log_labeler_inst_fail": "Error: cannot instantiate labeler {name}: {err}",
        "log_use_default_labeler": "Using default PaIssueLabeler",
        "log_unknown_labeler": "Warning: unknown labeler {name}, using default PaIssueLabeler",

        "log_extracting": "Extracting samples...",
        "log_samples_count": "Extracted samples: {n}",
        "log_samples_empty": "Warning: extracted samples list is empty!",

        "log_labeling": "Labeling samples...",
        "log_saving": "Saving results...",

        "log_repair_saved": "Repair Info log saved to: {path}",
        "log_repair_path_fail": "Cannot get Repair Info log file path",

        "log_done": "Completed!",
        "log_error": "Processing error: {err}",
        "log_trace": "Traceback: {trace}",

        "lang_btn": "中文",

        # extractor/labeler descriptions (en)
        "ex_desc": {
            "PaIssueExtractor": "PA extractor - extracts PA-related voltage/current/power features",
            "DcdcIssueExtractor": "DCDC extractor - extracts power rail voltage/current/efficiency features",
            "DigitalIssueExtractor": "Digital extractor - extracts timing/logic status features",
            "DpdIssueExtractor": "DPD extractor - extracts DPD parameters and KPIs",
            "FuIssueExtractor": "FU extractor - extracts frequency stability and phase noise features",
            "LtuIssueExtractor": "LTU extractor - extracts linearization unit features",
            "NffIssueExtractor": "NFF extractor - extracts test/diagnosis features for NFF",
            "SwIssueExtractor": "SW extractor - extracts log/status/performance features",
            "TrxIssueExtractor": "TRX extractor - extracts RF performance and config features",
        },
        "lb_desc": {
            "PaIssueLabeler": "PA labeler - labels PA status via Pattern analysis and Repair Info",
            "DcdcIssueLabeler": "DCDC labeler - labels via voltage stability and efficiency analysis",
            "DigitalIssueLabeler": "Digital labeler - labels via timing analysis and logic validation",
            "DpdIssueLabeler": "DPD labeler - labels via linearity and predistortion evaluation",
            "FuIssueLabeler": "FU labeler - labels via stability and phase noise evaluation",
            "LtuIssueLabeler": "LTU labeler - labels via performance analysis and parameter optimization",
            "NffIssueLabeler": "NFF labeler - labels via diagnosis and test verification",
            "SwIssueLabeler": "SW labeler - labels via log analysis and performance monitoring",
            "TrxIssueLabeler": "TRX labeler - labels via RF analysis and configuration validation",
        },
    }
}


class DataProcessorGUI:
    def __init__(self, parent):
        self.root = parent

        # language
        self.lang = "zh"  # default

        # 设置深色主题
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#007acc"
        self.frame_bg = "#2d2d2d"
        self.entry_bg = "#3d3d3d"

        # 存储选择的文件路径
        self.input_paths = []
        self.output_path = ""

        # 提取器映射
        self.extractor_mapping = {
            "PaIssueExtractor": PaIssueExtractor
        }

        # 打标器映射
        self.labeler_mapping = {
            "PaIssueLabeler": PaIssueLabeler
        }

        self.setup_dark_theme()
        self.setup_ui()

        # 设置窗口标题（如果是顶层窗口）
        try:
            self.root.title(self.t("win_title"))
        except Exception:
            pass

    # ---------------------
    # i18n helpers
    # ---------------------
    def t(self, key, **kwargs):
        text = I18N.get(self.lang, I18N["en"]).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.apply_language()

    def apply_language(self):
        # window title
        try:
            self.root.title(self.t("win_title"))
        except Exception:
            pass

        # title + lang btn
        self.title_label.configure(text=self.t("title"))
        self.lang_btn.configure(text=self.t("lang_btn"))

        # frames titles
        self.input_frame.configure(text=self.t("input_frame"))
        self.output_frame.configure(text=self.t("output_frame"))
        self.issue_frame.configure(text=self.t("issue_frame"))
        self.extractor_frame.configure(text=self.t("extractor_frame"))
        self.labeler_frame.configure(text=self.t("labeler_frame"))
        self.method_frame.configure(text=self.t("method_frame"))
        self.log_setting_frame.configure(text=self.t("logopt_frame"))
        self.progress_frame.configure(text=self.t("progress_frame"))
        self.log_display_frame.configure(text=self.t("log_display_frame"))

        # static labels
        self.input_hint_label.configure(text=self.t("input_hint"))
        self.output_hint_label.configure(text=self.t("output_hint"))
        self.issue_type_label.configure(text=self.t("issue_type"))
        self.extractor_select_label.configure(text=self.t("extractor_select"))
        self.labeler_select_label.configure(text=self.t("labeler_select"))

        # buttons
        self.btn_add_file.configure(text=self.t("btn_add_file"))
        self.btn_add_folder.configure(text=self.t("btn_add_folder"))
        self.btn_clear_all.configure(text=self.t("btn_clear_all"))
        self.btn_browse_dir.configure(text=self.t("btn_browse_dir"))

        self.btn_start.configure(text=self.t("btn_start"))
        self.btn_clear_log.configure(text=self.t("btn_clear_log"))
        self.btn_exit.configure(text=self.t("btn_exit"))

        # checkbuttons
        self.cb_pattern1.configure(text=self.t("method_pattern1"))
        self.cb_pattern2.configure(text=self.t("method_pattern2"))
        self.cb_repair.configure(text=self.t("method_repair"))
        self.cb_save_repair.configure(text=self.t("save_repair_logs"))

        # log option desc
        self.log_desc_label.configure(text=self.t("logopt_desc"))

        # file count
        self.update_file_count()

        # status text: keep current semantic state if possible
        current = self.status_var.get()
        # naive mapping based on zh/en
        if current in ("就绪", "Ready"):
            self.status_var.set(self.t("status_ready"))
        elif current in ("处理中...", "Processing..."):
            self.status_var.set(self.t("status_processing"))
        elif current in ("完成", "Done"):
            self.status_var.set(self.t("status_done"))
        elif current in ("错误", "Error"):
            self.status_var.set(self.t("status_error"))

        # update extractor/labeler descriptions
        self.update_extractor_description(self.extractor_var.get())
        self.update_labeler_description(self.labeler_var.get())

    def setup_dark_theme(self):
        """设置深色主题"""
        style = ttk.Style()
        # 配置样式
        style.configure("Black.TEntry",
                        fieldbackground=self.entry_bg,
                        foreground="#000000")  # 黑色文字
        style.configure("Black.TCombobox",
                        fieldbackground=self.entry_bg,
                        foreground="#000000")  # 黑色文字
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("TButton",
                        background=self.accent_color,
                        foreground="#000000")  # 黑色字体
        style.map("TButton",
                  background=[("active", self.accent_color),
                              ("pressed", self.accent_color)],
                  foreground=[("active", "#000000"),
                              ("pressed", "#000000")])
        style.configure("TEntry", fieldbackground=self.entry_bg, foreground=self.fg_color)
        style.configure("TCombobox", fieldbackground=self.entry_bg, foreground=self.fg_color)

        # 白色文字的 LabelFrame 样式
        style.configure("White.TLabelframe",
                        background=self.bg_color,
                        foreground=self.fg_color)  # 白色字体
        style.configure("White.TLabelframe.Label",
                        background=self.frame_bg,
                        foreground=self.fg_color)  # 白色字体
        style.configure("TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)
        style.configure("TProgressbar", background=self.accent_color, troughcolor=self.frame_bg)

    def setup_ui(self):
        """设置用户界面"""

        # 创建主滚动框架
        main_scroll_frame = ttk.Frame(self.root)
        main_scroll_frame.pack(fill=tk.BOTH, expand=True)

        # 创建Canvas和滚动条
        self.canvas = tk.Canvas(main_scroll_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_scroll_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # 放置Canvas和滚动条
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建可滚动的框架
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # 绑定事件以调整可滚动区域
        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # 绑定鼠标滚轮事件
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self.on_mousewheel)

        # 主框架（放在可滚动框架内）
        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置权重
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # 创建黑色文字样式
        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        style.configure("Black.TCombobox", foreground="#000000")

        # ========== 标题行：保留原布局，只加语言按钮 ==========
        title_row = ttk.Frame(main_frame)
        title_row.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        title_row.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            title_row,
            text=self.t("title"),
            font=("Arial", 16, "bold"),
            foreground=self.fg_color,
            background=self.bg_color
        )
        self.title_label.grid(row=0, column=0, sticky=tk.W)

        self.lang_btn = ttk.Button(
            title_row,
            text=self.t("lang_btn"),
            command=self.toggle_language
        )
        self.lang_btn.grid(row=0, column=1, sticky=tk.E, padx=5)

        # 输入路径选择
        self.input_frame = ttk.LabelFrame(main_frame, text=self.t("input_frame"), padding="5", style="White.TLabelframe")
        self.input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self.input_frame.columnconfigure(0, weight=1)

        self.input_hint_label = ttk.Label(self.input_frame, text=self.t("input_hint"))
        self.input_hint_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        input_btn_frame = ttk.Frame(self.input_frame)
        input_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        input_btn_frame.columnconfigure(0, weight=1)

        self.btn_add_file = ttk.Button(input_btn_frame, text=self.t("btn_add_file"), command=self.select_input_files)
        self.btn_add_file.grid(row=0, column=0, padx=2)

        self.btn_add_folder = ttk.Button(input_btn_frame, text=self.t("btn_add_folder"), command=self.select_input_folder)
        self.btn_add_folder.grid(row=0, column=1, padx=2)

        self.btn_clear_all = ttk.Button(input_btn_frame, text=self.t("btn_clear_all"), command=self.clear_input_files)
        self.btn_clear_all.grid(row=0, column=2, padx=2)

        self.input_listbox = tk.Listbox(self.input_frame, height=4, bg=self.entry_bg, fg=self.fg_color,
                                        selectbackground=self.accent_color)
        self.input_listbox.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)

        # 文件统计信息
        self.file_count_var = tk.StringVar(value=self.t("file_count", n=0))
        ttk.Label(self.input_frame, textvariable=self.file_count_var).grid(row=3, column=0, sticky=tk.W, pady=2)

        # 输出路径选择
        self.output_frame = ttk.LabelFrame(main_frame, text=self.t("output_frame"), padding="5", style="White.TLabelframe")
        self.output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        self.output_frame.columnconfigure(0, weight=1)

        self.output_hint_label = ttk.Label(self.output_frame, text=self.t("output_hint"))
        self.output_hint_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        output_btn_frame = ttk.Frame(self.output_frame)
        output_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        output_btn_frame.columnconfigure(0, weight=1)

        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(output_btn_frame, textvariable=self.output_var)
        output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=2)
        output_entry.configure(style="Black.TEntry")  # 黑色文字

        self.btn_browse_dir = ttk.Button(output_btn_frame, text=self.t("btn_browse_dir"), command=self.select_output_dir)
        self.btn_browse_dir.grid(row=0, column=1, padx=2)

        # 问题类型设置
        self.issue_frame = ttk.LabelFrame(main_frame, text=self.t("issue_frame"), padding="5", style="White.TLabelframe")
        self.issue_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        self.issue_frame.columnconfigure(1, weight=1)

        self.issue_type_label = ttk.Label(self.issue_frame, text=self.t("issue_type"))
        self.issue_type_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.issue_type_var = tk.StringVar(value="pa_issues")
        issue_types = ["pa_issues"]
        issue_combo = ttk.Combobox(self.issue_frame, textvariable=self.issue_type_var,
                                   values=issue_types, state="readonly")
        issue_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        issue_combo.configure(style="Black.TCombobox")
        issue_combo.bind('<<ComboboxSelected>>', self.on_issue_type_changed)

        # 特征抽取器设置
        self.extractor_frame = ttk.LabelFrame(main_frame, text=self.t("extractor_frame"), padding="5", style="White.TLabelframe")
        self.extractor_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        self.extractor_frame.columnconfigure(1, weight=1)

        self.extractor_select_label = ttk.Label(self.extractor_frame, text=self.t("extractor_select"))
        self.extractor_select_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.extractor_var = tk.StringVar(value="PaIssueExtractor")
        extractor_combo = ttk.Combobox(self.extractor_frame, textvariable=self.extractor_var,
                                       values=list(self.extractor_mapping.keys()), state="readonly")
        extractor_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        extractor_combo.configure(style="Black.TCombobox")
        extractor_combo.bind('<<ComboboxSelected>>', self.on_extractor_changed)

        # 抽取器描述
        self.extractor_desc_var = tk.StringVar(value=self.get_extractor_desc("PaIssueExtractor"))
        ttk.Label(self.extractor_frame, textvariable=self.extractor_desc_var,
                  wraplength=600, justify=tk.LEFT).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 打标器设置
        self.labeler_frame = ttk.LabelFrame(main_frame, text=self.t("labeler_frame"), padding="5", style="White.TLabelframe")
        self.labeler_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        self.labeler_frame.columnconfigure(1, weight=1)

        self.labeler_select_label = ttk.Label(self.labeler_frame, text=self.t("labeler_select"))
        self.labeler_select_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.labeler_var = tk.StringVar(value="PaIssueLabeler")
        labeler_combo = ttk.Combobox(self.labeler_frame, textvariable=self.labeler_var,
                                     values=list(self.labeler_mapping.keys()), state="readonly")
        labeler_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        labeler_combo.configure(style="Black.TCombobox")
        labeler_combo.bind('<<ComboboxSelected>>', self.on_labeler_changed)

        # 打标器描述
        self.labeler_desc_var = tk.StringVar(value=self.get_labeler_desc("PaIssueLabeler"))
        ttk.Label(self.labeler_frame, textvariable=self.labeler_desc_var,
                  wraplength=600, justify=tk.LEFT).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 打标方法选择
        self.method_frame = ttk.LabelFrame(main_frame, text=self.t("method_frame"), padding="5", style="White.TLabelframe")
        self.method_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        self.method_frame.columnconfigure(0, weight=1)
        self.method_frame.columnconfigure(1, weight=1)
        self.method_frame.columnconfigure(2, weight=1)

        self.pattern1_var = tk.BooleanVar(value=True)
        self.pattern2_var = tk.BooleanVar(value=True)
        self.repair_info_var = tk.BooleanVar(value=True)

        self.cb_pattern1 = ttk.Checkbutton(self.method_frame, text=self.t("method_pattern1"), variable=self.pattern1_var)
        self.cb_pattern1.grid(row=0, column=0, sticky=tk.W)

        self.cb_pattern2 = ttk.Checkbutton(self.method_frame, text=self.t("method_pattern2"), variable=self.pattern2_var)
        self.cb_pattern2.grid(row=0, column=1, sticky=tk.W)

        self.cb_repair = ttk.Checkbutton(self.method_frame, text=self.t("method_repair"), variable=self.repair_info_var)
        self.cb_repair.grid(row=0, column=2, sticky=tk.W)

        # 日志设置
        self.log_setting_frame = ttk.LabelFrame(main_frame, text=self.t("logopt_frame"), padding="5", style="White.TLabelframe")
        self.log_setting_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)
        self.log_setting_frame.columnconfigure(0, weight=1)

        self.save_detailed_logs_var = tk.BooleanVar(value=False)
        self.cb_save_repair = ttk.Checkbutton(self.log_setting_frame, text=self.t("save_repair_logs"),
                                              variable=self.save_detailed_logs_var)
        self.cb_save_repair.grid(row=0, column=0, sticky=tk.W)

        self.log_desc_label = ttk.Label(self.log_setting_frame, text=self.t("logopt_desc"),
                                        wraplength=600, justify=tk.LEFT)
        self.log_desc_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        # 进度显示
        self.progress_frame = ttk.LabelFrame(main_frame, text=self.t("progress_frame"), padding="5", style="White.TLabelframe")
        self.progress_frame.grid(row=8, column=0, sticky=(tk.W, tk.E), pady=5)
        self.progress_frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)

        self.status_var = tk.StringVar(value=self.t("status_ready"))
        ttk.Label(self.progress_frame, textvariable=self.status_var).grid(row=1, column=0, sticky=tk.W)

        # 日志显示
        self.log_display_frame = ttk.LabelFrame(main_frame, text=self.t("log_display_frame"), padding="5", style="White.TLabelframe")
        self.log_display_frame.grid(row=9, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.log_display_frame.columnconfigure(0, weight=1)
        self.log_display_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(self.log_display_frame, height=10, width=80, bg=self.entry_bg, fg=self.fg_color,
                                insertbackground=self.fg_color)
        scrollbar2 = ttk.Scrollbar(self.log_display_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar2.set)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar2.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=10, column=0, pady=10)

        self.btn_start = ttk.Button(btn_frame, text=self.t("btn_start"), command=self.start_processing)
        self.btn_start.grid(row=0, column=0, padx=5)

        self.btn_clear_log = ttk.Button(btn_frame, text=self.t("btn_clear_log"), command=self.clear_log)
        self.btn_clear_log.grid(row=0, column=1, padx=5)

        self.btn_exit = ttk.Button(btn_frame, text=self.t("btn_exit"), command=self.root.quit)
        self.btn_exit.grid(row=0, column=2, padx=5)

        # 配置权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)  # 日志显示行应该扩展

    def on_frame_configure(self, event):
        """更新滚动区域以匹配内部框架的大小"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """调整内部框架的宽度以匹配画布"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_issue_type_changed(self, event):
        """当问题类型改变时，自动更新特征抽取器和打标器"""
        issue_type = self.issue_type_var.get()
        mapping = {
            "pa_issues": ("PaIssueExtractor", "PaIssueLabeler"),
            "dcdc_issues": ("DcdcIssueExtractor", "DcdcIssueLabeler"),
            "digital_issues": ("DigitalIssueExtractor", "DigitalIssueLabeler"),
            "dpd_issues": ("DpdIssueExtractor", "DpdIssueLabeler"),
            "DPD_issues": ("DpdIssueExtractor", "DpdIssueLabeler"),
            "fu_issues": ("FuIssueExtractor", "FuIssueLabeler"),
            "ltu_issues": ("LtuIssueExtractor", "LtuIssueLabeler"),
            "nff_issues": ("NffIssueExtractor", "NffIssueLabeler"),
            "sw_issues": ("SwIssueExtractor", "SwIssueLabeler"),
            "trx_issues": ("TrxIssueExtractor", "TrxIssueLabeler")
        }
        if issue_type in mapping:
            extractor, labeler = mapping[issue_type]
            self.extractor_var.set(extractor)
            self.labeler_var.set(labeler)
            self.update_extractor_description(extractor)
            self.update_labeler_description(labeler)

    def on_extractor_changed(self, event):
        """当特征抽取器改变时，更新描述"""
        extractor_name = self.extractor_var.get()
        self.update_extractor_description(extractor_name)

    def on_labeler_changed(self, event):
        """当打标器改变时，更新描述"""
        labeler_name = self.labeler_var.get()
        self.update_labeler_description(labeler_name)

    def get_extractor_desc(self, extractor_name):
        desc_map = I18N.get(self.lang, I18N["en"]).get("ex_desc", {})
        return desc_map.get(extractor_name, self.t("extractor_desc_default"))

    def get_labeler_desc(self, labeler_name):
        desc_map = I18N.get(self.lang, I18N["en"]).get("lb_desc", {})
        return desc_map.get(labeler_name, self.t("labeler_desc_default"))

    def update_extractor_description(self, extractor_name):
        """更新特征抽取器描述"""
        self.extractor_desc_var.set(self.get_extractor_desc(extractor_name))

    def update_labeler_description(self, labeler_name):
        """更新打标器描述"""
        self.labeler_desc_var.set(self.get_labeler_desc(labeler_name))

    def log_message(self, message):
        """添加日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    def select_input_files(self):
        """选择输入文件"""
        files = filedialog.askopenfilenames(
            title=self.t("dlg_select_json"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if files:
            added_count = 0
            for file_path in files:
                # 验证文件路径格式（保留原逻辑：validate_input_path 返回tuple，原代码这里有用法不一致的问题）
                ok, _msg = self.validate_input_path(file_path)
                if not ok:
                    continue
                if not self.validate_json_file(file_path):
                    continue
                if file_path not in self.input_paths:
                    self.input_paths.append(file_path)
                    self.input_listbox.insert(tk.END, file_path)
                    added_count += 1
            self.update_file_count()
            self.log_message(self.t("log_added_files", n=added_count))

    def select_input_folder(self):
        """选择输入文件夹并自动展开所有JSON文件"""
        folder = filedialog.askdirectory(title=self.t("dlg_select_json_folder"), mustexist=True)
        if folder:
            if any(folder in path for path in self.input_paths):
                self.log_message(self.t("log_folder_exists", folder=folder))
                return
            self.log_message(self.t("log_scanning", folder=folder))

            thread = threading.Thread(
                target=self.scan_folder_for_json_files,
                args=(folder,)
            )
            thread.daemon = True
            thread.start()

    def scan_folder_for_json_files(self, folder_path):
        """扫描文件夹中的所有JSON文件"""
        try:
            json_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.json'):
                        full_path = os.path.join(root, file)
                        json_files.append(full_path)
            self.root.after(0, self.process_scanned_files, json_files, folder_path)
        except Exception as e:
            self.root.after(0, self.log_message, self.t("log_scan_error", err=str(e)))

    def process_scanned_files(self, json_files, folder_path):
        """处理扫描到的JSON文件"""
        valid_count = 0
        invalid_count = 0
        for file_path in json_files:
            ok, error_msg = self.validate_input_path(file_path)
            if not ok:
                invalid_count += 1
                self.log_message(self.t("log_file_invalid", name=os.path.basename(file_path), msg=error_msg))
                continue

            if not self.validate_json_file(file_path):
                invalid_count += 1
                continue

            if file_path not in self.input_paths:
                self.input_paths.append(file_path)
                self.input_listbox.insert(tk.END, file_path)
                valid_count += 1

        self.update_file_count()

        if isinstance(folder_path, str) and os.path.isdir(folder_path):
            display_name = os.path.basename(folder_path)
        else:
            display_name = folder_path

        self.log_message(self.t("log_scan_done", name=display_name, total=len(json_files)))
        self.log_message(self.t("log_scan_stat", ok=valid_count, bad=invalid_count))
        if invalid_count > 0:
            self.log_message(self.t("log_scan_hint"))

    def update_file_count(self):
        """更新文件计数显示"""
        count = len(self.input_paths)
        self.file_count_var.set(self.t("file_count", n=count))

    def validate_input_path(self, file_path):
        """验证输入路径格式"""
        try:
            if not file_path.lower().endswith('.json'):
                return False, "文件不是JSON格式" if self.lang == "zh" else "Not a JSON file"
            if not os.path.exists(file_path):
                return False, "文件不存在" if self.lang == "zh" else "File not found"

            dir_path = os.path.dirname(file_path)
            normalized_path = os.path.normpath(dir_path)
            path_parts = normalized_path.split(os.sep)
            path_parts = [part for part in path_parts if part]

            if len(path_parts) < 1:
                return False, "路径层级不足" if self.lang == "zh" else "Path depth is insufficient"

            sn = None
            issue_type = None

            for i in range(len(path_parts) - 1, -1, -1):
                part = path_parts[i]
                if sn is None and self._is_valid_sn(part):
                    sn = part
                    continue
                if sn is not None and issue_type is None and self._is_valid_issue_type(part):
                    issue_type = part
                    break

            if sn is None:
                return False, "无法在路径中找到有效的SN号" if self.lang == "zh" else "Cannot find a valid SN in path"
            if issue_type is None:
                return False, "无法在路径中找到有效的issue类型" if self.lang == "zh" else "Cannot find a valid issue type in path"

            return True, ""
        except Exception as e:
            return False, f"路径验证异常: {str(e)}" if self.lang == "zh" else f"Path validation error: {str(e)}"

    @staticmethod
    def _is_valid_sn(sn):
        """验证SN号格式"""
        if not sn or len(sn) != 10:
            return False
        if not sn[0].isalpha():
            return False
        if not sn.isalnum():
            return False
        return True

    @staticmethod
    def _is_valid_issue_type(issue_type):
        """验证issue类型格式"""
        valid_issue_types = {
            'pa_issues', 'dcdc_issues', 'digital_issues', 'dpd_issues', 'DPD_issues',
            'fu_issues', 'ltu_issues', 'nff_issues', 'sw_issues', 'trx_issues'
        }
        return issue_type in valid_issue_types

    def validate_json_file(self, file_path):
        """验证JSON文件格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except Exception as e:
            messagebox.showerror(self.t("json_error_title"),
                                 self.t("json_error_body", path=file_path, err=str(e)))
            return False

    def clear_input_files(self):
        """清除输入文件选择"""
        self.input_paths.clear()
        self.input_listbox.delete(0, tk.END)
        self.update_file_count()
        self.log_message(self.t("log_cleared_inputs"))

    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title=self.t("dlg_select_output"))
        if directory:
            self.output_var.set(directory)
            self.log_message(self.t("log_output_set", dir=directory))

    def get_labeling_methods(self):
        """获取选择的打标方法"""
        methods = []
        if self.pattern1_var.get():
            methods.append('pattern_1')
        if self.pattern2_var.get():
            methods.append('pattern_2')
        if self.repair_info_var.get():
            methods.append('repair_info')
        if not methods:
            messagebox.showwarning(self.t("warn"), self.t("warn_need_method"))
            return None
        return methods

    def start_processing(self):
        """开始处理"""
        if not self.input_paths:
            messagebox.showerror(self.t("error"), self.t("err_need_input"))
            return
        if not self.output_var.get():
            messagebox.showerror(self.t("error"), self.t("err_need_output"))
            return

        labeling_methods = self.get_labeling_methods()
        if not labeling_methods:
            return

        thread = threading.Thread(
            target=self.process_files,
            args=(self.input_paths, self.output_var.get(), labeling_methods)
        )
        thread.daemon = True
        thread.start()

    def process_files(self, input_paths, output_dir, labeling_methods):
        """处理文件的主逻辑"""
        try:
            self.progress.start()
            self.status_var.set(self.t("status_processing"))

            self.log_message(self.t("log_start"))
            self.log_message(self.t("log_input_count", n=len(input_paths)))
            self.log_message(self.t("log_output_dir", dir=output_dir))
            self.log_message(self.t("log_issue_type", issue=self.issue_type_var.get()))
            self.log_message(self.t("log_extractor", name=self.extractor_var.get()))
            self.log_message(self.t("log_labeler", name=self.labeler_var.get()))
            self.log_message(self.t("log_methods", methods=", ".join(labeling_methods)))

            # 设置repair_info日志保存选项
            save_detailed_logs = self.save_detailed_logs_var.get()
            if 'repair_info' in labeling_methods:
                try:
                    from tools.app.services.data_processing.data_processor.labeler.labeling_methods.repair_info import set_save_detailed_logs
                    set_save_detailed_logs(save_detailed_logs)
                    if save_detailed_logs:
                        self.log_message(self.t("log_repair_on"))
                    else:
                        self.log_message(self.t("log_repair_off"))
                except ImportError as e:
                    self.log_message(self.t("log_repair_import_fail", err=str(e)))
                    self.log_message(self.t("log_repair_unavailable"))

            # 根据选择的特征抽取器实例化
            extractor_name = self.extractor_var.get()
            if extractor_name in self.extractor_mapping:
                extractor_class = self.extractor_mapping[extractor_name]
                try:
                    extractor = extractor_class()
                    self.log_message(self.t("log_use_extractor", name=extractor_name))
                except Exception as e:
                    self.log_message(self.t("log_extractor_inst_fail", name=extractor_name, err=str(e)))
                    self.log_message(self.t("log_use_default_extractor"))
                    extractor = PaIssueExtractor()
            else:
                self.log_message(self.t("log_unknown_extractor", name=extractor_name))
                extractor = PaIssueExtractor()

            # 根据选择的打标器实例化
            labeler_name = self.labeler_var.get()
            if labeler_name in self.labeler_mapping:
                labeler_class = self.labeler_mapping[labeler_name]
                try:
                    labeler = labeler_class()
                    self.log_message(self.t("log_use_labeler", name=labeler_name))
                except Exception as e:
                    self.log_message(self.t("log_labeler_inst_fail", name=labeler_name, err=str(e)))
                    self.log_message(self.t("log_use_default_labeler"))
                    labeler = PaIssueLabeler()
            else:
                self.log_message(self.t("log_unknown_labeler", name=labeler_name))
                labeler = PaIssueLabeler()

            # 提取样本
            self.log_message(self.t("log_extracting"))
            samples = extractor.extract_samples_from_files(input_paths, output_dir)
            self.log_message(self.t("log_samples_count", n=len(samples)))
            if not samples:
                self.log_message(self.t("log_samples_empty"))
                return

            # 给样本打标
            self.log_message(self.t("log_labeling"))
            labeled_samples = labeler.label_samples(samples, labeling_method=labeling_methods)

            # 保存结果
            self.log_message(self.t("log_saving"))
            base_name = 'Training_samples'
            labeler.save_samples(labeled_samples, output_dir, base_name, labeling_method=labeling_methods)

            # 如果保存了详细日志，告知用户日志文件位置
            if 'repair_info' in labeling_methods and save_detailed_logs:
                try:
                    from tools.app.services.data_processing.data_processor.labeler.labeling_methods.repair_info import get_log_file_path
                    log_file = get_log_file_path()
                    if log_file and os.path.exists(log_file):
                        self.log_message(self.t("log_repair_saved", path=log_file))
                except ImportError:
                    self.log_message(self.t("log_repair_path_fail"))

            self.log_message(self.t("log_done"))
            self.status_var.set(self.t("status_done"))

        except Exception as e:
            self.log_message(self.t("log_error", err=str(e)))
            import traceback
            self.log_message(self.t("log_trace", trace=traceback.format_exc()))
            self.status_var.set(self.t("status_error"))

        finally:
            self.progress.stop()


def main():
    root = tk.Tk()
    DataProcessorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()