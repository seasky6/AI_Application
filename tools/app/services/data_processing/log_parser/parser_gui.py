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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        elog10_entries = [e for e in entries if e.log_type == 'elog' and e.log_id == '10'
                          and e.timestamp and e.timestamp != '']
        elog10_entries.sort(key=lambda x: pd.to_datetime(x.timestamp))

        # 处理空时间戳和无效时间戳
        valid_entries = []
        empty_entries = []

        # 第一次遍历：分类条目
        for entry in entries:
            if entry.timestamp and entry.timestamp != '':
                try:
                    dt = pd.to_datetime(entry.timestamp)
                    if dt >= self._min_valid_date:
                        valid_entries.append((dt, entry))
                except:
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
                        # 使用二分查找找到最接近的时间
                        from bisect import bisect_left
                        times = [ve[0] for ve in valid_entries]
                        idx = bisect_left(times, dt)

                        # 检查左右两边的时间
                        candidates = []
                        if idx > 0:
                            candidates.append(valid_entries[idx - 1])
                        if idx < len(valid_entries):
                            candidates.append(valid_entries[idx])

                        if candidates:
                            # 找到时间差最小的条目
                            closest_entry = min(
                                candidates,
                                key=lambda x: abs((x[0] - dt).total_seconds())
                            )[1]
                            entry.timestamp = closest_entry.timestamp
                except:
                    pass

        return entries

    def _post_process_entries(self):
        """
        对解析后的条目进行再处理，按serial分组处理
        """
        # 使用defaultdict提高分组效率
        from collections import defaultdict
        serial_groups = defaultdict(list)

        # 按serial分组
        for entry in self.log_entries:
            serial_groups[entry.serial_number].append(entry)

        # 清空原始log_entries以节省内存
        self.log_entries.clear()

        # 逐个处理serial组
        for serial, entries in serial_groups.items():
            processed_entries = self._process_serial_group(serial, entries)
            self.log_entries.extend(processed_entries)

    def parse_excel_sheet_log(self, file_path: str, sheet_name: str) -> List[LogEntry]:
        """
        解析Submit Pattern Lines工作表
        返回处理后的所有日志条目
        """
        # 使用defaultdict提高分组效率
        from collections import defaultdict

        try:
            # 先检查文件是否存在必要的工作表
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

            # 按serial分组原始数据
            serial_data = defaultdict(list)
            for row in df.itertuples(index=False):
                serial = str(row.Serial) if pd.notna(row.Serial) else ''
                serial_data[serial].append(row)

            # 清空现有日志条目
            self.log_entries.clear()

            # 逐个处理每个serial的数据
            for serial, rows in serial_data.items():
                # 重置解析器状态(如果需要)
                self.base_parser.reset_for_new_serial()

                # 处理当前serial的所有行
                for row_index, row in enumerate(rows):
                    product = str(row.ProductName) if pd.notna(row.ProductName) else ''
                    log_type = str(row.log_type) if pd.notna(row.log_type) else ''
                    log_line = str(row.log_line) if pd.notna(row.log_line) else ''

                    if not log_line:
                        continue

                    if log_type == 'trx_status':
                        print(f"  处理trx_status第{row_index+1}行: {log_line[:50]}...")
                        # 处理trx_status特殊逻辑
                        trx_lines = [log_line]
                        self.trx_status_parser.parse_trx_status_entry(
                            serial_number=serial,
                            product_name=product,
                            log_type=log_type,
                            line_iter=iter(trx_lines)
                        )
                        # 检查解析后是否有条目添加
                        current_count = len(self.base_parser.log_entries)
                        print(f"  解析trx_status后，总日志条目数: {current_count}")
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

                # 处理完成后对当前serial的条目进行后处理
                current_serial_entries = [e for e in self.base_parser.log_entries if e.serial_number == serial]
                processed_entries = self._process_serial_group(serial, current_serial_entries)

                # 移除旧的条目，添加处理后的条目
                self.base_parser.log_entries = [e for e in self.base_parser.log_entries if e.serial_number != serial]
                self.base_parser.log_entries.extend(processed_entries)

            return self.base_parser.log_entries

        except Exception as e:
            logger.error(f"处理过程中出错: {str(e)}")
            raise

    def parse_excel_sheet_alarm(self, file_path: str, sheet_name: str) -> None:
        """
        解析Submit Pattern Result工作表
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            if df.empty:
                print('警告：输入文件为空！')
                return

            required = ['Serial', 'ProductName', 'PartName', 'ProductNo', 'HWrev', 'Production', 'Alarm_time',
                        'Alarm_Name', 'AdditionalInfo']
            missing = [c for c in required if c not in df.columns]
            if missing:
                available = ', '.join(df.columns)
                raise ValueError(f'输入文件缺少列: {missing}! 现有列: {available}')

            # 使用itertuples()代替zip，效率更高
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
    """
    ExcelParser 的 GUI 界面
    """
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

        # 输入路径列表
        self.input_paths = []

        # 存储处理结果
        self.processed_files = []

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
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="Log文件解析", font=("Arial", 16, "bold"),
                                foreground=self.fg_color, background=self.bg_color)
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
        ttk.Button(input_button_frame, text="移除文件",
                   command=self.remove_input_path).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_button_frame, text="移除所有",
                   command=self.clear_input_paths).pack(side=tk.LEFT, padx=5)

        # 处理选项框架
        options_frame = ttk.LabelFrame(main_frame, text="处理选项", padding="10", style="White.TLabelframe")
        options_frame.pack(fill=tk.X, pady=5)

        # 输出格式选择
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=5)

        ttk.Label(format_frame, text="输出格式:").pack(side=tk.LEFT, padx=5)

        self.output_format = tk.StringVar(value="excel")
        ttk.Radiobutton(format_frame, text="Excel", variable=self.output_format,
                        value="excel").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="JSON", variable=self.output_format,
                        value="json").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="Both", variable=self.output_format,
                        value="both").pack(side=tk.LEFT, padx=5)

        # 处理按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="解析Excel文件",
                   command=self.process_excel_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出处理结果",
                   command=self.export_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空日志",
                   command=self.clear_log).pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

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
        self.log("欢迎使用 Excel 文件解析工具")
        self.log("请添加包含 Excel 文件的文件夹路径")

    def log(self, message):
        """添加日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def add_input_path(self):
        """添加输入路径"""
        path = filedialog.askdirectory(title="选择包含Excel文件的文件夹")
        if path and path not in self.input_paths:
            self.input_paths.append(path)
            self.input_listbox.insert(tk.END, path)
            self.log(f"添加输入路径: {path}")

    def remove_input_path(self):
        """移除选中的输入路径"""
        selection = self.input_listbox.curselection()
        if selection:
            index = selection[0]
            path = self.input_paths.pop(index)
            self.input_listbox.delete(index)
            self.log(f"移除输入路径: {path}")

    def clear_input_paths(self):
        """清空所有输入路径"""
        self.input_paths.clear()
        self.input_listbox.delete(0, tk.END)
        self.log("已清空所有输入路径")

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清空")

    def process_excel_files(self):
        """处理所有Excel文件"""
        if not self.input_paths:
            messagebox.showwarning("警告", "请至少添加一个输入路径")
            return

        # 收集所有Excel文件
        excel_files = []
        for input_path in self.input_paths:
            # 递归查找所有.xlsx文件
            for root_dir, _, files in os.walk(input_path):
                for file in files:
                    if (file.lower().endswith('.xlsx')
                            and not file.startswith('~') and '_parsed' not in file):  # 排除已解析的文件
                        full_path = os.path.join(root_dir, file)
                        excel_files.append(full_path)

        if not excel_files:
            self.log("在指定路径中未找到任何Excel文件")
            return

        self.log(f"找到 {len(excel_files)} 个Excel文件")

        # 设置进度条
        self.progress['maximum'] = len(excel_files)
        self.progress['value'] = 0

        total_processed = 0
        self.processed_files = []

        for file_index, excel_file in enumerate(excel_files):  # 使用 file_index 代替 i
            try:
                self.log(f"正在处理 ({file_index+1}/{len(excel_files)}): {os.path.basename(excel_file)}")

                # 检查文件是否包含必要的工作表
                try:
                    xl_file = pd.ExcelFile(excel_file)
                    if 'Submit Pattern Lines' not in xl_file.sheet_names:
                        self.log(f"跳过: {os.path.basename(excel_file)} 不包含 'Submit Pattern Lines' 工作表")
                        continue
                except Exception as e:
                    self.log(f"检查文件失败 {os.path.basename(excel_file)}: {str(e)}")
                    continue

                # 创建解析器实例
                parser = ExcelParser()

                # 解析文件
                start_time = datetime.now()

                # 添加更详细的错误处理
                try:
                    log_entries = parser.parse_excel_sheet_log(excel_file, sheet_name='Submit Pattern Lines')
                    self.log(f"成功解析 {len(log_entries)} 条日志条目")
                except Exception as parse_error:
                    self.log(f"解析文件内容失败: {str(parse_error)}")
                    continue

                end_time = datetime.now()
                elapsed = (end_time - start_time).total_seconds()

                # 生成输出文件名（原地存放）
                base_name = os.path.splitext(excel_file)[0]
                output_format = self.output_format.get()

                # 保存结果
                try:
                    if output_format in ["excel", "both"]:
                        output_excel = f"{base_name}_parsed.xlsx"
                        df = pd.DataFrame([entry.log_to_dict() for entry in log_entries])
                        df.to_excel(output_excel, index=False)
                        self.log(f"Excel结果已保存: {os.path.basename(output_excel)}")
                        self.processed_files.append(output_excel)

                    if output_format in ["json", "both"]:
                        output_json = f"{base_name}_parsed.json"
                        with open(output_json, 'w', encoding='utf-8') as f:
                            json.dump([entry.log_to_dict() for entry in log_entries],
                                      f, ensure_ascii=False, indent=2)
                        self.log(f"JSON结果已保存: {os.path.basename(output_json)}")
                        self.processed_files.append(output_json)

                    total_processed += 1
                    self.log(f"文件处理完成，耗时 {elapsed:.2f} 秒")

                except Exception as save_error:
                    self.log(f"保存结果失败: {str(save_error)}")
                    continue

            except Exception as e:
                self.log(f"处理失败 {os.path.basename(excel_file)}: {str(e)}")
                import traceback
                self.log(f"详细错误: {traceback.format_exc()}")
                continue
            finally:
                # 更新进度条
                # 更新进度条
                self.progress['value'] = file_index + 1
                self.root.update_idletasks()

        self.log(f"处理完成！共成功处理 {total_processed} 个Excel文件")
        messagebox.showinfo("完成", f"处理完成！共成功处理 {total_processed} 个文件")

    def export_results(self):
        """导出处理结果汇总"""
        if not self.processed_files:
            messagebox.showwarning("警告", "没有可导出的处理结果")
            return

        # 创建汇总数据
        summary_data = []
        for file_path in self.processed_files:
            file_info = {
                "文件名": os.path.basename(file_path),
                "文件路径": file_path,
                "文件大小": f"{os.path.getsize(file_path)} bytes",
                "修改时间": datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            }
            summary_data.append(file_info)

        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="导出处理结果汇总"
        )

        if file_path:
            try:
                df = pd.DataFrame(summary_data)
                df.to_excel(file_path, index=False)
                self.log(f"处理结果汇总已导出到: {file_path}")
                messagebox.showinfo("成功", f"处理结果汇总已导出到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")


def main():
    """主函数"""
    root = tk.Tk()
    ExcelParserGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
