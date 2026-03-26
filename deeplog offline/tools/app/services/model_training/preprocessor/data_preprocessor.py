# -*- coding: utf-8 -*-
"""
训练数据预处理模块（最终版）
- 保持原有预处理/划分/保存逻辑
- 新增：当未选择自定义目录时，仅保存到两个固定目录（files_for_training / processed_dataset）
- 若选择了自定义目录，则只保存到该路径，不再进行双份自动保存
- 修复：采用无锁复制(read_bytes/write_bytes) + 重试，避免 Windows 上 PermissionError(13)
"""

import json
import os
import numpy as np
import pandas as pd
from pathlib import Path
import time
import joblib
import traceback
from typing import Dict, List, Set, Tuple

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from tools.app.services.model_training.preprocessor.feature_encoder import FeatureEncoder
from tools.app.services.model_training.preprocessor.cgan_generator import ProductCGANGenerator


class TrainingDataProcessor:
    """训练数据预处理"""

    def __init__(self):
        self.raw_data = None
        self.processed_samples = None
        self.selected_samples: Set[int] = set()
        self.selected_input_features: Set[str] = set()
        self.selected_output_features: Set[str] = set()

        # 初始化特征编码器/CGAN
        self.encoder = FeatureEncoder()
        self.cgan_generator = ProductCGANGenerator()

        ################################################################################################
        # 定义特征分组（与你原文件一致）
        ################################################################################################

        # 一. 输入特征 - X
        self.numeric_features = [
            'DpaVddSv', 'PaVddSv',
            'IDpaSv:.0', 'IDpaSv:.1', 'IDpaSv:.2', 'IDpaSv:.3',
            'IMpaSv:.0', 'IMpaSv:.1', 'IMpaSv:.2', 'IMpaSv:.3',
            'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
            'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
            'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        # 原始数值特征（用于从 JSON 的 Parameters 合并）
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

        # 分类型特征（字符/布尔）
        self.categorical_features = [
            'autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable', 'desc', 'dpGainLoopEnable', 'dpTsEnable',
            'dpd', 'dpdAutoStart', 'gainAutoStart', 'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState',
            'islastDelEstFracSuccess', 'linearizationStateMachine', 'runMode', 'shpAutoStart', 'shpGanAlgEnabled',
            'shpGanAlgFunctionStatus', 'shpGanAlgHwCapablility', 'status', 'statusBit', 'subId', 'torSupported'
        ]
        self.bool_categorical_features = [
            'autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable',
            'dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart', 'gainAutoStart',
            'ganBoostModeEnable', 'islastDelEstFracSuccess', 'shpAutoStart',
            'shpGanAlgEnabled', 'shpGanAlgFunctionStatus', 'shpGanAlgHwCapablility',
            'torSupported'
        ]

        # 二. 输出特征 - Y
        self.output_features = ['PA Status Pattern 1', 'PA Status Pattern 2', 'PA Status Repair Info', 'Repair Info Details']

    # =========================
    # 固定目录 & 镜像复制（无锁+重试）
    # =========================
    def _current_eid(self) -> str:
        """以当前用户主目录名作为 EID（Windows: C:/Users/<EID>）。"""
        up = os.environ.get("USERPROFILE")
        if up:
            try:
                return Path(up).name
            except Exception:
                pass
        try:
            return Path.home().name
        except Exception:
            return "UnknownEID"

    def _fixed_bases(self) -> Tuple[Path, Path]:
        """
        返回两个固定输出基目录（自动带上 <EID>）：
          files_for_training / processed_dataset
        并确保目录已创建。
        """
        eid = self._current_eid()
        base = Path(f"C:/Users/{eid}/OneDrive - Ericsson/Desktop/deeplog/tools/data")
        d1 = base / "files_for_training"
        d2 = base / "processed_dataset"
        d1.mkdir(parents=True, exist_ok=True)
        d2.mkdir(parents=True, exist_ok=True)
        return d1, d2

    def _safe_copy(self, src: Path, dst: Path) -> None:
        """无锁复制：read_bytes/write_bytes + 重试（规避 PermissionError）。"""
        if not src.exists():
            return
        last_err = None
        for attempt in range(6):
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                data = src.read_bytes()
                dst.write_bytes(data)
                return
            except Exception as e:
                last_err = e
                time.sleep(0.2 * (attempt + 1))
        if last_err is not None:
            print(f"[mirror] 复制文件 {src.name} 到 {dst.parent} 失败: {repr(last_err)}")

    def _mirror_to_other_fixed(self, src_dir: Path, dataset_folder: str) -> None:
        """
        仅镜像到“另一个固定目录”：
          - 若源目录位于 base1 → 复制到 base2
          - 若源目录位于 base2 → 复制到 base1
          - 若源目录不在任一固定目录 → 复制到两边
        """
        if not isinstance(src_dir, Path):
            src_dir = Path(src_dir)
        base1, base2 = self._fixed_bases()

        src_dir_str = str(src_dir).replace("\\", "/")
        b1 = str(base1).replace("\\", "/")
        b2 = str(base2).replace("\\", "/")

        if src_dir_str.startswith(b1):
            targets = [base2 / dataset_folder]
        elif src_dir_str.startswith(b2):
            targets = [base1 / dataset_folder]
        else:
            targets = [base1 / dataset_folder, base2 / dataset_folder]

        files = ["train.csv", "val.csv", "test.csv", "scaler.pkl", "encoder.pkl", "metadata.json"]
        for tdir in targets:
            tdir.mkdir(parents=True, exist_ok=True)
            for fname in files:
                self._safe_copy(src_dir / fname, tdir / fname)

    # =========================
    # 数据加载与特征提取（与你原文件一致）
    # =========================
    @staticmethod
    def load_data(file_paths: List[str]) -> pd.DataFrame:
        """加载 JSON 数据文件（每个文件是样本列表/对象列表）"""
        all_samples = []
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                all_samples.extend(data)
            except Exception as e:
                print(f"读取文件 {file_path} 时出错: {str(e)}")
        return pd.DataFrame(all_samples)

    def extract_numeric_features(self, params: Dict) -> Dict:
        """
        提取数值型特征：合并 + 提取
        合并: DpaVddSv, PaVddSv, IDpaSv:.0~.3, IMpaSv:.0~.3
        提取: LinAlarm, dpdNomPwr, dpdRestartCounter, powerClass, powerLevel, ...
        """
        numeric_values = {}

        # 合并 DpaVddSv / PaVddSv（每个 0..7 取平均）
        def merge_voltage_features(prefix, params, range_count=8):
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

        numeric_values['DpaVddSv'] = merge_voltage_features('DpaVddSv', params)
        numeric_values['PaVddSv'] = merge_voltage_features('PaVddSv', params)

        # 合并 IDpaSv / IMpaSv 各 .0~.3（每个后缀分别对 0..7 取平均）
        def merge_current_features(prefix, suffixes, params, range_count=8):
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
        for prefix in ['IDpaSv', 'IMpaSv']:
            data = merge_current_features(prefix, suffixes, params)
            for suffix in suffixes:
                numeric_values[f'{prefix}:.{suffix}'] = np.nanmean(data[suffix]) if data[suffix] else np.nan

        # 处理其它直接数值特征
        for feat in self.other_numeric_features:
            if feat in params:
                val = params[feat]
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

    def extract_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取所有特征，创建样本表"""
        all_features = {}
        for feature in self.numeric_features + self.categorical_features + self.output_features:
            all_features[feature] = []
        all_features['ProductName'] = []
        all_features['Serial'] = []
        all_features['Timestamp'] = []

        valid_samples = []

        for idx, row in enumerate(df.itertuples()):
            try:
                original_row = df.iloc[idx] if hasattr(df, 'iloc') else row

                # 基础信息
                product_name = getattr(row, 'ProductName', '') if hasattr(row, 'ProductName') else original_row.get('ProductName', '')
                serial = getattr(row, 'Serial', '') if hasattr(row, 'Serial') else original_row.get('Serial', f'sample_{idx}')
                timestamp = getattr(row, 'Timestamp', '') if hasattr(row, 'Timestamp') else original_row.get('Timestamp', '')
                all_features['ProductName'].append(product_name)
                all_features['Serial'].append(serial)
                all_features['Timestamp'].append(timestamp)

                # Parameters
                if hasattr(row, 'Parameters'):
                    params = getattr(row, 'Parameters', {})
                else:
                    params = original_row.get('Parameters', {})

                # 数值特征（合并 + 提取）
                numeric_values = self.extract_numeric_features(params)
                for feat in self.numeric_features:
                    all_features[feat].append(numeric_values.get(feat, np.nan))

                # 分类特征
                for feat in self.categorical_features:
                    val = params.get(feat, '')
                    if feat in self.bool_categorical_features:
                        if isinstance(val, bool):
                            all_features[feat].append(str(val).lower())
                        elif val in [True, 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes', 'ON', 'On', 'on',
                                     'ENABLED', 'Enabled', 'enabled', 'ENABLE', 'Enable', 'enable', '1', 1]:
                            all_features[feat].append('true')
                        elif val in [False, 'FALSE', 'False', 'false', 'NO', 'No', 'no', 'OFF', 'Off', 'off',
                                     'DISABLED', 'Disabled', 'disabled', 'DISABLE', 'Disable', 'disable', '0', 0]:
                            all_features[feat].append('false')
                        else:
                            all_features[feat].append(str(val).strip() if val not in [None, ''] else '')
                    else:
                        all_features[feat].append(str(val).strip() if val not in [None, ''] else '')

                # 输出特征
                for feat in self.output_features:
                    val = ''
                    if hasattr(row, feat):
                        val = getattr(row, feat, '')
                    elif feat in original_row:
                        val = original_row[feat]
                    else:
                        val = params.get(feat, '')
                    if val in [None, '']:
                        print(f"警告: 样本 {idx} 的输出特征 '{feat}' 为空")
                    all_features[feat].append(str(val).strip() if val not in [None, ''] else '')

                valid_samples.append(idx)

            except Exception as e:
                print(f"处理样本 {idx} 时出错: {str(e)}")
                continue

        feature_df = pd.DataFrame(all_features)

        print(f"成功处理 {len(valid_samples)} 个样本")
        for feat in self.output_features:
            value_counts = feature_df[feat].value_counts()
            print(f"输出特征 '{feat}' 的值分布:")
            for value, count in value_counts.items():
                print(f" - '{value}': {count} 个样本")

        return feature_df

    # =========================
    # 选择数据 → 预处理 → 划分 → 保存（含“选择性跳过自定义路径”策略）
    # =========================
    def process_selected_data(self, output_dir: str, use_cgan_balance: bool = False, balance_ratio: float = 1.0):
        """
        处理用户选择的数据
        Args:
            output_dir: 输出目录
                - 若为空/默认值（未点击“选择输出目录”按钮）：主写入 = 固定目录 #1，并镜像到固定目录 #2
                - 若为非空自定义路径：仅保存到该路径（不再自动保存两份）
            use_cgan_balance: 是否使用 CGAN 平衡数据
            balance_ratio: 目标平衡比例（少数类:多数类）
        """
        try:
            # —— 识别是否使用“自定义目录” —— #
            auto_tokens = {None, "", ".", "./", ".\\", "__AUTO__", "__auto__", "%AUTO%", "%auto%"}
            use_custom_output = bool(output_dir) and (str(output_dir).strip() not in auto_tokens)

            # 基本检查
            if not self.selected_samples:
                raise ValueError("请至少选择一个样本")
            if not self.selected_input_features:
                raise ValueError("请至少选择一个输入特征")
            if not self.selected_output_features:
                raise ValueError("请至少选择一个输出特征")

            # 过滤样本、特征
            selected_indices = list(self.selected_samples)
            input_feats = list(self.selected_input_features)
            output_feats = list(self.selected_output_features)
            filtered_data = self.processed_samples.iloc[selected_indices].copy()

            # 剔除 Unknown
            unknown_mask = pd.Series([False] * len(filtered_data), index=filtered_data.index)
            for output_feat in output_feats:
                if output_feat not in filtered_data.columns:
                    print(f"警告: 输出特征 '{output_feat}' 不在数据中，跳过")
                    continue
                feat_series = filtered_data[output_feat].astype(str)
                feat_unknown_mask = feat_series.str.lower() == 'unknown'
                if not isinstance(feat_unknown_mask, pd.Series):
                    feat_unknown_mask = pd.Series([feat_unknown_mask] * len(filtered_data), index=filtered_data.index)
                if feat_unknown_mask.any():
                    print(f"输出特征 '{output_feat}' 中发现 {feat_unknown_mask.sum()} 个 Unknown 样本")
                unknown_mask = unknown_mask | feat_unknown_mask

            if unknown_mask.any():
                filtered_data = filtered_data[~unknown_mask]
                print(f"已剔除 {unknown_mask.sum()} 个包含 Unknown 值的样本")
            if filtered_data.empty:
                raise ValueError("没有有效的样本可用于训练")

            # 可选：CGAN 平衡
            generated_data = pd.DataFrame()
            if use_cgan_balance:
                print("使用 CGAN 进行数据平衡...")
                print(f"原始数据形状: {filtered_data.shape}")
                if 'PA Status Repair Info' not in filtered_data.columns:
                    raise ValueError("无法进行 CGAN 平衡: 缺少 PA Status Repair Info 列")

                original_counts = filtered_data['PA Status Repair Info'].value_counts()
                print(f"原始类别分布:\n{original_counts}")

                generated_data = self.cgan_generator.generate_product_samples(
                    filtered_data,
                    target_ratio=balance_ratio
                )
                if not generated_data.empty:
                    print(f"生成 {len(generated_data)} 个新的少数类条目")
                    print(f"生成的数据列: {generated_data.columns.tolist()}")

                    # 对齐列
                    missing_cols = set(filtered_data.columns) - set(generated_data.columns)
                    for col in missing_cols:
                        if col not in ['Generated', 'EntryID']:
                            generated_data[col] = 0 if col in self.numeric_features else ''
                    generated_data = generated_data.reindex(columns=filtered_data.columns, fill_value='')

                    combined_data = pd.concat([filtered_data, generated_data], ignore_index=True)
                    combined_counts = combined_data['PA Status Repair Info'].value_counts()
                    print(f"平衡后类别分布:\n{combined_counts}")

                    normal_count = combined_counts.get('Normal', 0)
                    abnormal_count = sum(combined_counts.get(k, 0) for k in combined_counts.index if 'Normal' not in str(k))
                    if abnormal_count > 0:
                        ratio = normal_count / abnormal_count
                        print(f"平衡比例 (正常:异常): {ratio:.2f}:1")
                    filtered_data = combined_data
                else:
                    print("未生成新数据，使用原始数据继续处理")

            # 特征/标签
            feature_cols = [col for col in input_feats if col not in ['Generated', 'EntryID']]
            X = filtered_data[feature_cols].copy()

            y_dict = {}
            for output_feat in output_feats:
                y = filtered_data[output_feat].copy()

                # 标签转换
                def convert_label(label):
                    label_str = str(label).strip()
                    if output_feat == 'PA Status Pattern 1':
                        if label_str == 'Normal':
                            return 1
                        elif label_str in ('PA might abnormal', 'PA abnormal'):
                            return 0
                        else:
                            print(f"警告: 未知标签值 '{label}'，已转换为0")
                            return 0
                    elif output_feat == 'PA Status Pattern 2':
                        if label_str == 'Normal':
                            return 1
                        elif label_str in ('PA abnormal', 'PA abnormal lin'):
                            return 0
                        else:
                            print(f"警告: 未知标签值 '{label}'，已转换为0")
                            return 0
                    elif output_feat == 'PA Status Repair Info':
                        if label_str == 'Normal':
                            return 1
                        elif label_str == 'PA abnormal':
                            return 0
                        else:
                            print(f"警告: 未知标签值 '{label}'，已转换为0")
                            return 0
                    else:
                        return 1 if 'Normal' in label_str else 0

                y_converted = y.apply(convert_label)
                y_dict[output_feat] = y_converted

                print(f"输出特征 '{output_feat}' 标签分布:")
                print(f" - 正常样本 (1): {y_converted.sum()}")
                abnormal = len(y_converted) - y_converted.sum()
                if abnormal > 0:
                    print(f" - 异常样本 (0): {abnormal}")
                    print(f" - 平衡比例: {y_converted.sum() / abnormal:.2f}:1")
                else:
                    print(f" - 异常样本 (0): 0")
                    print(" - 平衡比例: ∞:1")

            # 数值特征缺失/异常处理
            numeric_feats = [feat for feat in input_feats if feat in self.numeric_features]
            scaler = None
            if numeric_feats:
                X[numeric_feats] = X[numeric_feats].replace([np.inf, -np.inf], [1000, -1000])
                imputer = SimpleImputer(strategy='median')
                existing_numeric_feats = [feat for feat in numeric_feats if feat in X.columns]

                features_with_values, features_without_values = [], []
                for feat in existing_numeric_feats:
                    (features_with_values if X[feat].notna().any() else features_without_values).append(feat)

                if features_with_values:
                    X[features_with_values] = imputer.fit_transform(X[features_with_values])
                if features_without_values:
                    X[features_without_values] = 0
                    print(f"警告: 以下特征没有观测值，已用0填充: {features_without_values}")

            # 分类特征编码
            categorical_feats = [feat for feat in input_feats if feat in self.categorical_features]
            if categorical_feats:
                existing_categorical_feats = [feat for feat in categorical_feats if feat in X.columns]
                if existing_categorical_feats:
                    X_encoded = self.encoder.transform(X[existing_categorical_feats])
                    if len(X_encoded.columns) != len(existing_categorical_feats):
                        print(f"警告: 编码后特征数量 ({len(X_encoded.columns)}) 与原始分类特征数量 ({len(existing_categorical_feats)}) 不一致")
                        missing_cols = set(existing_categorical_feats) - set(X_encoded.columns)
                        for col in missing_cols:
                            X_encoded[col] = -1
                    X_encoded.index = X.index
                    X = X.drop(existing_categorical_feats, axis=1)
                    X = pd.concat([X, X_encoded], axis=1)

            # 数值特征标准化
            if numeric_feats:
                scaler = StandardScaler()
                existing_numeric_feats = [feat for feat in numeric_feats if feat in X.columns]
                if existing_numeric_feats:
                    X[existing_numeric_feats] = scaler.fit_transform(X[existing_numeric_feats])

            # —— 计算“最终主写入目录” —— #
            if use_custom_output:
                primary_output_root = Path(output_dir)
                print("[output] 使用用户自定义输出目录：", primary_output_root)
            else:
                # 未点击按钮：主写入 = 固定目录 #1
                base1, _ = self._fixed_bases()
                primary_output_root = base1
                print("[output] 未选择输出目录，使用固定目录 #1：", primary_output_root)

            primary_output_root.mkdir(parents=True, exist_ok=True)

            # 可选：写入 CGAN 统计（主写入目录）
            if use_cgan_balance and not generated_data.empty:
                balance_info = {
                    'original_samples': len(selected_indices),
                    'generated_samples': len(generated_data),
                    'total_samples': len(filtered_data),
                    'balance_ratio_used': balance_ratio,
                    'generation_timestamp': pd.Timestamp.now().isoformat()
                }
                with open(primary_output_root / 'cgan_balance_info.json', 'w', encoding='utf-8') as f:
                    json.dump(balance_info, f, indent=2, ensure_ascii=False)

            # —— 为每个输出特征生成 6 个文件 —— #
            for output_feat, y in y_dict.items():
                X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=42, stratify=y)
                X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

                dataset_folder = f"dataset_{output_feat.replace(' ', '_')}"
                feat_output_dir = primary_output_root / dataset_folder
                feat_output_dir.mkdir(parents=True, exist_ok=True)

                pd.concat([X_train, y_train.rename('target')], axis=1).to_csv(feat_output_dir / 'train.csv', index=False)
                pd.concat([X_val, y_val.rename('target')], axis=1).to_csv(feat_output_dir / 'val.csv', index=False)
                pd.concat([X_test, y_test.rename('target')], axis=1).to_csv(feat_output_dir / 'test.csv', index=False)

                if scaler:
                    joblib.dump(scaler, feat_output_dir / 'scaler.pkl')
                joblib.dump(self.encoder, feat_output_dir / 'encoder.pkl')

                metadata = {
                    'input_features': input_feats,
                    'output_feature': output_feat,
                    'numeric_features': numeric_feats,
                    'categorical_features': categorical_feats,
                    'selected_samples_count': len(filtered_data),
                    'cgan_balanced': use_cgan_balance,
                    'balance_ratio': balance_ratio if use_cgan_balance else None
                }
                with open(feat_output_dir / 'metadata.json', 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                # —— 镜像策略 —— #
                if use_custom_output:
                    # 用户选择了自定义目录 → 不做双份自动保存
                    print("[mirror] 用户已选择自定义目录 → 自动保存两份已跳过")
                else:
                    # 未点击按钮 → 把“固定目录 #1”的文件镜像到“固定目录 #2”
                    try:
                        self._mirror_to_other_fixed(feat_output_dir, dataset_folder)
                    except Exception as _e:
                        print(f"[mirror] 复制到固定目录失败: {repr(_e)}")

            return True, f"成功生成数据集到: {str(primary_output_root)}\n" + \
                   (f"使用CGAN生成了 {len(generated_data) if use_cgan_balance else 0} 个少数类样本" if use_cgan_balance else "")

        except Exception as e:
            return False, f"处理数据时出错: {str(e)}\n{traceback.format_exc()}"