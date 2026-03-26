import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from tools.app.services.model_prediction.function.labeler_manager import LabelerManager  # 本地测试用
from tools.app.services.model_prediction.function.predictor import Predictor


# =========================
# i18n 资源（Inference）
# =========================
_I18N = {
    "zh": {
        "tab_label": "样本打标",
        "tab_pred": "模型预测",
        "status_ready": "就绪",

        "lf_file": "文件选择",
        "lbl_sample": "样本文件:",
        "lbl_method": "打标方法:",
        "btn_browse": "浏览",
        "btn_run_label": "执行打标",
        "btn_save": "保存结果",
        "btn_clear": "清空结果",
        "lf_result_label": "打标结果",

        "dlg_err": "错误",
        "dlg_warn": "警告",
        "dlg_done": "完成",
        "dlg_success": "成功",

        "pick_sample_title": "选择样本文件",
        "need_sample": "请选择样本文件",
        "loading": "正在加载样本数据...\n",
        "loaded_ok": "样本数据加载成功，共 {n} 条记录\n",
        "labeling": "正在使用 {m} 方法进行打标...\n",
        "label_done": "打标完成！共处理 {n} 条记录\n",
        "label_done_popup": "样本打标完成！",
        "err_detail": "错误详情:\n{tb}\n",

        "stats_title": "打标结果统计",
        "dist": "{col} 分布:\n",
        "items": " {status}: {count} 个条目\n",
        "preview": "前10条记录预览:\n",

        "no_save": "没有可保存的打标结果",
        "save_label_title": "保存打标结果",
        "saved_to": "打标结果已保存到: {path}",

        # Prediction tab
        "pred_lf_file": "文件选择",
        "pred_sample": "样本文件:",
        "pred_model": "模型文件:",
        "pred_preproc": "预处理配置文件夹:",
        "pred_help": "提示：选择包含scaler.pkl、encoder.pkl和metadata.json的文件夹",
        "pred_model_type": "模型类型:",
        "btn_start_pred": "开始预测",
        "lf_pred_result": "预测结果",
        "tab_pred_result": "预测结果",
        "tab_acc": "准确性报告",

        "pick_model_title": "选择模型文件",
        "pick_preproc_title": "选择预处理配置文件夹",
        "preproc_missing": "预处理配置文件夹中缺少以下文件:\n{files}",

        "need_model": "请选择模型文件",
        "set_preproc": "设置预处理配置文件夹: {path}\n",
        "pred_start": "开始预测...\n",
        "step1": "1. 加载模型...\n",
        "step2": "2. 加载预处理对象...\n",
        "step3": "3. 处理特征数据...\n",
        "step4": "4. 应用预处理...\n",
        "step5": "5. 执行预测...\n",
        "pred_ok": "预测完成！{msg}\n",
        "pred_fail": "预测失败: {msg}\n",

        "overview": "预测结果概览",
        "dist_pred": "预测结果分布:\n",
        "pred_item": " {value}: {count} 个条目\n",
        "acc_title": "预测准确性报告\n",

        "save_pred_title": "保存预测结果",
        "no_pred_save": "没有可保存的结果",
        "saved_pred": "结果已保存到: {path}",
        "saved_pred_gbk": "结果已保存到: {path} (使用GBK编码)",
        "save_fail": "保存结果失败: {e}\n尝试GBK编码也失败: {e2}",
    },
    "en": {
        "tab_label": "Labeling",
        "tab_pred": "Prediction",
        "status_ready": "Ready",

        "lf_file": "File Selection",
        "lbl_sample": "Sample file:",
        "lbl_method": "Labeling method:",
        "btn_browse": "Browse",
        "btn_run_label": "Run Labeling",
        "btn_save": "Save",
        "btn_clear": "Clear",
        "lf_result_label": "Labeling Results",

        "dlg_err": "Error",
        "dlg_warn": "Warning",
        "dlg_done": "Done",
        "dlg_success": "Success",

        "pick_sample_title": "Select sample file",
        "need_sample": "Please select a sample file",
        "loading": "Loading sample data...\n",
        "loaded_ok": "Sample data loaded successfully, total {n} rows\n",
        "labeling": "Labeling with method: {m} ...\n",
        "label_done": "Labeling finished! Processed {n} rows\n",
        "label_done_popup": "Labeling completed!",
        "err_detail": "Details:\n{tb}\n",

        "stats_title": "Labeling Statistics",
        "dist": "{col} distribution:\n",
        "items": " {status}: {count} items\n",
        "preview": "Preview (top 10 rows):\n",

        "no_save": "No labeling result to save",
        "save_label_title": "Save labeling result",
        "saved_to": "Saved to: {path}",

        # Prediction tab
        "pred_lf_file": "File Selection",
        "pred_sample": "Sample file:",
        "pred_model": "Model file:",
        "pred_preproc": "Preprocess config folder:",
        "pred_help": "Tip: select the folder containing scaler.pkl, encoder.pkl and metadata.json",
        "pred_model_type": "Model type:",
        "btn_start_pred": "Run Prediction",
        "lf_pred_result": "Prediction Results",
        "tab_pred_result": "Predictions",
        "tab_acc": "Accuracy Report",

        "pick_model_title": "Select model file",
        "pick_preproc_title": "Select preprocess config folder",
        "preproc_missing": "Missing required files in preprocess folder:\n{files}",

        "need_model": "Please select a model file",
        "set_preproc": "Preprocess config folder set to: {path}\n",
        "pred_start": "Running prediction...\n",
        "step1": "1. Loading model...\n",
        "step2": "2. Loading preprocess objects...\n",
        "step3": "3. Preparing features...\n",
        "step4": "4. Applying preprocessing...\n",
        "step5": "5. Predicting...\n",
        "pred_ok": "Prediction finished! {msg}\n",
        "pred_fail": "Prediction failed: {msg}\n",

        "overview": "Prediction Overview",
        "dist_pred": "Prediction distribution:\n",
        "pred_item": " {value}: {count} items\n",
        "acc_title": "Accuracy Report\n",

        "save_pred_title": "Save prediction result",
        "no_pred_save": "No result to save",
        "saved_pred": "Saved to: {path}",
        "saved_pred_gbk": "Saved to: {path} (GBK encoding)",
        "save_fail": "Save failed: {e}\nGBK fallback also failed: {e2}",
    },
}


