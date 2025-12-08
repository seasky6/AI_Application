import json
import os
import numpy as np
import pandas as pd
import random
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.base import BaseEstimator, TransformerMixin
from pathlib import Path

# ==== 可选：GAN 开关与参数 ====
USE_GAN = True                 # 需要时置 True；不想用就 False
GAN_EPOCHS = 70               # 每类训练轮数
GAN_BATCH_SIZE = 60
GAN_SAMPLES_TARGET = 'max'     # 'max' 表示补齐到训练集中最多类的数量；也可填整数（如 1200）
GAN_RANDOM_SEED = 42

# 仅在 USE_GAN=True 且本地已安装 sdv 时启用
try:
    from ctgan import CTGAN
    SDV_AVAILABLE = True
except Exception:
    SDV_AVAILABLE = False


class FeatureEncoder(BaseEstimator, TransformerMixin):
    def __init__(self):
        # 预定义所有特征的编码映射
        self.mappings = {
            # 产品型号编码
            'ProductName': {
                'Radio 4471 B3': 0,
                'Radio 2271 B1': 1,
                'Radio 2271 B7': 2,
                'Radio 2271 B28': 3,
                'Radio 2271 B8': 4,
                'Radio 2271 B8B': 5,
                'Radio 2271 B20': 6,
                'Radio 4471 B3B': 7,
                'Radio 2271 B28A': 8,
                'Radio 2271 B0C': 9,
                'Radio 4471 B1': 10,
                'Radio 4471 B30': 11,
                'Radio 2271 B3': 12
            },
            # 文本描述编码
            'desc': {
                'linearization failure': 0,
                'ramping timeout': 1,
                'ramping timeout.': 1,
                'supervision': 2,
                'tuning timeout': 3,
                'Tuning timeout.': 3,
                'Wait for data timeout': 4,
                '': -1,
                np.nan: -1,
                None: -1
            },
            # 特殊布尔型（字符串形式）
            'dpd': {
                'off': 0,
                'on': 1,
                '': -1,
                np.nan: -1,
                None: -1
            },
            # 状态机类特征
            'gainStateMachine': {
                'CtrlGainStateRamping=paused': 0,
                'CtrlGainStateRamping=starting': 1,
                'CtrlGainStateTuned=started': 2,
                'CtrlGainStateTuning=paused': 3,
                'CtrlGainStateTuning=starting': 4,
                'CtrlGainStateWait=starting': 5,
                '': -1,
                np.nan: -1,
                None: -1
            },
            'ganBoostModeState': {
                'BOOST': 0,
                'NORMAL': 1,
                '': -1,
                np.nan: -1,
                None: -1
            },
            'linearizationStateMachine': {
                'CtrlLinStateStarted=started': 0,
                'CtrlLinStateStartLate=started': 1,
                'ns=stopped': 2,
                '': -1,
                np.nan: -1,
                None: -1
            },
            # 状态类特征
            'status': {
                'DPD_STATUS_FAIL': 0,
                'DPD_STATUS_OK': 1,
                '': -1,
                np.nan: -1,
                None: -1
            },
            'subId': {
                'ext-bb-data-missing': 0,
                'lin-other': 1,
                'lin-ramping': 2,
                'lin-sv': 3,
                'lin-sv-high-freq-fault': 4,
                'lin-tuning': 5,
                '': -1,
                np.nan: -1,
                None: -1
            },
            # 布尔型特征通用映射模板
            'bool_template': {
                True: 1,
                False: 0,
                'true': 1, 'false': 0,
                'yes': 1, 'no': 0,
                'on': 1, 'off': 0,
                '1': 1, '0': 0,
                '': -1,  # 空字符串
                np.nan: -1,  # NaN值
                None: -1  # None值
            },

            # 具体布尔型特征（继承模板并扩展）
            'dpGainLoopEnable': {},
            'dpTsEnable': {},
            'dpdAutoStart': {},
            'gainAutoStart': {},
            'ganBoostModeEnable': {},
            'islastDelEstFracSuccess': {},
            'shpAutoStart': {},
            'torSupported': {},
        }

        # 初始化布尔型特征的映射（继承模板）
        for bool_feature in ['dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart', 'gainAutoStart', 'ganBoostModeEnable',
                             'islastDelEstFracSuccess', 'shpAutoStart', 'torSupported']:
            self.mappings[bool_feature] = self.mappings['bool_template'].copy()

    def transform(self, X):
        X_encoded = X.copy()

        # 统一文本预处理函数
        def clean_text(text):
            if pd.isna(text) or text is None:
                return np.nan
            return str(text).strip()

        # 应用编码映射
        for feature in X.columns:
            if feature in self.mappings:
                # 特殊处理布尔型特征
                if feature in ['dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart',
                               'gainAutoStart', 'ganBoostModeEnable',
                               'islastDelEstFracSuccess', 'shpAutoStart',
                               'torSupported']:
                    # 统一转换为字符串并标准化
                    str_vals = X[feature].astype(str).str.lower().str.strip()
                    # 应用映射
                    X_encoded[feature] = str_vals.map(self.mappings[feature])

                # 处理其他分类特征
                else:
                    cleaned = X[feature].apply(clean_text)
                    X_encoded[feature] = cleaned.map(self.mappings[feature])

        # 处理未映射到的值（用-1表示）
        for col in X_encoded.columns:
            if col in self.mappings:
                X_encoded[col] = X_encoded[col].fillna(-1).astype(int)

        return X_encoded


