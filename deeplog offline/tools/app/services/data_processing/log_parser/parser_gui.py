import os
import pandas as pd
import json
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List
from datetime import datetime

from tools.app.services.data_processing.log_parser.models.log_entry import LogEntry
from tools.app.services.data_processing.log_parser.models.alarm_entry import AlarmEntry
from tools.app.services.data_processing.log_parser.parsers.base_parser import BaseParser
from tools.app.services.data_processing.log_parser.parsers.elog_parser import ElogParser
from tools.app.services.data_processing.log_parser.parsers.hwlog_parser import HWlogParser
from tools.app.services.data_processing.log_parser.parsers.read_parser import ReadParser
from tools.app.services.data_processing.log_parser.parsers.trx_parser import TrxStatusParser
from tools.app.services.data_processing.log_parser.parsers.pareadall_parser import PareadallParser

# =====================
# logging
# =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================
# i18n resources (EN/中文 toggle)
# =====================
I18N = {
    "zh": {
        "win_title": "Log文件解析",
        "title": "Log文件解析",

        "input_frame": "输入文件设置",
        "btn_add": "添加文件",
        "btn_remove": "移除文件",
        "btn_remove_all": "移除所有",

        "options_frame": "处理选项",
        "output_format": "输出格式:",

        "btn_parse": "解析Excel文件",
        "btn_export": "导出处理结果",
        "btn_clear_log": "清空日志",

        "log_frame": "处理日志",

        "init_log_1": "欢迎使用 Excel 文件解析工具",
        "init_log_2": "请添加包含 Excel 文件的文件夹路径",

        "dlg_pick_dir": "选择包含Excel文件的文件夹",
        "dlg_export_summary": "导出处理结果汇总",

        "warn": "警告",
        "error": "错误",
        "success": "成功",
        "done": "完成",

        "warn_need_input": "请至少添加一个输入路径",
        "warn_no_excel": "在指定路径中未找到任何Excel文件",
        "warn_no_export": "没有可导出的处理结果",

        "log_add_path": "添加输入路径: {path}",
        "log_remove_path": "移除输入路径: {path}",
        "log_clear_paths": "已清空所有输入路径",
        "log_cleared": "日志已清空",

        "log_found": "找到 {n} 个Excel文件",
        "log_processing": "正在处理 ({i}/{n}): {name}",
        "log_skip_sheet": "跳过: {name} 不包含 'Submit Pattern Lines' 工作表",
        "log_check_fail": "检查文件失败 {name}: {msg}",
        "log_parse_ok": "成功解析 {n} 条日志条目",
        "log_parse_fail": "解析文件内容失败: {msg}",
        "log_save_excel": "Excel结果已保存: {name}",
        "log_save_json": "JSON结果已保存: {name}",
        "log_elapsed": "文件处理完成，耗时 {sec:.2f} 秒",
        "log_save_fail": "保存结果失败: {msg}",
        "log_fail": "处理失败 {name}: {msg}",
        "log_trace": "详细错误: {trace}",

        "log_all_done": "处理完成！共成功处理 {n} 个Excel文件",
        "msg_all_done": "处理完成！共成功处理 {n} 个文件",

        "summary_file": "文件名",
        "summary_path": "文件路径",
        "summary_size": "文件大小",
        "summary_mtime": "修改时间",

        "log_exported": "处理结果汇总已导出到: {path}",
        "msg_exported": "处理结果汇总已导出到:\n{path}",
        "msg_export_fail": "导出失败: {msg}",

        # language toggle button label (shows the target language)
        "lang_btn": "EN",

        # sheets
        "sheet_submit": "Submit Pattern Lines",

        # radiobutton labels
        "fmt_excel": "Excel",
        "fmt_json": "JSON",
        "fmt_both": "Both",
    },
    "en": {
        "win_title": "Log Parser",
        "title": "Log Parser",

        "input_frame": "Input Settings",
        "btn_add": "Add Folder",
        "btn_remove": "Remove Selected",
        "btn_remove_all": "Remove All",

        "options_frame": "Options",
        "output_format": "Output:",

        "btn_parse": "Parse Excel Files",
        "btn_export": "Export Summary",
        "btn_clear_log": "Clear Log",

        "log_frame": "Logs",

        "init_log_1": "Welcome to the Excel parsing tool",
        "init_log_2": "Please add folder paths that contain Excel files",

        "dlg_pick_dir": "Select a folder that contains Excel files",
        "dlg_export_summary": "Export processing summary",

        "warn": "Warning",
        "error": "Error",
        "success": "Success",
        "done": "Done",

        "warn_need_input": "Please add at least one input folder.",
        "warn_no_excel": "No Excel files found under the selected paths.",
        "warn_no_export": "No processed results to export.",

        "log_add_path": "Added input path: {path}",
        "log_remove_path": "Removed input path: {path}",
        "log_clear_paths": "Cleared all input paths",
        "log_cleared": "Log cleared",

        "log_found": "Found {n} Excel files",
        "log_processing": "Processing ({i}/{n}): {name}",
        "log_skip_sheet": "Skipped: {name} does not contain 'Submit Pattern Lines' sheet",
        "log_check_fail": "Failed to inspect {name}: {msg}",
        "log_parse_ok": "Parsed {n} log entries successfully",
        "log_parse_fail": "Failed to parse file content: {msg}",
        "log_save_excel": "Excel saved: {name}",
        "log_save_json": "JSON saved: {name}",
        "log_elapsed": "Completed in {sec:.2f} seconds",
        "log_save_fail": "Failed to save output: {msg}",
        "log_fail": "Failed {name}: {msg}",
        "log_trace": "Trace: {trace}",

        "log_all_done": "Done! Successfully processed {n} Excel files",
        "msg_all_done": "Done! Successfully processed {n} files",

        "summary_file": "File Name",
        "summary_path": "File Path",
        "summary_size": "File Size",
        "summary_mtime": "Modified Time",

        "log_exported": "Summary exported to: {path}",
        "msg_exported": "Summary exported to:\n{path}",
        "msg_export_fail": "Export failed: {msg}",

        # language toggle button label (shows the target language)
        "lang_btn": "中文",

        # sheets
        "sheet_submit": "Submit Pattern Lines",

        # radiobutton labels
        "fmt_excel": "Excel",
        "fmt_json": "JSON",
        "fmt_both": "Both",
    }
}