def _fmt(text: str, **kw):
    try:
        return text.format(**kw)
    except Exception:
        return text


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
        self.lang = "zh"
        self._external_t = None  # 来自主界面的 t(key)

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

    # -------------------------
    # i18n helper
    # -------------------------
    def _t(self, key: str, **fmt_kw) -> str:
        if callable(self._external_t):
            v = self._external_t(key)
            if v != key:
                text = v
            else:
                text = _I18N.get(self.lang, _I18N["en"]).get(key, key)
        else:
            text = _I18N.get(self.lang, _I18N["en"]).get(key, key)
        return _fmt(text, **fmt_kw) if fmt_kw else text

    def apply_language(self, lang: str, t_func=None):
        """供主界面调用：切换语言并刷新UI"""
        self.lang = lang or "zh"
        self._external_t = t_func

        if hasattr(self, "notebook"):
            self.notebook.tab(self.labeling_tab.frame, text=self._t("tab_label"))
            self.notebook.tab(self.prediction_tab.frame, text=self._t("tab_pred"))

        if hasattr(self, "status_var"):
            # 仅当还是默认状态时更新
            if self.status_var.get() in ("就绪", "Ready"):
                self.status_var.set(self._t("status_ready"))

        # 下发到子tab
        if hasattr(self, "labeling_tab"):
            self.labeling_tab.apply_language(self.lang, self._external_t, self._t)
        if hasattr(self, "prediction_tab"):
            self.prediction_tab.apply_language(self.lang, self._external_t, self._t)

    # -------------------------
    # theme & UI
    # -------------------------
    def setup_dark_theme(self):
        """设置深色主题"""
        style = ttk.Style()

        # 配置黑色文字样式
        style.configure("Black.TEntry", fieldbackground=self.entry_bg, foreground="#000000")
        style.configure("Black.TCombobox", fieldbackground=self.entry_bg, foreground="#000000")

        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("TButton", background=self.accent_color, foreground="#000000")
        style.map(
            "TButton",
            background=[("active", self.accent_color), ("pressed", self.accent_color)],
            foreground=[("active", "#000000"), ("pressed", "#000000")],
        )
        style.configure("TEntry", fieldbackground=self.entry_bg, foreground=self.fg_color)
        style.configure("TCombobox", fieldbackground=self.entry_bg, foreground=self.fg_color)

        # 白色文字的 LabelFrame 样式
        style.configure("White.TLabelframe", background=self.bg_color, foreground=self.fg_color)
        style.configure("White.TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)
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
        self.notebook.add(self.labeling_tab.frame, text=self._t("tab_label"))

        # 创建预测标签页
        self.prediction_tab = PredictionTab(self.notebook, self)
        self.notebook.add(self.prediction_tab.frame, text=self._t("tab_pred"))

        # 连接两个标签页的数据传递
        self.labeling_tab.set_prediction_tab(self.prediction_tab)
        self.prediction_tab.set_labeling_tab(self.labeling_tab)

        # 状态信息
        self.status_var = tk.StringVar(value=self._t("status_ready"))
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))


