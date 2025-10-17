import json
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import joblib
from typing import Dict, List, Set
import traceback
from tools.app.services.model_training.preprocessor.feature_encoder import FeatureEncoder


class TrainingDataProcessor:
    """训练数据预处理"""
    def __init__(self):
        self.raw_data = None
        self.processed_samples = None
        self.selected_samples: Set[int] = set()
        self.selected_input_features: Set[str] = set()
        self.selected_output_features: Set[str] = set()
        # 初始化特征编码器
        self.encoder = FeatureEncoder()

        ################################################################################################################
        # 定义特征分组
        ################################################################################################################
        # 一. 输入特征 - X
        # 数值型特征
        self.numeric_features = [
            'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IDpaSv:.2', 'IDpaSv:.3',
            'IMpaSv:.0', 'IMpaSv:.1', 'IMpaSv:.2', 'IMpaSv:.3',
            'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
            'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
            'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        # 原始数值特征(用于合并)
        self.raw_numeric_features = [
            'DpaVddSv:0', 'DpaVddSv:1', 'DpaVddSv:2', 'DpaVddSv:3',
            'DpaVddSv:4', 'DpaVddSv:5', 'DpaVddSv:6', 'DpaVddSv:7',
            'PaVddSv:0', 'PaVddSv:1', 'PaVddSv:2', 'PaVddSv:3',
            'PaVddSv:4', 'PaVddSv:5', 'PaVddSv:6', 'PaVddSv:7',
            'IDpaSv:0.0', 'IDpaSv:0.1', 'IDpaSv:0.2', 'IDpaSv:0.3',
            'IDpaSv:1.0', 'IDpaSv:1.1', 'IDpaSv:1.2', 'IDpaSv:1.3',
            'IDpaSv:2.0', 'IDpaSv:2.1', 'IDpaSv:2.2', 'IDpaSv:2.3',
            'IDpaSv:3.0', 'IDpaSv:3.1', 'IDpaSv:3.2', 'IDpaSv:3.3',
            'IDpaSv:4.0', 'IDpaSv:4.1', 'IDpaSv:4.2', 'IDpaSv:4.3',
            'IDpaSv:5.0', 'IDpaSv:5.1', 'IDpaSv:5.2', 'IDpaSv:5.3',
            'IDpaSv:6.0', 'IDpaSv:6.1', 'IDpaSv:6.2', 'IDpaSv:6.3',
            'IDpaSv:7.0', 'IDpaSv:7.1', 'IDpaSv:7.2', 'IDpaSv:7.3',
            'IMpaSv:0.0', 'IMpaSv:0.1', 'IMpaSv:0.2', 'IMpaSv:0.3',
            'IMpaSv:1.0', 'IMpaSv:1.1', 'IMpaSv:1.2', 'IMpaSv:1.3',
            'IMpaSv:2.0', 'IMpaSv:2.1', 'IMpaSv:2.2', 'IMpaSv:2.3',
            'IMpaSv:3.0', 'IMpaSv:3.1', 'IMpaSv:3.2', 'IMpaSv:3.3',
            'IMpaSv:4.0', 'IMpaSv:4.1', 'IMpaSv:4.2', 'IMpaSv:4.3',
            'IMpaSv:5.0', 'IMpaSv:5.1', 'IMpaSv:5.2', 'IMpaSv:5.3',
            'IMpaSv:6.0', 'IMpaSv:6.1', 'IMpaSv:6.2', 'IMpaSv:6.3',
            'IMpaSv:7.0', 'IMpaSv:7.1', 'IMpaSv:7.2', 'IMpaSv:7.3',
        ]

        self.other_numeric_features = [
            'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
            'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
            'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        # 分类型特征(字符+布尔型)
        self.categorical_features = [
            'autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable', 'desc', 'dpGainLoopEnable', 'dpTsEnable',
            'dpd', 'dpdAutoStart', 'gainAutoStart', 'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState',
            'islastDelEstFracSuccess', 'linearizationStateMachine', 'runMode', 'shpAutoStart', 'shpGanAlgEnabled',
            'shpGanAlgFunctionStatus', 'shpGanAlgHwCapablility', 'status', 'statusBit', 'subId', 'torSupported'
        ]

        self.bool_categorical_features = ['autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable',
                                          'dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart', 'gainAutoStart',
                                          'ganBoostModeEnable', 'islastDelEstFracSuccess', 'shpAutoStart',
                                          'shpGanAlgEnabled', 'shpGanAlgFunctionStatus', 'shpGanAlgHwCapablility',
                                          'torSupported']

        # 二. 输出特征 - Y
        self.output_features = ['PA Status Pattern 1', 'PA Status Pattern 2', 'PA Status Repair Info']

    @staticmethod
    def load_data(file_paths: List[str]) -> pd.DataFrame:
        """加载JSON数据文件"""
        all_samples = []

        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_samples.extend(data)
            except Exception as e:
                print(f"读取文件 {file_path} 时出错: {str(e)}")
                continue

        return pd.DataFrame(all_samples)

    def extract_numeric_features(self, params: Dict) -> Dict:
        """
        提取数值型特征：合并 + 提取
        合并: DpaVddSv, PaVddSv, IDpaSv:.0, IDpaSv:.1, IDpaSv:.2, IDpaSv:.3; IMpaSv:.0, IMpaSv:.1, IMpaSv:.2, IMpaSv:.3
        提取: LinAlarm, dpdNomPwr, dpdRestartCounter, powerClass, powerLevel, ...
        """
        numeric_values = {}

        # 合并 DpaVddSv 和 PaVddSv
        def merge_voltage_features(prefix, params, range_count=8):
            """提取指定前缀的参数值(电压)并计算平均值"""
            values = []
            for i in range(range_count):
                key = f'{prefix}:{i}'
                val = params.get(key)
                if val not in ['', None]:
                    try:
                        values.append(float(val))
                    except (ValueError, TypeError):
                        pass
            return np.nanmean(values) if values else np.nan

        # 如果有非空值则取平均值，否则保持NaN
        numeric_values['DpaVddSv'] = merge_voltage_features('DpaVddSv', params)
        numeric_values['PaVddSv'] = merge_voltage_features('PaVddSv', params)

        # 合并 IDpaSv:.0, IDpaSv:.1, IDpaSv:.2, IDpaSv:.3 和 IMpaSv:.0, IMpaSv:.1, IMpaSv:.2, IMpaSv:.3
        def merge_current_features(prefix, suffixes, params, range_count=8):
            """提取指定前缀和各个后缀的参数值(电流)并计算平均值"""
            result = {suffix: [] for suffix in suffixes}

            for i in range(range_count):
                for suffix in suffixes:
                    key = f'{prefix}:{i}.{suffix}'
                    val = params.get(key)
                    if val not in ['', None]:
                        try:
                            result[suffix].append(float(val))
                        except (ValueError, TypeError):
                            pass
            return result

        suffixes = ['0', '1', '2', '3']

        # 如果有非空值则取平均值，否则保持NaN
        for prefix in ['IDpaSv', 'IMpaSv']:
            data = merge_current_features(prefix, suffixes, params)
            for suffix in suffixes:
                numeric_values[f'{prefix}:.{suffix}'] = np.nanmean(data[suffix]) if data[suffix] else np.nan

        # 处理其他数值型属性 - 这是需要补充的部分
        for feat in self.other_numeric_features:
            if feat in params:
                val = params[feat]
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

    def extract_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取所有特征，创建样本数据库"""
        all_features = {}

        # 初始化特征字典
        for feature in self.numeric_features + self.categorical_features + self.output_features:
            all_features[feature] = []

        all_features['ProductName'] = []
        all_features['Serial'] = []
        all_features['Timestamp'] = []

        valid_samples = []

        for idx, row in enumerate(df.itertuples()):
            try:
                # 获取原始数据行
                original_row = df.iloc[idx] if hasattr(df, 'iloc') else row

                # 提取基础信息
                product_name = getattr(row, 'ProductName', '') if hasattr(row, 'ProductName') else original_row.get(
                    'ProductName', '')
                serial = getattr(row, 'Serial', '') if hasattr(row, 'Serial') else original_row.get('Serial',
                                                                                                    f'sample_{idx}')
                timestamp = getattr(row, 'Timestamp', '') if hasattr(row, 'Timestamp') else original_row.get(
                    'Timestamp', '')

                all_features['ProductName'].append(product_name)
                all_features['Serial'].append(serial)
                all_features['Timestamp'].append(timestamp)

                # 提取Parameters字典
                params = {}
                if hasattr(row, 'Parameters'):
                    params = getattr(row, 'Parameters', {})
                else:
                    params = original_row.get('Parameters', {})

                ########################################################################################################
                # 提取数值特征 - 合并+提取
                numeric_values = self.extract_numeric_features(params)
                for feat in self.numeric_features:
                    all_features[feat].append(numeric_values.get(feat, np.nan))

                # 提取分类特征
                for feat in self.categorical_features:
                    val = params.get(feat, '')

                    # 特殊处理布尔型特征
                    if feat in self.bool_categorical_features:
                        # 布尔型特征可能以布尔值或字符串形式存在
                        if isinstance(val, bool):
                            all_features[feat].append(str(val).lower())
                        elif val in [True, 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes', 'ON', 'On', 'on',
                                     'ENABLED', 'Enabled', 'enabled', 'ENABLE', 'Enable', 'enable', '1', 1]:
                            all_features[feat].append('true')
                        elif val in [False, 'FALSE', 'False', 'false', 'NO', 'No', 'no', 'OFF', 'Off', 'off',
                                     'DISABLED', 'Disabled', 'disabled', 'DISABLE', 'Disable', 'disable', '0', 0]:
                            all_features[feat].append('false')
                        else:
                            # 对于其他情况，保持原样
                            all_features[feat].append(str(val).strip() if val not in [None, ''] else '')
                    else:
                        # 非布尔型分类特征
                        all_features[feat].append(str(val).strip() if val not in [None, ''] else '')

                # 提取输出特征
                for feat in self.output_features:
                    # 尝试从不同位置获取输出特征值
                    val = ''
                    if hasattr(row, feat):
                        val = getattr(row, feat, '')
                    elif feat in original_row:
                        val = original_row[feat]
                    else:
                        # 如果以上方法都失败，尝试从Parameters中获取
                        val = params.get(feat, '')

                    # 确保值不为空
                    if val in [None, '']:
                        print(f"警告: 样本 {idx} 的输出特征 '{feat}' 为空")

                    all_features[feat].append(str(val).strip() if val not in [None, ''] else '')

                valid_samples.append(idx)
                ########################################################################################################

            except Exception as e:
                print(f"处理样本 {idx} 时出错: {str(e)}")
                continue

        # 创建DataFrame
        feature_df = pd.DataFrame(all_features)

        # 检查输出特征的值分布
        print(f"成功处理 {len(valid_samples)} 个样本")
        for feat in self.output_features:
            value_counts = feature_df[feat].value_counts()
            print(f"输出特征 '{feat}' 的值分布:")
            for value, count in value_counts.items():
                print(f"  - '{value}': {count} 个样本")

        return feature_df

    def process_selected_data(self, output_dir: str):
        """处理用户选择的数据"""
        try:
            # 检查选择
            if not self.selected_samples:
                raise ValueError("请至少选择一个样本")
            if not self.selected_input_features:
                raise ValueError("请至少选择一个输入特征")
            if not self.selected_output_features:
                raise ValueError("请至少选择一个输出特征")

            # 过滤选中的样本和特征
            selected_indices = list(self.selected_samples)
            input_feats = list(self.selected_input_features)
            output_feats = list(self.selected_output_features)

            filtered_data = self.processed_samples.iloc[selected_indices].copy()

            # 检查并剔除输出特征中包含'Unknown'的样本
            unknown_mask = pd.Series([False] * len(filtered_data), index=filtered_data.index)
            for output_feat in output_feats:
                if output_feat not in filtered_data.columns:
                    print(f"警告: 输出特征 '{output_feat}' 不在数据中，跳过")
                    continue

                # 检查每个输出特征中的Unknown值（不区分大小写）
                # 确保使用.str访问器，即使列不是字符串类型
                feat_series = filtered_data[output_feat].astype(str)
                feat_unknown_mask = feat_series.str.lower() == 'unknown'

                # 确保feat_unknown_mask是Series
                if not isinstance(feat_unknown_mask, pd.Series):
                    feat_unknown_mask = pd.Series([feat_unknown_mask] * len(filtered_data),
                                                  index=filtered_data.index)

                # 打印Unknown样本统计
                if feat_unknown_mask.any():
                    unknown_count = feat_unknown_mask.sum()
                    print(f"输出特征 '{output_feat}' 中发现 {unknown_count} 个Unknown样本")

                unknown_mask = unknown_mask | feat_unknown_mask

            if unknown_mask.any():
                unknown_count = unknown_mask.sum()
                # 剔除包含Unknown的样本
                filtered_data = filtered_data[~unknown_mask]
                print(f"已剔除 {unknown_count} 个包含Unknown值的样本")

            if filtered_data.empty:
                raise ValueError("没有有效的样本可用于训练")

            # 分离特征和目标
            X = filtered_data[input_feats].copy()
            y_dict = {}

            for output_feat in output_feats:
                # 标签转换：Normal->1, 其他->0
                y = filtered_data[output_feat].copy()

                # 确保标签转换正确执行
                def convert_label(label):
                    label_str = str(label).strip()
                    # 针对不同的输出特征使用不同的转换规则
                    if output_feat == 'PA Status Pattern 1':
                        if label_str == 'Normal':
                            return 1
                        elif label_str == 'PA might abnormal':
                            return 0
                        elif label_str == 'PA abnormal':
                            return 0
                        else:
                            print(f"警告: 未知标签值 '{label}'，已转换为0")
                            return 0

                    elif output_feat == 'PA Status Pattern 2':
                        if label_str == 'Normal':
                            return 1
                        elif label_str == 'PA abnormal':
                            return 0
                        elif label_str == 'PA abnormal lin':
                            return 0
                        else:
                            print(f"警告: 未知标签值 '{label}'，已转换为0")
                            return 0

                    elif output_feat == 'PA Status Repair Info':
                        # 根据实际情况调整这个特征的转换规则
                        if label_str == 'Normal':
                            return 1
                        elif label_str == 'PA abnormal':
                            return 0
                        else:
                            print(f"警告: 未知标签值 '{label}'，已转换为0")
                            return 0

                    else:
                        # 通用规则
                        if 'Normal' in label_str:
                            return 1
                        else:
                            return 0

                y_converted = y.apply(convert_label)
                y_dict[output_feat] = y_converted

                # 打印标签分布信息
                print(f"输出特征 '{output_feat}' 标签分布:")
                print(f"  - 正常样本 (1): {y_converted.sum()}")
                print(f"  - 异常样本 (0): {len(y_converted) - y_converted.sum()}")

            # 处理数值特征的空值和inf
            numeric_feats = [feat for feat in input_feats if feat in self.numeric_features]
            if numeric_feats:
                # 替换inf/-inf
                X[numeric_feats] = X[numeric_feats].replace([np.inf, -np.inf], [1000, -1000])

                # 填充空值
                imputer = SimpleImputer(strategy='median')

                # 确保只对存在的数值特征进行处理
                existing_numeric_feats = [feat for feat in numeric_feats if feat in X.columns]

                # 检查哪些特征有非空值
                features_with_values = []
                features_without_values = []

                for feat in existing_numeric_feats:
                    if X[feat].notna().any():  # 检查是否有非空值
                        features_with_values.append(feat)
                    else:
                        features_without_values.append(feat)

                # 只对有值的特征使用Imputer
                if features_with_values:
                    X[features_with_values] = imputer.fit_transform(X[features_with_values])

                # 对没有值的特征填充0
                if features_without_values:
                    X[features_without_values] = 0
                    print(f"警告: 以下特征没有观测值，已用0填充: {features_without_values}")

            # 处理分类特征编码
            categorical_feats = [feat for feat in input_feats if feat in self.categorical_features]
            if categorical_feats:
                # 确保只对存在的分类特征进行处理
                existing_categorical_feats = [feat for feat in categorical_feats if feat in X.columns]
                if existing_categorical_feats:
                    X_encoded = self.encoder.transform(X[existing_categorical_feats])

                    # 确保编码后的特征与原始特征列数一致
                    if len(X_encoded.columns) != len(existing_categorical_feats):
                        print(
                            f"警告: 编码后特征数量 ({len(X_encoded.columns)}) 与原始分类特征数量 ({len(existing_categorical_feats)}) 不一致")
                        # 尝试重新对齐列
                        missing_cols = set(existing_categorical_feats) - set(X_encoded.columns)
                        if missing_cols:
                            for col in missing_cols:
                                X_encoded[col] = -1  # 用-1填充缺失的列

                    # 确保索引一致
                    X_encoded.index = X.index

                    # 删除原始分类特征，添加编码后的特征
                    X = X.drop(existing_categorical_feats, axis=1)
                    X = pd.concat([X, X_encoded], axis=1)

            # 数值特征标准化
            if numeric_feats:
                scaler = StandardScaler()
                # 只对存在的数值特征进行标准化
                existing_numeric_feats = [feat for feat in numeric_feats if feat in X.columns]
                if existing_numeric_feats:
                    X[existing_numeric_feats] = scaler.fit_transform(X[existing_numeric_feats])
            else:
                scaler = None

            # 数据集划分和保存
            os.makedirs(output_dir, exist_ok=True)

            # 对于每个输出特征，分别创建数据集
            for output_feat, y in y_dict.items():
                # 划分数据集
                X_train, X_temp, y_train, y_temp = train_test_split(
                    X, y, test_size=0.4, random_state=42, stratify=y)
                X_val, X_test, y_val, y_test = train_test_split(
                    X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

                # 保存数据集
                feat_output_dir = os.path.join(output_dir, f"dataset_{output_feat.replace(' ', '_')}")
                os.makedirs(feat_output_dir, exist_ok=True)

                pd.concat([X_train, y_train.rename('target')], axis=1).to_csv(
                    os.path.join(feat_output_dir, 'train.csv'), index=False)
                pd.concat([X_val, y_val.rename('target')], axis=1).to_csv(
                    os.path.join(feat_output_dir, 'val.csv'), index=False)
                pd.concat([X_test, y_test.rename('target')], axis=1).to_csv(
                    os.path.join(feat_output_dir, 'test.csv'), index=False)

                # 保存预处理对象
                if scaler:
                    joblib.dump(scaler, os.path.join(feat_output_dir, 'scaler.pkl'))
                joblib.dump(self.encoder, os.path.join(feat_output_dir, 'encoder.pkl'))

                # 保存特征元数据
                metadata = {
                    'input_features': input_feats,
                    'output_feature': output_feat,
                    'numeric_features': numeric_feats,
                    'categorical_features': categorical_feats,
                    'selected_samples_count': len(filtered_data)
                }

                with open(os.path.join(feat_output_dir, 'metadata.json'), 'w') as f:
                    json.dump(metadata, f, indent=2)

            return True, f"成功生成数据集到: {output_dir}"

        except Exception as e:
            return False, f"处理数据时出错: {str(e)}\n{traceback.format_exc()}"
