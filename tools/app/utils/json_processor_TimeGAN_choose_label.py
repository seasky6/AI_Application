import os
import json
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.base import BaseEstimator, TransformerMixin

from ydata_synthetic.synthesizers.timeseries import TimeSeriesSynthesizer
from ydata_synthetic.synthesizers import ModelParameters, TrainParameters


# ========= 特征编码器 =========
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
                '': -1,
                np.nan: -1,
                None: -1
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
        for bf in ['dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart',
                   'gainAutoStart', 'ganBoostModeEnable',
                   'islastDelEstFracSuccess', 'shpAutoStart',
                   'torSupported']:
            self.mappings[bf] = self.mappings['bool_template'].copy()

    def transform(self, X):
        X_encoded = X.copy()

        def clean_text(text):
            if pd.isna(text) or text is None:
                return np.nan
            return str(text).strip()

        # 应用映射
        for feature in X.columns:
            if feature in self.mappings:
                # 布尔型列
                if feature in ['dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart',
                               'gainAutoStart', 'ganBoostModeEnable',
                               'islastDelEstFracSuccess', 'shpAutoStart',
                               'torSupported']:
                    str_vals = X[feature].astype(str).str.lower().str.strip()
                    X_encoded[feature] = str_vals.map(self.mappings[feature])
                else:
                    cleaned = X[feature].apply(clean_text)
                    X_encoded[feature] = cleaned.map(self.mappings[feature])

        # 未映射到的值用 -1
        for col in X_encoded.columns:
            if col in self.mappings:
                X_encoded[col] = X_encoded[col].fillna(-1).astype(int)

        return X_encoded


