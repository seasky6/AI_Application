import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import numpy as np
import threading
import os
import sys
from datetime import datetime
from tools.app.services.model_training.preprocessor.data_preprocessor import TrainingDataProcessor


# ======================================================================================================================
# Training主窗口和标签页管理
# ======================================================================================================================
class TrainingGUI:
    """模型训练GUI - 使用独立的标签页类"""
    def __init__(self, parent, tab_style="TNotebook.Tab"):
        """
        初始化训练GUI

        Args:
            parent: 父容器，可以是Frame或其他tkinter容器
        """
        self.parent = parent
        self.processor = TrainingDataProcessor()

        # 设置深色主题
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#007acc"
        self.frame_bg = "#2d2d2d"
        self.entry_bg = "#3d3d3d"

        # 存储模型参数
        self.model_parameters = self.get_default_parameters()

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
        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", background=self.frame_bg, foreground="#000000")
        style.map("TNotebook.Tab", background=[("selected", self.accent_color)])
        style.configure("TProgressbar", background=self.accent_color, troughcolor=self.frame_bg)

    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # 创建Notebook（标签页）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 创建数据预处理标签页
        self.data_preprocessing_tab = DataPreprocessingTab(self.notebook, self)
        self.notebook.add(self.data_preprocessing_tab.frame, text="训练数据预处理")

        # 创建模型训练标签页
        self.model_training_tab = ModelTrainingTab(self.notebook, self)
        self.notebook.add(self.model_training_tab.frame, text="模型训练")

        # 状态信息
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

    @staticmethod
    def get_default_parameters():
        """获取各模型的默认参数"""
        return {
            "CatBoost": {
                "iterations": {"value": 1000, "type": "int", "range": (100, 5000), "description": "树的数量"},
                "learning_rate": {"value": 0.03, "type": "float", "range": (0.001, 1.0), "description": "学习率"},
                "depth": {"value": 6, "type": "int", "range": (1, 16), "description": "树的最大深度"},
                "l2_leaf_reg": {"value": 3, "type": "float", "range": (0, 10), "description": "L2正则化系数"},
                "random_strength": {"value": 1, "type": "float", "range": (0, 10), "description": "分裂分数随机性"},
                "bagging_temperature": {"value": 0.5, "type": "float", "range": (0, 1),
                                        "description": "贝叶斯自举温度"},
                "leaf_estimation_iterations": {"value": 1, "type": "int", "range": (1, 10),
                                               "description": "叶子值估计迭代次数"},
                "rsm": {"value": 1, "type": "float", "range": (0.1, 1.0), "description": "特征采样比例"}
            },
            "LightGBM": {
                "num_leaves": {"value": 31, "type": "int", "range": (2, 256), "description": "叶子数量"},
                "learning_rate": {"value": 0.1, "type": "float", "range": (0.01, 1.0), "description": "学习率"},
                "n_estimators": {"value": 100, "type": "int", "range": (10, 1000), "description": "树的数量"},
                "max_depth": {"value": -1, "type": "int", "range": (-1, 20),
                              "description": "树的最大深度(-1表示无限制)"},
                "subsample": {"value": 1.0, "type": "float", "range": (0.1, 1.0), "description": "样本采样比例"},
                "colsample_bytree": {"value": 1.0, "type": "float", "range": (0.1, 1.0), "description": "特征采样比例"},
                "reg_alpha": {"value": 0, "type": "float", "range": (0, 10), "description": "L1正则化系数"},
                "reg_lambda": {"value": 0, "type": "float", "range": (0, 10), "description": "L2正则化系数"}
            },
            "XGBoost": {
                "max_depth": {"value": 6, "type": "int", "range": (1, 20), "description": "树的最大深度"},
                "learning_rate": {"value": 0.1, "type": "float", "range": (0.01, 1.0), "description": "学习率"},
                "n_estimators": {"value": 100, "type": "int", "range": (10, 1000), "description": "树的数量"},
                "subsample": {"value": 0.8, "type": "float", "range": (0.1, 1.0), "description": "样本采样比例"},
                "colsample_bytree": {"value": 0.8, "type": "float", "range": (0.1, 1.0), "description": "特征采样比例"},
                "reg_alpha": {"value": 0, "type": "float", "range": (0, 10), "description": "L1正则化系数"},
                "reg_lambda": {"value": 1, "type": "float", "range": (0, 10), "description": "L2正则化系数"},
                "gamma": {"value": 0, "type": "float", "range": (0, 10), "description": "节点分裂所需最小损失减少"},
                "min_child_weight": {"value": 1, "type": "int", "range": (1, 20),
                                     "description": "最小叶子节点样本权重和"}
            },
            "TabNet": {
                "n_d": {"value": 8, "type": "int", "range": (1, 64), "description": "决策层宽度"},
                "n_a": {"value": 8, "type": "int", "range": (1, 64), "description": "注意力层宽度"},
                "n_steps": {"value": 3, "type": "int", "range": (1, 10), "description": "决策步骤数"},
                "gamma": {"value": 1.3, "type": "float", "range": (1.0, 2.0), "description": "缩放系数"},
                "lambda_sparse": {"value": 1e-3, "type": "float", "range": (1e-5, 1e-1),
                                  "description": "稀疏性损失权重"},
                "learning_rate": {"value": 0.02, "type": "float", "range": (0.001, 0.1), "description": "学习率"},
                "max_epochs": {"value": 100, "type": "int", "range": (10, 500), "description": "最大训练轮数"}
            }
        }

    def update_status(self, message):
        """更新状态信息"""
        self.status_var.set(message)

    def log_message(self, message):
        """在日志区域添加消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        if hasattr(self, 'model_training_tab') and hasattr(self.model_training_tab, 'log_text'):
            self.model_training_tab.log_text.insert(tk.END, formatted_message)
            self.model_training_tab.log_text.see(tk.END)
            self.model_training_tab.log_text.update()

    def get_processor(self):
        """获取数据处理器"""
        return self.processor

    def get_model_parameters(self):
        """获取模型参数"""
        return self.model_parameters

    def set_model_parameters(self, model_name, parameters):
        """设置模型参数"""
        self.model_parameters[model_name] = parameters


# ======================================================================================================================
# 数据预处理标签页
# ======================================================================================================================
class DataPreprocessingTab:
    """数据预处理标签页"""

    def __init__(self, parent, training_gui):
        """
        初始化数据预处理标签页

        Args:
            parent: 父容器
            training_gui: 主训练GUI引用
        """
        self.parent = parent
        self.training_gui = training_gui
        self.frame = ttk.Frame(parent)

        # 初始化变量
        self.input_files_var = tk.StringVar(value="未选择文件")
        self.output_dir_var = tk.StringVar(value="未选择目录")
        self.input_files = None
        self.output_dir = None

        # UI组件
        self.sample_listbox = None
        self.input_feature_listbox = None
        self.output_feature_listbox = None

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        # 配置数据预处理框架的网格权重
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=1)

        # 选择数据区域
        file_frame = ttk.LabelFrame(self.frame, text="1. 选择数据", padding="10", style="White.TLabelframe")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        ttk.Button(file_frame, text="选择数据文件",
                   command=self.select_input_files).grid(row=0, column=0, padx=(0, 10))
        ttk.Label(file_frame, textvariable=self.input_files_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Button(file_frame, text="选择输出目录",
                   command=self.select_output_dir).grid(row=1, column=0, padx=(0, 10), pady=(10, 0))
        ttk.Label(file_frame, textvariable=self.output_dir_var).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0))

        # 数据处理按钮
        ttk.Button(file_frame, text="加载数据",
                   command=self.load_and_process_data).grid(row=2, column=0, columnspan=2, pady=(10, 0))

        # 选择样本和特征区域
        selection_frame = ttk.LabelFrame(self.frame, text="2. 样本和特征选择", padding="10", style="White.TLabelframe")
        selection_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.columnconfigure(1, weight=1)
        selection_frame.rowconfigure(0, weight=1)

        # 样本选择
        sample_frame = ttk.Frame(selection_frame)
        sample_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        ttk.Label(sample_frame, text="样本选择:").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(sample_frame, text="全选", command=self.select_all_samples).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(sample_frame, text="全不选", command=self.clear_all_samples).grid(row=0, column=2, padx=(5, 5))
        ttk.Button(sample_frame, text="高级选项", command=self.advanced_sample_selection).grid(row=0, column=3,
                                                                                               padx=(5, 0))

        self.sample_listbox = tk.Listbox(sample_frame, selectmode=tk.MULTIPLE, height=15, exportselection=False,
                                         width=120)
        self.sample_listbox.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        self.sample_listbox.bind('<<ListboxSelect>>', self.on_sample_select)

        sample_scrollbar = ttk.Scrollbar(sample_frame, orient=tk.VERTICAL, command=self.sample_listbox.yview)
        sample_scrollbar.grid(row=1, column=4, sticky=(tk.N, tk.S), pady=(5, 0))
        self.sample_listbox.configure(yscrollcommand=sample_scrollbar.set)

        # 添加水平滚动条以适应更长的文本
        sample_hscrollbar = ttk.Scrollbar(sample_frame, orient=tk.HORIZONTAL, command=self.sample_listbox.xview)
        sample_hscrollbar.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E))
        self.sample_listbox.configure(xscrollcommand=sample_hscrollbar.set)

        sample_frame.rowconfigure(1, weight=1)
        sample_frame.columnconfigure(0, weight=1)

        # 特征选择
        feature_frame = ttk.Frame(selection_frame)
        feature_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        feature_frame.columnconfigure(0, weight=1)
        feature_frame.columnconfigure(1, weight=1)

        # 输入特征
        input_feature_frame = ttk.Frame(feature_frame)
        input_feature_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        input_feature_header = ttk.Frame(input_feature_frame)
        input_feature_header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(input_feature_header, text="输入特征 (X):").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(input_feature_header, text="全选",
                   command=lambda: self.select_all_features('input')).grid(row=0, column=1, padx=(10, 5))
        ttk.Button(input_feature_header, text="全不选",
                   command=lambda: self.clear_all_features('input')).grid(row=0, column=2, padx=(5, 0))

        self.input_feature_listbox = tk.Listbox(input_feature_frame, selectmode=tk.MULTIPLE, height=15,
                                                exportselection=False)
        self.input_feature_listbox.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        self.input_feature_listbox.bind('<<ListboxSelect>>', self.on_input_feature_select)

        input_feature_scrollbar = ttk.Scrollbar(input_feature_frame, orient=tk.VERTICAL,
                                                command=self.input_feature_listbox.yview)
        input_feature_scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S), pady=(5, 0))
        self.input_feature_listbox.configure(yscrollcommand=input_feature_scrollbar.set)

        input_feature_frame.rowconfigure(1, weight=1)
        input_feature_frame.columnconfigure(0, weight=1)

        # 输出特征
        output_feature_frame = ttk.Frame(feature_frame)
        output_feature_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        output_feature_header = ttk.Frame(output_feature_frame)
        output_feature_header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(output_feature_header, text="输出特征 (Y):").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(output_feature_header, text="全选",
                   command=lambda: self.select_all_features('output')).grid(row=0, column=1, padx=(10, 5))
        ttk.Button(output_feature_header, text="全不选",
                   command=lambda: self.clear_all_features('output')).grid(row=0, column=2, padx=(5, 0))

        self.output_feature_listbox = tk.Listbox(output_feature_frame, selectmode=tk.MULTIPLE, height=15,
                                                 exportselection=False)
        self.output_feature_listbox.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        self.output_feature_listbox.bind('<<ListboxSelect>>', self.on_output_feature_select)

        output_feature_scrollbar = ttk.Scrollbar(output_feature_frame, orient=tk.VERTICAL,
                                                 command=self.output_feature_listbox.yview)
        output_feature_scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S), pady=(5, 0))
        self.output_feature_listbox.configure(yscrollcommand=output_feature_scrollbar.set)

        output_feature_frame.rowconfigure(1, weight=1)
        output_feature_frame.columnconfigure(0, weight=1)

        # 导出和生成按钮
        button_frame = ttk.Frame(selection_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame, text="导出样本列表", command=self.export_sample_list).grid(row=0, column=0,
                                                                                            padx=(0, 10))
        ttk.Button(button_frame, text="生成训练数据集", command=self.generate_training_data).grid(row=0, column=1)

    # 数据预处理相关方法
    def on_sample_select(self, event):
        """处理样本选择事件"""
        selected_indices = self.sample_listbox.curselection()
        processor = self.training_gui.get_processor()
        processor.selected_samples = set(selected_indices)

    def on_input_feature_select(self, event):
        """处理输入特征选择事件"""
        selected_indices = self.input_feature_listbox.curselection()
        selected_features = [self.input_feature_listbox.get(i) for i in selected_indices]
        processor = self.training_gui.get_processor()
        processor.selected_input_features = set(selected_features)

    def on_output_feature_select(self, event):
        """处理输出特征选择事件"""
        selected_indices = self.output_feature_listbox.curselection()
        selected_features = [self.output_feature_listbox.get(i) for i in selected_indices]
        processor = self.training_gui.get_processor()
        processor.selected_output_features = set(selected_features)

    def select_input_files(self):
        """选择输入文件"""
        files = filedialog.askopenfilenames(
            title="选择JSON数据文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if files:
            self.input_files_var.set(f"; ".join([os.path.basename(f) for f in files]))
            self.input_files = files

    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(directory)
            self.output_dir = directory

    def load_and_process_data(self):
        """加载并处理数据"""
        if not hasattr(self, 'input_files') or not self.input_files:
            messagebox.showerror("错误", "请先选择输入文件")
            return

        self.training_gui.update_status("正在加载数据...")

        # 在新线程中处理数据
        def process_data():
            try:
                processor = self.training_gui.get_processor()

                # 加载原始数据
                processor.raw_data = processor.load_data(self.input_files)

                # 提取特征
                processor.processed_samples = processor.extract_all_features(processor.raw_data)

                # 更新UI
                self.frame.after(0, self.update_sample_feature_lists)
                self.frame.after(0, lambda: self.training_gui.update_status(
                    f"加载完成: {len(processor.processed_samples)} 个样本"))

            except Exception as e:
                self.frame.after(0, lambda: messagebox.showerror("错误", f"处理数据时出错: {str(e)}"))
                self.frame.after(0, lambda: self.training_gui.update_status("处理失败"))

        threading.Thread(target=process_data, daemon=True).start()

    def update_sample_feature_lists(self):
        """更新样本和特征列表"""
        processor = self.training_gui.get_processor()

        # 更新样本列表
        self.sample_listbox.delete(0, tk.END)
        for idx, row in processor.processed_samples.iterrows():
            serial = row.get('Serial', f'sample_{idx}')
            product_name = row.get('ProductName', 'Unknown')
            timestamp = row.get('Timestamp', 'Unknown')

            # 获取 PA Status Repair Info，如果不存在则显示 Unknown
            repair_info = row.get('PA Status Repair Info', 'Unknown')
            if repair_info in [None, '', np.nan]:
                repair_info = 'Unknown'

            # 格式化显示：序号: 串号 | 型号 | 时间戳 | PA Status Repair Info
            display_text = f"{idx}: {serial}    |    {product_name}    |    {timestamp}    |    {repair_info}"
            self.sample_listbox.insert(tk.END, display_text)

        # 全选样本
        self.select_all_samples()

        # 更新输入特征列表
        self.input_feature_listbox.delete(0, tk.END)
        input_features = processor.numeric_features + processor.categorical_features
        for feat in input_features:
            self.input_feature_listbox.insert(tk.END, feat)

        # 更新输出特征列表
        self.output_feature_listbox.delete(0, tk.END)
        for feat in processor.output_features:
            self.output_feature_listbox.insert(tk.END, feat)

        # 全选特征
        self.select_all_features('input')
        self.select_all_features('output')

    def select_all_samples(self):
        """选择所有样本"""
        self.sample_listbox.select_set(0, tk.END)
        processor = self.training_gui.get_processor()
        processor.selected_samples = set(range(self.sample_listbox.size()))

    def clear_all_samples(self):
        """清除所有样本选择"""
        self.sample_listbox.select_clear(0, tk.END)
        processor = self.training_gui.get_processor()
        processor.selected_samples.clear()

    def advanced_sample_selection(self):
        """高级样本选择功能"""
        processor = self.training_gui.get_processor()
        if processor.processed_samples is None:
            messagebox.showwarning("警告", "请先加载数据")
            return

        # 创建高级选择窗口
        selection_window = tk.Toplevel(self.frame)
        selection_window.title("高级样本选择")
        selection_window.geometry("800x600")
        selection_window.transient(self.frame)
        selection_window.grab_set()

        # 主框架
        main_frame = ttk.Frame(selection_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 搜索框
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind('<KeyRelease>', lambda e: self.filter_samples(selection_listbox, search_var.get()))

        # 样本列表框架
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 创建列表框和滚动条
        selection_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=20)
        selection_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=selection_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        selection_listbox.configure(yscrollcommand=scrollbar.set)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="全选",
                   command=lambda: self.select_all_in_advanced(selection_listbox)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="全不选",
                   command=lambda: selection_listbox.select_clear(0, tk.END)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="确定",
                   command=lambda: self.apply_advanced_selection(selection_window, selection_listbox)).pack(
            side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消",
                   command=selection_window.destroy).pack(side=tk.RIGHT, padx=(0, 5))

        # 存储串号到样本索引的映射
        self.serial_to_indices = {}

        # 填充样本列表（按产品型号排序）
        self.populate_advanced_selection(selection_listbox)

    def populate_advanced_selection(self, listbox):
        """填充高级选择列表"""
        processor = self.training_gui.get_processor()
        listbox.delete(0, tk.END)

        # 按产品型号分组样本
        product_groups = {}
        for idx, row in processor.processed_samples.iterrows():
            product_name = row.get('ProductName', 'Unknown')
            serial = row.get('Serial', f'sample_{idx}')
            repair_info = row.get('PA Status Repair Info', 'Unknown')

            # 存储串号到样本索引的映射
            if serial not in self.serial_to_indices:
                self.serial_to_indices[serial] = []
            self.serial_to_indices[serial].append(idx)

            if product_name not in product_groups:
                product_groups[product_name] = {}

            # 每个串号只存储一次（使用第一个样本的信息）
            if serial not in product_groups[product_name]:
                product_groups[product_name][serial] = {
                    'repair_info': repair_info,
                    'count': 0
                }

            # 计数该串号的样本数量
            product_groups[product_name][serial]['count'] += 1

        # 按产品型号排序
        sorted_products = sorted(product_groups.keys())

        # 填充列表
        for product in sorted_products:
            # 添加产品型号作为分组标题（不可选择）
            listbox.insert(tk.END, f"--- {product} ---")
            listbox.itemconfig(tk.END, {'fg': 'gray', 'selectbackground': 'white'})

            # 添加该产品下的所有串号（每个串号只显示一次）
            for serial, info in product_groups[product].items():
                display_text = f"    {serial} | {info['repair_info']} | ({info['count']} 个样本)"
                listbox.insert(tk.END, display_text)
                # 存储原始索引到列表项
                listbox.itemconfig(tk.END, {'bg': 'white'})

    def filter_samples(self, listbox, search_text):
        """根据搜索文本过滤样本"""
        # 先重新填充完整列表
        self.populate_advanced_selection(listbox)

        if not search_text.strip():
            return

        # 过滤显示的项目
        search_lower = search_text.lower()
        items_to_keep = []

        for i in range(listbox.size()):
            item_text = listbox.get(i)
            # 跳过分组标题
            if item_text.startswith("---"):
                continue

            if search_lower in item_text.lower():
                items_to_keep.append(i)

        # 隐藏不匹配的项目
        for i in range(listbox.size()):
            if i not in items_to_keep and not listbox.get(i).startswith("---"):
                listbox.itemconfig(i, {'fg': 'lightgray'})

    @staticmethod
    def select_all_in_advanced(listbox):
        """在高级选择窗口中选择所有样本"""
        for i in range(listbox.size()):
            # 跳过分组标题
            if not listbox.get(i).startswith("---"):
                listbox.selection_set(i)

    def apply_advanced_selection(self, window, listbox):
        """应用高级选择到主窗口"""
        # 获取选中的项目
        selected_indices = listbox.curselection()

        if not selected_indices:
            messagebox.showwarning("警告", "请至少选择一个样本")
            return

        # 收集所有选中的串号
        selected_serials = set()
        for i in selected_indices:
            item_text = listbox.get(i)
            # 跳过分组标题
            if item_text.startswith("---"):
                continue

            # 提取串号（格式："    {serial} | {repair_info} | ({count} 个样本)"）
            serial = item_text.split(' | ')[0].strip()
            selected_serials.add(serial)

        # 在主窗口中选择所有匹配的样本
        main_selected_indices = []
        for serial in selected_serials:
            if serial in self.serial_to_indices:
                main_selected_indices.extend(self.serial_to_indices[serial])

        # 更新主窗口的样本选择
        self.sample_listbox.select_clear(0, tk.END)
        for idx in main_selected_indices:
            self.sample_listbox.selection_set(idx)

        # 更新处理器的选择
        processor = self.training_gui.get_processor()
        processor.selected_samples = set(main_selected_indices)

        # 关闭窗口
        window.destroy()

        # 显示选择结果
        messagebox.showinfo("成功", f"已选择 {len(main_selected_indices)} 个样本")

    def select_all_features(self, feature_type):
        """选择所有特征"""
        processor = self.training_gui.get_processor()

        if feature_type == 'input':
            listbox = self.input_feature_listbox
            feature_set = processor.selected_input_features
            features = processor.numeric_features + processor.categorical_features
        else:
            listbox = self.output_feature_listbox
            feature_set = processor.selected_output_features
            features = processor.output_features

        listbox.select_set(0, tk.END)
        feature_set.update(features)

    def clear_all_features(self, feature_type):
        """清除所有特征选择"""
        processor = self.training_gui.get_processor()

        if feature_type == 'input':
            listbox = self.input_feature_listbox
            feature_set = processor.selected_input_features
        else:
            listbox = self.output_feature_listbox
            feature_set = processor.selected_output_features

        listbox.select_clear(0, tk.END)
        feature_set.clear()

    def export_sample_list(self):
        """导出样本列表"""
        processor = self.training_gui.get_processor()

        if processor.processed_samples is None:
            messagebox.showerror("错误", "没有可导出的数据")
            return

        # 检查选择
        if not processor.selected_samples:
            messagebox.showerror("错误", "请至少选择一个样本")
            return
        if not processor.selected_input_features and not processor.selected_output_features:
            messagebox.showerror("错误", "请至少选择一个输入特征或输出特征")
            return

        file_path = filedialog.asksaveasfilename(
            title="导出样本列表",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if file_path:
            try:
                # 获取用户选择的样本和特征
                selected_indices = list(processor.selected_samples)
                selected_input_features = list(processor.selected_input_features)
                selected_output_features = list(processor.selected_output_features)

                # 基础信息列（总是包含）
                base_columns = ['ProductName', 'Serial', 'Timestamp']

                # 所有要导出的列
                all_columns = base_columns + selected_input_features + selected_output_features

                # 过滤数据：只包含选中的样本和列
                filtered_data = processor.processed_samples.loc[selected_indices, all_columns].copy()

                # 添加样本索引列作为第一列
                filtered_data.insert(0, 'SampleIndex', filtered_data.index)

                # 处理特殊值：将 -inf 替换为 -1000，inf 替换为 1000
                # 识别数值型列
                numeric_columns = [col for col in filtered_data.columns
                                   if col in processor.numeric_features]

                # 对于数值型列，将特殊值转换为适当的数值
                for col in numeric_columns:
                    if col in filtered_data.columns:
                        # 创建一个掩码来识别特殊值
                        inf_mask = filtered_data[col] == np.inf
                        neg_inf_mask = filtered_data[col] == -np.inf
                        nan_mask = filtered_data[col].isna()

                        # 复制列以避免SettingWithCopyWarning
                        col_data = filtered_data[col].copy()

                        # 替换特殊值
                        col_data[inf_mask] = 1000
                        col_data[neg_inf_mask] = -1000
                        # 空值替换为 NaN（保持数值类型）
                        col_data[nan_mask] = np.nan

                        filtered_data[col] = col_data

                # 导出数据 - 使用 na_rep 参数指定 NaN 值的表示方式
                filtered_data.to_csv(file_path, index=False, encoding='utf-8-sig', na_rep='')

                # 显示导出统计信息
                sample_count = len(filtered_data)
                input_feature_count = len(selected_input_features)
                output_feature_count = len(selected_output_features)

                messagebox.showinfo("成功",
                                    f"样本列表已导出到: {file_path}\n\n"
                                    f"导出统计:\n"
                                    f"- 样本数量: {sample_count}\n"
                                    f"- 输入特征: {input_feature_count}\n"
                                    f"- 输出特征: {output_feature_count}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

    def generate_training_data(self):
        """生成训练数据集"""
        if not hasattr(self, 'output_dir') or not self.output_dir:
            messagebox.showerror("错误", "请先选择输出目录")
            return

        processor = self.training_gui.get_processor()

        # 验证选择
        if not processor.selected_samples:
            messagebox.showerror("错误", "请至少选择一个样本")
            return
        if not processor.selected_input_features:
            messagebox.showerror("错误", "请至少选择一个输入特征")
            return
        if not processor.selected_output_features:
            messagebox.showerror("错误", "请至少选择一个输出特征")
            return

        self.training_gui.update_status("正在生成训练数据集...")

        def generate_data():
            success, message = processor.process_selected_data(self.output_dir)
            self.frame.after(0, lambda: self.training_gui.update_status("生成完成" if success else "生成失败"))
            if success:
                self.frame.after(0, lambda: messagebox.showinfo("成功", message))
            else:
                self.frame.after(0, lambda: messagebox.showerror("错误", message))

        threading.Thread(target=generate_data, daemon=True).start()


# ======================================================================================================================
# 模型训练标签页
# ======================================================================================================================
class ModelTrainingTab:
    """模型训练标签页"""

    def __init__(self, parent, training_gui):
        """
        初始化模型训练标签页

        Args:
            parent: 父容器
            training_gui: 主训练GUI引用
        """
        self.parent = parent
        self.training_gui = training_gui
        self.frame = ttk.Frame(parent)

        # 初始化变量
        self.training_dataset_path = None
        self.model_save_path = None
        self.training_dataset_var = tk.StringVar(value="未选择数据")
        self.model_save_path_var = tk.StringVar(value="未选择路径")
        self.model_var = tk.StringVar(value="XGBoost")
        self.progress_var = tk.DoubleVar()

        # UI组件
        self.progress_bar = None
        self.log_text = None

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        # 配置模型训练框架的网格权重
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(3, weight=1)

        # 数据集选择区域
        dataset_frame = ttk.LabelFrame(self.frame, text="1. 训练数据集选择", padding="10", style="White.TLabelframe")
        dataset_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        dataset_frame.columnconfigure(1, weight=1)

        ttk.Button(dataset_frame, text="选择训练数据",
                   command=self.select_training_dataset).grid(row=0, column=0, padx=(0, 10))
        ttk.Label(dataset_frame, textvariable=self.training_dataset_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

        # 模型保存路径
        model_save_frame = ttk.LabelFrame(self.frame, text="2. 模型保存路径", padding="10", style="White.TLabelframe")
        model_save_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        model_save_frame.columnconfigure(1, weight=1)

        ttk.Button(model_save_frame, text="选择模型保存路径",
                   command=self.select_model_save_path).grid(row=0, column=0, padx=(0, 10))
        ttk.Label(model_save_frame, textvariable=self.model_save_path_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

        # 模型选择区域
        model_selection_frame = ttk.LabelFrame(self.frame, text="3. 模型选择", padding="10", style="White.TLabelframe")
        model_selection_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        models = ["CatBoost", "LightGBM", "XGBoost", "TabNet"]

        for i, model in enumerate(models):
            ttk.Radiobutton(model_selection_frame, text=model, variable=self.model_var,
                            value=model).grid(row=0, column=i, padx=(10, 10), pady=5)

        # 模型参数设置按钮
        ttk.Button(model_selection_frame, text="设置模型参数",
                   command=self.open_parameter_settings).grid(row=0, column=len(models), padx=(10, 0))

        # 训练按钮和进度显示
        training_control_frame = ttk.Frame(self.frame)
        training_control_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        ttk.Button(training_control_frame, text="开始训练",
                   command=self.start_training).grid(row=0, column=0, padx=(0, 10))

        # 进度条
        self.progress_bar = ttk.Progressbar(training_control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        training_control_frame.columnconfigure(1, weight=1)

        # 打开报告文件夹
        ttk.Button(training_control_frame, text="打开报告文件夹",
                   command=self.open_visualization_dir).grid(row=0, column=3, padx=(10, 0))

        # 训练日志
        log_frame = ttk.LabelFrame(self.frame, text="训练日志", padding="10", style="White.TLabelframe")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=25)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # 模型训练相关方法
    def select_training_dataset(self):
        """选择训练数据集"""
        dataset_path = filedialog.askdirectory(title="选择训练数据集目录")
        if dataset_path:
            self.training_dataset_var.set(dataset_path)
            self.training_dataset_path = dataset_path
            self.training_gui.log_message(f"已选择训练数据集: {dataset_path}")

    def select_model_save_path(self):
        """选择模型保存路径"""
        save_path = filedialog.askdirectory(title="选择模型保存路径")
        if save_path:
            self.model_save_path_var.set(save_path)
            self.model_save_path = save_path
            self.training_gui.log_message(f"模型将保存到: {save_path}")

    def open_parameter_settings(self):
        """打开参数设置窗口"""
        selected_model = self.model_var.get()

        # 创建参数设置窗口
        param_window = tk.Toplevel(self.frame)
        param_window.title(f"{selected_model} 参数设置")
        param_window.geometry("700x700")
        param_window.transient(self.frame)
        param_window.grab_set()

        # 主框架
        main_frame = ttk.Frame(param_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text=f"{selected_model} 模型参数设置",
                                font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))

        # 说明文本
        description_text = (
            "调整以下参数以优化模型性能\n"
            "建议值基于理论和实践经验，但最佳参数可能因数据而异\n"
            "调整后可以训练多个模型进行比较"
        )
        description_label = ttk.Label(main_frame, text=description_text,
                                      wraplength=550, justify=tk.LEFT)
        description_label.pack(pady=(0, 10))

        # 创建滚动框架
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 获取当前模型的参数
        model_params = self.training_gui.get_model_parameters().get(selected_model, {})

        # 存储输入框的变量
        param_vars = {}

        # 创建参数输入控件
        for i, (param_name, param_config) in enumerate(model_params.items()):
            param_frame = ttk.Frame(scrollable_frame)
            param_frame.pack(fill=tk.X, pady=5)

            # 参数名称和描述
            param_label = ttk.Label(param_frame, text=f"{param_name}:", width=20)
            param_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

            desc_label = ttk.Label(param_frame, text=param_config["description"],
                                   foreground="gray", wraplength=300)
            desc_label.grid(row=0, column=1, sticky=tk.W)

            # 根据参数类型创建不同的输入控件
            if param_config["type"] in ["int", "float"]:
                # 数值输入框
                var = tk.StringVar(value=str(param_config["value"]))
                entry = ttk.Entry(param_frame, textvariable=var, foreground="#000000")
                entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

                # 范围标签
                min_val, max_val = param_config["range"]
                range_label = ttk.Label(param_frame, text=f"范围: {min_val} - {max_val}",
                                        foreground="white")
                range_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))

            param_vars[param_name] = var

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # 重置按钮
        ttk.Button(button_frame, text="默认值",
                   command=lambda: self.reset_parameters(param_vars, selected_model)).pack(side=tk.LEFT)

        # 确定和取消按钮
        ttk.Button(button_frame, text="取消", width=10,
                   command=param_window.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="确定", width=10,
                   command=lambda: self.save_parameters(param_vars, selected_model, param_window)).pack(side=tk.RIGHT)

        # 配置网格权重
        scrollable_frame.columnconfigure(1, weight=1)

    def reset_parameters(self, param_vars, model_name):
        """重置参数为默认值"""
        model_params = self.training_gui.get_model_parameters().get(model_name, {})
        for param_name, param_config in model_params.items():
            if param_name in param_vars:
                param_vars[param_name].set(str(param_config["value"]))

    def save_parameters(self, param_vars, model_name, window):
        """保存参数设置"""
        try:
            model_params = self.training_gui.get_model_parameters().get(model_name, {})
            updated_params = {}

            for param_name, var in param_vars.items():
                param_config = model_params[param_name]
                value = var.get()

                # 验证和转换参数值
                if param_config["type"] == "int":
                    try:
                        value = int(value)
                        min_val, max_val = param_config["range"]
                        if not (min_val <= value <= max_val):
                            raise ValueError(f"值必须在 {min_val} 和 {max_val} 之间")
                    except ValueError as e:
                        messagebox.showerror("参数错误", f"参数 '{param_name}' 输入错误: {str(e)}")
                        return

                elif param_config["type"] == "float":
                    try:
                        value = float(value)
                        min_val, max_val = param_config["range"]
                        if not (min_val <= value <= max_val):
                            raise ValueError(f"值必须在 {min_val} 和 {max_val} 之间")
                    except ValueError as e:
                        messagebox.showerror("参数错误", f"参数 '{param_name}' 输入错误: {str(e)}")
                        return

                updated_params[param_name] = value

            # 更新模型参数
            for param_name, value in updated_params.items():
                self.training_gui.get_model_parameters()[model_name][param_name]["value"] = value

            self.training_gui.log_message(f"{model_name} 参数已更新")

            # 显示参数摘要
            param_summary = f"{model_name} 参数设置:\n"
            for param_name, value in updated_params.items():
                param_summary += f"  {param_name}: {value}\n"
            self.training_gui.log_message(param_summary)

            window.destroy()

        except Exception as e:
            messagebox.showerror("错误", f"保存参数时出错: {str(e)}")

    def start_training(self):
        """开始模型训练"""
        # 验证输入
        if not hasattr(self, 'training_dataset_path') or not self.training_dataset_path:
            messagebox.showerror("错误", "请选择训练数据集")
            return

        if not hasattr(self, 'model_save_path') or not self.model_save_path:
            messagebox.showerror("错误", "请选择模型保存路径")
            return

        selected_model = self.model_var.get()
        self.training_gui.log_message(f"开始训练 {selected_model} 模型...")
        self.training_gui.update_status(f"正在训练 {selected_model} 模型...")

        # 在新线程中运行训练
        def run_training():
            try:
                # 根据选择的模型调用相应的训练模块
                if selected_model == "CatBoost":
                    success, message = self.train_catboost()
                elif selected_model == "LightGBM":
                    success, message = self.train_lightgbm()
                elif selected_model == "XGBoost":
                    success, message = self.train_xgboost()
                elif selected_model == "TabNet":
                    success, message = self.train_tabnet()
                else:
                    success, message = False, f"不支持的模型: {selected_model}"

                # 更新UI
                self.frame.after(0, lambda: self.training_completed(success, message))

            except Exception as e:
                self.frame.after(0, lambda: self.training_completed(False, f"训练过程中出错: {str(e)}"))

        threading.Thread(target=run_training, daemon=True).start()

    def training_completed(self, success, message):
        """训练完成回调"""
        if success:
            self.training_gui.log_message(f"训练完成: {message}")
            self.training_gui.update_status("训练完成")
            messagebox.showinfo("成功", message)
        else:
            self.training_gui.log_message(f"训练失败: {message}")
            self.training_gui.update_status("训练失败")
            messagebox.showerror("错误", message)

        # 重置进度条
        self.progress_var.set(0)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_var.set(value)
        self.frame.update()

    # 各个模型的训练方法
    def train_catboost(self):
        """训练CatBoost模型"""
        try:
            from tools.app.services.model_training.models.catboost.catboost import train

            self.training_gui.log_message("正在加载CatBoost训练模块...")

            # 获取用户设置的参数
            cb_params = {}
            model_params = self.training_gui.get_model_parameters().get("CatBoost", {})
            for param_name, param_config in model_params.items():
                cb_params[param_name] = param_config["value"]

            self.training_gui.log_message(f"使用参数: {cb_params}")

            success, message = train(
                dataset_path=self.training_dataset_path,
                model_save_path=self.model_save_path,
                progress_callback=self.update_progress,
                log_callback=lambda msg: self.training_gui.log_message(msg),
                custom_params=cb_params
            )

            return success, message

        except Exception as e:
            return False, f"CatBoost训练失败: {str(e)}"

    def train_lightgbm(self):
        """训练LightGBM模型"""
        try:
            from tools.app.services.model_training.models.lightgbm.lightgbm import train

            self.training_gui.log_message("正在加载LightGBM训练模块...")

            # 获取用户设置的参数
            lgb_params = {}
            model_params = self.training_gui.get_model_parameters().get("LightGBM", {})
            for param_name, param_config in model_params.items():
                lgb_params[param_name] = param_config["value"]

            self.training_gui.log_message(f"使用参数: {lgb_params}")

            success, message = train(
                dataset_path=self.training_dataset_path,
                model_save_path=self.model_save_path,
                progress_callback=self.update_progress,
                log_callback=lambda msg: self.training_gui.log_message(msg),
                custom_params=lgb_params
            )

            return success, message

        except Exception as e:
            error_msg = f"LightGBM训练失败: {str(e)}"
            self.training_gui.log_message(error_msg)
            return False, error_msg

    def train_xgboost(self):
        """训练XGBoost模型"""
        try:
            from tools.app.services.model_training.models.xgboost.xgboost import train

            self.training_gui.log_message("正在加载XGBoost训练模块...")

            # 获取用户设置的参数
            xgb_params = {}
            model_params = self.training_gui.get_model_parameters().get("XGBoost", {})
            for param_name, param_config in model_params.items():
                xgb_params[param_name] = param_config["value"]

            self.training_gui.log_message(f"使用参数: {xgb_params}")

            # 调用训练函数
            success, message = train(
                dataset_path=self.training_dataset_path,
                model_save_path=self.model_save_path,
                progress_callback=self.update_progress,
                log_callback=lambda msg: self.training_gui.log_message(msg),
                custom_params=xgb_params  # 传递自定义参数
            )

            return success, message

        except Exception as e:
            error_msg = f"XGBoost训练失败: {str(e)}"
            self.training_gui.log_message(error_msg)
            return False, error_msg

    def train_tabnet(self):
        """训练TabNet模型"""
        try:
            from tools.app.services.model_training.models.tabnet.tabnet import train

            self.training_gui.log_message("正在加载TabNet训练模块...")

            # 获取用户设置的参数
            tnt_params = {}
            model_params = self.training_gui.get_model_parameters().get("TabNet", {})
            for param_name, param_config in model_params.items():
                tnt_params[param_name] = param_config["value"]

            self.training_gui.log_message(f"使用参数: {tnt_params}")

            success, message = train(
                dataset_path=self.training_dataset_path,
                model_save_path=self.model_save_path,
                progress_callback=self.update_progress,
                log_callback=lambda msg: self.training_gui.log_message(msg),
                custom_params=tnt_params
            )

            return success, message

        except Exception as e:
            return False, f"TabNet训练失败: {str(e)}"

    def open_visualization_dir(self):
        """打开可视化目录"""
        if not hasattr(self, 'model_save_path') or not self.model_save_path:
            messagebox.showwarning("警告", "请先选择训练数据和模型保存路径并完成训练")
            return

        visualization_dir = os.path.join(self.model_save_path, 'xgboost_visualizations')

        self.training_gui.log_message(f"检查可视化目录: {visualization_dir}")
        self.training_gui.log_message(f"目录是否存在: {os.path.exists(visualization_dir)}")

        if not os.path.exists(visualization_dir):
            messagebox.showwarning("警告",
                                   f"可视化目录不存在:\n{visualization_dir}\n\n"
                                   f"可能的原因:\n"
                                   f"1. 训练尚未完成\n"
                                   f"2. 训练过程中出现错误\n"
                                   f"3. 目录创建失败")
            return

        try:
            # 使用更可靠的目录打开方法
            # 首先规范化路径，确保使用正确的路径分隔符
            normalized_path = os.path.normpath(visualization_dir)

            # 在Windows上，使用explorer命令并确保路径被正确引用
            if os.name == 'nt':  # Windows
                # 使用原始字符串和正确的引号处理
                cmd = f'explorer "{normalized_path}"'
                self.training_gui.log_message(f"执行命令: {cmd}")
                os.system(cmd)
            elif os.name == 'posix':  # macOS or Linux
                if sys.platform == 'darwin':  # macOS
                    os.system(f'open "{normalized_path}"')
                else:  # Linux
                    os.system(f'xdg-open "{normalized_path}"')

            self.training_gui.log_message(f"已尝试打开可视化目录: {normalized_path}")

            # 同时显示目录内容
            try:
                files = os.listdir(visualization_dir)
                if files:
                    file_list = "\n".join(files)
                    self.training_gui.log_message(f"目录内容:\n{file_list}")
                else:
                    self.training_gui.log_message("目录为空")
            except Exception as e:
                self.training_gui.log_message(f"无法读取目录内容: {str(e)}")

        except Exception as e:
            self.training_gui.log_message(f"打开目录时出错: {str(e)}")
            # 如果自动打开失败，显示目录路径让用户手动打开
            messagebox.showinfo("目录位置",
                                f"无法自动打开目录，请手动访问:\n\n{visualization_dir}")


# ======================================================================================================================
# 主程序入口 - 支持training GUI独立运行
# ======================================================================================================================
def main():
    """独立运行训练GUI"""
    root = tk.Tk()
    root.title("模型训练")
    app = TrainingGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