# ======================================================================================================================
# 打标标签页
# ======================================================================================================================
class LabelingTab:
    def __init__(self, parent, inference_gui: InferenceGUI):
        self.labeler_manager = inference_gui.labeler_manager
        self.predictor = inference_gui.predictor
        self.parent = parent
        self.inference_gui = inference_gui
        self.frame = ttk.Frame(parent)
        self.prediction_tab = None

        self.lang = "zh"
        self._external_t = None
        self._t_local = None  # fallback

        # 初始化变量
        self.sample_file_path = tk.StringVar()
        self.labeling_method = tk.StringVar(value="pattern_2")
        self.labeled_file_path = tk.StringVar()

        # ui refs
        self.file_frame = None
        self.results_frame = None
        self.results_text = None
        self.btn_run = None
        self.btn_save = None
        self.btn_clear = None
        self.lbl_sample = None
        self.lbl_method = None
        self.btn_browse = None

        self.create_widgets()

    def apply_language(self, lang: str, t_func=None, t_local=None):
        self.lang = lang or "zh"
        self._external_t = t_func
        self._t_local = t_local

        # update frame texts
        if self.file_frame is not None:
            self.file_frame.configure(text=self._t("lf_file"))
        if self.results_frame is not None:
            self.results_frame.configure(text=self._t("lf_result_label"))
        if self.lbl_sample is not None:
            self.lbl_sample.configure(text=self._t("lbl_sample"))
        if self.lbl_method is not None:
            self.lbl_method.configure(text=self._t("lbl_method"))
        if self.btn_browse is not None:
            self.btn_browse.configure(text=self._t("btn_browse"))
        if self.btn_run is not None:
            self.btn_run.configure(text=self._t("btn_run_label"))
        if self.btn_save is not None:
            self.btn_save.configure(text=self._t("btn_save"))
        if self.btn_clear is not None:
            self.btn_clear.configure(text=self._t("btn_clear"))

    def _t(self, key: str, **fmt_kw) -> str:
        if callable(self._external_t):
            v = self._external_t(key)
            if v != key:
                text = v
            else:
                text = _I18N.get(self.lang, _I18N["en"]).get(key, key)
        else:
            text = _I18N.get(self.lang, _I18N["en"]).get(key, key)
        return _fmt(text, **fmt_kw) if fmt_kw else text

    def set_prediction_tab(self, prediction_tab):
        """设置预测标签页引用"""
        self.prediction_tab = prediction_tab

    def create_widgets(self):
        """创建打标标签页组件"""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)

        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        style.configure("Black.TCombobox", foreground="#000000")

        # 文件选择区域
        self.file_frame = ttk.LabelFrame(main_frame, text=self.inference_gui._t("lf_file"),
                                         padding="10", style="White.TLabelframe")
        self.file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.file_frame.columnconfigure(1, weight=1)

        # 样本文件选择
        self.lbl_sample = ttk.Label(self.file_frame, text=self.inference_gui._t("lbl_sample"))
        self.lbl_sample.grid(row=0, column=0, sticky=tk.W, pady=5)

        sample_entry = ttk.Entry(self.file_frame, textvariable=self.sample_file_path, width=60)
        sample_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        sample_entry.configure(style="Black.TEntry")

        self.btn_browse = ttk.Button(self.file_frame, text=self.inference_gui._t("btn_browse"),
                                     command=self.browse_sample_file)
        self.btn_browse.grid(row=0, column=2, padx=5)

        # 打标方法选择
        self.lbl_method = ttk.Label(self.file_frame, text=self.inference_gui._t("lbl_method"))
        self.lbl_method.grid(row=1, column=0, sticky=tk.W, pady=5)

        labeling_combo = ttk.Combobox(
            self.file_frame,
            textvariable=self.labeling_method,
            values=["pattern_1", "pattern_2"],
            state="readonly",
        )
        labeling_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        labeling_combo.configure(style="Black.TCombobox")
        labeling_combo.set("pattern_2")

        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.btn_run = ttk.Button(button_frame, text=self.inference_gui._t("btn_run_label"),
                                  command=self.execute_labeling)
        self.btn_run.pack(side=tk.LEFT, padx=5)

        self.btn_save = ttk.Button(button_frame, text=self.inference_gui._t("btn_save"),
                                   command=self.save_labeled_data)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(button_frame, text=self.inference_gui._t("btn_clear"),
                                    command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # 结果显示区域
        self.results_frame = ttk.LabelFrame(main_frame, text=self.inference_gui._t("lf_result_label"),
                                            padding="10", style="White.TLabelframe")
        self.results_frame.grid(row=2, column=0, columnspan=2,
                                sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)

        self.results_text = scrolledtext.ScrolledText(self.results_frame, wrap=tk.WORD, width=100, height=25)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)

    def browse_sample_file(self):
        """浏览样本文件"""
        filename = filedialog.askopenfilename(
            title=self.inference_gui._t("pick_sample_title"),
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self.sample_file_path.set(filename)

    def execute_labeling(self):
        """执行打标操作"""
        try:
            self.results_text.delete(1.0, tk.END)
            sample_path = self.sample_file_path.get()
            if not sample_path:
                messagebox.showerror(self.inference_gui._t("dlg_err"), self.inference_gui._t("need_sample"))
                return

            self.results_text.insert(tk.END, self.inference_gui._t("loading"))
            self.frame.update()

            df = self.labeler_manager.load_sample_data(sample_path)
            if df is None:
                return

            self.results_text.insert(tk.END, self.inference_gui._t("loaded_ok", n=len(df)))

            labeling_method = self.labeling_method.get()
            self.results_text.insert(tk.END, self.inference_gui._t("labeling", m=labeling_method))
            self.frame.update()

            labeled_df = self.labeler_manager.execute_labeling(df, labeling_method)
            if labeled_df is not None:
                self.results_text.insert(tk.END, self.inference_gui._t("label_done", n=len(labeled_df)))

                self.display_labeling_stats(labeled_df, labeling_method)

                # 自动更新预测标签页的文件路径
                if self.prediction_tab:
                    output_dir = os.path.dirname(sample_path)
                    base_name = os.path.splitext(os.path.basename(sample_path))[0]
                    labeled_file = os.path.join(output_dir, f"{base_name}_labeled.csv")
                    self.labeled_file_path.set(labeled_file)
                    self.prediction_tab.set_sample_file(labeled_file)

                messagebox.showinfo(self.inference_gui._t("dlg_done"), self.inference_gui._t("label_done_popup"))

        except Exception as e:
            messagebox.showerror(self.inference_gui._t("dlg_err"), f"{self.inference_gui._t('pred_fail', msg=str(e))}")
            import traceback
            self.results_text.insert(tk.END, self.inference_gui._t("err_detail", tb=traceback.format_exc()))

    def display_labeling_stats(self, df, method):
        """显示打标结果统计"""
        self.results_text.insert(tk.END, "\n" + "=" * 50 + "\n")
        self.results_text.insert(tk.END, self.inference_gui._t("stats_title") + "\n")
        self.results_text.insert(tk.END, "=" * 50 + "\n\n")

        output_columns = ['PA Status Pattern 1', 'PA Status Pattern 2', 'PA Status Repair Info']
        for col in output_columns:
            if col in df.columns:
                counts = df[col].value_counts()
                self.results_text.insert(tk.END, self.inference_gui._t("dist", col=col))
                for status, count in counts.items():
                    self.results_text.insert(tk.END, self.inference_gui._t("items", status=status, count=count))
                self.results_text.insert(tk.END, "\n")

        self.results_text.insert(tk.END, self.inference_gui._t("preview"))
        preview_columns = ['Serial', 'ProductName']
        for col in output_columns:
            if col in df.columns:
                preview_columns.append(col)
        if 'Symptoms' in df.columns:
            preview_columns.append('Symptoms')
        preview_df = df[preview_columns].head(10)
        self.results_text.insert(tk.END, preview_df.to_string() + "\n")

    def save_labeled_data(self):
        """保存打标结果"""
        if not hasattr(self.labeler_manager, 'labeled_df') or self.labeler_manager.labeled_df is None:
            messagebox.showwarning(self.inference_gui._t("dlg_warn"), self.inference_gui._t("no_save"))
            return

        filename = filedialog.asksaveasfilename(
            title=self.inference_gui._t("save_label_title"),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if filename:
            try:
                self.labeler_manager.labeled_df.to_csv(filename, index=False)
                self.labeled_file_path.set(filename)
                messagebox.showinfo(self.inference_gui._t("dlg_success"),
                                    self.inference_gui._t("saved_to", path=filename))
            except Exception as e:
                messagebox.showerror(self.inference_gui._t("dlg_err"), str(e))

    def clear_results(self):
        """清空结果"""
        self.results_text.delete(1.0, tk.END)
        if hasattr(self.labeler_manager, 'labeled_df'):
            self.labeler_manager.labeled_df = None


# ======================================================================================================================
# 预测标签页
# ======================================================================================================================
class PredictionTab:
    def __init__(self, parent, inference_gui: InferenceGUI):
        self.predictor = inference_gui.predictor
        self.labeling_tab = inference_gui.labeling_tab
        self.parent = parent
        self.inference_gui = inference_gui
        self.frame = ttk.Frame(parent)

        self.lang = "zh"
        self._external_t = None
        self._t_local = None

        # 初始化变量
        self.sample_file_path = tk.StringVar()
        self.model_file_path = tk.StringVar()
        self.model_type = tk.StringVar(value="auto")
        self.preprocess_config_path = tk.StringVar()

        # ui refs
        self.file_frame = None
        self.lbl_sample = None
        self.lbl_model = None
        self.lbl_preproc = None
        self.lbl_model_type = None
        self.help_label = None
        self.btn_browse_sample = None
        self.btn_browse_model = None
        self.btn_browse_preproc = None
        self.btn_run = None
        self.btn_save = None
        self.btn_clear = None
        self.results_frame = None
        self.results_notebook = None
        self.prediction_tab = None
        self.accuracy_tab = None

        self.prediction_text = None
        self.accuracy_text = None

        self.create_widgets()

    def apply_language(self, lang: str, t_func=None, t_local=None):
        self.lang = lang or "zh"
        self._external_t = t_func
        self._t_local = t_local

        if self.file_frame is not None:
            self.file_frame.configure(text=self._t("pred_lf_file"))
        if self.lbl_sample is not None:
            self.lbl_sample.configure(text=self._t("pred_sample"))
        if self.lbl_model is not None:
            self.lbl_model.configure(text=self._t("pred_model"))
        if self.lbl_preproc is not None:
            self.lbl_preproc.configure(text=self._t("pred_preproc"))
        if self.lbl_model_type is not None:
            self.lbl_model_type.configure(text=self._t("pred_model_type"))
        if self.help_label is not None:
            self.help_label.configure(text=self._t("pred_help"))

        for btn in (self.btn_browse_sample, self.btn_browse_model, self.btn_browse_preproc):
            if btn is not None:
                btn.configure(text=self._t("btn_browse"))

        if self.btn_run is not None:
            self.btn_run.configure(text=self._t("btn_start_pred"))
        if self.btn_save is not None:
            self.btn_save.configure(text=self._t("btn_save"))
        if self.btn_clear is not None:
            self.btn_clear.configure(text=self._t("btn_clear"))

        if self.results_frame is not None:
            self.results_frame.configure(text=self._t("lf_pred_result"))

        if self.results_notebook is not None and self.prediction_tab is not None and self.accuracy_tab is not None:
            self.results_notebook.tab(self.prediction_tab, text=self._t("tab_pred_result"))
            self.results_notebook.tab(self.accuracy_tab, text=self._t("tab_acc"))

    def _t(self, key: str, **fmt_kw) -> str:
        if callable(self._external_t):
            v = self._external_t(key)
            if v != key:
                text = v
            else:
                text = _I18N.get(self.lang, _I18N["en"]).get(key, key)
        else:
            text = _I18N.get(self.lang, _I18N["en"]).get(key, key)
        return _fmt(text, **fmt_kw) if fmt_kw else text

    def set_labeling_tab(self, labeling_tab):
        """设置打标标签页引用"""
        self.labeling_tab = labeling_tab

    def set_sample_file(self, file_path):
        """设置样本文件路径"""
        self.sample_file_path.set(file_path)

    def create_widgets(self):
        """创建预测标签页组件"""
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        style = ttk.Style()
        style.configure("Black.TEntry", foreground="#000000")
        style.configure("Black.TCombobox", foreground="#000000")

        # 文件选择区域
        self.file_frame = ttk.LabelFrame(main_frame, text=self.inference_gui._t("pred_lf_file"),
                                         padding="10", style="White.TLabelframe")
        self.file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.file_frame.columnconfigure(1, weight=1)

        # 样本文件选择
        self.lbl_sample = ttk.Label(self.file_frame, text=self.inference_gui._t("pred_sample"))
        self.lbl_sample.grid(row=0, column=0, sticky=tk.W, pady=5)
        sample_entry = ttk.Entry(self.file_frame, textvariable=self.sample_file_path, width=60)
        sample_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        sample_entry.configure(style="Black.TEntry")
        self.btn_browse_sample = ttk.Button(self.file_frame, text=self.inference_gui._t("btn_browse"),
                                            command=self.browse_sample_file)
        self.btn_browse_sample.grid(row=0, column=2, padx=5)

        # 模型文件选择
        self.lbl_model = ttk.Label(self.file_frame, text=self.inference_gui._t("pred_model"))
        self.lbl_model.grid(row=1, column=0, sticky=tk.W, pady=5)
        model_entry = ttk.Entry(self.file_frame, textvariable=self.model_file_path, width=60)
        model_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        model_entry.configure(style="Black.TEntry")
        self.btn_browse_model = ttk.Button(self.file_frame, text=self.inference_gui._t("btn_browse"),
                                           command=self.browse_model_file)
        self.btn_browse_model.grid(row=1, column=2, padx=5)

        # 预处理配置选择
        self.lbl_preproc = ttk.Label(self.file_frame, text=self.inference_gui._t("pred_preproc"))
        self.lbl_preproc.grid(row=2, column=0, sticky=tk.W, pady=5)
        preprocess_entry = ttk.Entry(self.file_frame, textvariable=self.preprocess_config_path, width=60)
        preprocess_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        preprocess_entry.configure(style="Black.TEntry")
        self.btn_browse_preproc = ttk.Button(self.file_frame, text=self.inference_gui._t("btn_browse"),
                                             command=self.browse_preprocess_config)
        self.btn_browse_preproc.grid(row=2, column=2, padx=5)

        self.help_label = ttk.Label(
            self.file_frame,
            text=self.inference_gui._t("pred_help"),
            foreground="gray",
            font=("Arial", 8),
        )
        self.help_label.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))

        # 模型类型选择
        self.lbl_model_type = ttk.Label(self.file_frame, text=self.inference_gui._t("pred_model_type"))
        self.lbl_model_type.grid(row=3, column=0, sticky=tk.W, pady=5)
        model_type_combo = ttk.Combobox(
            self.file_frame,
            textvariable=self.model_type,
            values=["auto", "xgboost", "lightgbm", "tabnet", "catboost", "sklearn"],
            state="readonly",
        )
        model_type_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)
        model_type_combo.configure(style="Black.TCombobox")
        model_type_combo.set("auto")

        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.btn_run = ttk.Button(button_frame, text=self.inference_gui._t("btn_start_pred"),
                                  command=self.run_prediction)
        self.btn_run.pack(side=tk.LEFT, padx=5)

        self.btn_save = ttk.Button(button_frame, text=self.inference_gui._t("btn_save"),
                                   command=self.save_results)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(button_frame, text=self.inference_gui._t("btn_clear"),
                                    command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # 结果显示区域 - 使用标签页
        self.results_frame = ttk.LabelFrame(main_frame, text=self.inference_gui._t("lf_pred_result"),
                                            padding="10", style="White.TLabelframe")
        self.results_frame.grid(row=2, column=0, columnspan=2,
                                sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)

        self.results_notebook = ttk.Notebook(self.results_frame)
        self.results_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.prediction_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.prediction_tab, text=self.inference_gui._t("tab_pred_result"))

        self.accuracy_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.accuracy_tab, text=self.inference_gui._t("tab_acc"))

        self.prediction_tab.columnconfigure(0, weight=1)
        self.prediction_tab.rowconfigure(0, weight=1)
        self.prediction_text = scrolledtext.ScrolledText(self.prediction_tab, wrap=tk.WORD, width=100, height=20)
        self.prediction_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)

        self.accuracy_tab.columnconfigure(0, weight=1)
        self.accuracy_tab.rowconfigure(0, weight=1)
        self.accuracy_text = scrolledtext.ScrolledText(self.accuracy_tab, wrap=tk.WORD, width=100, height=20)
        self.accuracy_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)

    def browse_sample_file(self):
        filename = filedialog.askopenfilename(
            title=self.inference_gui._t("pick_sample_title"),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if filename:
            self.sample_file_path.set(filename)

    def browse_model_file(self):
        filetypes = [
            ("All supported model files", "*.json;*.txt;*.zip;*.cbm;*.pkl;*.joblib;*.model"),
            ("XGBoost model", "*.json"),
            ("LightGBM model", "*.txt"),
            ("TabNet model", "*.zip"),
            ("CatBoost model", "*.cbm"),
            ("Scikit-learn model", "*.pkl;*.joblib;*.model"),
            ("All files", "*.*"),
        ]
        filename = filedialog.askopenfilename(title=self.inference_gui._t("pick_model_title"), filetypes=filetypes)
        if filename:
            self.model_file_path.set(filename)
            # 根据扩展名自动识别
            if filename.endswith(".json"):
                self.model_type.set("xgboost")
            elif filename.endswith(".txt"):
                self.model_type.set("lightgbm")
            elif filename.endswith(".zip"):
                self.model_type.set("tabnet")
            elif filename.endswith(".cbm"):
                self.model_type.set("catboost")
            elif filename.endswith((".pkl", ".joblib", ".model")):
                self.model_type.set("sklearn")
            else:
                self.model_type.set("auto")

    def browse_preprocess_config(self):
        folder_path = filedialog.askdirectory(title=self.inference_gui._t("pick_preproc_title"), mustexist=True)
        if folder_path:
            self.preprocess_config_path.set(folder_path)
            required_files = ["scaler.pkl", "encoder.pkl", "metadata.json"]
            missing = [f for f in required_files if not os.path.exists(os.path.join(folder_path, f))]
            if missing:
                messagebox.showwarning(self.inference_gui._t("dlg_warn"),
                                       self.inference_gui._t("preproc_missing", files="\n".join(missing)))

    def run_prediction(self):
        try:
            self.prediction_text.delete(1.0, tk.END)
            self.accuracy_text.delete(1.0, tk.END)

            sample_path = self.sample_file_path.get()
            model_path = self.model_file_path.get()

            if not sample_path:
                messagebox.showerror(self.inference_gui._t("dlg_err"), self.inference_gui._t("need_sample"))
                return
            if not model_path:
                messagebox.showerror(self.inference_gui._t("dlg_err"), self.inference_gui._t("need_model"))
                return

            self.predictor.set_model_file(model_path, self.model_type.get())
            self.predictor.set_sample_file(sample_path)

            if self.preprocess_config_path.get():
                self.predictor.set_preprocess_config(self.preprocess_config_path.get())
                self.prediction_text.insert(tk.END, self.inference_gui._t("set_preproc",
                                                                         path=self.preprocess_config_path.get()))

            self.prediction_text.insert(tk.END, self.inference_gui._t("pred_start"))
            self.prediction_text.insert(tk.END, self.inference_gui._t("step1"))
            self.frame.update()
            self.prediction_text.insert(tk.END, self.inference_gui._t("step2"))
            self.frame.update()
            self.prediction_text.insert(tk.END, self.inference_gui._t("step3"))
            self.frame.update()
            self.prediction_text.insert(tk.END, self.inference_gui._t("step4"))
            self.frame.update()
            self.prediction_text.insert(tk.END, self.inference_gui._t("step5"))
            self.frame.update()

            success, message = self.predictor.run_prediction()
            if success:
                self.prediction_text.insert(tk.END, self.inference_gui._t("pred_ok", msg=message))
                self.display_prediction_results()
                self.display_accuracy_report()
                messagebox.showinfo(self.inference_gui._t("dlg_done"), self.inference_gui._t("dlg_done"))
            else:
                self.prediction_text.insert(tk.END, self.inference_gui._t("pred_fail", msg=message))
                messagebox.showerror(self.inference_gui._t("dlg_err"),
                                     self.inference_gui._t("pred_fail", msg=message))

        except Exception as e:
            import traceback
            error_msg = str(e)
            self.prediction_text.insert(tk.END, self.inference_gui._t("pred_fail", msg=error_msg))
            self.prediction_text.insert(tk.END, self.inference_gui._t("err_detail", tb=traceback.format_exc()))
            messagebox.showerror(self.inference_gui._t("dlg_err"), self.inference_gui._t("pred_fail", msg=error_msg))

    def display_prediction_results(self):
        if self.predictor.results_df is None:
            return

        self.prediction_text.insert(tk.END, "\n" + "=" * 50 + "\n")
        self.prediction_text.insert(tk.END, self.inference_gui._t("overview") + "\n")
        self.prediction_text.insert(tk.END, "=" * 50 + "\n\n")

        display_columns = ["Prediction Result", "Prediction Label"]
        if "PA Status Pattern 1" in self.predictor.results_df.columns:
            display_columns.append("PA Status Pattern 1")
        if "PA Status Pattern 2" in self.predictor.results_df.columns:
            display_columns.append("PA Status Pattern 2")

        feature_cols = [col for col in self.predictor.results_df.columns if col not in
                        ["Prediction Result", "Prediction Label", "PA Status Pattern 1", "PA Status Pattern 2",
                         "PA Status Repair Info", "Repair Center Info", "Symptoms", "Serial", "ProductName", "Timestamp"]]
        display_columns.extend(feature_cols[:3])

        preview_df = self.predictor.results_df[display_columns].head(20)
        self.prediction_text.insert(tk.END, preview_df.to_string() + "\n\n")

        self.prediction_text.insert(tk.END, self.inference_gui._t("dist_pred"))
        prediction_counts = self.predictor.results_df["Prediction Label"].value_counts()
        for value, count in prediction_counts.items():
            self.prediction_text.insert(tk.END, self.inference_gui._t("pred_item", value=value, count=count))

    def display_accuracy_report(self):
        if self.predictor.results_df is None:
            return
        self.accuracy_text.insert(tk.END, "=" * 50 + "\n")
        self.accuracy_text.insert(tk.END, self.inference_gui._t("acc_title"))
        self.accuracy_text.insert(tk.END, "=" * 50 + "\n\n")
        accuracy_report = self.predictor.get_accuracy_report()
        self.accuracy_text.insert(tk.END, accuracy_report)

    def save_results(self):
        if self.predictor.results_df is None:
            messagebox.showwarning(self.inference_gui._t("dlg_warn"), self.inference_gui._t("no_pred_save"))
            return

        filename = filedialog.asksaveasfilename(
            title=self.inference_gui._t("save_pred_title"),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if filename:
            try:
                self.predictor.results_df.to_csv(filename, index=False, encoding="utf-8-sig")
                messagebox.showinfo(self.inference_gui._t("dlg_success"),
                                    self.inference_gui._t("saved_pred", path=filename))
            except Exception as e:
                try:
                    self.predictor.results_df.to_csv(filename, index=False, encoding="gbk")
                    messagebox.showinfo(self.inference_gui._t("dlg_success"),
                                        self.inference_gui._t("saved_pred_gbk", path=filename))
                except Exception as e2:
                    messagebox.showerror(self.inference_gui._t("dlg_err"),
                                         self.inference_gui._t("save_fail", e=str(e), e2=str(e2)))

    def clear_results(self):
        self.prediction_text.delete(1.0, tk.END)
        self.accuracy_text.delete(1.0, tk.END)
        self.predictor.clear_results()


# ======================================================================================================================
# 主程序入口 - 支持inference GUI独立运行
# ======================================================================================================================
def main():
    root = tk.Tk()
    root.title("Inference")
    app = InferenceGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()