class ExcelParser:
    """
    主解析器：解析对象是PDP/EELA对proactive log处理后的excel文件
    使用组合模式代替多重继承
    """

    def __init__(self):
        self.base_parser = BaseParser()
        self.elog_parser = ElogParser(self.base_parser)
        self.hwlog_parser = HWlogParser(self.base_parser)
        self.read_parser = ReadParser(self.base_parser)
        self.trx_status_parser = TrxStatusParser(self.base_parser)
        self.pareadall_parser = PareadallParser(self.base_parser)

        self.log_entries = self.base_parser.log_entries
        self.alarm_entries = self.base_parser.alarm_entries

        self._min_valid_date = pd.to_datetime('2022-01-01 00:00:00')

    def _process_serial_group(self, serial, entries):
        """
        处理单个serial的条目
        1. 处理timestamp='' 的条目
        2. 处理timestamp早于20220101 00:00:00的条目
        """
        # 收集该serial的elog10条目
        elog10_entries = [
            e for e in entries
            if e.log_type == 'elog' and e.log_id == '10' and e.timestamp and e.timestamp != ''
        ]
        elog10_entries.sort(key=lambda x: pd.to_datetime(x.timestamp))

        valid_entries = []
        empty_entries = []

        # 第一次遍历：分类条目
        for entry in entries:
            if entry.timestamp and entry.timestamp != '':
                try:
                    dt = pd.to_datetime(entry.timestamp)
                    if dt >= self._min_valid_date:
                        valid_entries.append((dt, entry))
                except Exception:
                    pass
            else:
                empty_entries.append(entry)

        # 处理空时间戳
        last_key_value = None
        elog_index = 0
        for empty_entry in empty_entries:
            current_key_value = (empty_entry.key, empty_entry.value)
            if current_key_value == last_key_value and elog_index + 1 < len(elog10_entries):
                elog_index += 1
            elif current_key_value != last_key_value:
                elog_index = 0

            if elog_index < len(elog10_entries):
                elog_entry = elog10_entries[elog_index]
                empty_entry.timestamp = elog_entry.timestamp
                empty_entry.parent_index = elog_entry.parent_index

            last_key_value = current_key_value

        # 处理无效时间戳
        for entry in entries:
            if entry.timestamp and entry.timestamp != '':
                try:
                    dt = pd.to_datetime(entry.timestamp)
                    if dt < self._min_valid_date and valid_entries:
                        from bisect import bisect_left
                        times = [ve[0] for ve in valid_entries]
                        idx = bisect_left(times, dt)
                        candidates = []
                        if idx > 0:
                            candidates.append(valid_entries[idx - 1])
                        if idx < len(valid_entries):
                            candidates.append(valid_entries[idx])
                        if candidates:
                            closest_entry = min(
                                candidates,
                                key=lambda x: abs((x[0] - dt).total_seconds())
                            )[1]
                            entry.timestamp = closest_entry.timestamp
                except Exception:
                    pass

        return entries

    def _post_process_entries(self):
        """对解析后的条目进行再处理，按serial分组处理"""
        from collections import defaultdict
        serial_groups = defaultdict(list)
        for entry in self.log_entries:
            serial_groups[entry.serial_number].append(entry)

        self.log_entries.clear()
        for serial, entries in serial_groups.items():
            processed_entries = self._process_serial_group(serial, entries)
            self.log_entries.extend(processed_entries)

    def parse_excel_sheet_log(self, file_path: str, sheet_name: str) -> List[LogEntry]:
        """
        解析Submit Pattern Lines工作表
        返回处理后的所有日志条目
        """
        from collections import defaultdict
        try:
            xl_file = pd.ExcelFile(file_path)
            if sheet_name not in xl_file.sheet_names:
                raise ValueError(f"工作表 '{sheet_name}' 不存在")

            df = pd.read_excel(file_path, sheet_name=sheet_name)
            if df.empty:
                print('警告：输入文件为空！')
                return []

            required = ['Serial', 'ProductName', 'log_type', 'log_line']
            missing = [c for c in required if c not in df.columns]
            if missing:
                available = ', '.join(df.columns)
                raise ValueError(f'输入文件缺少列: {missing}! 现有列: {available}')

            serial_data = defaultdict(list)
            for row in df.itertuples(index=False):
                serial = str(row.Serial) if pd.notna(row.Serial) else ''
                serial_data[serial].append(row)

            self.log_entries.clear()

            for serial, rows in serial_data.items():
                self.base_parser.reset_for_new_serial()

                for row_index, row in enumerate(rows):
                    product = str(row.ProductName) if pd.notna(row.ProductName) else ''
                    log_type = str(row.log_type) if pd.notna(row.log_type) else ''
                    log_line = str(row.log_line) if pd.notna(row.log_line) else ''
                    if not log_line:
                        continue

                    if log_type == 'trx_status':
                        print(f" 处理trx_status第{row_index + 1}行: {log_line[:50]}...")
                        trx_lines = [log_line]
                        self.trx_status_parser.parse_trx_status_entry(
                            serial_number=serial,
                            product_name=product,
                            log_type=log_type,
                            line_iter=iter(trx_lines)
                        )
                        current_count = len(self.base_parser.log_entries)
                        print(f" 解析trx_status后，总日志条目数: {current_count}")
                        continue

                    if log_type in ('csread', 'vsread', 'tsread'):
                        self.read_parser.parse_read_entry(serial, product, log_type, log_line)
                    elif log_type == 'hwlog':
                        self.hwlog_parser.parse_hwlog_entry(serial, product, log_type, log_line)
                    elif log_type == 'pareadall':
                        self.pareadall_parser.parse_pareadall_entry(serial, product, log_type, log_line)
                    elif log_type == 'elog':
                        self.elog_parser.parse_elog_entry(serial, product, log_type, log_line)
                    else:
                        self.base_parser.add_log_entry(
                            serial_number=serial,
                            product_name=product,
                            log_type=log_type,
                            timestamp='',
                            log_id='',
                            content=log_line,
                            slogan=log_line,
                            key='',
                            value='',
                            value_type='',
                            is_measured_value=False,
                            parent_index=self.base_parser.log_index + 1
                        )

                current_serial_entries = [
                    e for e in self.base_parser.log_entries if e.serial_number == serial
                ]
                processed_entries = self._process_serial_group(serial, current_serial_entries)
                self.base_parser.log_entries = [
                    e for e in self.base_parser.log_entries if e.serial_number != serial
                ]
                self.base_parser.log_entries.extend(processed_entries)

            return self.base_parser.log_entries

        except Exception as e:
            logger.error(f"处理过程中出错: {str(e)}")
            raise

    def parse_excel_sheet_alarm(self, file_path: str, sheet_name: str) -> None:
        """解析Submit Pattern Result工作表"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            if df.empty:
                print('警告：输入文件为空！')
                return

            required = [
                'Serial', 'ProductName', 'PartName', 'ProductNo', 'HWrev', 'Production',
                'Alarm_time', 'Alarm_Name', 'AdditionalInfo'
            ]
            missing = [c for c in required if c not in df.columns]
            if missing:
                available = ', '.join(df.columns)
                raise ValueError(f'输入文件缺少列: {missing}! 现有列: {available}')

            for row in df.itertuples(index=False):
                serial = str(row.Serial) if pd.notna(row.Serial) else ''
                product_name = str(row.ProductName) if pd.notna(row.ProductName) else ''
                part_name = str(row.PartName) if pd.notna(row.PartName) else ''
                production_no = str(row.ProductNo) if pd.notna(row.ProductNo) else ''
                hw_rev = str(row.HWrev) if pd.notna(row.HWrev) else ''
                production_time = str(row.Production) if pd.notna(row.Production) else ''
                alarm_time = str(row.Alarm_time) if pd.notna(row.Alarm_time) else ''
                alarm_name = str(row.Alarm_Name) if pd.notna(row.Alarm_Name) else ''
                additional_info = str(row.AdditionalInfo) if pd.notna(row.AdditionalInfo) else ''

                self.base_parser.add_alarm_entry(
                    serial_number=serial,
                    product_name=product_name,
                    part_name=part_name,
                    production_no=production_no,
                    hw_rev=hw_rev,
                    production_time=production_time,
                    alarm_time=alarm_time,
                    alarm_name=alarm_name,
                    additional_info=additional_info,
                    parent_index=self.base_parser.alarm_index + 1
                )

        except Exception as e:
            logger.error(f"处理过程中出错: {str(e)}", exc_info=True)
            raise

    def save_log_to_excel(self, output_path: str) -> None:
        df = pd.DataFrame([entry.log_to_dict() for entry in self.log_entries])
        df.to_excel(output_path, index=False)

    def save_alarm_to_excel(self, output_path: str) -> None:
        df = pd.DataFrame([entry.alarm_to_dict() for entry in self.alarm_entries])
        df.to_excel(output_path, index=False)

    def save_log_to_json(self, output_path: str) -> None:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([entry.log_to_dict() for entry in self.log_entries], f, ensure_ascii=False, indent=2)

    def save_alarm_to_json(self, output_path: str) -> None:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([entry.alarm_to_dict() for entry in self.alarm_entries], f, ensure_ascii=False, indent=2)

    def get_log_entries(self) -> List[LogEntry]:
        return self.log_entries.copy()

    def get_alarm_entries(self) -> List[AlarmEntry]:
        return self.alarm_entries.copy()


class ExcelParserGUI:
    """ExcelParser 的 GUI 界面"""

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

        # 输入路径列表
        self.input_paths = []

        # 存储处理结果
        self.processed_files = []

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
        # window title
        try:
            self.root.title(self.t("win_title"))
        except Exception:
            pass

        # title + lang button
        if hasattr(self, "title_label"):
            self.title_label.configure(text=self.t("title"))
        if hasattr(self, "lang_btn"):
            self.lang_btn.configure(text=self.t("lang_btn"))

        # labelframes
        if hasattr(self, "input_frame"):
            self.input_frame.configure(text=self.t("input_frame"))
        if hasattr(self, "options_frame"):
            self.options_frame.configure(text=self.t("options_frame"))
        if hasattr(self, "log_frame"):
            self.log_frame.configure(text=self.t("log_frame"))

        # labels
        if hasattr(self, "lbl_output_format"):
            self.lbl_output_format.configure(text=self.t("output_format"))

        # radiobuttons
        if hasattr(self, "rb_excel"):
            self.rb_excel.configure(text=self.t("fmt_excel"))
        if hasattr(self, "rb_json"):
            self.rb_json.configure(text=self.t("fmt_json"))
        if hasattr(self, "rb_both"):
            self.rb_both.configure(text=self.t("fmt_both"))

        # buttons
        mapping = [
            ("btn_add", "btn_add"),
            ("btn_remove", "btn_remove"),
            ("btn_remove_all", "btn_remove_all"),
            ("btn_parse", "btn_parse"),
            ("btn_export", "btn_export"),
            ("btn_clear_log", "btn_clear_log"),
        ]
        for attr, key in mapping:
            if hasattr(self, attr):
                getattr(self, attr).configure(text=self.t(key))

    def setup_dark_theme(self):
        """设置深色主题"""
        style = ttk.Style()

        style.configure(
            "Black.TEntry",
            fieldbackground=self.entry_bg,
            foreground="#000000"
        )
        style.configure(
            "Black.TCombobox",
            fieldbackground=self.entry_bg,
            foreground="#000000"
        )

        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure(
            "TButton",
            background=self.accent_color,
            foreground="#000000"
        )
        style.map(
            "TButton",
            background=[("active", self.accent_color), ("pressed", self.accent_color)],
            foreground=[("active", "#000000"), ("pressed", "#000000")]
        )
        style.configure("TEntry", fieldbackground=self.entry_bg, foreground=self.fg_color)

        style.configure(
            "White.TLabelframe",
            background=self.bg_color,
            foreground=self.fg_color
        )
        style.configure(
            "White.TLabelframe.Label",
            background=self.frame_bg,
            foreground=self.fg_color
        )
        style.configure("TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)

        style.configure("TProgressbar", background=self.accent_color, troughcolor=self.frame_bg)

    def setup_ui(self):
        """设置用户界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题栏：标题 + 语言切换
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
        self.input_frame = ttk.LabelFrame(main_frame, text=self.t("input_frame"), padding="10", style="White.TLabelframe")
        self.input_frame.pack(fill=tk.X, pady=5)

        self.input_listbox = tk.Listbox(
            self.input_frame,
            height=4,
            bg=self.entry_bg,
            fg=self.fg_color,
            selectbackground=self.accent_color
        )
        self.input_listbox.pack(fill=tk.X, pady=5)

        input_button_frame = ttk.Frame(self.input_frame)
        input_button_frame.pack(fill=tk.X)

        self.btn_add = ttk.Button(input_button_frame, text=self.t("btn_add"), command=self.add_input_path)
        self.btn_add.pack(side=tk.LEFT, padx=5)

        self.btn_remove = ttk.Button(input_button_frame, text=self.t("btn_remove"), command=self.remove_input_path)
        self.btn_remove.pack(side=tk.LEFT, padx=5)

        self.btn_remove_all = ttk.Button(input_button_frame, text=self.t("btn_remove_all"), command=self.clear_input_paths)
        self.btn_remove_all.pack(side=tk.LEFT, padx=5)

        # 处理选项框架
        self.options_frame = ttk.LabelFrame(main_frame, text=self.t("options_frame"), padding="10", style="White.TLabelframe")
        self.options_frame.pack(fill=tk.X, pady=5)

        format_frame = ttk.Frame(self.options_frame)
        format_frame.pack(fill=tk.X, pady=5)

        self.lbl_output_format = ttk.Label(format_frame, text=self.t("output_format"))
        self.lbl_output_format.pack(side=tk.LEFT, padx=5)

        self.output_format = tk.StringVar(value="excel")

        self.rb_excel = ttk.Radiobutton(format_frame, text=self.t("fmt_excel"), variable=self.output_format, value="excel")
        self.rb_excel.pack(side=tk.LEFT, padx=5)

        self.rb_json = ttk.Radiobutton(format_frame, text=self.t("fmt_json"), variable=self.output_format, value="json")
        self.rb_json.pack(side=tk.LEFT, padx=5)

        self.rb_both = ttk.Radiobutton(format_frame, text=self.t("fmt_both"), variable=self.output_format, value="both")
        self.rb_both.pack(side=tk.LEFT, padx=5)

        # 处理按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.btn_parse = ttk.Button(button_frame, text=self.t("btn_parse"), command=self.process_excel_files)
        self.btn_parse.pack(side=tk.LEFT, padx=5)

        self.btn_export = ttk.Button(button_frame, text=self.t("btn_export"), command=self.export_results)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        self.btn_clear_log = ttk.Button(button_frame, text=self.t("btn_clear_log"), command=self.clear_log)
        self.btn_clear_log.pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        # 日志显示框架
        self.log_frame = ttk.LabelFrame(main_frame, text=self.t("log_frame"), padding="10", style="White.TLabelframe")
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(
            self.log_frame,
            height=15,
            bg=self.entry_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color
        )
        scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 初始日志
        self.log(self.t("init_log_1"))
        self.log(self.t("init_log_2"))

    def log(self, message: str):
        """添加日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    def add_input_path(self):
        """添加输入路径"""
        path = filedialog.askdirectory(title=self.t("dlg_pick_dir"))
        if path and path not in self.input_paths:
            self.input_paths.append(path)
            self.input_listbox.insert(tk.END, path)
            self.log(self.t("log_add_path", path=path))

    def remove_input_path(self):
        """移除选中的输入路径"""
        selection = self.input_listbox.curselection()
        if selection:
            index = selection[0]
            path = self.input_paths.pop(index)
            self.input_listbox.delete(index)
            self.log(self.t("log_remove_path", path=path))

    def clear_input_paths(self):
        """清空所有输入路径"""
        self.input_paths.clear()
        self.input_listbox.delete(0, tk.END)
        self.log(self.t("log_clear_paths"))

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log(self.t("log_cleared"))

    def process_excel_files(self):
        """处理所有Excel文件"""
        if not self.input_paths:
            messagebox.showwarning(self.t("warn"), self.t("warn_need_input"))
            return

        # 收集所有Excel文件
        excel_files = []
        for input_path in self.input_paths:
            for root_dir, _, files in os.walk(input_path):
                for file in files:
                    if (file.lower().endswith('.xlsx')
                            and not file.startswith('~')
                            and '_parsed' not in file):  # 排除已解析的文件
                        excel_files.append(os.path.join(root_dir, file))

        if not excel_files:
            self.log(self.t("warn_no_excel"))
            return

        self.log(self.t("log_found", n=len(excel_files)))

        # 设置进度条
        self.progress['maximum'] = len(excel_files)
        self.progress['value'] = 0

        total_processed = 0
        self.processed_files = []

        for file_index, excel_file in enumerate(excel_files):
            try:
                self.log(self.t(
                    "log_processing",
                    i=file_index + 1,
                    n=len(excel_files),
                    name=os.path.basename(excel_file)
                ))

                # 检查文件是否包含必要的工作表
                try:
                    xl_file = pd.ExcelFile(excel_file)
                    if self.t("sheet_submit") not in xl_file.sheet_names:
                        self.log(self.t("log_skip_sheet", name=os.path.basename(excel_file)))
                        continue
                except Exception as e:
                    self.log(self.t("log_check_fail", name=os.path.basename(excel_file), msg=str(e)))
                    continue

                # 创建解析器实例
                parser = ExcelParser()

                # 解析文件
                start_time = datetime.now()
                try:
                    log_entries = parser.parse_excel_sheet_log(excel_file, sheet_name=self.t("sheet_submit"))
                    self.log(self.t("log_parse_ok", n=len(log_entries)))
                except Exception as parse_error:
                    self.log(self.t("log_parse_fail", msg=str(parse_error)))
                    continue

                elapsed = (datetime.now() - start_time).total_seconds()

                # 生成输出文件名（原地存放）
                base_name = os.path.splitext(excel_file)[0]
                output_format = self.output_format.get()

                # 保存结果
                try:
                    if output_format in ["excel", "both"]:
                        output_excel = f"{base_name}_parsed.xlsx"
                        df = pd.DataFrame([entry.log_to_dict() for entry in log_entries])
                        df.to_excel(output_excel, index=False)
                        self.log(self.t("log_save_excel", name=os.path.basename(output_excel)))
                        self.processed_files.append(output_excel)

                    if output_format in ["json", "both"]:
                        output_json = f"{base_name}_parsed.json"
                        with open(output_json, 'w', encoding='utf-8') as f:
                            json.dump([entry.log_to_dict() for entry in log_entries], f, ensure_ascii=False, indent=2)
                        self.log(self.t("log_save_json", name=os.path.basename(output_json)))
                        self.processed_files.append(output_json)

                    total_processed += 1
                    self.log(self.t("log_elapsed", sec=elapsed))

                except Exception as save_error:
                    self.log(self.t("log_save_fail", msg=str(save_error)))
                    continue

            except Exception as e:
                import traceback
                self.log(self.t("log_fail", name=os.path.basename(excel_file), msg=str(e)))
                self.log(self.t("log_trace", trace=traceback.format_exc()))
                continue

            finally:
                # 更新进度条
                self.progress['value'] = file_index + 1
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass

        self.log(self.t("log_all_done", n=total_processed))
        messagebox.showinfo(self.t("done"), self.t("msg_all_done", n=total_processed))

    def export_results(self):
        """导出处理结果汇总"""
        if not self.processed_files:
            messagebox.showwarning(self.t("warn"), self.t("warn_no_export"))
            return

        summary_data = []
        for file_path in self.processed_files:
            file_info = {
                self.t("summary_file"): os.path.basename(file_path),
                self.t("summary_path"): file_path,
                self.t("summary_size"): f"{os.path.getsize(file_path)} bytes",
                self.t("summary_mtime"): datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            }
            summary_data.append(file_info)

        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title=self.t("dlg_export_summary")
        )

        if save_path:
            try:
                df = pd.DataFrame(summary_data)
                df.to_excel(save_path, index=False)
                self.log(self.t("log_exported", path=save_path))
                messagebox.showinfo(self.t("success"), self.t("msg_exported", path=save_path))
            except Exception as e:
                messagebox.showerror(self.t("error"), self.t("msg_export_fail", msg=str(e)))


def main():
    root = tk.Tk()
    ExcelParserGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()