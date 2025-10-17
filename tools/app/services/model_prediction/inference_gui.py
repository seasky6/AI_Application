import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tools.app.services.model_prediction.function.labeler_manager import LabelerManager  # 本地测试用
from tools.app.services.model_prediction.function.predictor import Predictor


# ======================================================================================================================
# Inference主窗口和标签页管理
# ======================================================================================================================
class InferenceGUI:
    """模型推理GUI - 适配为可嵌入组件"""
    def __init__(self, parent):
        """
        初始化推理GUI

        Args:
            parent: 父容器，可以是Frame或其他tkinter容器
        """
        self.parent = parent

        # 设置深色主题
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#007acc"
        self.frame_bg = "#2d2d2d"
        self.entry_bg = "#3d3d3d"

        # 初始化打标管理器和预测器
        self.labeler_manager = LabelerManager()
        self.predictor = Predictor()

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

    def setup_ui(self):
        """设置用户界面"""
        # 使用传入的parent作为主容器
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # 创建标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 创建打标标签页
        self.labeling_tab = LabelingTab(self.notebook, self)
        self.notebook.add(self.labeling_tab.frame, text="样本打标")

        # 创建预测标签页
        self.prediction_tab = PredictionTab(self.notebook, self)
        self.notebook.add(self.prediction_tab.frame, text="模型预测")

        # 连接两个标签页的数据传递
        self.labeling_tab.set_prediction_tab(self.prediction_tab)
        self.prediction_tab.set_labeling_tab(self.labeling_tab)

        # 状态信息
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))


