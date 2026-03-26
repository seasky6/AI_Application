# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import numpy as np
import threading
import os
import sys
from datetime import datetime

from tools.app.services.model_training.preprocessor.data_preprocessor import TrainingDataProcessor


# =========================
# i18n 资源（Training）
# =========================
_I18N = {
    "zh": {
        "tab_pre": "训练数据预处理",
        "tab_train": "模型训练",
        "status_ready": "就绪",

        # DataPreprocessingTab
        "sec1": "1. 选择数据",
        "btn_pick_data": "选择数据文件",
        "btn_pick_out": "选择输出目录",
        "btn_fixed_out": "使用固定路径",
        "btn_load": "加载数据",

        "sec2": "2. 数据平衡选项",
        "use_cgan": "使用CGAN平衡少数类样本（产品级别）",
        "ratio_lbl": "目标平衡比例 (正常:异常):",
        "ratio_help": "1.0 表示 1:1 平衡",

        "sec3": "3. 样本和特征选择",
        "sample_sel": "样本选择:",
        "all": "全选",
        "none": "全不选",
        "adv": "高级选项",
        "xfeat": "输入特征 (X):",
        "yfeat": "输出特征 (Y):",

        "btn_export": "导出样本列表",
        "btn_gen": "生成训练数据集",

        "out_reset_title": "输出目录",
        "out_reset_msg": "已切换为使用固定路径：\n主写入保存于 files_for_training，并自动镜像到 processed_dataset。",

        "err": "错误",
        "warn": "警告",
        "ok": "成功",
        "cancel": "取消",
        "confirm": "确认",

        "need_load": "请先加载数据",
        "need_input": "请先选择输入文件",
        "need_sample": "请至少选择一个样本",
        "need_x": "请至少选择一个输入特征",
        "need_y": "请至少选择一个输出特征",
        "need_feat_any": "请至少选择一个输入特征或输出特征",
        "no_export": "没有可导出的数据",

        "pick_json": "选择JSON数据文件",
        "pick_out": "选择输出目录",
        "loaded": "加载完成: {n} 个样本",
        "loading": "正在加载数据...",

        "export_title": "导出样本列表",
        "export_done": "样本列表已导出到: {path}\n\n导出统计:\n- 样本数量: {sn}\n- 输入特征: {xn}\n- 输出特征: {yn}",

        "cgan_confirm_title": "确认CGAN平衡",
        "cgan_confirm_msg": "您选择了使用CGAN平衡数据，目标平衡比例为 {r}:1。\n\n这将在产品级别生成少数类样本，可能花费一些时间。\n是否继续？",

        # ModelTrainingTab
        "train_sec1": "1. 训练数据集选择",
        "btn_pick_dataset": "选择训练数据",
        "train_sec2": "2. 模型保存路径",
        "btn_pick_save": "选择模型保存路径",
        "train_sec3": "3. 模型选择",
        "btn_param": "设置模型参数",
        "btn_start": "开始训练",
        "btn_open_report": "打开报告文件夹",
        "log_title": "训练日志",

        "pick_dataset_title": "选择训练数据集目录",
        "pick_save_title": "选择模型保存路径",

        "train_done": "训练完成",
        "train_fail": "训练失败",
        "train_running": "正在训练 {m} 模型...",
        "train_start": "开始训练 {m} 模型...",

        "not_supported": "不支持的模型: {m}",
        "train_err": "训练过程中出错: {e}",

        # Parameter window
        "param_title": "{m} 参数设置",
        "param_header": "{m} 模型参数设置",
        "param_desc": "调整以下参数以优化模型性能\n建议值基于理论和实践经验，但最佳参数可能因数据而异\n调整后可以训练多个模型进行比较",
        "btn_default": "默认值",
        "btn_ok": "确定",

        # Advanced sample selection
        "adv_title": "高级样本选择",
        "search": "搜索:",
        "adv_ok": "确定",
        "adv_cancel": "取消",
        "adv_selected": "已选择 {n} 个样本",

        # Visualization
        "viz_warn": "请先选择训练数据和模型保存路径并完成训练",
        "viz_missing": "可视化目录不存在:\n{path}\n\n可能的原因:\n1. 训练尚未完成\n2. 训练过程中出现错误\n3. 目录创建失败",
        "viz_manual": "无法自动打开目录，请手动访问:\n\n{path}",
    },
    "en": {
        "tab_pre": "Data Preprocessing",
        "tab_train": "Model Training",
        "status_ready": "Ready",

        # DataPreprocessingTab
        "sec1": "1. Select Data",
        "btn_pick_data": "Select Data Files",
        "btn_pick_out": "Select Output Folder",
        "btn_fixed_out": "Use Fixed Path",
        "btn_load": "Load Data",

        "sec2": "2. Balancing Options",
        "use_cgan": "Use CGAN to balance minority class (product level)",
        "ratio_lbl": "Target ratio (Normal:Abnormal):",
        "ratio_help": "1.0 means 1:1 balance",

        "sec3": "3. Sample & Feature Selection",
        "sample_sel": "Samples:",
        "all": "Select All",
        "none": "Clear All",
        "adv": "Advanced",
        "xfeat": "Input Features (X):",
        "yfeat": "Output Features (Y):",

        "btn_export": "Export Sample List",
        "btn_gen": "Generate Training Dataset",

        "out_reset_title": "Output Folder",
        "out_reset_msg": "Switched to fixed output path:\nPrimary output goes to files_for_training and will be mirrored to processed_dataset.",

        "err": "Error",
        "warn": "Warning",
        "ok": "Success",
        "cancel": "Cancel",
        "confirm": "Confirm",

        "need_load": "Please load data first",
        "need_input": "Please select input files first",
        "need_sample": "Please select at least one sample",
        "need_x": "Please select at least one input feature",
        "need_y": "Please select at least one output feature",
        "need_feat_any": "Please select at least one input or output feature",
        "no_export": "No data to export",

        "pick_json": "Select JSON data files",
        "pick_out": "Select output folder",
        "loaded": "Loaded: {n} samples",
        "loading": "Loading data...",

        "export_title": "Export sample list",
        "export_done": "Exported to: {path}\n\nSummary:\n- Samples: {sn}\n- Input features: {xn}\n- Output features: {yn}",

        "cgan_confirm_title": "Confirm CGAN Balancing",
        "cgan_confirm_msg": "You chose CGAN balancing with target ratio {r}:1.\n\nThis may take some time.\nContinue?",

        # ModelTrainingTab
        "train_sec1": "1. Training Dataset",
        "btn_pick_dataset": "Select Training Dataset",
        "train_sec2": "2. Model Save Folder",
        "btn_pick_save": "Select Save Folder",
        "train_sec3": "3. Model Selection",
        "btn_param": "Set Parameters",
        "btn_start": "Start Training",
        "btn_open_report": "Open Report Folder",
        "log_title": "Training Log",

        "pick_dataset_title": "Select training dataset folder",
        "pick_save_title": "Select model save folder",

        "train_done": "Training finished",
        "train_fail": "Training failed",
        "train_running": "Training {m} ...",
        "train_start": "Start training {m} ...",

        "not_supported": "Unsupported model: {m}",
        "train_err": "Training error: {e}",

        # Parameter window
        "param_title": "{m} Parameters",
        "param_header": "{m} Parameter Settings",
        "param_desc": "Tune the parameters below to improve model performance\nRecommended values are general guidance; best settings depend on your data\nYou may train multiple models to compare",
        "btn_default": "Defaults",
        "btn_ok": "OK",

        # Advanced sample selection
        "adv_title": "Advanced Sample Selection",
        "search": "Search:",
        "adv_ok": "OK",
        "adv_cancel": "Cancel",
        "adv_selected": "Selected {n} samples",

        # Visualization
        "viz_warn": "Please select dataset & save folder and finish training first",
        "viz_missing": "Visualization folder does not exist:\n{path}\n\nPossible reasons:\n1. Training not finished\n2. Error during training\n3. Folder creation failed",
        "viz_manual": "Cannot open folder automatically. Please open it manually:\n\n{path}",
    },
}


