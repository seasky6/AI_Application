import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from datetime import datetime
import matplotlib
from matplotlib import font_manager
import numpy as np


class DataAnalysisTool:
    def __init__(self, root):
        self.root = root
        self.root.title("数据分析工具")
        self.root.geometry("1000x700")  # 增加窗口大小以容纳更多内容

        self.data = None
        self.product_stats = None
        self.pa_status_stats = None

        # 设置中文字体
        self.setup_chinese_font()

        self.setup_ui()

    def setup_chinese_font(self):
        """设置中文字体支持"""
        try:
            # 尝试设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

            # 检查系统可用的中文字体
            chinese_fonts = []
            for f in font_manager.fontManager.ttflist:
                if any(char in f.name for char in ['黑体', '宋体', '微软', 'Sim', 'MS']):
                    chinese_fonts.append(f.name)

            if chinese_fonts:
                # 优先使用常见的中文字体
                preferred_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi']
                available_fonts = [f for f in preferred_fonts if f in chinese_fonts]
                if available_fonts:
                    plt.rcParams['font.sans-serif'] = available_fonts + ['DejaVu Sans']
                    print(f"使用中文字体: {available_fonts[0]}")

        except Exception as e:
            print(f"字体设置失败: {e}")
            # 如果字体设置失败，使用英文显示
            self.use_english = True
        else:
            self.use_english = False

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择" if not self.use_english else "File Selection",
                                    padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path, width=70).grid(row=0, column=0, padx=5)
        ttk.Button(file_frame, text="选择文件" if not self.use_english else "Select File",
                   command=self.select_file).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="分析数据" if not self.use_english else "Analyze Data",
                   command=self.analyze_data).grid(row=0, column=2, padx=5)

        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="分析结果" if not self.use_english else "Analysis Results",
                                      padding="10")
        result_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 创建文本框显示统计结果
        self.result_text = tk.Text(result_frame, height=15, width=80)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.configure(yscrollcommand=scrollbar.set)

        # 图表显示区域 - 使用Notebook实现标签页
        self.chart_notebook = ttk.Notebook(main_frame)
        self.chart_notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 产品分布图标签页
        self.pie_chart_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(self.pie_chart_frame,
                                text="产品分布图" if not self.use_english else "Product Distribution")

        # PA状态分布图标签页
        self.bar_chart_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(self.bar_chart_frame,
                                text="PA状态分布" if not self.use_english else "PA Status Distribution")

        # 保存按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="生成分析报告" if not self.use_english else "Generate Report",
                   command=self.generate_report).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="保存图表" if not self.use_english else "Save Chart",
                   command=self.save_chart).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="清除结果" if not self.use_english else "Clear Results",
                   command=self.clear_results).grid(row=0, column=2, padx=5)

        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

    def select_file(self):
        file_types = [
            ("Excel files", "*.xlsx"),
            ("CSV files", "*.csv"),
            ("All files", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="选择数据文件" if not self.use_english else "Select Data File",
            filetypes=file_types
        )

        if filename:
            self.file_path.set(filename)
            self.load_data(filename)

    def load_data(self, filename):
        try:
            if filename.endswith('.xlsx'):
                self.data = pd.read_excel(filename)
            elif filename.endswith('.csv'):
                self.data = pd.read_csv(filename)
            else:
                messagebox.showerror("错误" if not self.use_english else "Error",
                                     "不支持的文件格式" if not self.use_english else "Unsupported file format")
                return

            messagebox.showinfo("成功" if not self.use_english else "Success",
                                f"文件加载成功！\n数据形状: {self.data.shape}" if not self.use_english else f"File loaded successfully!\nData shape: {self.data.shape}")

        except Exception as e:
            messagebox.showerror("错误" if not self.use_english else "Error",
                                 f"加载文件时出错: {str(e)}" if not self.use_english else f"Error loading file: {str(e)}")

    def analyze_data(self):
        if self.data is None:
            messagebox.showerror("错误" if not self.use_english else "Error",
                                 "请先选择数据文件" if not self.use_english else "Please select a data file first")
            return

        try:
            # 检查必要的列是否存在
            required_columns = ['Serial', 'ProductName', 'PA Status Repair Info']
            missing_columns = [col for col in required_columns if col not in self.data.columns]
            if missing_columns:
                messagebox.showerror("错误" if not self.use_english else "Error",
                                     f"缺少必要列: {missing_columns}" if not self.use_english else f"Missing required columns: {missing_columns}")
                return

            # 按照Serial统计产品类型，每个Serial只记一次
            unique_products = self.data.drop_duplicates(subset=['Serial'])[['Serial', 'ProductName']]

            # 统计各产品类型的数量
            product_counts = unique_products['ProductName'].value_counts()
            total_products = len(unique_products)

            # 计算百分比
            product_percentages = (product_counts / total_products * 100).round(2)

            # 保存统计结果
            self.product_stats = pd.DataFrame({
                '产品类型' if not self.use_english else 'Product Type': product_counts.index,
                '数量' if not self.use_english else 'Count': product_counts.values,
                '百分比(%)' if not self.use_english else 'Percentage(%)': product_percentages.values
            })

            # 统计PA状态
            self.analyze_pa_status()

            # 显示结果
            self.display_results()

            # 生成图表
            self.generate_charts()

        except Exception as e:
            messagebox.showerror("错误" if not self.use_english else "Error",
                                 f"分析数据时出错: {str(e)}" if not self.use_english else f"Error analyzing data: {str(e)}")

    def analyze_pa_status(self):
        """分析PA状态 - 基于产品维度"""
        # 按照Serial分组，统计每个产品的PA状态
        product_pa_status = []

        # 获取所有唯一的产品序列号
        unique_serials = self.data['Serial'].unique()

        for serial in unique_serials:
            # 获取该序列号的所有记录
            serial_data = self.data[self.data['Serial'] == serial]

            # 获取产品名称（应该相同）
            product_name = serial_data['ProductName'].iloc[0]

            # 统计该产品的PA状态
            pa_status_counts = serial_data['PA Status Repair Info'].value_counts()

            # 计算每个状态的百分比
            total_records = len(serial_data)
            pa_status_percentages = (pa_status_counts / total_records * 100).round(2)

            # 确定主要状态（>50%）
            main_status = None
            for status, percentage in pa_status_percentages.items():
                if percentage > 50:
                    main_status = status
                    break

            # 如果没有状态超过50%，则使用出现次数最多的状态
            if main_status is None and not pa_status_counts.empty:
                main_status = pa_status_counts.index[0]

            # 如果没有任何状态数据，则标记为Unknown
            if main_status is None:
                main_status = "Unknown"

            product_pa_status.append({
                'Serial': serial,
                'ProductName': product_name,
                'MainPAStatus': main_status,
                'TotalRecords': total_records,
                'StatusDetails': pa_status_counts.to_dict()
            })

        # 转换为DataFrame
        product_pa_df = pd.DataFrame(product_pa_status)

        # 按产品类型和主要PA状态进行统计
        pa_status_summary = product_pa_df.groupby(['ProductName', 'MainPAStatus']).size().reset_index(
            name='ProductCount')

        # 计算每个产品类型的总数
        product_totals = product_pa_df.groupby('ProductName').size().reset_index(name='TotalProducts')

        # 合并数据
        pa_status_summary = pd.merge(pa_status_summary, product_totals, on='ProductName')

        # 计算百分比
        pa_status_summary['百分比(%)'] = (
                    pa_status_summary['ProductCount'] / pa_status_summary['TotalProducts'] * 100).round(2)

        # 保存统计结果
        self.pa_status_stats = pa_status_summary
        self.product_pa_details = product_pa_df

    def display_results(self):
        if self.product_stats is None or self.pa_status_stats is None:
            return

        self.result_text.delete(1.0, tk.END)

        # 添加标题
        title = "产品统计报告" if not self.use_english else "Product Statistics Report"
        self.result_text.insert(tk.END, f"{title}\n")
        self.result_text.insert(tk.END, "=" * 50 + "\n\n")

        # 添加总产品数
        total_count = self.product_stats['数量' if not self.use_english else 'Count'].sum()
        total_text = f"总产品数量: {total_count}" if not self.use_english else f"Total Products: {total_count}"
        self.result_text.insert(tk.END, f"{total_text}\n\n")

        # 添加产品类型统计表格头
        col1 = "产品类型" if not self.use_english else "Product Type"
        col2 = "数量" if not self.use_english else "Count"
        col3 = "百分比(%)" if not self.use_english else "Percentage(%)"

        self.result_text.insert(tk.END, f"{col1:<20} {col2:<8} {col3:<10}\n")
        self.result_text.insert(tk.END, "-" * 40 + "\n")

        # 添加每行产品数据
        for _, row in self.product_stats.iterrows():
            product_type = row['产品类型' if not self.use_english else 'Product Type']
            count = row['数量' if not self.use_english else 'Count']
            percentage = row['百分比(%)' if not self.use_english else 'Percentage(%)']
            self.result_text.insert(tk.END, f"{product_type:<20} {count:<8} {percentage:<10}\n")

        # 添加PA状态统计
        self.result_text.insert(tk.END, "\n\nPA状态统计 (基于产品维度):\n")
        self.result_text.insert(tk.END, "=" * 50 + "\n\n")

        # 按产品类型分组显示PA状态
        products = self.pa_status_stats['ProductName'].unique()

        for product in products:
            self.result_text.insert(tk.END, f"{product}:\n")
            product_data = self.pa_status_stats[self.pa_status_stats['ProductName'] == product]

            for _, row in product_data.iterrows():
                status = row['MainPAStatus']
                count = row['ProductCount']
                percentage = row['百分比(%)']
                self.result_text.insert(tk.END, f"  {status}: {count} ({percentage}%)\n")

            self.result_text.insert(tk.END, "\n")

    def generate_charts(self):
        """生成所有图表"""
        self.generate_pie_chart()
        self.generate_bar_chart()

    def generate_pie_chart(self):
        """生成产品分布饼图"""
        if self.product_stats is None:
            return

        # 清除之前的图表
        for widget in self.pie_chart_frame.winfo_children():
            widget.destroy()

        # 创建新图表
        fig, ax = plt.subplots(figsize=(8, 6))

        # 准备数据 - 合并小扇区
        threshold = 2  # 百分比阈值，小于此值的扇区将合并为"其他"

        # 计算每个类别的百分比
        labels = self.product_stats['产品类型' if not self.use_english else 'Product Type'].tolist()
        sizes = self.product_stats['数量' if not self.use_english else 'Count'].tolist()
        percentages = self.product_stats['百分比(%)' if not self.use_english else 'Percentage(%)'].tolist()

        # 合并小扇区
        main_labels = []
        main_sizes = []
        other_size = 0

        for i, (label, size, percentage) in enumerate(zip(labels, sizes, percentages)):
            if percentage >= threshold:
                main_labels.append(label)  # 只显示产品名，不包含百分比
                main_sizes.append(size)
            else:
                other_size += size

        # 如果有小扇区，添加"其他"类别
        if other_size > 0:
            main_labels.append("Other" if not self.use_english else "Other")
            main_sizes.append(other_size)

        # 生成饼图
        colors = plt.cm.Set3(np.linspace(0, 1, len(main_labels)))

        # # 使用explode突出显示小扇区
        # explode = [0.05 if label == "其他" or label == "Other" else 0 for label in main_labels]

        wedges, texts, autotexts = ax.pie(
            main_sizes,
            labels=None,  # 不显示外部标签
            autopct='',
            startangle=90,
            colors=colors,
            # explode=explode,
            shadow=False
        )

        # 设置百分比文本 - 只在扇区足够大时显示百分比
        for i, (wedge, size, label) in enumerate(zip(wedges, main_sizes, main_labels)):
            ang = (wedge.theta2 - wedge.theta1) / 2. + wedge.theta1
            y = np.sin(np.deg2rad(ang))
            x = np.cos(np.deg2rad(ang))

            # 计算当前扇区的百分比
            total = sum(main_sizes)
            percentage = size / total * 100

            # 只在扇区足够大时显示百分比
            if percentage >= 1:  # 只显示大于1%的扇区内部百分比
                # 添加百分比文本
                ax.text(x * 0.7, y * 0.7, f'{percentage:.1f}%',
                        horizontalalignment='center',
                        verticalalignment='center',
                        fontsize=14,
                        fontweight='bold',
                        color='black')

        # 设置标题
        chart_title = 'Radio Type Distribution' if not self.use_english else 'Product Type Distribution'
        ax.set_title(chart_title, fontsize=14, fontweight='bold')

        # 添加图例 - 调整位置到右下方
        # 创建图例标签，包含产品名和百分比
        legend_labels = []
        for i, (label, size) in enumerate(zip(main_labels, main_sizes)):
            total = sum(main_sizes)
            percentage = size / total * 100
            legend_labels.append(f"{label} ({percentage:.1f}%)")

        # 将图例放在右下方，避免覆盖饼图
        ax.legend(wedges, legend_labels,
                  title="Radio Type" if not self.use_english else "Product Types",
                  loc="lower right",  # 定位到右下方
                  bbox_to_anchor=(1.1, 0.1),  # 稍微向右下方偏移
                  fontsize=12)

        # 在Tkinter中显示图表
        canvas = FigureCanvasTkAgg(fig, self.pie_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 保存图表引用
        self.pie_fig = fig
        self.pie_canvas = canvas

    def generate_bar_chart(self):
        """生成PA状态柱状图 - 基于产品维度"""
        if self.pa_status_stats is None:
            return

        # 清除之前的图表
        for widget in self.bar_chart_frame.winfo_children():
            widget.destroy()

        # 创建新图表
        fig, ax = plt.subplots(figsize=(10, 6))

        # 准备数据
        products = self.pa_status_stats['ProductName'].unique()
        statuses = self.pa_status_stats['MainPAStatus'].unique()

        # 设置柱状图位置
        x = np.arange(len(products))
        width = 0.35  # 柱状图宽度

        # 为每个状态创建柱状图
        for i, status in enumerate(statuses):
            status_data = self.pa_status_stats[self.pa_status_stats['MainPAStatus'] == status]
            counts = []

            # 确保每个产品都有对应的计数
            for product in products:
                product_status_data = status_data[status_data['ProductName'] == product]
                if not product_status_data.empty:
                    counts.append(product_status_data.iloc[0]['ProductCount'])
                else:
                    counts.append(0)

            # 绘制柱状图
            offset = width * i - (width * (len(statuses) - 1) / 2)
            bars = ax.bar(x + offset, counts, width, label=status)

            # 在柱子上方显示数值
            for bar in bars:
                height = bar.get_height()
                if height > 0:  # 只在有值的柱子上显示数值
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                            f'{int(height)}', ha='center', va='bottom')

        # 设置图表属性
        ax.set_xlabel('产品类型' if not self.use_english else 'Product Type', fontsize=12)
        ax.set_ylabel('产品数量' if not self.use_english else 'Product Count', fontsize=12)
        ax.set_title('PA状态分布 (基于产品维度)' if not self.use_english else 'PA Status Distribution (Product-based)',
                     fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(products, rotation=45, ha='right')
        ax.legend()

        # 调整布局
        fig.tight_layout()

        # 在Tkinter中显示图表
        canvas = FigureCanvasTkAgg(fig, self.bar_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 保存图表引用
        self.bar_fig = fig
        self.bar_canvas = canvas

    def generate_report(self):
        if self.product_stats is None or self.pa_status_stats is None:
            messagebox.showerror("错误" if not self.use_english else "Error",
                                 "请先分析数据" if not self.use_english else "Please analyze data first")
            return

        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ],
            title="保存分析报告" if not self.use_english else "Save Analysis Report"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                report_title = "产品统计分析报告" if not self.use_english else "Product Statistics Analysis Report"
                f.write(f"{report_title}\n")
                f.write("=" * 50 + "\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")

                # 产品类型统计
                total_count = self.product_stats['数量' if not self.use_english else 'Count'].sum()
                total_text = f"总产品数量: {total_count}" if not self.use_english else f"Total Products: {total_count}"
                f.write(f"{total_text}\n\n")

                col1 = "产品类型" if not self.use_english else "Product Type"
                col2 = "数量" if not self.use_english else "Count"
                col3 = "百分比(%)" if not self.use_english else "Percentage(%)"

                f.write(f"{col1:<20} {col2:<8} {col3:<10}\n")
                f.write("-" * 40 + "\n")

                for _, row in self.product_stats.iterrows():
                    product_type = row['产品类型' if not self.use_english else 'Product Type']
                    count = row['数量' if not self.use_english else 'Count']
                    percentage = row['百分比(%)' if not self.use_english else 'Percentage(%)']
                    f.write(f"{product_type:<20} {count:<8} {percentage:<10}\n")

                # PA状态统计
                f.write("\n\nPA状态统计 (基于产品维度):\n")
                f.write("=" * 50 + "\n\n")

                # 按产品类型分组显示PA状态
                products = self.pa_status_stats['ProductName'].unique()

                for product in products:
                    f.write(f"{product}:\n")
                    product_data = self.pa_status_stats[self.pa_status_stats['ProductName'] == product]

                    for _, row in product_data.iterrows():
                        status = row['MainPAStatus']
                        count = row['ProductCount']
                        percentage = row['百分比(%)']
                        f.write(f"  {status}: {count} ({percentage}%)\n")

                    f.write("\n")

            # 保存图表
            if hasattr(self, 'pie_fig'):
                pie_chart_path = file_path.replace('.txt', '_pie_chart.png')
                self.pie_fig.savefig(pie_chart_path, dpi=300, bbox_inches='tight')

            if hasattr(self, 'bar_fig'):
                bar_chart_path = file_path.replace('.txt', '_bar_chart.png')
                self.bar_fig.savefig(bar_chart_path, dpi=300, bbox_inches='tight')

            success_msg = f"分析报告已保存到:\n{file_path}" if not self.use_english else f"Analysis report saved to:\n{file_path}"
            messagebox.showinfo("成功" if not self.use_english else "Success", success_msg)

        except Exception as e:
            error_msg = f"保存报告时出错: {str(e)}" if not self.use_english else f"Error saving report: {str(e)}"
            messagebox.showerror("错误" if not self.use_english else "Error", error_msg)

    def save_chart(self):
        # 获取当前选中的标签页
        current_tab = self.chart_notebook.index(self.chart_notebook.select())

        if current_tab == 0 and hasattr(self, 'pie_fig'):
            # 保存饼图
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("PDF files", "*.pdf"),
                    ("All files", "*.*")
                ],
                title="保存饼图" if not self.use_english else "Save Pie Chart"
            )

            if file_path:
                try:
                    self.pie_fig.savefig(file_path, dpi=300, bbox_inches='tight')
                    success_msg = f"饼图已保存到:\n{file_path}" if not self.use_english else f"Pie chart saved to:\n{file_path}"
                    messagebox.showinfo("成功" if not self.use_english else "Success", success_msg)
                except Exception as e:
                    error_msg = f"保存饼图时出错: {str(e)}" if not self.use_english else f"Error saving pie chart: {str(e)}"
                    messagebox.showerror("错误" if not self.use_english else "Error", error_msg)

        elif current_tab == 1 and hasattr(self, 'bar_fig'):
            # 保存柱状图
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("PDF files", "*.pdf"),
                    ("All files", "*.*")
                ],
                title="保存柱状图" if not self.use_english else "Save Bar Chart"
            )

            if file_path:
                try:
                    self.bar_fig.savefig(file_path, dpi=300, bbox_inches='tight')
                    success_msg = f"柱状图已保存到:\n{file_path}" if not self.use_english else f"Bar chart saved到:\n{file_path}"
                    messagebox.showinfo("成功" if not self.use_english else "Success", success_msg)
                except Exception as e:
                    error_msg = f"保存柱状图时出错: {str(e)}" if not self.use_english else f"Error saving bar chart: {str(e)}"
                    messagebox.showerror("错误" if not self.use_english else "Error", error_msg)
        else:
            messagebox.showerror("错误" if not self.use_english else "Error",
                                 "没有可用的图表" if not self.use_english else "No chart available")

    def clear_results(self):
        self.result_text.delete(1.0, tk.END)
        self.data = None
        self.product_stats = None
        self.pa_status_stats = None

        # 清除图表
        for widget in self.pie_chart_frame.winfo_children():
            widget.destroy()

        for widget in self.bar_chart_frame.winfo_children():
            widget.destroy()


def main():
    root = tk.Tk()
    app = DataAnalysisTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