# ======================================================================================================================
# 打标标签页
# ======================================================================================================================
class LabelingTab:
    def __init__(self, parent, inference_gui):
        self.labeler_manager = inference_gui.labeler_manager
        self.predictor = inference_gui.predictor
        self.parent = parent
        self.inference_gui = inference_gui
        self.frame = ttk.Frame(parent)
        self.prediction_tab = None

        # 初始化变量
        self.sample_file_path = tk.StringVar()
        self.labeling_method = tk.StringVar(value="pattern_2")
        self.labeled_file_path = tk.StringVar()

        self.create_widgets()

    def set_prediction_tab(self, prediction_tab):
        """设置预测标签页引用"""
        self.prediction_tab = prediction_tab

    def create_widgets(self):
        """创建打标标签页组件"""
        # 主框架
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # 创建黑色文字样式
        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        style.configure("Black.TCombobox", foreground="#000000")

        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10", style="White.TLabelframe")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # 样本文件选择
        ttk.Label(file_frame, text="样本文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        sample_entry = ttk.Entry(file_frame, textvariable=self.sample_file_path, width=60)
        sample_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        sample_entry.configure(style="Black.TEntry")  # 黑色文字

        ttk.Button(file_frame, text="浏览", command=self.browse_sample_file).grid(row=0, column=2, padx=5)

        # 打标方法选择
        ttk.Label(file_frame, text="打标方法:").grid(row=1, column=0, sticky=tk.W, pady=5)
        labeling_combo = ttk.Combobox(file_frame, textvariable=self.labeling_method,
                                      values=["pattern_1", "pattern_2"],
                                      state="readonly")
        labeling_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        labeling_combo.configure(style="Black.TCombobox")  # 黑色文字
        labeling_combo.set("pattern_2")

        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="执行打标", command=self.execute_labeling).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存结果", command=self.save_labeled_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)

        # 结果显示区域
        results_frame = ttk.LabelFrame(main_frame, text="打标结果", padding="10", style="White.TLabelframe")
        results_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # 创建结果文本框
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, width=100, height=25)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)

    def browse_sample_file(self):
        """浏览样本文件"""
        filename = filedialog.askopenfilename(
            title="选择样本文件",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"),
                       ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.sample_file_path.set(filename)

    def execute_labeling(self):
        """执行打标操作"""
        try:
            self.results_text.delete(1.0, tk.END)

            sample_path = self.sample_file_path.get()
            if not sample_path:
                messagebox.showerror("错误", "请选择样本文件")
                return

            self.results_text.insert(tk.END, "正在加载样本数据...\n")
            self.frame.update()

            # 加载样本数据
            df = self.labeler_manager.load_sample_data(sample_path)
            if df is None:
                return

            self.results_text.insert(tk.END, f"样本数据加载成功，共 {len(df)} 条记录\n")

            # 执行打标
            labeling_method = self.labeling_method.get()
            self.results_text.insert(tk.END, f"正在使用 {labeling_method} 方法进行打标...\n")
            self.frame.update()

            # 执行打标
            labeled_df = self.labeler_manager.execute_labeling(df, labeling_method)

            if labeled_df is not None:
                self.results_text.insert(tk.END, f"打标完成！共处理 {len(labeled_df)} 条记录\n")

                # 显示打标结果统计
                self.display_labeling_stats(labeled_df, labeling_method)

                # 自动更新预测标签页的文件路径
                if self.prediction_tab:
                    output_dir = os.path.dirname(sample_path)
                    base_name = os.path.splitext(os.path.basename(sample_path))[0]
                    labeled_file = os.path.join(output_dir, f"{base_name}_labeled.csv")
                    self.labeled_file_path.set(labeled_file)
                    self.prediction_tab.set_sample_file(labeled_file)

                messagebox.showinfo("完成", "样本打标完成！")

        except Exception as e:
            messagebox.showerror("错误", f"打标过程中出错: {str(e)}")
            import traceback
            self.results_text.insert(tk.END, f"错误详情:\n{traceback.format_exc()}\n")

    def display_labeling_stats(self, df, method):
        """显示打标结果统计"""
        self.results_text.insert(tk.END, "\n" + "=" * 50 + "\n")
        self.results_text.insert(tk.END, "打标结果统计\n")
        self.results_text.insert(tk.END, "=" * 50 + "\n\n")

        # 显示所有输出特征列的分布
        output_columns = ['PA Status Pattern 1', 'PA Status Pattern 2', 'PA Status Repair Info']

        for col in output_columns:
            if col in df.columns:
                counts = df[col].value_counts()
                self.results_text.insert(tk.END, f"{col} 分布:\n")
                for status, count in counts.items():
                    self.results_text.insert(tk.END, f"  {status}: {count} 个样本\n")
                self.results_text.insert(tk.END, "\n")

        # 显示前10条记录
        self.results_text.insert(tk.END, "前10条记录预览:\n")
        preview_columns = ['Serial', 'ProductName']

        # 添加所有存在的输出特征列
        for col in output_columns:
            if col in df.columns:
                preview_columns.append(col)

        # 添加Symptoms列（如果存在）
        if 'Symptoms' in df.columns:
            preview_columns.append('Symptoms')

        preview_df = df[preview_columns].head(10)
        self.results_text.insert(tk.END, preview_df.to_string() + "\n")

    def save_labeled_data(self):
        """保存打标结果"""
        if not hasattr(self.labeler_manager, 'labeled_df') or self.labeler_manager.labeled_df is None:
            messagebox.showwarning("警告", "没有可保存的打标结果")
            return

        filename = filedialog.asksaveasfilename(
            title="保存打标结果",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                self.labeler_manager.labeled_df.to_csv(filename, index=False)
                self.labeled_file_path.set(filename)
                messagebox.showinfo("成功", f"打标结果已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存结果失败: {str(e)}")

    def clear_results(self):
        """清空结果"""
        self.results_text.delete(1.0, tk.END)
        if hasattr(self.labeler_manager, 'labeled_df'):
            self.labeler_manager.labeled_df = None


# ======================================================================================================================
# 预测标签页
# ======================================================================================================================
class PredictionTab:
    def __init__(self, parent, inference_gui):
        self.predictor = inference_gui.predictor
        self.labeling_tab = inference_gui.labeling_tab
        self.parent = parent
        self.inference_gui = inference_gui
        self.frame = ttk.Frame(parent)


        # 初始化变量
        self.sample_file_path = tk.StringVar()
        self.model_file_path = tk.StringVar()
        self.model_type = tk.StringVar(value="auto")
        self.preprocess_config_path = tk.StringVar()

        self.create_widgets()

    def set_labeling_tab(self, labeling_tab):
        """设置打标标签页引用"""
        self.labeling_tab = labeling_tab

    def set_sample_file(self, file_path):
        """设置样本文件路径"""
        self.sample_file_path.set(file_path)

    def create_widgets(self):
        """创建预测标签页组件"""
        # 主框架
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # 创建黑色文字样式
        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        style.configure("Black.TCombobox", foreground="#000000")

        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10", style="White.TLabelframe")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # 样本文件选择
        ttk.Label(file_frame, text="样本文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        sample_entry = ttk.Entry(file_frame, textvariable=self.sample_file_path, width=60)
        sample_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        sample_entry.configure(style="Black.TEntry")  # 黑色文字
        ttk.Button(file_frame, text="浏览", command=self.browse_sample_file).grid(row=0, column=2, padx=5)

        # 模型文件选择
        ttk.Label(file_frame, text="模型文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        model_entry = ttk.Entry(file_frame, textvariable=self.model_file_path, width=60)
        model_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        model_entry.configure(style="Black.TEntry")  # 黑色文字
        ttk.Button(file_frame, text="浏览", command=self.browse_model_file).grid(row=1, column=2, padx=5)

        # 预处理配置选择
        ttk.Label(file_frame, text="预处理配置文件夹:").grid(row=2, column=0, sticky=tk.W, pady=5)
        preprocess_entry = ttk.Entry(file_frame, textvariable=self.preprocess_config_path, width=60)
        preprocess_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        preprocess_entry.configure(style="Black.TEntry")  # 黑色文字
        ttk.Button(file_frame, text="浏览", command=self.browse_preprocess_config).grid(row=2, column=2, padx=5)

        # 添加提示信息
        help_label = ttk.Label(file_frame,
                               text="提示：选择包含scaler.pkl、encoder.pkl和metadata.json的文件夹",
                               foreground="gray",
                               font=("Arial", 8))
        help_label.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))

        # 模型类型选择
        ttk.Label(file_frame, text="模型类型:").grid(row=3, column=0, sticky=tk.W, pady=5)
        model_type_combo = ttk.Combobox(file_frame, textvariable=self.model_type,
                                        values=["auto", "xgboost", "lightgbm", "tabnet", "catboost", "sklearn"],
                                        state="readonly")
        model_type_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)
        model_type_combo.configure(style="Black.TCombobox")  # 黑色文字
        model_type_combo.set("auto")

        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="开始预测", command=self.run_prediction).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存结果", command=self.save_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)

        # 结果显示区域 - 使用标签页
        results_frame = ttk.LabelFrame(main_frame, text="预测结果", padding="10", style="White.TLabelframe")
        results_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # 创建结果标签页
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 预测结果标签页
        self.prediction_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.prediction_tab, text="预测结果")

        # 准确性报告标签页
        self.accuracy_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.accuracy_tab, text="准确性报告")

        # 配置预测结果标签页
        self.prediction_tab.columnconfigure(0, weight=1)
        self.prediction_tab.rowconfigure(0, weight=1)

        # 创建预测结果文本框
        self.prediction_text = scrolledtext.ScrolledText(self.prediction_tab, wrap=tk.WORD, width=100, height=20)
        self.prediction_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)

        # 配置准确性报告标签页
        self.accuracy_tab.columnconfigure(0, weight=1)
        self.accuracy_tab.rowconfigure(0, weight=1)

        # 创建准确性报告文本框
        self.accuracy_text = scrolledtext.ScrolledText(self.accuracy_tab, wrap=tk.WORD, width=100, height=20)
        self.accuracy_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)

    def browse_sample_file(self):
        """浏览样本文件"""
        filename = filedialog.askopenfilename(
            title="选择样本文件",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.sample_file_path.set(filename)

    def browse_model_file(self):
        """浏览模型文件"""
        filetypes = [
            ("所有支持的模型文件", "*.json;*.txt;*.zip;*.cbm;*.pkl;*.joblib;*.model"),
            ("XGBoost 模型", "*.json"),
            ("LightGBM 模型", "*.txt"),
            ("TabNet 模型", "*.zip"),
            ("CatBoost 模型", "*.cbm"),
            ("Scikit-learn 模型", "*.pkl;*.joblib;*.model"),
            ("所有文件", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=filetypes
        )

        if filename:
            self.model_file_path.set(filename)
            # 根据文件扩展名自动检测模型类型
            if filename.endswith('.json'):
                self.model_type.set('xgboost')
            elif filename.endswith('.txt'):
                self.model_type.set('lightgbm')
            elif filename.endswith('.zip'):
                self.model_type.set('tabnet')
            elif filename.endswith('.cbm'):
                self.model_type.set('catboost')
            elif filename.endswith(('.pkl', '.joblib', '.model')):
                self.model_type.set('sklearn')
            else:
                # 如果无法自动识别，保持当前选择或使用auto
                self.model_type.set('auto')

    def browse_preprocess_config(self):
        """浏览预处理配置文件夹"""
        folder_path = filedialog.askdirectory(
            title="选择预处理配置文件夹",
            mustexist=True  # 确保文件夹存在
        )
        if folder_path:
            self.preprocess_config_path.set(folder_path)
            # 验证文件夹中是否包含必要的文件
            required_files = ['scaler.pkl', 'encoder.pkl', 'metadata.json']
            missing_files = []
            for file in required_files:
                if not os.path.exists(os.path.join(folder_path, file)):
                    missing_files.append(file)

            if missing_files:
                messagebox.showwarning("警告",
                                       f"预处理配置文件夹中缺少以下文件:\n" + "\n".join(missing_files))

    def run_prediction(self):
        """运行预测"""
        try:
            # 清空结果
            self.prediction_text.delete(1.0, tk.END)
            self.accuracy_text.delete(1.0, tk.END)

            # 检查文件
            sample_path = self.sample_file_path.get()
            model_path = self.model_file_path.get()

            if not sample_path:
                messagebox.showerror("错误", "请选择样本文件")
                return

            if not model_path:
                messagebox.showerror("错误", "请选择模型文件")
                return

            # 设置预测器参数
            self.predictor.set_model_file(model_path, self.model_type.get())
            self.predictor.set_sample_file(sample_path)

            if self.preprocess_config_path.get():
                self.predictor.set_preprocess_config(self.preprocess_config_path.get())
                self.prediction_text.insert(tk.END, f"设置预处理配置文件夹: {self.preprocess_config_path.get()}\n")

            # 执行预测
            self.prediction_text.insert(tk.END, "开始预测...\n")
            self.prediction_text.insert(tk.END, "1. 加载模型...\n")
            self.frame.update()

            # 添加详细的步骤日志
            self.prediction_text.insert(tk.END, "2. 加载预处理对象...\n")
            self.frame.update()

            self.prediction_text.insert(tk.END, "3. 处理特征数据...\n")
            self.frame.update()

            self.prediction_text.insert(tk.END, "4. 应用预处理...\n")
            self.frame.update()

            self.prediction_text.insert(tk.END, "5. 执行预测...\n")
            self.frame.update()

            success, message = self.predictor.run_prediction()

            if success:
                self.prediction_text.insert(tk.END, f"预测完成！{message}\n")
                self.display_prediction_results()
                self.display_accuracy_report()
                messagebox.showinfo("完成", "预测完成！")
            else:
                # 显示详细的错误信息
                self.prediction_text.insert(tk.END, f"预测失败: {message}\n")
                messagebox.showerror("错误", f"预测失败: {message}")

        except Exception as e:
            error_msg = f"预测过程中出错: {str(e)}"
            self.prediction_text.insert(tk.END, f"{error_msg}\n")
            # 显示更详细的错误信息
            import traceback
            self.prediction_text.insert(tk.END, f"错误详情:\n{traceback.format_exc()}\n")
            messagebox.showerror("错误", error_msg)

    def display_prediction_results(self):
        """显示预测结果"""
        if self.predictor.results_df is None:
            return

        self.prediction_text.insert(tk.END, "\n" + "=" * 50 + "\n")
        self.prediction_text.insert(tk.END, "预测结果概览\n")
        self.prediction_text.insert(tk.END, "=" * 50 + "\n\n")

        # 显示前20条记录
        display_columns = ['预测结果', '预测标签']
        if 'PA Status Pattern 1' in self.predictor.results_df.columns:
            display_columns.append('PA Status Pattern 1')
        if 'PA Status Pattern 2' in self.predictor.results_df.columns:
            display_columns.append('PA Status Pattern 2')

        # 添加一些特征列用于参考
        feature_cols = [col for col in self.predictor.results_df.columns if col not in
                        ['预测结果', '预测标签', 'PA Status Pattern 1', 'PA Status Pattern 2', 'PA Status Repair Info',
                         'Symptoms',
                         'Serial', 'ProductName', 'Timestamp']]
        display_columns.extend(feature_cols[:3])  # 显示前3个特征列

        preview_df = self.predictor.results_df[display_columns].head(20)
        self.prediction_text.insert(tk.END, preview_df.to_string() + "\n\n")

        # 显示预测结果分布
        self.prediction_text.insert(tk.END, "预测结果分布:\n")
        prediction_counts = self.predictor.results_df['预测标签'].value_counts()
        for value, count in prediction_counts.items():
            self.prediction_text.insert(tk.END, f"  {value}: {count} 个样本\n")

    def display_accuracy_report(self):
        """显示准确性报告"""
        if self.predictor.results_df is None:
            return

        self.accuracy_text.insert(tk.END, "=" * 50 + "\n")
        self.accuracy_text.insert(tk.END, "预测准确性报告\n")
        self.accuracy_text.insert(tk.END, "=" * 50 + "\n\n")

        # 获取准确性报告
        accuracy_report = self.predictor.get_accuracy_report()
        self.accuracy_text.insert(tk.END, accuracy_report)

    def save_results(self):
        """保存预测结果"""
        if self.predictor.results_df is None:
            messagebox.showwarning("警告", "没有可保存的结果")
            return

        filename = filedialog.asksaveasfilename(
            title="保存预测结果",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                # 使用 utf-8-sig 编码保存，确保中文正常显示
                self.predictor.results_df.to_csv(filename, index=False, encoding='utf-8-sig')
                messagebox.showinfo("成功", f"结果已保存到: {filename}")
            except Exception as e:
                # 如果 utf-8-sig 失败，尝试其他编码
                try:
                    self.predictor.results_df.to_csv(filename, index=False, encoding='gbk')
                    messagebox.showinfo("成功", f"结果已保存到: {filename} (使用GBK编码)")
                except Exception as e2:
                    messagebox.showerror("错误", f"保存结果失败: {str(e)}\n尝试GBK编码也失败: {str(e2)}")

    def clear_results(self):
        """清空结果"""
        self.prediction_text.delete(1.0, tk.END)
        self.accuracy_text.delete(1.0, tk.END)
        self.predictor.clear_results()


# ======================================================================================================================
# 主程序入口 - 支持inference GUI独立运行
# ======================================================================================================================
def main():
    """独立运行推理GUI"""
    root = tk.Tk()
    root.title("模型推理")
    InferenceGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
