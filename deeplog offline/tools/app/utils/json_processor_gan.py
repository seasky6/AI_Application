import json
import os
import numpy as np
import pandas as pd
from ctgan.ctgan.synthesizers.base import random_state
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.base import BaseEstimator, TransformerMixin
from ctgan.synthesizers.ctgan import CTGAN
from sdv.single_table.copulagan import CopulaGANSynthesizer
from sdv.metadata.single_table import SingleTableMetadata


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


def gan_generator(df):
    df_copy = df.copy()
    label_map = {'Normal': 0, 'PA might broken': 1, 'PA broken': 2}
    y_train = df_copy['PA Status'].map(label_map)
    X_train = df_copy.drop('PA Status', axis=1)

    df_real = pd.DataFrame(X_train.copy())
    df_real['PA Status'] = pd.DataFrame(y_train.copy())

    unique_classes = np.unique(df_real['PA Status'])

    samples_per_class_map = {
        0: 1200,
        1: 1200,
        2: 600
    }

    batch_size_map = {
        0: 20,
        1: 30,
        2: 250
    }

    epochs_size_map = {
        0: 250,
        1: 130,
        2: 100
    }

    gan_synthetic_data = []

    for cls in unique_classes:
        df_cls = df_real[df_real['PA Status'] == cls].copy()
        print(f"训练 CTGAN（类别 {cls}, 样本 {len(df_cls)}）...")

        batch_size = batch_size_map[cls]  # 直接取出，不做限制

        epochs_size = epochs_size_map[cls]  # 直接取出，不做限制

        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(data=df_cls)
        for col in ['gainStateMachine', 'ganBoostModeState', 'linearizationStateMachine']:
            metadata.update_column(col, sdtype='categorical')
        ctgan = CopulaGANSynthesizer(
            metadata,
            epochs=epochs_size,
            default_distribution='gaussian_kde',
            verbose=True,
            batch_size=batch_size,
            embedding_dim=64,
            generator_dim=(128, 128),
            discriminator_dim=(128, 128),
            generator_lr=1e-4,
            generator_decay=1e-5,
            discriminator_lr=1e-4,
            discriminator_decay=1e-5,
            discriminator_steps=2,
            log_frequency=True,
            pac=5,
            cuda=True,
        )
        ctgan.fit(df_cls)

        num_samples = samples_per_class_map.get(cls, 0)
        syn_cls = ctgan.sample(num_samples)
        gan_synthetic_data.append(syn_cls)

    # 合并所有类生成的数据
    df_gan_all = pd.concat(gan_synthetic_data, ignore_index=True)
    return df_gan_all

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

    def load_and_filter_data(self):
        """加载数据并过滤Unknown样本"""
        json_files = [f for f in os.listdir(self.input_dir) if f.endswith('.json')]
        all_samples = []

        for json_file in json_files:
            with open(os.path.join(self.input_dir, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)

                for sample in data:
                    # 显式提取所有字段（确保无遗漏）
                    processed = {
                        'Serial': sample.get('Serial'),
                        'ProductName': sample.get('ProductName'),
                        'Timestamp': sample.get('Timestamp'),
                        'PA Status': sample.get('PA Status'),  # 关键修复：显式提取
                        'Parameters': sample.get('Parameters', {})
                    }
                    if processed['PA Status'] != 'Unknown':  # 过滤Unknown
                        all_samples.append(processed)

        print(f"加载样本数: {len(all_samples)} (已过滤Unknown状态)")
        return pd.DataFrame(all_samples)

    @staticmethod
    def process_numeric_features(params):
        """处理数值型特征，按照需求合并相关特征"""
        numeric_values = {}

        # 1.1 处理DpaVddSv - 合并所有DpaVddSv参数
        dpa_values = []
        for i in range(8):
            key = f'DpaVddSv:{i}'
            if key in params:
                val = params[key].get('Value', np.nan)
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
                val = params[key].get('Value', np.nan)
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
                val = params[key].get('Value', np.nan)
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
                val = params[key].get('Value', np.nan)
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
                val = params[key].get('Value', np.nan)
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
                val = params[key].get('Value', np.nan)
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
                val = params[feat].get('Value', np.nan)
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

        for idx, row in enumerate(df.itertuples()):
            # 调试：打印第一条记录的结构

            params = getattr(row, 'Parameters', {})
            is_valid = True

            # ========== 1. 数值特征有效性检查(使用原始特征列表) ==========
            for feat in self.raw_numeric_features:
                if feat in params:
                    val = params[feat].get('Value', np.nan)
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
                        val = params.get(feat, {}).get('Value', 'unknown')
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
        # """数据预处理流程"""
        #
        # # 1. 编码分类特征
        # df_encoded = self.encoder.transform(df)
        #
        # # 2. 数值特征处理
        # numeric_data = df_encoded[self.numeric_features].copy()
        #
        # # 2.1 处理无限大值
        # numeric_data = numeric_data.replace([np.inf, -np.inf], np.nan)
        #
        # # 2.2 处理全空列（填充0）
        # empty_cols = numeric_data.columns[numeric_data.isna().all()].tolist()
        # for col in empty_cols:
        #     numeric_data[col] = 0
        #
        # # 2.3 中位数填充其他缺失值
        # imputer = SimpleImputer(strategy='median')
        # numeric_data_imputed = pd.DataFrame(
        #     imputer.fit_transform(numeric_data),
        #     columns=numeric_data.columns
        # )
        #
        # df_generate = gan_generator(df)
        #
        #
        # # 3. 数据标准化（带异常值处理）
        # scaler = StandardScaler()
        #
        # # 3.1 检查是否存在零方差特征
        # variances = numeric_data_imputed.var()
        # zero_var_cols = variances[variances == 0].index.tolist()
        # if zero_var_cols:
        #     print(f"警告: 以下特征方差为零，标准化时将跳过: {zero_var_cols}")
        #     # 对这些列不进行标准化（保持原值）
        #     non_zero_var_cols = [col for col in numeric_data_imputed.columns if col not in zero_var_cols]
        #     scaled_values = scaler.fit_transform(numeric_data_imputed[non_zero_var_cols])
        #     numeric_data_imputed[non_zero_var_cols] = scaled_values
        # else:
        #     numeric_data_imputed[:] = scaler.fit_transform(numeric_data_imputed)
        #
        # df_encoded[self.numeric_features] = numeric_data_imputed
        #
        # return df_encoded, scaler
        """数据预处理流程，返回归一化后的原始数据 & GAN数据"""

        # 0. 标签标准化处理：添加 __target__ 列
        label_map = {'Normal': 0, 'PA might broken': 1, 'PA broken': 2}
        df['PA Status'].map(label_map)

        # 1. 编码分类特征
        df_encoded = self.encoder.transform(df)

        # 2. 数值特征处理（原始数据）
        numeric_data = df_encoded[self.numeric_features].copy()
        numeric_data = numeric_data.replace([np.inf, -np.inf], np.nan)

        empty_cols = numeric_data.columns[numeric_data.isna().all()].tolist()
        for col in empty_cols:
            numeric_data[col] = 0

        imputer = SimpleImputer(strategy='median')
        numeric_data_imputed = pd.DataFrame(
            imputer.fit_transform(numeric_data),
            columns=numeric_data.columns
        )

        # 3. 使用填充后的 df_encoded_copy 生成合成数据
        df_encoded[self.numeric_features] = numeric_data_imputed

        df_generated = gan_generator(df_encoded)

        # 4. 标准化原始数据
        scaler = StandardScaler()
        variances = numeric_data_imputed.var()
        zero_var_cols = variances[variances == 0].index.tolist()

        if zero_var_cols:
            print(f"警告: 以下特征方差为零，标准化时将跳过: {zero_var_cols}")
            non_zero_var_cols = [col for col in numeric_data_imputed.columns if col not in zero_var_cols]
            scaled_values = scaler.fit_transform(numeric_data_imputed[non_zero_var_cols])
            numeric_data_imputed[non_zero_var_cols] = scaled_values
        else:
            numeric_data_imputed[:] = scaler.fit_transform(numeric_data_imputed)

        df_encoded[self.numeric_features] = numeric_data_imputed


        # 5. 对 GAN 数据的数值列进行相同处理（注意填充方式要保持一致）
        numeric_gan = df_generated[self.numeric_features].copy()
        numeric_gan = numeric_gan.replace([np.inf, -np.inf], np.nan)

        # 仅标准化，不再做填充处理
        if zero_var_cols:
            numeric_gan[non_zero_var_cols] = scaler.transform(numeric_gan[non_zero_var_cols])
        else:
            numeric_gan[:] = scaler.transform(numeric_gan)

        # 替换回 df_generated
        df_generated[self.numeric_features] = numeric_gan

        return df_encoded, df_generated, scaler

    def split_and_save_data(self, df_encoded, df_generated):
        """数据集划分与保存"""
        # 转换标签
        label_map = {'Normal': 0, 'PA might broken': 1, 'PA broken': 2}
        y_real = df_encoded['PA Status'].map(label_map)
        x_real = df_encoded.drop('PA Status', axis=1)

        y_gan = df_generated['PA Status']
        x_gan = df_generated.drop('PA Status', axis=1)

        # 3. 划分验证集与测试集（原始数据：20% + 20%）
        X_val, X_test, y_val, y_test = train_test_split(
            x_real, y_real, test_size=0.5, random_state=42, stratify=y_real)

        # 4. GAN 生成数据作为训练集（不做再划分）
        X_train, y_train = x_gan, y_gan

        # 保存数据集
        save_paths = {
            'train.csv': (X_train, y_train),
            'val.csv': (X_val, y_val),
            'ctgan.csv': (X_test, y_test)
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
        processed_df, generated_df, scaler = self.preprocess_data(feature_df)

        # 4. 数据集划分与保存
        self.split_and_save_data(processed_df, generated_df)

        # 5. 保存预处理对象
        import joblib
        joblib.dump(self.encoder, os.path.join(self.output_dir, 'feature_encoder.pkl'))
        joblib.dump(scaler, os.path.join(self.output_dir, 'scaler.pkl'))

        print("预处理流程完成")


if __name__ == '__main__':
    # 使用示例
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../'))
    INPUT_DIR = os.path.join(ROOT_DIR, 'files_for_training')
    OUTPUT_DIR = os.path.join(ROOT_DIR, 'processed_datasets')

    processor = TrainingDataProcessor(INPUT_DIR, OUTPUT_DIR)
    processor.process()
