import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from tools.app.services.data_processing.data_processor.extractor.pa_issue_extractor import PaIssueExtractor
from tools.app.services.data_processing.data_processor.labeler.pa_issue_labeler import PaIssueLabeler


class DataProcessorGUI:
    def __init__(self, parent):
        self.root = parent

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

    def setup_dark_theme(self):
        """设置深色主题"""
        style = ttk.Style()

        # 配置样式
        # 配置黑色文字样式
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

        # style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
        # 白色文字的 LabelFrame 样式
        style.configure("White.TLabelframe",
                        background=self.bg_color,
                        foreground=self.fg_color)  # 白色字体
        style.configure("White.TLabelframe.Label",
                        background=self.frame_bg,
                        foreground=self.fg_color)  # 白色字体

        style.configure("TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)
        style.configure("TProgressbar", background=self.accent_color, troughcolor=self.frame_bg)

        # # 设置根窗口背景
        # self.root.configure(bg=self.bg_color)

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

        # UI设置代码
        # 创建黑色文字样式
        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        style.configure("Black.TCombobox", foreground="#000000")

        # 添加标题
        title_label = ttk.Label(
            main_frame,
            text="生成样本数据",
            font=("Arial", 16, "bold"),
            foreground=self.fg_color,
            background=self.bg_color
        )
        title_label.grid(row=0, column=0, columnspan=2, sticky="", pady=(0, 10))

        # 输入路径选择
        input_frame = ttk.LabelFrame(main_frame, text="输入文件设置", padding="5", style="White.TLabelframe")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(0, weight=1)

        ttk.Label(input_frame, text="选择输入文件或者文件夹:").grid(row=0, column=0, sticky=tk.W, pady=2)

        input_btn_frame = ttk.Frame(input_frame)
        input_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        input_btn_frame.columnconfigure(0, weight=1)

        ttk.Button(input_btn_frame, text="添加文件", command=self.select_input_files).grid(row=0, column=0, padx=2)
        ttk.Button(input_btn_frame, text="添加文件夹", command=self.select_input_folder).grid(row=0, column=1, padx=2)
        ttk.Button(input_btn_frame, text="清除所有", command=self.clear_input_files).grid(row=0, column=2, padx=2)

        self.input_listbox = tk.Listbox(input_frame, height=4, bg=self.entry_bg, fg=self.fg_color,
                                        selectbackground=self.accent_color)
        self.input_listbox.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)

        # 文件统计信息
        self.file_count_var = tk.StringVar(value="已选择 0 个文件")
        ttk.Label(input_frame, textvariable=self.file_count_var).grid(row=3, column=0, sticky=tk.W, pady=2)

        # 输出路径选择
        output_frame = ttk.LabelFrame(main_frame, text="输出路径设置", padding="5", style="White.TLabelframe")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)

        ttk.Label(output_frame, text="选择输出目录:").grid(row=0, column=0, sticky=tk.W, pady=2)

        output_btn_frame = ttk.Frame(output_frame)
        output_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        output_btn_frame.columnconfigure(0, weight=1)

        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(output_btn_frame, textvariable=self.output_var)
        output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=2)
        output_entry.configure(style="Black.TEntry")  # 黑色文字

        ttk.Button(output_btn_frame, text="浏览目录", command=self.select_output_dir).grid(row=0, column=1, padx=2)

        # 问题类型设置
        issue_frame = ttk.LabelFrame(main_frame, text="问题类型设置", padding="5", style="White.TLabelframe")
        issue_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        issue_frame.columnconfigure(1, weight=1)

        ttk.Label(issue_frame, text="问题类型:").grid(row=0, column=0, sticky=tk.W, pady=2)

        self.issue_type_var = tk.StringVar(value="pa_issues")
        issue_types = ["pa_issues"]

        issue_combo = ttk.Combobox(issue_frame, textvariable=self.issue_type_var,
                                   values=issue_types, state="readonly")
        issue_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        issue_combo.configure(style="Black.TCombobox")  # 黑色文字
        issue_combo.bind('<<ComboboxSelected>>', self.on_issue_type_changed)

        # 特征抽取器设置
        extractor_frame = ttk.LabelFrame(main_frame, text="特征抽取设置", padding="5", style="White.TLabelframe")
        extractor_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        extractor_frame.columnconfigure(1, weight=1)

        ttk.Label(extractor_frame, text="选择特征抽取器:").grid(row=0, column=0, sticky=tk.W, pady=2)

        self.extractor_var = tk.StringVar(value="PaIssueExtractor")
        extractor_combo = ttk.Combobox(extractor_frame, textvariable=self.extractor_var,
                                       values=list(self.extractor_mapping.keys()), state="readonly")
        extractor_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        extractor_combo.configure(style="Black.TCombobox")  # 黑色文字
        extractor_combo.bind('<<ComboboxSelected>>', self.on_extractor_changed)

        # 抽取器描述
        self.extractor_desc_var = tk.StringVar(value="PA问题特征抽取器 - 提取PA相关的电压、电流、功率等特征")
        ttk.Label(extractor_frame, textvariable=self.extractor_desc_var,
                  wraplength=600, justify=tk.LEFT).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 打标器设置
        labeler_frame = ttk.LabelFrame(main_frame, text="打标器设置", padding="5", style="White.TLabelframe")
        labeler_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        labeler_frame.columnconfigure(1, weight=1)

        ttk.Label(labeler_frame, text="选择打标器:").grid(row=0, column=0, sticky=tk.W, pady=2)

        self.labeler_var = tk.StringVar(value="PaIssueLabeler")
        labeler_combo = ttk.Combobox(labeler_frame, textvariable=self.labeler_var,
                                     values=list(self.labeler_mapping.keys()), state="readonly")
        labeler_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        labeler_combo.configure(style="Black.TCombobox")  # 黑色文字
        labeler_combo.bind('<<ComboboxSelected>>', self.on_labeler_changed)

        # 打标器描述
        self.labeler_desc_var = tk.StringVar(value="PA问题打标器 - 使用Pattern分析和Repair Info方法标注PA状态")
        ttk.Label(labeler_frame, textvariable=self.labeler_desc_var,
                  wraplength=600, justify=tk.LEFT).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 打标方法选择
        method_frame = ttk.LabelFrame(main_frame, text="打标方法选择", padding="5", style="White.TLabelframe")
        method_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        method_frame.columnconfigure(0, weight=1)
        method_frame.columnconfigure(1, weight=1)
        method_frame.columnconfigure(2, weight=1)

        self.pattern1_var = tk.BooleanVar(value=True)
        self.pattern2_var = tk.BooleanVar(value=True)
        self.repair_info_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(method_frame, text="Pattern分析方法一", variable=self.pattern1_var).grid(row=0, column=0,
                                                                                                 sticky=tk.W)
        ttk.Checkbutton(method_frame, text="Pattern分析方法二", variable=self.pattern2_var).grid(row=0, column=1,
                                                                                                 sticky=tk.W)
        ttk.Checkbutton(method_frame, text="Repair Info方法", variable=self.repair_info_var).grid(row=0, column=2,
                                                                                                  sticky=tk.W)

        # 日志设置
        log_frame = ttk.LabelFrame(main_frame, text="日志设置", padding="5", style="White.TLabelframe")
        log_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)
        log_frame.columnconfigure(0, weight=1)

        self.save_detailed_logs_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(log_frame, text="保存Repair Info详细日志", variable=self.save_detailed_logs_var).grid(row=0,
                                                                                                              column=0,
                                                                                                              sticky=tk.W)

        # 日志描述
        log_desc = "如果勾选，repair_info方法的详细调试日志将保存到logs文件夹中"
        ttk.Label(log_frame, text=log_desc, wraplength=600, justify=tk.LEFT).grid(row=1, column=0, sticky=tk.W, pady=2)

        # 进度显示
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding="5", style="White.TLabelframe")
        progress_frame.grid(row=8, column=0, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=1, column=0, sticky=tk.W)

        # 日志显示
        log_display_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="5", style="White.TLabelframe")
        log_display_frame.grid(row=9, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_display_frame.columnconfigure(0, weight=1)
        log_display_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_display_frame, height=10, width=80, bg=self.entry_bg, fg=self.fg_color,
                                insertbackground=self.fg_color)
        scrollbar = ttk.Scrollbar(log_display_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=10, column=0, pady=10)

        ttk.Button(btn_frame, text="开始处理", command=self.start_processing).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="清空日志", command=self.clear_log).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="退出", command=self.root.quit).grid(row=0, column=2, padx=5)

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

        # 根据问题类型设置默认的提取器和标签器
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

    def update_extractor_description(self, extractor_name):
        """更新特征抽取器描述"""
        descriptions = {
            "PaIssueExtractor": "PA问题特征抽取器 - 提取PA相关的电压、电流、功率等特征",
            "DcdcIssueExtractor": "DCDC问题特征抽取器 - 提取DCDC电源相关的电压、电流、效率等特征",
            "DigitalIssueExtractor": "数字问题特征抽取器 - 提取数字电路相关的时序、逻辑状态等特征",
            "DpdIssueExtractor": "DPD问题特征抽取器 - 提取数字预失真相关的参数和性能指标",
            "FuIssueExtractor": "FU问题特征抽取器 - 提取频率单元相关的频率稳定度、相位噪声等特征",
            "LtuIssueExtractor": "LTU问题特征抽取器 - 提取线性化技术单元相关的特征参数",
            "NffIssueExtractor": "NFF问题特征抽取器 - 提取无故障发现相关的测试和诊断特征",
            "SwIssueExtractor": "软件问题特征抽取器 - 提取软件相关的日志、状态、性能指标",
            "TrxIssueExtractor": "TRX问题特征抽取器 - 提取收发器相关的射频性能和配置参数"
        }

        self.extractor_desc_var.set(descriptions.get(extractor_name, "特征抽取器描述"))

    def update_labeler_description(self, labeler_name):
        """更新打标器描述"""
        descriptions = {
            "PaIssueLabeler": "PA问题打标器 - 使用Pattern分析和Repair Info方法标注PA状态",
            "DcdcIssueLabeler": "DCDC问题打标器 - 使用电压稳定性分析和效率计算方法标注DCDC状态",
            "DigitalIssueLabeler": "数字问题打标器 - 使用时序分析和逻辑状态验证方法标注数字电路状态",
            "DpdIssueLabeler": "DPD问题打标器 - 使用线性度分析和预失真效果评估方法标注DPD状态",
            "FuIssueLabeler": "FU问题打标器 - 使用频率稳定度分析和相位噪声评估方法标注频率单元状态",
            "LtuIssueLabeler": "LTU问题打标器 - 使用线性化性能分析和参数优化方法标注LTU状态",
            "NffIssueLabeler": "NFF问题打标器 - 使用故障诊断和测试验证方法标注NFF状态",
            "SwIssueLabeler": "软件问题打标器 - 使用日志分析和性能监控方法标注软件状态",
            "TrxIssueLabeler": "TRX问题打标器 - 使用射频性能分析和配置验证方法标注收发器状态"
        }

        self.labeler_desc_var.set(descriptions.get(labeler_name, "打标器描述"))

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
            title="选择JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if files:
            added_count = 0
            for file_path in files:
                # 验证文件路径格式
                if not self.validate_input_path(file_path):
                    continue

                # 验证JSON格式
                if not self.validate_json_file(file_path):
                    continue

                if file_path not in self.input_paths:
                    self.input_paths.append(file_path)
                    self.input_listbox.insert(tk.END, file_path)
                    added_count += 1

            self.update_file_count()
            self.log_message(f"已添加 {added_count} 个文件")

    def select_input_folder(self):
        """选择输入文件夹并自动展开所有JSON文件"""
        folder = filedialog.askdirectory(title="选择包含JSON文件的文件夹(支持多选)", mustexist=True)

        if folder:
            # 检查是否已经选择过这个文件夹
            if any(folder in path for path in self.input_paths):
                self.log_message(f"文件夹已存在: {folder}")
                return

            self.log_message(f"正在扫描文件夹: {folder}")

            # 在新线程中扫描文件夹，避免界面卡顿
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

            # 递归扫描所有子文件夹
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.json'):
                        full_path = os.path.join(root, file)
                        json_files.append(full_path)

            # 在主线程中更新UI
            self.root.after(0, self.process_scanned_files, json_files, folder_path)

        except Exception as e:
            self.root.after(0, self.log_message, f"扫描文件夹时出错: {str(e)}")

    def process_scanned_files(self, json_files, folder_path):
        """处理扫描到的JSON文件"""
        valid_count = 0
        invalid_count = 0

        for file_path in json_files:
            # 验证文件路径格式
            is_valid, error_msg = self.validate_input_path(file_path)
            if not is_valid:
                invalid_count += 1
                self.log_message(f"文件验证失败: {os.path.basename(file_path)} - {error_msg}")
                continue

            # 验证JSON格式
            if not self.validate_json_file(file_path):
                invalid_count += 1
                continue

            if file_path not in self.input_paths:
                self.input_paths.append(file_path)
                self.input_listbox.insert(tk.END, file_path)
                valid_count += 1

        self.update_file_count()

        # 显示扫描结果
        if isinstance(folder_path, str) and os.path.isdir(folder_path):
            display_name = os.path.basename(folder_path)
        else:
            display_name = folder_path

        self.log_message(f"扫描完成: 从 '{display_name}' 中找到 {len(json_files)} 个JSON文件")
        self.log_message(f"有效文件: {valid_count} 个, 无效文件: {invalid_count} 个")

        if invalid_count > 0:
            self.log_message("无效文件可能由于路径格式不正确或JSON格式错误")

    def update_file_count(self):
        """更新文件计数显示"""
        count = len(self.input_paths)
        self.file_count_var.set(f"已选择 {count} 个文件")

    def validate_input_path(self, file_path):
        """验证输入路径格式"""
        try:
            # 检查文件扩展名
            if not file_path.lower().endswith('.json'):
                return False, "文件不是JSON格式"

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False, "文件不存在"

            # 获取文件所在目录并规范化路径
            dir_path = os.path.dirname(file_path)
            normalized_path = os.path.normpath(dir_path)
            path_parts = normalized_path.split(os.sep)

            # 过滤掉空字符串
            path_parts = [part for part in path_parts if part]

            # 如果路径层级不足，返回False
            if len(path_parts) < 1:
                return False, "路径层级不足"

            # 从路径末尾开始查找SN和issue_type
            sn = None
            issue_type = None

            # 从后往前遍历路径部分
            for i in range(len(path_parts) - 1, -1, -1):
                part = path_parts[i]

                # 如果还没有找到SN，检查当前部分是否是有效的SN
                if sn is None and self._is_valid_sn(part):
                    sn = part
                    continue

                # 如果已经找到SN但还没有找到issue_type，检查当前部分是否是有效的issue_type
                if sn is not None and issue_type is None and self._is_valid_issue_type(part):
                    issue_type = part
                    break

            # 验证是否找到了SN和issue_type
            if sn is None:
                return False, "无法在路径中找到有效的SN号"

            if issue_type is None:
                return False, "无法在路径中找到有效的issue类型"

            return True, ""

        except Exception as e:
            return False, f"路径验证异常: {str(e)}"

    @staticmethod
    def _is_valid_sn(sn):
        """
        验证SN号格式
        SN号要求：
        - 总共10位
        - 由字母和数字构成
        - 第一位必须是字母
        """
        if not sn or len(sn) != 10:
            return False

        # 检查第一位是否是字母
        if not sn[0].isalpha():
            return False

        # 检查所有字符是否都是字母或数字
        if not sn.isalnum():
            return False

        return True

    @staticmethod
    def _is_valid_issue_type(issue_type):
        """
        验证issue类型格式
        有效的issue类型包括：
        - pa_issues
        - dcdc_issues
        - digital_issues
        - dpd_issues
        - fu_issues
        - ltu_issues
        - nff_issues
        - sw_issues
        - trx_issues
        """
        valid_issue_types = {
            'pa_issues', 'dcdc_issues', 'digital_issues', 'dpd_issues', 'DPD_issues',
            'fu_issues', 'ltu_issues', 'nff_issues', 'sw_issues', 'trx_issues'
        }

        return issue_type in valid_issue_types

    @staticmethod
    def validate_json_file(file_path):
        """验证JSON文件格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except Exception as e:
            messagebox.showerror("JSON错误", f"文件不是有效的JSON格式: {file_path}\n错误: {str(e)}")
            return False

    def clear_input_files(self):
        """清除输入文件选择"""
        self.input_paths.clear()
        self.input_listbox.delete(0, tk.END)
        self.update_file_count()
        self.log_message("已清除所有输入文件")

    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_var.set(directory)
            self.log_message(f"输出目录设置为: {directory}")

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
            messagebox.showwarning("警告", "请至少选择一种打标方法")
            return None

        return methods

    def start_processing(self):
        """开始处理"""
        # 验证输入
        if not self.input_paths:
            messagebox.showerror("错误", "请选择输入文件")
            return

        if not self.output_var.get():
            messagebox.showerror("错误", "请选择输出目录")
            return

        labeling_methods = self.get_labeling_methods()
        if not labeling_methods:
            return

        # 在新线程中执行处理
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
            self.status_var.set("处理中...")

            self.log_message("开始处理文件...")
            self.log_message(f"输入文件: {len(input_paths)} 个")
            self.log_message(f"输出目录: {output_dir}")
            self.log_message(f"问题类型: {self.issue_type_var.get()}")
            self.log_message(f"特征抽取器: {self.extractor_var.get()}")
            self.log_message(f"打标器: {self.labeler_var.get()}")
            self.log_message(f"打标方法: {', '.join(labeling_methods)}")

            # 设置repair_info日志保存选项
            save_detailed_logs = self.save_detailed_logs_var.get()
            if 'repair_info' in labeling_methods:
                try:
                    from tools.app.services.data_processing.data_processor.labeler.labeling_methods.repair_info import set_save_detailed_logs
                    set_save_detailed_logs(save_detailed_logs)
                    if save_detailed_logs:
                        self.log_message("已启用Repair Info详细日志保存")
                    else:
                        self.log_message("Repair Info详细日志保存已禁用")
                except ImportError as e:
                    self.log_message(f"警告: 无法导入 repair_info 模块: {e}")
                    # 如果导入失败，继续处理但不保存详细日志
                    self.log_message("Repair Info详细日志功能不可用")

            # 根据选择的特征抽取器实例化
            extractor_name = self.extractor_var.get()
            if extractor_name in self.extractor_mapping:
                extractor_class = self.extractor_mapping[extractor_name]
                try:
                    extractor = extractor_class()
                    self.log_message(f"使用特征抽取器: {extractor_name}")
                except Exception as e:
                    self.log_message(f"错误: 无法实例化特征抽取器 {extractor_name}: {str(e)}")
                    self.log_message("使用默认的PaIssueExtractor")
                    extractor = PaIssueExtractor()
            else:
                self.log_message(f"警告: 未知的特征抽取器 {extractor_name}，使用默认的PaIssueExtractor")
                extractor = PaIssueExtractor()

            # 根据选择的打标器实例化
            labeler_name = self.labeler_var.get()
            if labeler_name in self.labeler_mapping:
                labeler_class = self.labeler_mapping[labeler_name]
                try:
                    labeler = labeler_class()
                    self.log_message(f"使用打标器: {labeler_name}")
                except Exception as e:
                    self.log_message(f"错误: 无法实例化打标器 {labeler_name}: {str(e)}")
                    self.log_message("使用默认的PaIssueLabeler")
                    labeler = PaIssueLabeler()
            else:
                self.log_message(f"警告: 未知的打标器 {labeler_name}，使用默认的PaIssueLabeler")
                labeler = PaIssueLabeler()

            # 提取样本
            self.log_message("正在提取样本...")
            samples = extractor.extract_samples_from_files(input_paths, output_dir)

            self.log_message(f"提取到的样本数量: {len(samples)}")
            if not samples:
                self.log_message("警告: 提取到空样本列表!")
                return

            # 给样本打标
            self.log_message("正在打标样本...")
            labeled_samples = labeler.label_samples(samples, labeling_method=labeling_methods)

            # 保存结果
            self.log_message("正在保存结果...")
            base_name = 'Training_samples'
            labeler.save_samples(labeled_samples, output_dir, base_name, labeling_method=labeling_methods)

            # 如果保存了详细日志，告知用户日志文件位置
            if 'repair_info' in labeling_methods and save_detailed_logs:
                try:
                    from tools.app.services.data_processing.data_processor.labeler.labeling_methods.repair_info import get_log_file_path
                    log_file = get_log_file_path()
                    if log_file and os.path.exists(log_file):
                        self.log_message(f"Repair Info详细日志已保存到: {log_file}")
                except ImportError:
                    self.log_message("无法获取Repair Info日志文件路径")

            self.log_message("处理完成!")
            self.status_var.set("完成")

        except Exception as e:
            self.log_message(f"处理过程中发生错误: {str(e)}")
            # 添加更详细的错误信息
            import traceback
            self.log_message(f"详细错误信息: {traceback.format_exc()}")
            self.status_var.set("错误")
        finally:
            self.progress.stop()


def main():
    root = tk.Tk()
    DataProcessorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