def _fmt(text: str, **kw):
    try:
        return text.format(**kw)
    except Exception:
        return text


# ======================================================================================================================
# Training主窗口和标签页管理
# ======================================================================================================================
class TrainingGUI:
    """模型训练GUI - 使用独立的标签页类"""

    def __init__(self, parent, tab_style="TNotebook.Tab"):
        self.parent = parent
        self.processor = TrainingDataProcessor()

        self.lang = "zh"
        self._external_t = None

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
            self.notebook.tab(self.data_preprocessing_tab.frame, text=self._t("tab_pre"))
            self.notebook.tab(self.model_training_tab.frame, text=self._t("tab_train"))

        if hasattr(self, "status_var"):
            if self.status_var.get() in ("就绪", "Ready"):
                self.status_var.set(self._t("status_ready"))

        # 下发到子tab
        if hasattr(self, "data_preprocessing_tab"):
            self.data_preprocessing_tab.apply_language(self.lang, self._external_t, self._t)
        if hasattr(self, "model_training_tab"):
            self.model_training_tab.apply_language(self.lang, self._external_t, self._t)

    # -------------------------
    # theme & UI
    # -------------------------
    def setup_dark_theme(self):
        style = ttk.Style()

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

        style.configure("White.TLabelframe", background=self.bg_color, foreground=self.fg_color)
        style.configure("White.TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)
        style.configure("TLabelframe.Label", background=self.frame_bg, foreground=self.fg_color)

        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", background=self.frame_bg, foreground="#000000")
        style.map("TNotebook.Tab", background=[("selected", self.accent_color)])
        style.configure("TProgressbar", background=self.accent_color, troughcolor=self.frame_bg)

    def setup_ui(self):
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, columnspan=2,
                           sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.data_preprocessing_tab = DataPreprocessingTab(self.notebook, self)
        self.notebook.add(self.data_preprocessing_tab.frame, text=self._t("tab_pre"))

        self.model_training_tab = ModelTrainingTab(self.notebook, self)
        self.notebook.add(self.model_training_tab.frame, text=self._t("tab_train"))

        self.status_var = tk.StringVar(value=self._t("status_ready"))
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

    @staticmethod
    def get_default_parameters():
        # 原逻辑保持不变（省略：与你原文件一致）
        return {
            "CatBoost": {
                "iterations": {"value": 1000, "type": "int", "range": (100, 5000), "description": "树的数量"},
                "learning_rate": {"value": 0.03, "type": "float", "range": (0.001, 1.0), "description": "学习率"},
                "depth": {"value": 6, "type": "int", "range": (1, 16), "description": "树的最大深度"},
                "l2_leaf_reg": {"value": 3, "type": "float", "range": (0, 10), "description": "L2正则化系数"},
                "random_strength": {"value": 1, "type": "float", "range": (0, 10), "description": "分裂分数随机性"},
                "bagging_temperature": {"value": 0.5, "type": "float", "range": (0, 1), "description": "贝叶斯自举温度"},
                "leaf_estimation_iterations": {"value": 1, "type": "int", "range": (1, 10), "description": "叶子值估计迭代次数"},
                "rsm": {"value": 1, "type": "float", "range": (0.1, 1.0), "description": "特征采样比例"},
            },
            "LightGBM": {
                "num_leaves": {"value": 31, "type": "int", "range": (2, 256), "description": "叶子数量"},
                "learning_rate": {"value": 0.1, "type": "float", "range": (0.01, 1.0), "description": "学习率"},
                "n_estimators": {"value": 100, "type": "int", "range": (10, 1000), "description": "树的数量"},
                "max_depth": {"value": -1, "type": "int", "range": (-1, 20), "description": "树的最大深度(-1表示无限制)"},
                "subsample": {"value": 1.0, "type": "float", "range": (0.1, 1.0), "description": "样本采样比例"},
                "colsample_bytree": {"value": 1.0, "type": "float", "range": (0.1, 1.0), "description": "特征采样比例"},
                "reg_alpha": {"value": 0, "type": "float", "range": (0, 10), "description": "L1正则化系数"},
                "reg_lambda": {"value": 0, "type": "float", "range": (0, 10), "description": "L2正则化系数"},
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
                "min_child_weight": {"value": 1, "type": "int", "range": (1, 20), "description": "最小叶子节点样本权重和"},
            },
            "TabNet": {
                "n_d": {"value": 8, "type": "int", "range": (1, 64), "description": "决策层宽度"},
                "n_a": {"value": 8, "type": "int", "range": (1, 64), "description": "注意力层宽度"},
                "n_steps": {"value": 3, "type": "int", "range": (1, 10), "description": "决策步骤数"},
                "gamma": {"value": 1.3, "type": "float", "range": (1.0, 2.0), "description": "缩放系数"},
                "lambda_sparse": {"value": 1e-3, "type": "float", "range": (1e-5, 1e-1), "description": "稀疏性损失权重"},
                "learning_rate": {"value": 0.02, "type": "float", "range": (0.001, 0.1), "description": "学习率"},
                "max_epochs": {"value": 100, "type": "int", "range": (10, 500), "description": "最大训练轮数"},
            },
        }

    def update_status(self, message):
        self.status_var.set(message)

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        if hasattr(self, "model_training_tab") and hasattr(self.model_training_tab, "log_text"):
            self.model_training_tab.log_text.insert(tk.END, formatted_message)
            self.model_training_tab.log_text.see(tk.END)
            self.model_training_tab.log_text.update()

    def get_processor(self):
        return self.processor

    def get_model_parameters(self):
        return self.model_parameters

    def set_model_parameters(self, model_name, parameters):
        self.model_parameters[model_name] = parameters


# ======================================================================================================================
# 数据预处理标签页
# ======================================================================================================================
class DataPreprocessingTab:
    def __init__(self, parent, training_gui: TrainingGUI):
        self.parent = parent
        self.training_gui = training_gui
        self.frame = ttk.Frame(parent)

        self.lang = "zh"
        self._external_t = None
        self._t_local = None

        self.input_files_var = tk.StringVar(value="未选择文件")
        self.output_dir_var = tk.StringVar(value="未选择目录（将使用固定路径）")
        self.input_files = None
        self.output_dir = ""

        self.use_cgan_var = tk.BooleanVar(value=False)
        self.balance_ratio_var = tk.DoubleVar(value=1.0)

        self.sample_listbox = None
        self.input_feature_listbox = None
        self.output_feature_listbox = None

        # refs
        self.file_frame = None
        self.cgan_frame = None
        self.selection_frame = None
        self.ratio_help = None
        self.balance_stats_var = tk.StringVar(value="")
        self.ratio_combobox = None

        self.btn_pick_data = None
        self.btn_pick_out = None
        self.btn_fixed_out = None
        self.btn_load = None

        self.lbl_sample_sel = None
        self.lbl_x = None
        self.lbl_y = None

        self.btn_export = None
        self.generate_button = None

        self.setup_ui()

    def apply_language(self, lang: str, t_func=None, t_local=None):
        self.lang = lang or "zh"
        self._external_t = t_func
        self._t_local = t_local

        if self.file_frame is not None:
            self.file_frame.configure(text=self._t("sec1"))
        if self.cgan_frame is not None:
            self.cgan_frame.configure(text=self._t("sec2"))
        if self.selection_frame is not None:
            self.selection_frame.configure(text=self._t("sec3"))

        if self.btn_pick_data is not None:
            self.btn_pick_data.configure(text=self._t("btn_pick_data"))
        if self.btn_pick_out is not None:
            self.btn_pick_out.configure(text=self._t("btn_pick_out"))
        if self.btn_fixed_out is not None:
            self.btn_fixed_out.configure(text=self._t("btn_fixed_out"))
        if self.btn_load is not None:
            self.btn_load.configure(text=self._t("btn_load"))

        if hasattr(self, "cgan_check") and self.cgan_check is not None:
            self.cgan_check.configure(text=self._t("use_cgan"))
        if hasattr(self, "ratio_label") and self.ratio_label is not None:
            self.ratio_label.configure(text=self._t("ratio_lbl"))
        if self.ratio_help is not None:
            self.ratio_help.configure(text=self._t("ratio_help"))

        if self.lbl_sample_sel is not None:
            self.lbl_sample_sel.configure(text=self._t("sample_sel"))
        if self.lbl_x is not None:
            self.lbl_x.configure(text=self._t("xfeat"))
        if self.lbl_y is not None:
            self.lbl_y.configure(text=self._t("yfeat"))

        # 按钮“全选/全不选/高级选项”等在创建时就绑定文字，这里简单刷新常用按钮（存在则更新）
        for attr, key in [
            ("btn_sample_all", "all"), ("btn_sample_none", "none"), ("btn_sample_adv", "adv"),
            ("btn_x_all", "all"), ("btn_x_none", "none"),
            ("btn_y_all", "all"), ("btn_y_none", "none"),
        ]:
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.configure(text=self._t(key))

        if self.btn_export is not None:
            self.btn_export.configure(text=self._t("btn_export"))
        if self.generate_button is not None:
            self.generate_button.configure(text=self._t("btn_gen"))

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

    def setup_ui(self):
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=1)

        # 选择数据区域
        self.file_frame = ttk.LabelFrame(self.frame, text=self.training_gui._t("sec1"),
                                         padding="10", style="White.TLabelframe")
        self.file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.file_frame.columnconfigure(1, weight=1)

        self.btn_pick_data = ttk.Button(self.file_frame, text=self.training_gui._t("btn_pick_data"),
                                        command=self.select_input_files)
        self.btn_pick_data.grid(row=0, column=0, padx=(0, 10))
        ttk.Label(self.file_frame, textvariable=self.input_files_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

        btn_bar = ttk.Frame(self.file_frame)
        btn_bar.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))

        self.btn_pick_out = ttk.Button(btn_bar, text=self.training_gui._t("btn_pick_out"),
                                       command=self.select_output_dir)
        self.btn_pick_out.pack(side=tk.LEFT)

        self.btn_fixed_out = ttk.Button(btn_bar, text=self.training_gui._t("btn_fixed_out"),
                                        command=self.use_fixed_output_dir)
        self.btn_fixed_out.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(self.file_frame, textvariable=self.output_dir_var).grid(row=1, column=1,
                                                                          sticky=(tk.W, tk.E), pady=(10, 0))

        self.btn_load = ttk.Button(self.file_frame, text=self.training_gui._t("btn_load"),
                                   command=self.load_and_process_data)
        self.btn_load.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        # CGAN 数据平衡选项
        self.cgan_frame = ttk.LabelFrame(self.frame, text=self.training_gui._t("sec2"),
                                         padding="10", style="White.TLabelframe")
        self.cgan_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.cgan_frame.columnconfigure(1, weight=1)

        self.cgan_check = ttk.Checkbutton(
            self.cgan_frame,
            text=self.training_gui._t("use_cgan"),
            variable=self.use_cgan_var,
            command=self.toggle_cgan_options
        )
        self.cgan_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ratio_frame = ttk.Frame(self.cgan_frame)
        ratio_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.ratio_label = ttk.Label(ratio_frame, text=self.training_gui._t("ratio_lbl"))
        self.ratio_label.pack(side=tk.LEFT, padx=(0, 10))

        self.ratio_combobox = ttk.Combobox(
            ratio_frame,
            textvariable=self.balance_ratio_var,
            values=[0.5, 0.8, 1.0, 1.2, 1.5],
            state="readonly",
            width=10
        )
        self.ratio_combobox.pack(side=tk.LEFT)
        self.ratio_combobox.set(1.0)

        self.ratio_help = ttk.Label(ratio_frame, text=self.training_gui._t("ratio_help"), foreground="gray")
        self.ratio_help.pack(side=tk.LEFT, padx=(10, 0))

        self.ratio_combobox.configure(state="disabled")

        stats_label = ttk.Label(self.cgan_frame, textvariable=self.balance_stats_var, foreground="yellow")
        stats_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        # 样本和特征选择
        self.selection_frame = ttk.LabelFrame(self.frame, text=self.training_gui._t("sec3"),
                                              padding="10", style="White.TLabelframe")
        self.selection_frame.grid(row=2, column=0, columnspan=2,
                                  sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.selection_frame.columnconfigure(0, weight=1)
        self.selection_frame.columnconfigure(1, weight=1)
        self.selection_frame.rowconfigure(0, weight=1)

        # 样本选择
        sample_frame = ttk.Frame(self.selection_frame)
        sample_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        self.lbl_sample_sel = ttk.Label(sample_frame, text=self.training_gui._t("sample_sel"))
        self.lbl_sample_sel.grid(row=0, column=0, sticky=tk.W)

        self.btn_sample_all = ttk.Button(sample_frame, text=self.training_gui._t("all"),
                                         command=self.select_all_samples)
        self.btn_sample_all.grid(row=0, column=1, padx=(5, 5))

        self.btn_sample_none = ttk.Button(sample_frame, text=self.training_gui._t("none"),
                                          command=self.clear_all_samples)
        self.btn_sample_none.grid(row=0, column=2, padx=(5, 5))

        self.btn_sample_adv = ttk.Button(sample_frame, text=self.training_gui._t("adv"),
                                         command=self.advanced_sample_selection)
        self.btn_sample_adv.grid(row=0, column=3, padx=(5, 0))

        self.sample_listbox = tk.Listbox(sample_frame, selectmode=tk.MULTIPLE, height=15,
                                         exportselection=False, width=120)
        self.sample_listbox.grid(row=1, column=0, columnspan=4,
                                 sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        self.sample_listbox.bind("<<ListboxSelect>>", self.on_sample_select)

        sample_scrollbar = ttk.Scrollbar(sample_frame, orient=tk.VERTICAL, command=self.sample_listbox.yview)
        sample_scrollbar.grid(row=1, column=4, sticky=(tk.N, tk.S), pady=(5, 0))
        self.sample_listbox.configure(yscrollcommand=sample_scrollbar.set)

        sample_hscrollbar = ttk.Scrollbar(sample_frame, orient=tk.HORIZONTAL, command=self.sample_listbox.xview)
        sample_hscrollbar.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E))
        self.sample_listbox.configure(xscrollcommand=sample_hscrollbar.set)

        sample_frame.rowconfigure(1, weight=1)
        sample_frame.columnconfigure(0, weight=1)

        # 特征选择
        feature_frame = ttk.Frame(self.selection_frame)
        feature_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        feature_frame.columnconfigure(0, weight=1)
        feature_frame.columnconfigure(1, weight=1)

        # 输入特征
        input_feature_frame = ttk.Frame(feature_frame)
        input_feature_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        input_feature_header = ttk.Frame(input_feature_frame)
        input_feature_header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

        self.lbl_x = ttk.Label(input_feature_header, text=self.training_gui._t("xfeat"))
        self.lbl_x.grid(row=0, column=0, sticky=tk.W)

        self.btn_x_all = ttk.Button(input_feature_header, text=self.training_gui._t("all"),
                                    command=lambda: self.select_all_features("input"))
        self.btn_x_all.grid(row=0, column=1, padx=(10, 5))

        self.btn_x_none = ttk.Button(input_feature_header, text=self.training_gui._t("none"),
                                     command=lambda: self.clear_all_features("input"))
        self.btn_x_none.grid(row=0, column=2, padx=(5, 0))

        self.input_feature_listbox = tk.Listbox(input_feature_frame, selectmode=tk.MULTIPLE,
                                                height=15, exportselection=False)
        self.input_feature_listbox.grid(row=1, column=0, columnspan=2,
                                        sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        self.input_feature_listbox.bind("<<ListboxSelect>>", self.on_input_feature_select)

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

        self.lbl_y = ttk.Label(output_feature_header, text=self.training_gui._t("yfeat"))
        self.lbl_y.grid(row=0, column=0, sticky=tk.W)

        self.btn_y_all = ttk.Button(output_feature_header, text=self.training_gui._t("all"),
                                    command=lambda: self.select_all_features("output"))
        self.btn_y_all.grid(row=0, column=1, padx=(10, 5))

        self.btn_y_none = ttk.Button(output_feature_header, text=self.training_gui._t("none"),
                                     command=lambda: self.clear_all_features("output"))
        self.btn_y_none.grid(row=0, column=2, padx=(5, 0))

        self.output_feature_listbox = tk.Listbox(output_feature_frame, selectmode=tk.MULTIPLE,
                                                 height=15, exportselection=False)
        self.output_feature_listbox.grid(row=1, column=0, columnspan=2,
                                         sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        self.output_feature_listbox.bind("<<ListboxSelect>>", self.on_output_feature_select)

        output_feature_scrollbar = ttk.Scrollbar(output_feature_frame, orient=tk.VERTICAL,
                                                 command=self.output_feature_listbox.yview)
        output_feature_scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S), pady=(5, 0))
        self.output_feature_listbox.configure(yscrollcommand=output_feature_scrollbar.set)

        output_feature_frame.rowconfigure(1, weight=1)
        output_feature_frame.columnconfigure(0, weight=1)

        # 导出/生成
        button_frame = ttk.Frame(self.selection_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.btn_export = ttk.Button(button_frame, text=self.training_gui._t("btn_export"),
                                     command=self.export_sample_list)
        self.btn_export.grid(row=0, column=0, padx=(0, 10))

        self.generate_button = ttk.Button(button_frame, text=self.training_gui._t("btn_gen"),
                                          command=self.generate_training_data)
        self.generate_button.grid(row=0, column=1)

    # === 以下方法：保留原业务逻辑，仅替换 messagebox 文案为 i18n ===
    def on_sample_select(self, event):
        selected_indices = self.sample_listbox.curselection()
        processor = self.training_gui.get_processor()
        processor.selected_samples = set(selected_indices)

    def on_input_feature_select(self, event):
        selected_indices = self.input_feature_listbox.curselection()
        selected_features = [self.input_feature_listbox.get(i) for i in selected_indices]
        processor = self.training_gui.get_processor()
        processor.selected_input_features = set(selected_features)

    def on_output_feature_select(self, event):
        selected_indices = self.output_feature_listbox.curselection()
        selected_features = [self.output_feature_listbox.get(i) for i in selected_indices]
        processor = self.training_gui.get_processor()
        processor.selected_output_features = set(selected_features)

    def select_input_files(self):
        files = filedialog.askopenfilenames(
            title=self.training_gui._t("pick_json"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if files:
            self.input_files_var.set("; ".join([os.path.basename(f) for f in files]))
            self.input_files = files

    def select_output_dir(self):
        directory = filedialog.askdirectory(title=self.training_gui._t("pick_out"))
        if directory:
            self.output_dir_var.set(directory)
            self.output_dir = directory

    def use_fixed_output_dir(self):
        self.output_dir = ""
        self.output_dir_var.set("未选择目录（将使用固定路径）" if self.lang == "zh"
                                else "No folder selected (use fixed path)")
        messagebox.showinfo(self.training_gui._t("out_reset_title"), self.training_gui._t("out_reset_msg"))

    def toggle_cgan_options(self):
        if self.use_cgan_var.get():
            self.ratio_combobox.configure(state="readonly")
            self.update_balance_stats()
        else:
            self.ratio_combobox.configure(state="disabled")
            self.balance_stats_var.set("")

    def update_balance_stats(self):
        processor = self.training_gui.get_processor()
        if processor.processed_samples is None:
            return
        if "PA Status Repair Info" not in processor.processed_samples.columns:
            return

        pa_counts = processor.processed_samples["PA Status Repair Info"].value_counts()
        normal_count = 0
        abnormal_count = 0
        for status, count in pa_counts.items():
            status_str = str(status)
            if "Normal" in status_str:
                normal_count += count
            else:
                abnormal_count += count

        if abnormal_count > 0:
            current_ratio = normal_count / abnormal_count
            target_ratio = self.balance_ratio_var.get()
            samples_to_generate = max(0, int(abnormal_count * target_ratio) - normal_count)
            if self.lang == "zh":
                stats_text = (f"当前分布: 正常={normal_count}, 异常={abnormal_count} (比例={current_ratio:.2f}:1)\n"
                              f"目标比例: {target_ratio}:1 \n"
                              f"需生成: {samples_to_generate} 个正常样本")
            else:
                stats_text = (f"Current: Normal={normal_count}, Abnormal={abnormal_count} (ratio={current_ratio:.2f}:1)\n"
                              f"Target ratio: {target_ratio}:1\n"
                              f"To generate: {samples_to_generate} normal samples")
        else:
            stats_text = "未检测到异常样本" if self.lang == "zh" else "No abnormal samples detected"
        self.balance_stats_var.set(stats_text)

    def load_and_process_data(self):
        if not hasattr(self, "input_files") or not self.input_files:
            messagebox.showerror(self.training_gui._t("err"), self.training_gui._t("need_input"))
            return

        self.training_gui.update_status(self.training_gui._t("loading"))

        def process_data():
            try:
                processor = self.training_gui.get_processor()
                processor.raw_data = processor.load_data(self.input_files)
                processor.processed_samples = processor.extract_all_features(processor.raw_data)

                self.frame.after(0, self.update_sample_feature_lists)
                self.frame.after(0, lambda: self.training_gui.update_status(
                    self.training_gui._t("loaded", n=len(processor.processed_samples))
                ))

                if self.use_cgan_var.get():
                    self.frame.after(0, self.update_balance_stats)

            except Exception as e:
                self.frame.after(0, lambda: messagebox.showerror(self.training_gui._t("err"), str(e)))
                self.frame.after(0, lambda: self.training_gui.update_status(self.training_gui._t("train_fail")))

        threading.Thread(target=process_data, daemon=True).start()

    def update_sample_feature_lists(self):
        processor = self.training_gui.get_processor()

        self.sample_listbox.delete(0, tk.END)
        for idx, row in processor.processed_samples.iterrows():
            serial = row.get("Serial", f"sample_{idx}")
            product_name = row.get("ProductName", "Unknown")
            timestamp = row.get("Timestamp", "Unknown")
            repair_info = row.get("PA Status Repair Info", "Unknown")
            if repair_info in [None, "", np.nan]:
                repair_info = "Unknown"
            repair_detail = row.get("Repair Info Details", "")
            if repair_detail in [None, "", np.nan]:
                repair_detail = ""

            display_text = (f"{idx}: {serial} \n"
                            f"{product_name} \n"
                            f"{timestamp} \n"
                            f"{repair_info} \n"
                            f" {repair_detail}")
            self.sample_listbox.insert(tk.END, display_text)

        self.select_all_samples()

        self.input_feature_listbox.delete(0, tk.END)
        input_features = processor.numeric_features + processor.categorical_features
        for feat in input_features:
            self.input_feature_listbox.insert(tk.END, feat)

        self.output_feature_listbox.delete(0, tk.END)
        for feat in processor.output_features:
            self.output_feature_listbox.insert(tk.END, feat)

        self.select_all_features("input")
        self.select_all_features("output")

    def select_all_samples(self):
        self.sample_listbox.select_set(0, tk.END)
        processor = self.training_gui.get_processor()
        processor.selected_samples = set(range(self.sample_listbox.size()))

    def clear_all_samples(self):
        self.sample_listbox.select_clear(0, tk.END)
        processor = self.training_gui.get_processor()
        processor.selected_samples.clear()

    def advanced_sample_selection(self):
        processor = self.training_gui.get_processor()
        if processor.processed_samples is None:
            messagebox.showwarning(self.training_gui._t("warn"), self.training_gui._t("need_load"))
            return

        selection_window = tk.Toplevel(self.frame)
        selection_window.title(self.training_gui._t("adv_title"))
        selection_window.geometry("1000x700")
        selection_window.transient(self.frame)
        selection_window.grab_set()

        main_frame = ttk.Frame(selection_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text=self.training_gui._t("search")).pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        selection_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=20)
        selection_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=selection_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        selection_listbox.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text=self.training_gui._t("all"),
                   command=lambda: self.select_all_in_advanced(selection_listbox)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text=self.training_gui._t("none"),
                   command=lambda: selection_listbox.select_clear(0, tk.END)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text=self.training_gui._t("adv_ok"),
                   command=lambda: self.apply_advanced_selection(selection_window, selection_listbox)).pack(
            side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text=self.training_gui._t("adv_cancel"),
                   command=selection_window.destroy).pack(side=tk.RIGHT, padx=(0, 5))

        self.serial_to_indices = {}
        self.populate_advanced_selection(selection_listbox)

        search_entry.bind("<KeyRelease>",
                          lambda e: self.filter_samples(selection_listbox, search_var.get()))

    # 下面的高级选择/导出/生成训练数据集逻辑与你原文件一致，仅替换 messagebox 文案为 i18n
    def populate_advanced_selection(self, listbox):
        processor = self.training_gui.get_processor()
        listbox.delete(0, tk.END)
        product_groups = {}

        for idx, row in processor.processed_samples.iterrows():
            product_name = row.get("ProductName", "Unknown")
            serial = row.get("Serial", f"sample_{idx}")
            repair_info = row.get("PA Status Repair Info", "Unknown")
            repair_detail = row.get("Repair Info Details", "")

            self.serial_to_indices.setdefault(serial, []).append(idx)
            product_groups.setdefault(product_name, {})
            if serial not in product_groups[product_name]:
                product_groups[product_name][serial] = {
                    "repair_info": repair_info,
                    "repair_detail": repair_detail,
                    "count": 0
                }
            product_groups[product_name][serial]["count"] += 1

        for product in sorted(product_groups.keys()):
            listbox.insert(tk.END, f"--- {product} ---")
            listbox.itemconfig(tk.END, {"fg": "gray", "selectbackground": "white"})
            for serial, info in product_groups[product].items():
                if self.lang == "zh":
                    display_text = f" {serial} \n{info['repair_info']} \n{info['repair_detail']} \n({info['count']} 个样本)"
                else:
                    display_text = f" {serial} \n{info['repair_info']} \n{info['repair_detail']} \n({info['count']} samples)"
                listbox.insert(tk.END, display_text)
                listbox.itemconfig(tk.END, {"bg": "white"})

    def filter_samples(self, listbox, search_text):
        self.populate_advanced_selection(listbox)
        if not search_text.strip():
            return
        search_lower = search_text.lower()
        keep = []
        for i in range(listbox.size()):
            item = listbox.get(i)
            if item.startswith("---"):
                continue
            if search_lower in item.lower():
                keep.append(i)
        for i in range(listbox.size()):
            if i not in keep and not listbox.get(i).startswith("---"):
                listbox.itemconfig(i, {"fg": "lightgray"})

    @staticmethod
    def select_all_in_advanced(listbox):
        for i in range(listbox.size()):
            if not listbox.get(i).startswith("---"):
                listbox.selection_set(i)

    def apply_advanced_selection(self, window, listbox):
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(self.training_gui._t("warn"),
                                   self.training_gui._t("need_sample"))
            return

        selected_serials = set()
        for i in selected_indices:
            item = listbox.get(i)
            if item.startswith("---"):
                continue
            serial = item.split(" \n")[0].strip()
            selected_serials.add(serial)

        main_selected = []
        for serial in selected_serials:
            main_selected.extend(self.serial_to_indices.get(serial, []))

        self.sample_listbox.select_clear(0, tk.END)
        for idx in main_selected:
            self.sample_listbox.selection_set(idx)

        processor = self.training_gui.get_processor()
        processor.selected_samples = set(main_selected)
        window.destroy()

        messagebox.showinfo(self.training_gui._t("ok"),
                            self.training_gui._t("adv_selected", n=len(main_selected)))

    def select_all_features(self, feature_type):
        processor = self.training_gui.get_processor()
        if feature_type == "input":
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
        processor = self.training_gui.get_processor()
        if feature_type == "input":
            listbox = self.input_feature_listbox
            feature_set = processor.selected_input_features
        else:
            listbox = self.output_feature_listbox
            feature_set = processor.selected_output_features
        listbox.select_clear(0, tk.END)
        feature_set.clear()

    def export_sample_list(self):
        processor = self.training_gui.get_processor()
        if processor.processed_samples is None:
            messagebox.showerror(self.training_gui._t("err"), self.training_gui._t("no_export"))
            return
        if not processor.selected_samples:
            messagebox.showerror(self.training_gui._t("err"), self.training_gui._t("need_sample"))
            return
        if not processor.selected_input_features and not processor.selected_output_features:
            messagebox.showerror(self.training_gui._t("err"), self.training_gui._t("need_feat_any"))
            return

        file_path = filedialog.asksaveasfilename(
            title=self.training_gui._t("export_title"),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            try:
                selected_indices = list(processor.selected_samples)
                selected_input = list(processor.selected_input_features)
                selected_output = list(processor.selected_output_features)

                base_columns = ['ProductName', 'Serial', 'Timestamp', 'PA Status Repair Info', 'Repair Info Details']
                all_columns = base_columns + selected_input + selected_output
                filtered = processor.processed_samples.loc[selected_indices, all_columns].copy()
                filtered.insert(0, 'SampleIndex', filtered.index)

                numeric_columns = [col for col in filtered.columns if col in processor.numeric_features]
                for col in numeric_columns:
                    if col in filtered.columns:
                        inf_mask = filtered[col] == np.inf
                        neg_inf_mask = filtered[col] == -np.inf
                        nan_mask = filtered[col].isna()
                        col_data = filtered[col].copy()
                        col_data[inf_mask] = 1000
                        col_data[neg_inf_mask] = -1000
                        col_data[nan_mask] = np.nan
                        filtered[col] = col_data

                filtered.to_csv(file_path, index=False, encoding='utf-8-sig', na_rep='')

                messagebox.showinfo(self.training_gui._t("ok"),
                                    self.training_gui._t("export_done",
                                                         path=file_path,
                                                         sn=len(filtered),
                                                         xn=len(selected_input),
                                                         yn=len(selected_output)))
            except Exception as e:
                messagebox.showerror(self.training_gui._t("err"), str(e))

    def generate_training_data(self):
        processor = self.training_gui.get_processor()

        if not processor.selected_samples:
            messagebox.showerror(self.training_gui._t("err"), self.training_gui._t("need_sample"))
            return
        if not processor.selected_input_features:
            messagebox.showerror(self.training_gui._t("err"), self.training_gui._t("need_x"))
            return
        if not processor.selected_output_features:
            messagebox.showerror(self.training_gui._t("err"), self.training_gui._t("need_y"))
            return

        use_cgan = self.use_cgan_var.get()
        balance_ratio = self.balance_ratio_var.get()

        if use_cgan:
            confirm = messagebox.askyesno(
                self.training_gui._t("cgan_confirm_title"),
                self.training_gui._t("cgan_confirm_msg", r=balance_ratio)
            )
            if not confirm:
                return

        self.training_gui.update_status("正在生成训练数据集..." if self.lang == "zh" else "Generating training dataset...")

        output_dir_to_use = self.output_dir if isinstance(self.output_dir, str) else ""
        output_dir_to_use = output_dir_to_use.strip()

        def generate_data():
            success, message = processor.process_selected_data(
                output_dir_to_use,
                use_cgan_balance=use_cgan,
                balance_ratio=balance_ratio
            )
            self.frame.after(0, lambda: self.training_gui.update_status(
                "生成完成" if success else "生成失败" if self.lang == "zh" else ("Done" if success else "Failed")
            ))
            if success:
                self.frame.after(0, lambda: messagebox.showinfo(self.training_gui._t("ok"), message))
            else:
                self.frame.after(0, lambda: messagebox.showerror(self.training_gui._t("err"), message))

        threading.Thread(target=generate_data, daemon=True).start()


# ======================================================================================================================
# 模型训练标签页
# ======================================================================================================================
class ModelTrainingTab:
    def __init__(self, parent, training_gui: TrainingGUI):
        self.parent = parent
        self.training_gui = training_gui
        self.frame = ttk.Frame(parent)

        self.lang = "zh"
        self._external_t = None
        self._t_local = None

        self.training_dataset_path = None
        self.model_save_path = None

        self.training_dataset_var = tk.StringVar(value="未选择数据")
        self.model_save_path_var = tk.StringVar(value="未选择路径")
        self.model_var = tk.StringVar(value="XGBoost")

        self.progress_var = tk.DoubleVar()
        self.progress_bar = None
        self.log_text = None

        # refs
        self.dataset_frame = None
        self.save_frame = None
        self.model_frame = None
        self.log_frame = None
        self.btn_pick_dataset = None
        self.btn_pick_save = None
        self.btn_param = None
        self.btn_start = None
        self.btn_open_report = None

        self.setup_ui()

    def apply_language(self, lang: str, t_func=None, t_local=None):
        self.lang = lang or "zh"
        self._external_t = t_func
        self._t_local = t_local

        if self.dataset_frame is not None:
            self.dataset_frame.configure(text=self._t("train_sec1"))
        if self.save_frame is not None:
            self.save_frame.configure(text=self._t("train_sec2"))
        if self.model_frame is not None:
            self.model_frame.configure(text=self._t("train_sec3"))
        if self.log_frame is not None:
            self.log_frame.configure(text=self._t("log_title"))

        if self.btn_pick_dataset is not None:
            self.btn_pick_dataset.configure(text=self._t("btn_pick_dataset"))
        if self.btn_pick_save is not None:
            self.btn_pick_save.configure(text=self._t("btn_pick_save"))
        if self.btn_param is not None:
            self.btn_param.configure(text=self._t("btn_param"))
        if self.btn_start is not None:
            self.btn_start.configure(text=self._t("btn_start"))
        if self.btn_open_report is not None:
            self.btn_open_report.configure(text=self._t("btn_open_report"))

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

    def setup_ui(self):
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(3, weight=1)

        self.dataset_frame = ttk.LabelFrame(self.frame, text=self.training_gui._t("train_sec1"),
                                            padding="10", style="White.TLabelframe")
        self.dataset_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.dataset_frame.columnconfigure(1, weight=1)

        self.btn_pick_dataset = ttk.Button(self.dataset_frame, text=self.training_gui._t("btn_pick_dataset"),
                                           command=self.select_training_dataset)
        self.btn_pick_dataset.grid(row=0, column=0, padx=(0, 10))
        ttk.Label(self.dataset_frame, textvariable=self.training_dataset_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

        self.save_frame = ttk.LabelFrame(self.frame, text=self.training_gui._t("train_sec2"),
                                         padding="10", style="White.TLabelframe")
        self.save_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.save_frame.columnconfigure(1, weight=1)

        self.btn_pick_save = ttk.Button(self.save_frame, text=self.training_gui._t("btn_pick_save"),
                                        command=self.select_model_save_path)
        self.btn_pick_save.grid(row=0, column=0, padx=(0, 10))
        ttk.Label(self.save_frame, textvariable=self.model_save_path_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

        self.model_frame = ttk.LabelFrame(self.frame, text=self.training_gui._t("train_sec3"),
                                          padding="10", style="White.TLabelframe")
        self.model_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        models = ["CatBoost", "LightGBM", "XGBoost", "TabNet"]
        for i, model in enumerate(models):
            ttk.Radiobutton(self.model_frame, text=model, variable=self.model_var, value=model)\
                .grid(row=0, column=i, padx=(10, 10), pady=5)

        self.btn_param = ttk.Button(self.model_frame, text=self.training_gui._t("btn_param"),
                                    command=self.open_parameter_settings)
        self.btn_param.grid(row=0, column=len(models), padx=(10, 0))

        training_control_frame = ttk.Frame(self.frame)
        training_control_frame.grid(row=3, column=0, columnspan=2,
                                    sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.btn_start = ttk.Button(training_control_frame, text=self.training_gui._t("btn_start"),
                                    command=self.start_training)
        self.btn_start.grid(row=0, column=0, padx=(0, 10))

        self.progress_bar = ttk.Progressbar(training_control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        training_control_frame.columnconfigure(1, weight=1)

        self.btn_open_report = ttk.Button(training_control_frame, text=self.training_gui._t("btn_open_report"),
                                          command=self.open_visualization_dir)
        self.btn_open_report.grid(row=0, column=3, padx=(10, 0))

        self.log_frame = ttk.LabelFrame(self.frame, text=self.training_gui._t("log_title"),
                                        padding="10", style="White.TLabelframe")
        self.log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, height=25)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def select_training_dataset(self):
        dataset_path = filedialog.askdirectory(title=self.training_gui._t("pick_dataset_title"))
        if dataset_path:
            self.training_dataset_var.set(dataset_path)
            self.training_dataset_path = dataset_path
            self.training_gui.log_message(
                f"{'已选择训练数据集' if self.lang=='zh' else 'Selected dataset'}: {dataset_path}"
            )

    def select_model_save_path(self):
        save_path = filedialog.askdirectory(title=self.training_gui._t("pick_save_title"))
        if save_path:
            self.model_save_path_var.set(save_path)
            self.model_save_path = save_path
            self.training_gui.log_message(
                f"{'模型将保存到' if self.lang=='zh' else 'Model will be saved to'}: {save_path}"
            )

    def open_parameter_settings(self):
        selected_model = self.model_var.get()
        param_window = tk.Toplevel(self.frame)
        param_window.title(self.training_gui._t("param_title", m=selected_model))
        param_window.geometry("700x700")
        param_window.transient(self.frame)
        param_window.grab_set()

        main_frame = ttk.Frame(param_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame,
                                text=self.training_gui._t("param_header", m=selected_model),
                                font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))

        description_label = ttk.Label(main_frame,
                                      text=self.training_gui._t("param_desc"),
                                      wraplength=550, justify=tk.LEFT)
        description_label.pack(pady=(0, 10))

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        model_params = self.training_gui.get_model_parameters().get(selected_model, {})
        param_vars = {}
        for param_name, param_config in model_params.items():
            pf = ttk.Frame(scrollable_frame)
            pf.pack(fill=tk.X, pady=5)

            ttk.Label(pf, text=f"{param_name}:", width=20).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            ttk.Label(pf, text=param_config["description"], foreground="gray", wraplength=300)\
                .grid(row=0, column=1, sticky=tk.W)

            if param_config["type"] in ["int", "float"]:
                var = tk.StringVar(value=str(param_config["value"]))
                entry = ttk.Entry(pf, textvariable=var, foreground="#000000")
                entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
                min_val, max_val = param_config["range"]
                ttk.Label(pf, text=f"Range: {min_val} - {max_val}", foreground="white")\
                    .grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
                param_vars[param_name] = var

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text=self.training_gui._t("btn_default"),
                   command=lambda: self.reset_parameters(param_vars, selected_model)).pack(side=tk.LEFT)
        ttk.Button(button_frame, text=self.training_gui._t("cancel"), width=10,
                   command=param_window.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text=self.training_gui._t("btn_ok"), width=10,
                   command=lambda: self.save_parameters(param_vars, selected_model, param_window)).pack(side=tk.RIGHT)

        scrollable_frame.columnconfigure(1, weight=1)

    def reset_parameters(self, param_vars, model_name):
        model_params = self.training_gui.get_model_parameters().get(model_name, {})
        for pn, pc in model_params.items():
            if pn in param_vars:
                param_vars[pn].set(str(pc["value"]))

    def save_parameters(self, param_vars, model_name, window):
        try:
            model_params = self.training_gui.get_model_parameters().get(model_name, {})
            updated = {}
            for pn, var in param_vars.items():
                pc = model_params[pn]
                value = var.get()

                if pc["type"] == "int":
                    try:
                        value = int(value)
                        mn, mx = pc["range"]
                        if not (mn <= value <= mx):
                            raise ValueError(f"Value must be between {mn} and {mx}")
                    except ValueError as e:
                        messagebox.showerror(self.training_gui._t("err"), f"{pn}: {str(e)}")
                        return
                elif pc["type"] == "float":
                    try:
                        value = float(value)
                        mn, mx = pc["range"]
                        if not (mn <= value <= mx):
                            raise ValueError(f"Value must be between {mn} and {mx}")
                    except ValueError as e:
                        messagebox.showerror(self.training_gui._t("err"), f"{pn}: {str(e)}")
                        return
                updated[pn] = value

            for pn, value in updated.items():
                self.training_gui.get_model_parameters()[model_name][pn]["value"] = value

            self.training_gui.log_message(f"{model_name} parameters updated")
            window.destroy()

        except Exception as e:
            messagebox.showerror(self.training_gui._t("err"), str(e))

    def start_training(self):
        if not self.training_dataset_path:
            messagebox.showerror(self.training_gui._t("err"),
                                 "请选择训练数据集" if self.lang == "zh" else "Please select dataset")
            return
        if not self.model_save_path:
            messagebox.showerror(self.training_gui._t("err"),
                                 "请选择模型保存路径" if self.lang == "zh" else "Please select save folder")
            return

        selected_model = self.model_var.get()
        self.training_gui.log_message(self.training_gui._t("train_start", m=selected_model))
        self.training_gui.update_status(self.training_gui._t("train_running", m=selected_model))

        def run_training():
            try:
                if selected_model == "CatBoost":
                    success, message = self.train_catboost()
                elif selected_model == "LightGBM":
                    success, message = self.train_lightgbm()
                elif selected_model == "XGBoost":
                    success, message = self.train_xgboost()
                elif selected_model == "TabNet":
                    success, message = self.train_tabnet()
                else:
                    success, message = False, self.training_gui._t("not_supported", m=selected_model)
                self.frame.after(0, lambda: self.training_completed(success, message))
            except Exception as e:
                self.frame.after(0, lambda: self.training_completed(False, self.training_gui._t("train_err", e=str(e))))

        threading.Thread(target=run_training, daemon=True).start()

    def training_completed(self, success, message):
        if success:
            self.training_gui.log_message(f"{self.training_gui._t('train_done')}: {message}")
            self.training_gui.update_status(self.training_gui._t("train_done"))
            messagebox.showinfo(self.training_gui._t("ok"), message)
        else:
            self.training_gui.log_message(f"{self.training_gui._t('train_fail')}: {message}")
            self.training_gui.update_status(self.training_gui._t("train_fail"))
            messagebox.showerror(self.training_gui._t("err"), message)
        self.progress_var.set(0)

    def update_progress(self, value):
        self.progress_var.set(value)
        self.frame.update()

    # 原训练方法保持：只略改日志/错误消息
    def train_catboost(self):
        from tools.app.services.model_training.models.catboost.catboost import train
        cb_params = {k: v["value"] for k, v in self.training_gui.get_model_parameters().get("CatBoost", {}).items()}
        return train(
            dataset_path=self.training_dataset_path,
            model_save_path=self.model_save_path,
            progress_callback=self.update_progress,
            log_callback=lambda msg: self.training_gui.log_message(msg),
            custom_params=cb_params
        )

    def train_lightgbm(self):
        from tools.app.services.model_training.models.lightgbm.lightgbm import train
        lgb_params = {k: v["value"] for k, v in self.training_gui.get_model_parameters().get("LightGBM", {}).items()}
        return train(
            dataset_path=self.training_dataset_path,
            model_save_path=self.model_save_path,
            progress_callback=self.update_progress,
            log_callback=lambda msg: self.training_gui.log_message(msg),
            custom_params=lgb_params
        )

    def train_xgboost(self):
        from tools.app.services.model_training.models.xgboost.xgboost import train
        xgb_params = {k: v["value"] for k, v in self.training_gui.get_model_parameters().get("XGBoost", {}).items()}
        return train(
            dataset_path=self.training_dataset_path,
            model_save_path=self.model_save_path,
            progress_callback=self.update_progress,
            log_callback=lambda msg: self.training_gui.log_message(msg),
            custom_params=xgb_params
        )

    def train_tabnet(self):
        from tools.app.services.model_training.models.tabnet.tabnet import train
        tnt_params = {k: v["value"] for k, v in self.training_gui.get_model_parameters().get("TabNet", {}).items()}
        return train(
            dataset_path=self.training_dataset_path,
            model_save_path=self.model_save_path,
            progress_callback=self.update_progress,
            log_callback=lambda msg: self.training_gui.log_message(msg),
            custom_params=tnt_params
        )

    def open_visualization_dir(self):
        if not self.model_save_path:
            messagebox.showwarning(self.training_gui._t("warn"), self.training_gui._t("viz_warn"))
            return

        visualization_dir = os.path.join(self.model_save_path, "xgboost_visualizations")
        if not os.path.exists(visualization_dir):
            messagebox.showwarning(self.training_gui._t("warn"),
                                   self.training_gui._t("viz_missing", path=visualization_dir))
            return

        try:
            normalized_path = os.path.normpath(visualization_dir)
            if os.name == "nt":
                os.system(f'explorer "{normalized_path}"')
            elif os.name == "posix":
                if sys.platform == "darwin":
                    os.system(f'open "{normalized_path}"')
                else:
                    os.system(f'xdg-open "{normalized_path}"')
        except Exception:
            messagebox.showinfo(self.training_gui._t("confirm"),
                                self.training_gui._t("viz_manual", path=visualization_dir))


def main():
    root = tk.Tk()
    root.title("Training")
    app = TrainingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()