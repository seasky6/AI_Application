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
pqat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                         'pqat_downloader', 'db')
sys.path.insert(0, pqat_path)
from tools.app.services.data_processing.pqat_downloader.db.db_manager import db_manager

pd.set_option('future.no_silent_downcasting', True)


class ZipExtractorGUI:
    def __init__(self, parent):
        self.root = parent

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
        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", background=self.frame_bg, foreground=self.fg_color)
        style.map("TNotebook.Tab", background=[("selected", self.accent_color)])

        # # 设置根窗口背景
        # self.root.configure(bg=self.bg_color)

    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="Zip压缩日志文件提取",
                                font=("Arial", 16, "bold"), foreground=self.fg_color, background=self.bg_color)
        title_label.pack(pady=10)

        # 输入路径设置框架
        input_frame = ttk.LabelFrame(main_frame, text="输入文件设置", padding="10", style="White.TLabelframe")
        input_frame.pack(fill=tk.X, pady=5)

        # 输入路径列表和按钮
        self.input_listbox = tk.Listbox(input_frame, height=4, bg=self.entry_bg, fg=self.fg_color,
                                        selectbackground=self.accent_color)
        self.input_listbox.pack(fill=tk.X, pady=5)

        input_button_frame = ttk.Frame(input_frame)
        input_button_frame.pack(fill=tk.X)

        ttk.Button(input_button_frame, text="添加文件",
                   command=self.add_input_path).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_button_frame, text="添加文件夹",
                   command=self.add_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_button_frame, text="移除文件",
                   command=self.remove_input_path).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_button_frame, text="移除所有",
                   command=self.clear_input_paths).pack(side=tk.LEFT, padx=5)

        # 数据库管理按钮框架
        db_frame = ttk.Frame(main_frame)
        db_frame.pack(fill=tk.X, pady=5)

        ttk.Button(db_frame, text="查看数据库内容",
                   command=self.show_database_content).pack(side=tk.LEFT, padx=5)

        # 处理按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="处理ZIP文件",
                   command=self.process_all_zips).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="显示统计图表",
                   command=self.show_statistics).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出处理结果",
                   command=self.export_results).pack(side=tk.LEFT, padx=5)

        # 日志显示框架
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="10", style="White.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, height=15, bg=self.entry_bg, fg=self.fg_color,
                                insertbackground=self.fg_color)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 初始日志
        self.log("欢迎使用Zip压缩日志文件提取工具")
        self.log("注意：输入路径应以 SN 号结尾（如：CN3A023818）")
        self.log("或者选择文件夹，程序会自动搜索其中的ZIP文件")
        self.log(f"使用共享数据库: {db_manager.db_path}")

    def log(self, message):
        """添加日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def add_input_path(self):
        """添加输入路径"""
        path = filedialog.askdirectory(title="选择包含ZIP文件的文件夹")
        if path:
            # 验证路径是否以 SN 号结尾（假设 SN 号规则为字母数字组合，且长度固定为10）
            sn_pattern = re.compile(r"[A-Z0-9]{10}$", re.IGNORECASE)
            last_part = os.path.basename(path)

            if not sn_pattern.match(last_part):
                messagebox.showwarning("警告", "输入文件的文件夹名称必须以有效的SN号结尾，例如：CN3A023818")
                return

            if path not in self.input_paths:
                self.input_paths.append(path)
                self.input_listbox.insert(tk.END, path)
                self.log(f"添加文件: {path}")

    def add_folder(self):
        """添加文件夹，自动搜索其中的ZIP文件"""
        folder = filedialog.askdirectory(title="选择包含ZIP文件的文件夹")
        if folder:
            if folder not in self.input_paths:
                self.input_paths.append(folder)
                self.input_listbox.insert(tk.END, folder)
                self.log(f"添加文件夹: {folder}")
                self.log("程序将自动搜索该文件夹中的所有ZIP文件")

    def remove_input_path(self):
        """移除选中的输入路径"""
        selection = self.input_listbox.curselection()
        if selection:
            index = selection[0]
            path = self.input_paths.pop(index)
            self.input_listbox.delete(index)
            self.log(f"移除文件: {path}")

    def clear_input_paths(self):
        """清空所有输入路径"""
        self.input_paths.clear()
        self.input_listbox.delete(0, tk.END)
        self.log("已清空所有文件")

    def extract_path_info(self, input_path):
        """
        从输入路径中提取 Platform, Model, Issue 信息
        路径格式: .../Platform/Model/xxx_issues/SN
        """
        try:
            # 标准化路径并分割
            normalized_path = os.path.normpath(input_path)
            path_parts = normalized_path.split(os.sep)

            # 查找包含 "files_to_be_processed" 的起始位置
            base_index = -1
            for i, part in enumerate(path_parts):
                if "files_to_be_processed" in part.lower():
                    base_index = i
                    break

            if base_index == -1:
                # 如果没有找到，从末尾开始提取
                if len(path_parts) >= 3:
                    issue = path_parts[-1]
                    model = path_parts[-2]
                    platform = path_parts[-3]
                else:
                    platform, model, issue = "Unknown", "Unknown", "Unknown"
            else:
                # 从 base_index 开始提取
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

            self.log(f"路径解析: Platform={platform}, Model={model}, Issue={issue}")
            return platform, model, issue

        except Exception as e:
            self.log(f"路径解析错误: {str(e)}")
            return "Unknown", "Unknown", "Unknown"

    def extract_info_from_zip_path(self, zip_path):
        """
        从ZIP文件路径中提取 Platform, Model, Issue 信息
        适用于文件夹模式，从ZIP文件所在目录结构推断信息
        """
        try:
            # 标准化路径并分割
            normalized_path = os.path.normpath(zip_path)
            path_parts = normalized_path.split(os.sep)

            # 从ZIP文件所在目录开始向上查找信息
            dir_parts = path_parts[:-1]  # 去掉文件名部分

            # 尝试从目录结构中提取信息
            platform, model, issue = "Unknown", "Unknown", "Unknown"

            # 查找可能的SN号（10位字母数字）
            sn_pattern = re.compile(r"[A-Z0-9]{10}$", re.IGNORECASE)
            for part in reversed(dir_parts):
                if sn_pattern.match(part):
                    issue = part  # 假设SN号所在目录是Issue
                    break

            # 查找可能的Model和Platform
            for i, part in enumerate(dir_parts):
                if "platform" in part.lower():
                    platform = part
                elif "model" in part.lower():
                    model = part
                elif "issue" in part.lower() and i > 0:
                    issue = dir_parts[i - 1] if i > 0 else "Unknown"

            self.log(f"从ZIP路径解析: Platform={platform}, Model={model}, Issue={issue}")
            return platform, model, issue

        except Exception as e:
            self.log(f"ZIP路径解析错误: {str(e)}")
            return "Unknown", "Unknown", "Unknown"

    def determine_parser_type(self, zip_filename):
        """根据文件名判断应该使用哪个解析器"""
        filename_lower = zip_filename.lower()

        # 检查是否是return格式
        for pattern in self.return_formats:
            if re.match(pattern, zip_filename, re.IGNORECASE):
                self.log(f"检测到Return格式文件: {zip_filename}")
                return "return"

        # 检查是否是proactive格式
        for pattern in self.proactive_formats:
            if re.match(pattern, zip_filename, re.IGNORECASE):
                self.log(f"检测到Proactive格式文件: {zip_filename}")
                return "proactive"

        # 默认使用proactive，但会记录警告
        self.log(f"警告: 无法识别文件格式，默认使用Proactive解析器: {zip_filename}")
        return "proactive"

    def parse_zip_file(self, input_zip, input_path, platform, model, issue):
        """
        解析ZIP文件并提取平台、型号、Issue信息
        """
        zip_filename = os.path.basename(input_zip)
        parser_type = self.determine_parser_type(zip_filename)

        if parser_type == "return":
            # 首先尝试ReturnLogParser
            self.log("DEBUG: 根据文件名判断，使用ReturnLogParser...")
            try:
                df = ReturnLogParser.parse(input_zip)
                # df["Platform"] = platform
                # df["Model"] = model
                # df["Issue"] = issue
                # df["File_Path"] = input_path
                self.log("DEBUG: ReturnLogParser succeeded")
                return "ReturnLogParser", df
            except Exception as e:
                self.log(f"DEBUG: ReturnLogParser failed: {str(e)}")
                self.log("DEBUG: 尝试备用解析器ProactiveLogParser...")
                try:
                    df = ProactiveLogParser.parse(input_zip)
                    # df["Platform"] = platform
                    # df["Model"] = model
                    # df["Issue"] = issue
                    # df["File_Path"] = input_path
                    self.log("DEBUG: ProactiveLogParser succeeded")
                    return "ProactiveLogParser", df
                except Exception as e2:
                    self.log(f"DEBUG: ProactiveLogParser also failed: {str(e2)}")
                    raise Exception(f"两种解析器都无法处理文件: Return错误: {str(e)}, Proactive错误: {str(e2)}")

        else:  # proactive 或 默认情况
            # 首先尝试ProactiveLogParser
            self.log("DEBUG: 根据文件名判断，使用ProactiveLogParser...")
            try:
                df = ProactiveLogParser.parse(input_zip)
                # df["Platform"] = platform
                # df["Model"] = model
                # df["Issue"] = issue
                # df["File_Path"] = input_path
                self.log("DEBUG: ProactiveLogParser succeeded")
                return "ProactiveLogParser", df
            except Exception as e:
                self.log(f"DEBUG: ProactiveLogParser failed: {str(e)}")
                self.log("DEBUG: 尝试备用解析器ReturnLogParser...")
                try:
                    df = ReturnLogParser.parse(input_zip)
                    # df["Platform"] = platform
                    # df["Model"] = model
                    # df["Issue"] = issue
                    # df["File_Path"] = input_path
                    self.log("DEBUG: ReturnLogParser succeeded")
                    return "ReturnLogParser", df
                except Exception as e2:
                    self.log(f"DEBUG: ReturnLogParser also failed: {str(e2)}")
                    raise Exception(f"两种解析器都无法处理文件: Proactive错误: {str(e)}, Return错误: {str(e2)}")

    def save_to_database(self, zip_file_path, xlsx_file_path, platform, model, issue, file_size, df):
        """将处理结果保存到共享数据库"""
        try:
            # 从DataFrame中提取序列号（取第一个非空序列号）
            serial_number = "Unknown"
            if 'Serial' in df.columns and not df['Serial'].empty:
                valid_serials = df[df['Serial'].notna()]['Serial']
                if not valid_serials.empty:
                    serial_number = valid_serials.iloc[0]

            # 使用日志类型 5 表示处理后的XLSX文件
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
                self.log(f"成功保存到共享数据库: {os.path.basename(xlsx_file_path)}")
            else:
                self.log(f"文件已存在于共享数据库: {os.path.basename(xlsx_file_path)}")

            return success
        except Exception as e:
            self.log(f"数据库保存错误: {str(e)}")
            return False

    def process_all_zips(self):
        """处理所有输入路径下的ZIP文件"""
        if not self.input_paths:
            messagebox.showwarning("警告", "请至少添加一个输入路径或文件夹")
            return

        all_data = []
        total_processed = 0

        for input_path in self.input_paths:
            self.log(f"处理路径: {input_path}")

            # 检查路径类型
            is_sn_path = False
            sn_pattern = re.compile(r"[A-Z0-9]{10}$", re.IGNORECASE)
            last_part = os.path.basename(input_path)

            if sn_pattern.match(last_part):
                # 这是SN号路径，使用原有逻辑
                is_sn_path = True
                platform, model, issue = self.extract_path_info(input_path)
                self.log(f"SN路径 - Platform: {platform}, Model: {model}, Issue: {issue}")
            else:
                # 这是普通文件夹，设置默认值
                platform, model, issue = "Unknown", "Unknown", "Unknown"
                self.log("普通文件夹模式，将尝试从ZIP文件路径提取信息")

            # 递归查找所有ZIP文件
            zip_files = []
            for root_dir, _, files in os.walk(input_path):
                for file in files:
                    if file.lower().endswith('.zip'):
                        full_path = os.path.join(root_dir, file)
                        zip_files.append(full_path)

            self.log(f"找到 {len(zip_files)} 个ZIP文件")

            for zip_path in zip_files:
                try:
                    filename = os.path.basename(zip_path)
                    self.log(f"正在处理: {filename}")

                    # 检查是否已处理过（通过数据库记录）
                    xlsx_filename = f"{os.path.splitext(filename)[0]}_extracted.xlsx"
                    existing_records = db_manager.search_radio_units(xlsx_filename)

                    if existing_records:
                        self.log(f"文件已处理过，跳过: {filename}")
                        continue

                    # 对于普通文件夹模式，尝试从ZIP文件路径提取更多信息
                    if not is_sn_path:
                        zip_platform, zip_model, zip_issue = self.extract_info_from_zip_path(zip_path)
                        # 如果从ZIP路径提取到了更具体的信息，使用这些信息
                        if zip_platform != "Unknown":
                            platform = zip_platform
                        if zip_model != "Unknown":
                            model = zip_model
                        if zip_issue != "Unknown":
                            issue = zip_issue

                    # 解析ZIP文件
                    parser_name, df = self.parse_zip_file(zip_path, input_path, platform, model, issue)
                    self.log(f"使用 {parser_name} 成功解析文件")

                    # 生成输出文件名（在同一目录下）
                    output_excel = os.path.join(os.path.dirname(zip_path), xlsx_filename)

                    # 保存到Excel
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name="Submit Pattern Lines", index=False)

                    # 记录到共享数据库
                    file_size = os.path.getsize(output_excel)
                    self.save_to_database(zip_path, output_excel, platform, model, issue, file_size, df)

                    # 添加到总数据
                    all_data.append(df)
                    total_processed += 1

                    self.log(f"结果已保存到: {output_excel}")

                except Exception as e:
                    self.log(f"处理失败 {os.path.basename(zip_path)}: {str(e)}")
                    continue

        # 合并所有处理结果
        if all_data:
            self.processed_data = pd.concat(all_data, ignore_index=True)
            self.log(f"处理完成！共处理 {total_processed} 个ZIP文件")
            self.log(f"总数据量: {len(self.processed_data)} 行")

            # 显示数据库统计
            self.show_database_stats()
        else:
            self.log("没有成功处理任何文件")

    def show_database_content(self):
        """显示数据库内容"""
        try:
            # 创建数据库查看窗口
            db_window = tk.Toplevel(self.root)
            db_window.title("共享数据库内容")
            db_window.geometry("1200x600")

            # 创建选项卡
            notebook = ttk.Notebook(db_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Radio Units 选项卡
            units_frame = ttk.Frame(notebook, padding="10")
            notebook.add(units_frame, text="Radio Units")

            # 搜索框
            search_frame = ttk.Frame(units_frame)
            search_frame.pack(fill=tk.X, pady=5)

            ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=5)
            search_var = tk.StringVar()
            search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
            search_entry.pack(side=tk.LEFT, padx=5)

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

            ttk.Button(search_frame, text="搜索", command=perform_search).pack(side=tk.LEFT, padx=5)
            ttk.Button(search_frame, text="显示全部",
                       command=lambda: [search_var.set(""), perform_search()]).pack(side=tk.LEFT, padx=5)

            # Radio Units 表格
            units_columns = ("serial_number", "model", "platform", "issue_description", "created_date")
            units_tree = ttk.Treeview(units_frame, columns=units_columns, show="headings", height=15)

            units_tree.heading("serial_number", text="序列号")
            units_tree.heading("model", text="型号")
            units_tree.heading("platform", text="平台")
            units_tree.heading("issue_description", text="问题描述")
            units_tree.heading("created_date", text="创建日期")

            units_tree.column("serial_number", width=150)
            units_tree.column("model", width=150)
            units_tree.column("platform", width=100)
            units_tree.column("issue_description", width=200)
            units_tree.column("created_date", width=150)

            scrollbar = ttk.Scrollbar(units_frame, orient=tk.VERTICAL, command=units_tree.yview)
            units_tree.configure(yscrollcommand=scrollbar.set)

            units_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Log Files 选项卡
            logs_frame = ttk.Frame(notebook, padding="10")
            notebook.add(logs_frame, text="日志文件")

            # Log Files 表格
            logs_columns = ("serial_number", "log_type", "file_name", "file_path", "download_date")
            logs_tree = ttk.Treeview(logs_frame, columns=logs_columns, show="headings", height=15)

            logs_tree.heading("serial_number", text="序列号")
            logs_tree.heading("log_type", text="日志类型")
            logs_tree.heading("file_name", text="文件名")
            logs_tree.heading("file_path", text="文件路径")
            logs_tree.heading("download_date", text="下载日期")

            logs_tree.column("serial_number", width=150)
            logs_tree.column("log_type", width=100)
            logs_tree.column("file_name", width=200)
            logs_tree.column("file_path", width=300)
            logs_tree.column("download_date", width=150)

            logs_scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=logs_tree.yview)
            logs_tree.configure(yscrollcommand=logs_scrollbar.set)

            logs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            logs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 初始加载数据
            perform_search()
            self.load_log_files(logs_tree)

        except Exception as e:
            messagebox.showerror("错误", f"无法显示数据库内容: {str(e)}")

    @staticmethod
    def load_log_files(tree):
        """加载日志文件数据"""
        for item in tree.get_children():
            tree.delete(item)

        # 获取所有radio units
        units = db_manager.search_radio_units("")
        for unit in units:
            log_files = db_manager.get_log_files(unit["serial_number"])
            for log_file in log_files:
                log_type_map = {
                    1: "ExtLog", 2: "Site Failure Note", 3: "Proactive Logs",
                    4: "HWS Scrap Pictures", 5: "Processed XLSX"
                }
                log_type_name = log_type_map.get(log_file["log_type"], "未知")

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
                    file_types[log_file["log_type"]] += 1

            self.log("=== 数据库统计 ===")
            self.log(f"Radio Units 总数: {len(units)}")
            self.log(f"日志文件总数: {total_files}")
            self.log("各类型文件数量:")
            self.log(f"  - ExtLog: {file_types[1]}")
            self.log(f"  - Site Failure Note: {file_types[2]}")
            self.log(f"  - Proactive Logs: {file_types[3]}")
            self.log(f"  - HWS Scrap Pictures: {file_types[4]}")
            self.log(f"  - Processed XLSX: {file_types[5]}")

        except Exception as e:
            self.log(f"数据库统计错误: {str(e)}")

    def show_statistics(self):
        """显示统计图表"""
        if self.processed_data.empty:
            # 如果没有处理数据，尝试从数据库加载
            try:
                self.load_data_from_database()
            except:
                messagebox.showwarning("警告", "请先处理ZIP文件或数据库中没有数据")
                return

        # 创建统计窗口
        stats_window = tk.Toplevel(self.root)
        stats_window.title("统计图表")
        stats_window.geometry("1000x800")

        # 创建选项卡
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # # 平台分布图
        # platform_frame = ttk.Frame(notebook)
        # notebook.add(platform_frame, text="平台分布")
        #
        # # 型号分布图
        # model_frame = ttk.Frame(notebook)
        # notebook.add(model_frame, text="型号分布")
        #
        # # 问题分布图
        # issue_frame = ttk.Frame(notebook)
        # notebook.add(issue_frame, text="问题分布")

        # # 生成图表
        # self.create_platform_chart(platform_frame)
        # self.create_model_chart(model_frame)
        # self.create_issue_chart(issue_frame)

        # 序列号分布图（替代原来的平台分布）
        serial_frame = ttk.Frame(notebook)
        notebook.add(serial_frame, text="序列号分布")

        # 生成图表
        self.create_serial_chart(serial_frame)

    def load_data_from_database(self):
        """从数据库加载数据到processed_data"""
        try:
            all_data = []
            units = db_manager.search_radio_units("")

            for unit in units:
                # 从数据库加载数据时，只加载序列号信息
                temp_df = pd.DataFrame({
                    "Serial": [unit["serial_number"]]
                })
                all_data.append(temp_df)

            if all_data:
                self.processed_data = pd.concat(all_data, ignore_index=True)
                self.log(f"从数据库加载了 {len(self.processed_data)} 条记录")
            else:
                raise Exception("数据库中没有足够的数据")

        except Exception as e:
            raise Exception(f"从数据库加载数据失败: {str(e)}")

    # def create_platform_chart(self, parent):
    #     """创建平台分布饼图"""
    #     platform_counts = self.processed_data['Platform'].value_counts()
    #
    #     fig, ax = plt.subplots(figsize=(8, 6))
    #     colors = sns.color_palette('pastel', len(platform_counts))
    #
    #     wedges, texts, autotexts = ax.pie(platform_counts.values,
    #                                       labels=platform_counts.index,
    #                                       autopct='%1.1f%%',
    #                                       colors=colors,
    #                                       startangle=90)
    #
    #     # 美化文本
    #     for autotext in autotexts:
    #         autotext.set_color('black')
    #         autotext.set_fontsize(10)
    #
    #     ax.set_title('Distribution of Radio Platforms', fontsize=14, fontweight='bold')
    #
    #     # 嵌入到Tkinter
    #     canvas = FigureCanvasTkAgg(fig, parent)
    #     canvas.draw()
    #     canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    #
    # def create_model_chart(self, parent):
    #     """创建型号分布饼图"""
    #     model_counts = self.processed_data['Model'].value_counts()
    #
    #     # 如果型号太多，只显示前10个
    #     if len(model_counts) > 10:
    #         top_models = model_counts.head(10)
    #         other_count = model_counts[10:].sum()
    #         top_models['其他'] = other_count
    #         model_counts = top_models
    #
    #     fig, ax = plt.subplots(figsize=(8, 6))
    #     colors = sns.color_palette('Set3', len(model_counts))
    #
    #     wedges, texts, autotexts = ax.pie(model_counts.values,
    #                                       labels=model_counts.index,
    #                                       autopct='%1.1f%%',
    #                                       colors=colors,
    #                                       startangle=90)
    #
    #     for autotext in autotexts:
    #         autotext.set_color('black')
    #         autotext.set_fontsize(9)
    #
    #     ax.set_title('Distribution of Radio Products', fontsize=14, fontweight='bold')
    #
    #     canvas = FigureCanvasTkAgg(fig, parent)
    #     canvas.draw()
    #     canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    #
    # def create_issue_chart(self, parent):
    #     """创建问题分布饼图"""
    #     issue_counts = self.processed_data['Issue'].value_counts()
    #
    #     # 如果问题类型太多，只显示前8个
    #     if len(issue_counts) > 8:
    #         top_issues = issue_counts.head(8)
    #         other_count = issue_counts[8:].sum()
    #         top_issues['其他'] = other_count
    #         issue_counts = top_issues
    #
    #     fig, ax = plt.subplots(figsize=(8, 6))
    #     colors = sns.color_palette('husl', len(issue_counts))
    #
    #     wedges, texts, autotexts = ax.pie(issue_counts.values,
    #                                       labels=issue_counts.index,
    #                                       autopct='%1.1f%%',
    #                                       colors=colors,
    #                                       startangle=90)
    #
    #     for autotext in autotexts:
    #         autotext.set_color('black')
    #         autotext.set_fontsize(9)
    #
    #     ax.set_title('Distribution of Issues', fontsize=14, fontweight='bold')
    #
    #     canvas = FigureCanvasTkAgg(fig, parent)
    #     canvas.draw()
    #     canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_serial_chart(self, parent):
        """创建序列号分布饼图（显示前10个最常见的序列号）"""
        if 'Serial' in self.processed_data.columns:
            serial_counts = self.processed_data['Serial'].value_counts()

            # 只显示前10个序列号，其余的归为"其他"
            if len(serial_counts) > 10:
                top_serials = serial_counts.head(10)
                other_count = serial_counts[10:].sum()
                top_serials['其他'] = other_count
                serial_counts = top_serials

            fig, ax = plt.subplots(figsize=(8, 6))
            colors = sns.color_palette('pastel', len(serial_counts))

            wedges, texts, autotexts = ax.pie(serial_counts.values,
                                              labels=serial_counts.index,
                                              autopct='%1.1f%%',
                                              colors=colors,
                                              startangle=90)

            # 美化文本
            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontsize(8)

            ax.set_title('Distribution of Radio Serials (Top 10)', fontsize=14, fontweight='bold')

            # 嵌入到Tkinter
            canvas = FigureCanvasTkAgg(fig, parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            # 如果没有Serial列，显示提示信息
            label = ttk.Label(parent, text="没有序列号数据可用", font=("Arial", 12))
            label.pack(expand=True)

    def export_results(self):
        """导出处理结果"""
        if self.processed_data.empty:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="导出处理结果"
        )

        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    # 保存主数据
                    self.processed_data.to_excel(writer, sheet_name="所有数据", index=False)

                    # 保存统计摘要
                    summary_data = self.create_summary()
                    summary_data.to_excel(writer, sheet_name="统计摘要", index=False)

                self.log(f"结果已导出到: {file_path}")
                messagebox.showinfo("成功", f"数据已成功导出到:\n{file_path}")

            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

    def create_summary(self):
        """创建统计摘要"""
        summary = {
            '统计项': ['总数据行数', '唯一序列号数量'],
            '数值': [
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