# ========= 数据预处理 + 序列构建 =========
class TrainingDataProcessor:
    """训练数据预处理（TimeGAN 序列 + 有监督标签）"""

    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 合并后的数值型特征
        self.numeric_features = [
            'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IMpaSv:.0', 'IMpaSv:.1',
            'dpdNomPwr', 'powerClass', 'powerLevel', 'rfPower', 'torGainBackoff',
            'torTemp', 'txAtt', 'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        # 原始数值型特征，用于检查/合并
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

        self.encoder = FeatureEncoder()

    # ---------- 选择标签来源 ----------
    def select_labels(self, df):
        # 默认使用 Repair Info 标签（2）
        selection = 2

        if selection == 1:
            df.drop(columns=['PA Status Repair Info'], inplace=True)
            df.rename(columns={'PA Status Pattern 2': 'PA Status'}, inplace=True)
        elif selection == 2:
            df.drop(columns=['PA Status Pattern 2'], inplace=True)
            df.rename(columns={'PA Status Repair Info': 'PA Status'}, inplace=True)
        else:
            raise ValueError("Wrong input, please enter 1 or 2")

        return df

    # ---------- 1. 读取 JSON ----------
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
                    # 过滤 Unknown
                    if processed['PA Status Repair Info'] != 'Unknown':
                        all_samples.append(processed)

        df = pd.DataFrame(all_samples)
        df = self.select_labels(df)

        print(f"加载样本数: {len(df)}")
        return df

    # ---------- 2. 数值特征合并 ----------
    @staticmethod
    def process_numeric_features(params):
        numeric_values = {}

        def safe_get_value(params, key):
            if not isinstance(params, dict):
                return np.nan
            val = params.get(key, np.nan)
            if isinstance(val, dict):
                return val.get('Value', np.nan)
            return val

        # DpaVddSv 合并
        dpa_values = []
        for i in range(8):
            key = f'DpaVddSv:{i}'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:
                        dpa_values.append(float(val))
                except (ValueError, TypeError):
                    pass
        numeric_values['DpaVddSv'] = np.nanmean(dpa_values) if dpa_values else np.nan

        # PaVddSv 合并
        pa_values = []
        for i in range(8):
            key = f'PaVddSv:{i}'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:
                        pa_values.append(float(val))
                except (ValueError, TypeError):
                    pass
        numeric_values['PaVddSv'] = np.nanmean(pa_values) if pa_values else np.nan

        # IDpaSv 合并
        idpa_0_values = []
        for i in range(8):
            key = f'IDpaSv:{i}.0'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:
                        idpa_0_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        idpa_1_values = []
        for i in range(8):
            key = f'IDpaSv:{i}.1'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:
                        idpa_1_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        numeric_values['IDpaSv:.0'] = np.nanmean(idpa_0_values) if idpa_0_values else np.nan
        numeric_values['IDpaSv:.1'] = np.nanmean(idpa_1_values) if idpa_1_values else np.nan

        # IMpaSv 合并
        impa_0_values = []
        for i in range(8):
            key = f'IMpaSv:{i}.0'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:
                        impa_0_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        impa_1_values = []
        for i in range(8):
            key = f'IMpaSv:{i}.1'
            if key in params:
                val = safe_get_value(params, key)
                try:
                    if val not in ['', None]:
                        impa_1_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        numeric_values['IMpaSv:.0'] = np.nanmean(impa_0_values) if impa_0_values else np.nan
        numeric_values['IMpaSv:.1'] = np.nanmean(impa_1_values) if impa_1_values else np.nan

        # 其他数值型属性
        other_numeric_features = [
            'dpdNomPwr', 'powerClass', 'powerLevel', 'rfPower', 'torGainBackoff',
            'torTemp', 'txAtt', 'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        for feat in other_numeric_features:
            if feat in params:
                val = safe_get_value(params, feat)
                try:
                    if feat == 'powerClass' and isinstance(val, str):
                        val = int(val) if val.isdigit() else np.nan
                    if val not in ['', None]:
                        numeric_values[feat] = float(val)
                    else:
                        numeric_values[feat] = np.nan
                except (ValueError, TypeError):
                    numeric_values[feat] = np.nan
            else:
                numeric_values[feat] = np.nan

        return numeric_values

    # ---------- 3. 特征提取（含 Serial / Timestamp / PA Status） ----------
    def extract_features(self, df):
        all_feature_cols = ['Serial', 'Timestamp'] + self.numeric_features + self.categorical_features
        features = {col: [] for col in all_feature_cols}
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
            params = getattr(row, 'Parameters', {})
            is_valid = True

            # 数值有效性检查
            for feat in self.raw_numeric_features:
                if feat in params:
                    val = safe_get_value(params, feat)
                    try:
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

            if not is_valid:
                continue

            valid_indices.append(idx)

            # Serial / Timestamp
            serial = getattr(row, 'Serial', None)
            timestamp = getattr(row, 'Timestamp', None)
            features['Serial'].append(serial)
            features['Timestamp'].append(timestamp)

            # 数值特征合并
            numeric_values = self.process_numeric_features(params)
            for feat in self.numeric_features:
                features[feat].append(numeric_values.get(feat, np.nan))

            # 类别特征
            for feat in self.categorical_features:
                if feat == 'ProductName':
                    val = (getattr(row, 'ProductName', None) or
                           params.get('ProductName', {}).get('Value', 'unknown'))
                else:
                    val = safe_get_value(params, feat)
                features[feat].append(str(val).strip())

            # PA Status
            if 'PA Status' in df.columns:
                pa_status = df.iloc[idx]['PA Status']
            else:
                pa_status = 'Normal'
            features['PA Status'].append(pa_status)

        print(f"\n=== 特征提取结果 ===")
        print(f"有效样本数: {len(valid_indices)} (剔除异常样本: {len(df) - len(valid_indices)})")

        return pd.DataFrame(features)

    # ---------- 4. 编码 + 标准化 ----------
    def preprocess_data(self, df):
        df_encoded = self.encoder.transform(df)

        numeric_data = df_encoded[self.numeric_features].copy()
        numeric_data = numeric_data.replace([np.inf, -np.inf], -1000)

        # 全空列填 0
        empty_cols = numeric_data.columns[numeric_data.isna().all()].tolist()
        for col in empty_cols:
            numeric_data[col] = 0

        imputer = SimpleImputer(strategy='median')
        numeric_data_imputed = pd.DataFrame(
            imputer.fit_transform(numeric_data),
            columns=numeric_data.columns
        )

        scaler = StandardScaler()
        variances = numeric_data_imputed.var()
        zero_var_cols = variances[variances == 0].index.tolist()
        if zero_var_cols:
            print(f"警告: 以下特征方差为零，将跳过标准化: {zero_var_cols}")
            non_zero_var_cols = [c for c in numeric_data_imputed.columns if c not in zero_var_cols]
            scaled_values = scaler.fit_transform(numeric_data_imputed[non_zero_var_cols])
            numeric_data_imputed[non_zero_var_cols] = scaled_values
        else:
            numeric_data_imputed[:] = scaler.fit_transform(numeric_data_imputed)

        df_encoded[self.numeric_features] = numeric_data_imputed
        return df_encoded, scaler

    # ---------- 5. 构造 TimeGAN 序列（不补 0，长度不足直接丢弃） ----------
    def build_timegan_sequences(self, df, seq_len=20):
        """
        构造给分类模型用的固定长度序列。
        这里只用来生成 X_real / y_real，不喂回 TimeGAN。
        """
        # 0️⃣ PA Status 映射为 0/1
        label_map = {'Normal': 0, 'PA abnormal': 1}
        if df["PA Status"].dtype == object:
            df = df.copy()
            df["PA Status"] = df["PA Status"].map(lambda x: label_map.get(x, 0)).astype(int)
        else:
            df["PA Status"] = df["PA Status"].astype(int)

        # 1️⃣ 时间排序 + 计算归一化时间（仅用于排序，不作为特征列）
        df_sorted = df.sort_values(["Serial", "Timestamp"]).copy()
        df_sorted["Timestamp"] = pd.to_datetime(df_sorted["Timestamp"])

        df_sorted["time_delta_sec"] = (
            df_sorted.groupby("Serial")["Timestamp"]
            .transform(lambda x: (x - x.min()).dt.total_seconds())
        )
        df_sorted["time_delta_sec_norm"] = (
            df_sorted.groupby("Serial")["time_delta_sec"]
            .transform(lambda x: x / x.max() if x.max() > 0 else 0)
        )

        # TimeGAN & 分类用的特征列（不含时间）
        all_features = self.numeric_features + self.categorical_features

        seq_list, seq_labels, serial_ids = [], [], []
        dropped_short = 0

        for serial, g in df_sorted.groupby("Serial"):
            X_mat = g[all_features].to_numpy(dtype=np.float32)
            y_label = int(g["PA Status"].iloc[-1])

            T_i = len(g)
            if T_i < seq_len:
                dropped_short += 1
                continue  # 丢掉太短的序列

            # 只取最后 seq_len 个时间步
            X_fixed = X_mat[-seq_len:, :]

            seq_list.append(X_fixed)
            seq_labels.append(y_label)
            serial_ids.append(serial)

        X_seq = np.stack(seq_list, axis=0)      # (N, T, D)
        y_seq = np.array(seq_labels, dtype=int)
        serial_ids = np.array(serial_ids)

        print(f"[Real 序列] 构造完成: {X_seq.shape[0]} 条序列, "
              f"每条长度 {seq_len}, 特征维度 {X_seq.shape[2]}, "
              f"丢弃短序列 {dropped_short} 条")
        return X_seq, y_seq, serial_ids



# ========= 主流程：0/1 分别训练 TimeGAN 并生成合成序列 =========
def main():
    # 你自己的路径
    input_dir = "/Users/sunjiaxiang/DeepLog_AI/tools/data/files_for_training"   # 放 JSON 的目录
    output_dir = "/Users/sunjiaxiang/DeepLog_AI/tools/data/processed_dataset"
    os.makedirs(output_dir, exist_ok=True)

    seq_len = 20  # TimeGAN 窗口长度，可根据 Serial 长度分布调整

    processor = TrainingDataProcessor(input_dir, output_dir)

    # 1. 读入 & 过滤标签
    df_raw = processor.load_and_filter_data()

    # 2. 提取特征
    df_features = processor.extract_features(df_raw)

    # 3. 编码 + 标准化
    df_preprocessed, scaler = processor.preprocess_data(df_features)

    # 4. 构造真实序列（用于后续分类训练）
    X_seq, y_seq, serial_ids = processor.build_timegan_sequences(df_preprocessed, seq_len=seq_len)

    # 5. 按标签拆分真实序列（仅用于统计 & 合成数量）
    X_seq_0 = X_seq[y_seq == 0]   # Normal
    X_seq_1 = X_seq[y_seq == 1]   # PA abnormal

    print(f"Normal 序列数: {X_seq_0.shape[0]}, Abnormal 序列数: {X_seq_1.shape[0]}")

    if X_seq_0.shape[0] == 0 or X_seq_1.shape[0] == 0:
        raise RuntimeError("有一类样本为空，无法分别训练两个 TimeGAN，请检查标签分布。")

    SEQ_LEN = seq_len
    # TimeGAN 使用的特征列（与 build_timegan_sequences 一致）
    feature_cols = processor.numeric_features + processor.categorical_features
    D = len(feature_cols)
    print(f"TimeGAN 输入特征数 D = {D}, feature_cols 数量 = {len(feature_cols)}")

    # ----- 为 TimeGAN 构造按类划分的 DataFrame -----
    # 把字符串标签映射成数值标签，只用于筛选
    label_map = {'Normal': 0, 'PA abnormal': 1}
    df_for_gan = df_preprocessed.copy()
    df_for_gan["PA_Status_num"] = df_for_gan["PA Status"].map(lambda x: label_map.get(x, 0)).astype(int)

    df_0 = df_for_gan[df_for_gan["PA_Status_num"] == 0]  # Normal
    df_1 = df_for_gan[df_for_gan["PA_Status_num"] == 1]  # Abnormal

    # 只保留 TimeGAN 需要的特征列（按时间排序，保持一定时序感）
    df_0_gan = df_0.sort_values(["Serial", "Timestamp"])[feature_cols]
    df_1_gan = df_1.sort_values(["Serial", "Timestamp"])[feature_cols]

    # ------- 定义 TimeGAN 参数（两类共用一套超参数） -------
    gan_args = ModelParameters(
        batch_size=64,
        lr=5e-4,
        noise_dim=32,
        layers_dim=128,
        latent_dim=24,
        gamma=1,
    )

    # 注意：这里 number_sequences 必须是 特征维度 D，而不是样本条数！
    # 官方 Yahoo Stock 例子里就是 number_sequences=列数=6 :contentReference[oaicite:2]{index=2}

    # ========== 训练 Normal 类（label=0）的 TimeGAN ==========
    train_args_0 = TrainParameters(
        epochs=20,              # 调试时先小一点，OK 再加大
        sequence_length=SEQ_LEN,
        number_sequences=D,
    )

    print("\n===== 训练 TimeGAN（Normal 类, label=0）=====")
    synth_0 = TimeSeriesSynthesizer(modelname='timegan', model_parameters=gan_args)
    # ⭐ 关键：传 DataFrame，并指定 num_cols；TimeGAN 内部会做窗口划分
    synth_0.fit(df_0_gan, train_args_0, num_cols=feature_cols)

    # 生成合成 Normal 序列，数量与真实 Normal 序列数一致
    n_syn_0 = X_seq_0.shape[0]
    syn_blocks_0 = synth_0.sample(n_samples=n_syn_0)

    # TimeSeriesSynthesizer.sample 返回 list[pd.DataFrame]，每个是 (SEQ_LEN, D)
    syn_X_0 = np.stack(
        [block.to_numpy(dtype=np.float32) for block in syn_blocks_0],
        axis=0
    )   # (N0, SEQ_LEN, D)

    print(f"合成 Normal 序列形状: {syn_X_0.shape}")

    # ========== 训练 Abnormal 类（label=1）的 TimeGAN ==========
    train_args_1 = TrainParameters(
        epochs=20,
        sequence_length=SEQ_LEN,
        number_sequences=D,
    )

    print("\n===== 训练 TimeGAN（Abnormal 类, label=1）=====")
    synth_1 = TimeSeriesSynthesizer(modelname='timegan', model_parameters=gan_args)
    synth_1.fit(df_1_gan, train_args_1, num_cols=feature_cols)

    n_syn_1 = X_seq_1.shape[0]
    syn_blocks_1 = synth_1.sample(n_samples=n_syn_1)

    syn_X_1 = np.stack(
        [block.to_numpy(dtype=np.float32) for block in syn_blocks_1],
        axis=0
    )   # (N1, SEQ_LEN, D)

    print(f"合成 Abnormal 序列形状: {syn_X_1.shape}")

    # 6. 给合成样本加标签，拼成一个大的训练集（时序级别）
    y_syn_0 = np.zeros(syn_X_0.shape[0], dtype=int)
    y_syn_1 = np.ones(syn_X_1.shape[0], dtype=int)

    X_syn_all = np.concatenate([syn_X_0, syn_X_1], axis=0)
    y_syn_all = np.concatenate([y_syn_0, y_syn_1], axis=0)

    print(f"\n总共合成序列数: {X_syn_all.shape[0]}")

    # 7. 保存 numpy 文件，后续可以直接喂给分类模型
    np.save(os.path.join(output_dir, "X_real.npy"), X_seq)
    np.save(os.path.join(output_dir, "y_real.npy"), y_seq)
    np.save(os.path.join(output_dir, "X_syn.npy"), X_syn_all)
    np.save(os.path.join(output_dir, "y_syn.npy"), y_syn_all)

    print(f"\n已保存到目录: {output_dir}")
    print("X_real.npy / y_real.npy 为真实序列；X_syn.npy / y_syn.npy 为 TimeGAN 生成序列。")


if __name__ == "__main__":
    main()