class TrainingDataProcessor:
    """训练数据预处理（更新数值型特征版）"""

    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 定义要提取的特征
        # 数值型特征
        self.numeric_features = [
            'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IMpaSv:.0', 'IMpaSv:.1',  # 合并后的特征
            'dpdNomPwr', 'powerClass', 'powerLevel', 'rfPower', 'torGainBackoff',
            'torTemp', 'txAtt', 'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        # 原始数值型特征（用于提取时处理）
        self.raw_numeric_features = [
            'DpaVddSv:0', 'DpaVddSv:1', 'DpaVddSv:2', 'DpaVddSv:3',
            'DpaVddSv:4', 'DpaVddSv:5', 'DpaVddSv:6', 'DpaVddSv:7',
            'PaVddSv:0', 'PaVddSv:1', 'PaVddSv:2', 'PaVddSv:3',
            'PaVddSv:4', 'PaVddSv:5', 'PaVddSv:6', 'PaVddSv:7',
            'IDpaSv:0.0', 'IDpaSv:0.1', 'IDpaSv:1.0', 'IDpaSv:1.1',
            'IDpaSv:2.0', 'IDpaSv:2.1', 'IDpaSv:3.0', 'IDpaSv:3.1',
            'IDpaSv:4.0', 'IDpaSv:4.1', 'IDpaSv:5.0', 'IDpaSv:5.1',
            'IDpaSv:6.0', 'IDpaSv:6.1', 'IDpaSv:7.0', 'IDpaSv:7.1',
            'IMpaSv:0.0', 'IMpaSv:0.1', 'IMpaSv:1.0', 'IMpaSv:1.1',
            'IMpaSv:2.0', 'IMpaSv:2.1', 'IMpaSv:3.0', 'IMpaSv:3.1',
            'IMpaSv:4.0', 'IMpaSv:4.1', 'IMpaSv:5.0', 'IMpaSv:5.1',
            'IMpaSv:6.0', 'IMpaSv:6.1', 'IMpaSv:7.0', 'IMpaSv:7.1',
            'dpdNomPwr', 'powerClass', 'powerLevel', 'rfPower', 'torGainBackoff',
            'torTemp', 'txAtt', 'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        # 字符+布尔型特征
        self.categorical_features = [
            'ProductName', 'desc', 'dpGainLoopEnable', 'dpTsEnable', 'dpd', 'dpdAutoStart', 'gainAutoStart',
            'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState', 'islastDelEstFracSuccess',
            'linearizationStateMachine', 'shpAutoStart', 'status', 'subId', 'torSupported'
        ]

        # 初始化特征编码器
        self.encoder = FeatureEncoder()

    def select_labels(self, df):
        print("请选择标签 (1: Legacy, 2: New)")
        selection = int(input())

        if selection == 1:
            df.drop(columns=['PA Status Repair Info'], inplace=True)
            df.rename(columns={'PA Status Pattern 2': 'PA Status'}, inplace=True)
        elif selection == 2:
            df.drop(columns=['PA Status Pattern 2'], inplace=True)
            df.rename(columns={'PA Status Repair Info': 'PA Status'}, inplace=True)
        else:
            raise ValueError("Wrong input, please enter 1 or 2")

        return df

    def load_and_filter_data(self):
        json_files = [f for f in os.listdir(self.input_dir) if f.endswith('.json')]
        all_samples = []

        for json_file in json_files:
            with open(os.path.join(self.input_dir, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                for sample in data:
                    processed = {
                        'Serial': sample.get('Serial'),
                        'ProductName': sample.get('ProductName'),
                        'Timestamp': sample.get('Timestamp'),
                        'PA Status Pattern 2': sample.get('PA Status Pattern 2'),
                        'Symptoms': sample.get('Symptoms', ''),
                        'PA Status Repair Info': sample.get('PA Status Repair Info'),
                        'Parameters': sample.get('Parameters', {})
                    }
                    if processed['PA Status Repair Info'] != 'Unknown':
                        all_samples.append(processed)

        df = pd.DataFrame(all_samples)

        # 在这里调用 label 选择
        df = self.select_labels(df)

        print(f"加载样本数: {len(df)}")
        return df


    def gan_generator_per_class(self, X_df, y_series):
        """
        针对训练集，按类别拟合 CopulaGAN，并把每个类别补齐到目标数量。
        - X_df: 训练集特征（DataFrame，已是数值化/标准化后的）
        - y_series: 训练集标签（Series，int）
        返回：X_aug, y_aug（包含原始 + GAN 合成）
        """
        if not USE_GAN or not SDV_AVAILABLE:
            print("[GAN] 跳过：未启用或未安装 sdv")
            return X_df, y_series

        label_col = "__label__"
        df_tr = X_df.copy()
        df_tr[label_col] = y_series.values
        classes = sorted(df_tr[label_col].unique().tolist())

        discrete_columns = [
            'ProductName', 'desc', 'dpGainLoopEnable', 'dpTsEnable', 'dpd', 'dpdAutoStart', 'gainAutoStart',
            'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState', 'islastDelEstFracSuccess',
            'linearizationStateMachine', 'shpAutoStart', 'status', 'subId', 'torSupported',
            'PA Status'
        ]

        # 计算每类目标样本数量
        from collections import Counter
        cnt = Counter(df_tr[label_col].tolist())
        if GAN_SAMPLES_TARGET == 'max':
            target_per_class = max(cnt.values())
        else:
            # 固定目标样本数（整数）
            target_per_class = int(GAN_SAMPLES_TARGET)

        print(f"[GAN] 类分布: {cnt}, 目标每类: {target_per_class}")

        syn_list = []
        for c in classes:
            df_c = df_tr[df_tr[label_col] == c].reset_index(drop=True)
            n_cur = len(df_c)
            n_need = max(0, target_per_class - n_cur)
            if n_need == 0:
                continue

            print(f"[GAN] 训练 CopulaGAN 类别={c}, n={n_cur}, 生成={n_need}")

            # # 只给该类的数据拟合
            # metadata = SingleTableMetadata()
            # metadata.detect_from_dataframe(data=df_c)
            #
            # # 指定一些列为 categorical（如果存在）
            # for col in ['gainStateMachine', 'ganBoostModeState', 'linearizationStateMachine',
            #             'status', 'subId', 'ProductName', 'desc', 'dpd',
            #             'dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart', 'gainAutoStart',
            #             'ganBoostModeEnable', 'islastDelEstFracSuccess', 'shpAutoStart', 'torSupported']:
            #     if col in df_c.columns:
            #         metadata.update_column(col, sdtype='categorical')

            # ctgan = CopulaGANSynthesizer(
            #     metadata,
            #     epochs=GAN_EPOCHS,
            #     batch_size=GAN_BATCH_SIZE,
            #     verbose=True,
            #     default_distribution='gaussian_kde',
            #     embedding_dim=64,
            #     generator_dim=(128, 128),
            #     discriminator_dim=(128, 128),
            #     generator_lr=1e-4, generator_decay=1e-5,
            #     discriminator_lr=1e-4, discriminator_decay=1e-5,
            #     discriminator_steps=2,
            #     pac=5,
            #     cuda=use_cuda,
            #     # random_state=GAN_RANDOM_STATE  # 某些版本不支持该参数
            # )

            # # ctgan.fit(df_c)
            # # syn = ctgan.sample(n_need)
            # ctgan = CTGAN(epochs=200, batch_size=128)
            # ctgan.fit(df_encoded, discrete_columns=discrete_columns)
            #
            # # 3) 生成
            # syn = ctgan.sample(2000)  # 含所有列；若纳入了标签，会直接生成标签

            # 当前类训练数据：仅特征
            train_df = df_c.drop(columns=[label_col])

            # 只保留实际存在的离散列（防止传了不存在的列名）
            disc_cols_present = [col for col in discrete_columns if col in train_df.columns]

            import torch

            # ===== 检测可用设备 =====
            if torch.backends.mps.is_available():
                device = "mps"
                print("[Device] Using Apple Silicon GPU (MPS)")
            elif torch.cuda.is_available():
                device = "cuda"
                print("[Device] Using NVIDIA GPU (CUDA)")
            else:
                device = "cpu"
                print("[Device] Using CPU only")

            # ===== 设置随机种子 =====
            torch.manual_seed(GAN_RANDOM_SEED)
            random.seed(GAN_RANDOM_SEED)
            np.random.seed(GAN_RANDOM_SEED)
            if device == "cuda":
                torch.cuda.manual_seed_all(GAN_RANDOM_SEED)

            # ===== 在训练前强制设置默认设备 =====
            if device == "mps":
                torch.set_default_device("mps")
            elif device == "cuda":
                torch.set_default_device("cuda")
            else:
                torch.set_default_device("cpu")

            # ===== 实例化 CTGAN（不要传 device 参数）=====
            ctgan = CTGAN(
                epochs=GAN_EPOCHS,
                batch_size=GAN_BATCH_SIZE,
                generator_dim=(128, 128),
                discriminator_dim=(128, 128),
                verbose=True
            )

            print(f"[CTGAN] Training on {device.upper()} ...")

            # ===== 训练 GAN =====
            ctgan.fit(train_df, discrete_columns=disc_cols_present)

            # 按需生成
            syn = ctgan.sample(n_need)

            # 回填标签列
            syn[label_col] = c
            syn_list.append(syn)

            # 保护：确保标签列存在且为该类
            if label_col not in syn.columns:
                syn[label_col] = c
            else:
                syn[label_col] = c

            syn_list.append(syn)

        if not syn_list:
            print("[GAN] 无需生成：所有类别已满足目标数量")
            return X_df, y_series

        syn_all = pd.concat(syn_list, ignore_index=True)

        # 拆回 X/y
        y_syn = syn_all[label_col].astype(int)
        X_syn = syn_all.drop(columns=[label_col])

        # 与原训练集拼接
        X_aug = pd.concat([X_df, X_syn], axis=0).reset_index(drop=True)
        y_aug = pd.concat([y_series, y_syn], axis=0).reset_index(drop=True)

        print(f"[GAN] 合并后训练集大小: {len(X_aug)} (原 {len(X_df)} + 合成 {len(X_aug) - len(X_df)})")
        return X_aug, y_aug


    @staticmethod
    def process_numeric_features(params):
        """处理数值型特征，按照需求合并相关特征"""
        numeric_values = {}

        def safe_get_value(params, key):
            if not isinstance(params, dict):
                return np.nan
            val = params.get(key, np.nan)
            if isinstance(val, dict):
                return val.get('Value', np.nan)
            return val
        # 1.1 处理DpaVddSv - 合并所有DpaVddSv参数
        dpa_values = []
        for i in range(8):
            key = f'DpaVddSv:{i}'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:  # 只收集非空值
                        dpa_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        # 如果有非空值则取平均值，否则保持NaN
        numeric_values['DpaVddSv'] = np.nanmean(dpa_values) if dpa_values else np.nan

        # 1.1 同样处理PaVddSv - 合并所有PaVddSv参数
        pa_values = []
        for i in range(8):
            key = f'PaVddSv:{i}'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:  # 只收集非空值
                        pa_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        numeric_values['PaVddSv'] = np.nanmean(pa_values) if pa_values else np.nan

        # 1.2 处理IDpaSv - 合并所有IDpaSv:x.0到IDpaSv:.0
        idpa_0_values = []
        for i in range(8):
            key = f'IDpaSv:{i}.0'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:  # 只收集非空值
                        idpa_0_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        # 合并所有IDpaSv:x.1到IDpaSv:.1
        idpa_1_values = []
        for i in range(8):
            key = f'IDpaSv:{i}.1'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:  # 只收集非空值
                        idpa_1_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        numeric_values['IDpaSv:.0'] = np.nanmean(idpa_0_values) if idpa_0_values else np.nan
        numeric_values['IDpaSv:.1'] = np.nanmean(idpa_1_values) if idpa_1_values else np.nan

        # 1.2 处理IMpaSv - 合并所有IMpaSv:x.0到IMpaSv:.0
        impa_0_values = []
        for i in range(8):
            key = f'IMpaSv:{i}.0'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:  # 只收集非空值
                        impa_0_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        # 合并所有IMpaSv:x.1到IMpaSv:.1
        impa_1_values = []
        for i in range(8):
            key = f'IMpaSv:{i}.1'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:  # 只收集非空值
                        impa_1_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        numeric_values['IMpaSv:.0'] = np.nanmean(impa_0_values) if impa_0_values else np.nan
        numeric_values['IMpaSv:.1'] = np.nanmean(impa_1_values) if impa_1_values else np.nan

        # 1.3 处理其他数值型属性
        other_numeric_features = [
            'dpdNomPwr', 'powerClass', 'powerLevel', 'rfPower', 'torGainBackoff',
            'torTemp', 'txAtt', 'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]


        for feat in other_numeric_features:
            if feat in params:
                val = safe_get_value(params, feat)

                try:
                    # 处理powerClass的字符串值
                    if feat == 'powerClass' and isinstance(val, str):
                        val = int(val) if val.isdigit() else np.nan
                    # 检查空值
                    if val not in ['', None]:
                        numeric_values[feat] = float(val)
                    else:
                        numeric_values[feat] = np.nan
                except (ValueError, TypeError):
                    numeric_values[feat] = np.nan
            else:
                numeric_values[feat] = np.nan

        return numeric_values

    def extract_features(self, df):
        """提取并处理特征（完整修复版）"""
        # 初始化特征字典
        features = {col: [] for col in self.numeric_features + self.categorical_features}
        features['PA Status'] = []
        valid_indices = []

        def safe_get_value(params, key):
            if not isinstance(params, dict):
                return np.nan
            val = params.get(key, np.nan)
            if isinstance(val, dict):
                return val.get('Value', np.nan)
            return val

        for idx, row in enumerate(df.itertuples()):
            # 调试：打印第一条记录的结构

            params = getattr(row, 'Parameters', {})
            is_valid = True

            # ========== 1. 数值特征有效性检查(使用原始特征列表) ==========
            for feat in self.raw_numeric_features:
                if feat in params:
                    val = safe_get_value(params, feat)

                    try:
                        # powerClass允许字符串数字
                        if feat == 'powerClass' and isinstance(val, str):
                            if not val.isdigit():
                                is_valid = False
                                break
                        else:
                            float_val = float(val)
                            if np.isinf(float_val) or abs(float_val) > 1e308:
                                is_valid = False
                                break
                    except (ValueError, TypeError):
                        is_valid = False
                        break

            if is_valid:
                valid_indices.append(idx)

                # ========== 2. 数值特征处理(使用合并后的逻辑) ==========
                numeric_values = self.process_numeric_features(params)
                for feat in self.numeric_features:
                    features[feat].append(numeric_values.get(feat, np.nan))

                # ========== 3. 分类特征处理 ==========
                for feat in self.categorical_features:
                    if feat == 'ProductName':
                        val = (getattr(row, 'ProductName', None) or
                               params.get('ProductName', {}).get('Value', 'unknown'))
                    else:
                        val = safe_get_value(params, feat)
                    features[feat].append(str(val).strip())

                # ========== 4. PA Status提取 ==========
                if hasattr(df, '_original_data'):
                    pa_status = df._original_data[idx].get('PA Status', 'Normal')
                elif 'PA Status' in df.columns:
                    pa_status = df.iloc[idx]['PA Status']
                else:
                    pa_status = 'Normal'
                    print(f"警告: 样本 {idx} 无法定位PA Status，使用默认值")
                features['PA Status'].append(pa_status)

        # ========== 结果验证 ==========
        print(f"\n=== 处理结果 ===")
        print(f"有效样本数: {len(valid_indices)} (剔除异常值样本: {len(df) - len(valid_indices)})")

        return pd.DataFrame(features)

    def preprocess_data(self, df):
        """数据预处理流程"""
        # 1. 编码分类特征
        df_encoded = self.encoder.transform(df)

        # 2. 数值特征处理
        numeric_data = df_encoded[self.numeric_features].copy()

        # 2.1 处理无限大值
        numeric_data = numeric_data.replace([np.inf, -np.inf], -1000)

        # 2.2 处理全空列（填充0）
        empty_cols = numeric_data.columns[numeric_data.isna().all()].tolist()
        for col in empty_cols:
            numeric_data[col] = 0

        # 2.3 中位数填充其他缺失值
        imputer = SimpleImputer(strategy='median')
        numeric_data_imputed = pd.DataFrame(
            imputer.fit_transform(numeric_data),
            columns=numeric_data.columns
        )

        # 3. 数据标准化（带异常值处理）
        scaler = StandardScaler()

        # 3.1 检查是否存在零方差特征
        variances = numeric_data_imputed.var()
        zero_var_cols = variances[variances == 0].index.tolist()
        if zero_var_cols:
            print(f"警告: 以下特征方差为零，标准化时将跳过: {zero_var_cols}")
            # 对这些列不进行标准化（保持原值）
            non_zero_var_cols = [col for col in numeric_data_imputed.columns if col not in zero_var_cols]
            scaled_values = scaler.fit_transform(numeric_data_imputed[non_zero_var_cols])
            numeric_data_imputed[non_zero_var_cols] = scaled_values
        else:
            numeric_data_imputed[:] = scaler.fit_transform(numeric_data_imputed)

        df_encoded[self.numeric_features] = numeric_data_imputed

        return df_encoded, scaler


    def select_labels_with_mode(self, df):
        print("请选择模式 (1: 原本标签, 2: 新标签)")
        selection = int(input().strip())

        if selection == 1:
            # 原本逻辑
            label_map = {'Normal': 0, 'PA abnormal': 1}
            df = df[df['PA Status'].isin(label_map.keys())]  # 过滤非法标签
            y = df['PA Status'].map(label_map).astype(int)
            return df, y

        elif selection == 2:
            # 只保留两类标签
            def convert_label(x):
                if x == 'PA abnormal':
                    return 'PA abnormal'
                else:
                    return 'Normal'

            df['PA Status'] = df['PA Status'].apply(convert_label)
            label_map = {'Normal': 0, 'PA abnormal': 1}
            y = df['PA Status'].map(label_map).astype(int)
            return df, y

        else:
            raise ValueError("Wrong input, please enter 1 or 2")

    def split_and_save_data(self, df):
        """数据集划分与保存"""
        # 转换标签（你原有的 1=三分类 / 2=二分类 逻辑，不动）
        df, y = self.select_labels_with_mode(df)
        X = df.drop('PA Status', axis=1)

        # 划分数据集（60%:20%:20%）——保持不变
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.4, random_state=42, stratify=y)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

        # ====== 仅此处新增：用 GAN 扩充训练集（可选） ======
        if USE_GAN:
            if not SDV_AVAILABLE:
                print("[GAN] 未安装 sdv，跳过 GAN 生成（pip install sdv）")
            else:
                X_train, y_train = self.gan_generator_per_class(X_train, y_train)

        # 保存数据集（保持你原逻辑）
        save_paths = {
            'train.csv': (X_train, y_train),
            'val.csv': (X_val, y_val),
            'test.csv': (X_test, y_test)
        }
        for filename, (X_data, y_data) in save_paths.items():
            pd.concat([X_data, y_data], axis=1).to_csv(
                os.path.join(self.output_dir, filename),
                index=False
            )

        print(f"数据集已保存至 {self.output_dir}:")
        print(f"- 训练集: {len(X_train)} 样本")
        print(f"- 验证集: {len(X_val)} 样本")
        print(f"- 测试集: {len(X_test)} 样本")

    def process(self):
        """完整处理流程"""
        # 1. 数据加载与过滤
        raw_df = self.load_and_filter_data()

        # 2. 特征提取
        feature_df = self.extract_features(raw_df)

        # 3. 数据预处理
        processed_df, scaler = self.preprocess_data(feature_df)

        # 4. 数据集划分与保存
        self.split_and_save_data(processed_df)

        # 5. 保存预处理对象
        import joblib
        joblib.dump(self.encoder, os.path.join(self.output_dir, 'feature_encoder.pkl'))
        joblib.dump(scaler, os.path.join(self.output_dir, 'scaler.pkl'))

        print("预处理流程完成")


if __name__ == '__main__':

    # 使用示例
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../'))

    INPUT_DIR = "/Users/sunjiaxiang/DeepLog_AI/tools/data/files_for_training"
    OUTPUT_DIR = "/Users/sunjiaxiang/DeepLog_AI/tools/data/processed_dataset"
    # INPUT_DIR = os.path.join(ROOT_DIR, 'files_for_training')
    # OUTPUT_DIR = os.path.join(ROOT_DIR, 'processed_datasets')
    print("ROOT_DIR:", ROOT_DIR)
    print("OUTPUT_DIR:", OUTPUT_DIR)


    processor = TrainingDataProcessor(INPUT_DIR, OUTPUT_DIR)
    processor.process()