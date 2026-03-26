import os
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from sklearn.impute import SimpleImputer
from pytorch_tabnet.tab_model import TabNetClassifier


class PAStatusPredictor:
    """PA状态预测应用模块"""
    def __init__(self):
        # 设置路径
        self.SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        self.ROOT_DIR = os.path.normpath(os.path.join(self.SCRIPT_DIR, '../../../'))
        self.DATASET_DIR = os.path.join(self.ROOT_DIR, 'processed_datasets')
        self.MODEL_DIR = os.path.join(self.ROOT_DIR, 'saved_models')
        self.SAMPLE_DIR = os.path.join(self.ROOT_DIR, 'for_application')

        # 确保目录存在
        os.makedirs(self.SAMPLE_DIR, exist_ok=True)

        # 数值型特征
        self.numeric_features = [
            'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IMpaSv:.0', 'IMpaSv:.1',
            'dpdNomPwr', 'powerClass', 'powerLevel', 'rfPower', 'torGainBackoff',
            'torTemp', 'txAtt', 'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        # 分类型(字符型)特征
        # self.categorical_features = [
        #     'ProductName', 'desc', 'dpGainLoopEnable', 'dpTsEnable', 'dpd', 'dpdAutoStart', 'gainAutoStart',
        #     'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState', 'islastDelEstFracSuccess',
        #     'linearizationStateMachine', 'shpAutoStart', 'status', 'subId', 'torSupported'
        # ]
        # 移除特征 - ‘ProductName’
        self.categorical_features = [
            'desc', 'dpGainLoopEnable', 'dpTsEnable', 'dpd', 'dpdAutoStart', 'gainAutoStart',
            'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState', 'islastDelEstFracSuccess',
            'linearizationStateMachine', 'shpAutoStart', 'status', 'subId', 'torSupported'
        ]

        # 模型类型标记
        self.model_types = ['xgboost', 'tabnet']  # 支持的模型类型

        # 加载预处理元数据和模型
        self._load_metadata_and_model()

    def _load_metadata_and_model(self):
        """加载预处理元数据和训练好的模型（精确路径版）"""
        try:
            # 1. 动态添加feature_encoder模块路径
            import sys
            from pathlib import Path

            # 计算feature_encoder.py的绝对路径
            encoder_module_path = str(
                Path(__file__).parent.parent  # 到services目录
                / "model_training"
                / "preprocessor"
            )

            if encoder_module_path not in sys.path:
                sys.path.insert(0, encoder_module_path)  # 优先搜索

            # 2. 加载特征元数据（从processed_datasets目录）
            metadata_path = os.path.join(self.DATASET_DIR, 'feature_metadata.json')
            if not os.path.exists(metadata_path):
                raise FileNotFoundError(f"元数据文件不存在: {metadata_path}")
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)

            # 3. 加载特征编码器（从processed_datasets目录）
            encoder_pkl_path = os.path.join(self.DATASET_DIR, 'feature_encoder.pkl')
            if not os.path.exists(encoder_pkl_path):
                raise FileNotFoundError(f"编码器文件不存在: {encoder_pkl_path}")
            import joblib
            self.encoder = joblib.load(encoder_pkl_path)

            # 4. 初始化标准化器
            self.scaler = StandardScaler()

            # 从元数据获取标准化参数
            if 'fitted_scaler_params' in self.metadata:
                scaler_params = self.metadata['fitted_scaler_params']

                # 设置特征顺序
                if 'mean' in scaler_params and scaler_params['mean']:
                    feature_names = list(scaler_params['mean'].keys())
                    # （数值）特征顺序
                    self.scaler.feature_names_in_ = np.array(feature_names)
                    # # 设置均值和标准差
                    self.scaler.mean_ = np.array([scaler_params['mean'][f] for f in feature_names])
                    self.scaler.scale_ = np.array([scaler_params['scale'][f] for f in feature_names])
                else:
                    raise ValueError("元数据中缺少标准化参数")
            else:
                # 兼容旧版本（从pkl加载）
                scaler_path = os.path.join(self.DATASET_DIR, 'scaler.pkl')
                if os.path.exists(scaler_path):
                    scaler_data = joblib.load(scaler_path)
                    self.scaler.mean_ = scaler_data.mean_
                    self.scaler.scale_ = scaler_data.scale_
                else:
                    raise FileNotFoundError("找不到标准化器文件且元数据中无参数")

            # 5. 加载XGBoost模型
            xgb_model_path = os.path.join(self.MODEL_DIR, 'xgboost_model.json')
            if not os.path.exists(xgb_model_path):
                raise FileNotFoundError(f"XGBoost模型文件不存在: {xgb_model_path}")

            self.xgb_model = xgb.Booster()
            self.xgb_model.load_model(xgb_model_path)
            print("成功加载XGBoost模型")

            # 6. 加载TabNet模型
            tabnet_model_path = os.path.join(self.MODEL_DIR, 'tabnet_base_model.zip')
            tabnet_metadata_path = os.path.join(self.MODEL_DIR, 'tabnet_base_metadata.json')

            if os.path.exists(tabnet_model_path) and os.path.exists(tabnet_metadata_path):
                # 加载TabNet模型
                self.tabnet_model = TabNetClassifier()
                self.tabnet_model.load_model(tabnet_model_path)

                # 加载TabNet元数据
                with open(tabnet_metadata_path, 'r') as f:
                    self.tabnet_metadata = json.load(f)

                print("成功加载TabNet模型和元数据")
            else:
                print("警告: TabNet模型或元数据文件不存在，将仅使用XGBoost")
                self.tabnet_model = None

            print("成功加载所有模型文件和预处理对象")

        except Exception as e:
            raise RuntimeError(f"加载元数据或模型失败: {str(e)}")

    @staticmethod
    def _process_numeric_features(params):
        """处理数值型特征(改进版，兼容直接提供合并特征的情况)"""
        numeric_values = {}

        # 1. 处理DpaVddSv - 优先使用直接提供的值，否则合并计算
        if 'DpaVddSv' in params and params['DpaVddSv'] not in ['', None, np.nan]:
            try:
                numeric_values['DpaVddSv'] = float(params['DpaVddSv'])
            except (ValueError, TypeError):
                pass
        else:
            dpa_values = []
            for i in range(8):
                key = f'DpaVddSv:{i}'
                if key in params:
                    val = params[key]
                    try:
                        if val not in ['', None, np.nan]:
                            dpa_values.append(float(val))
                    except (ValueError, TypeError):
                        pass
            numeric_values['DpaVddSv'] = np.nanmean(dpa_values) if dpa_values else np.nan

        # 2. 处理PaVddSv - 同样优先使用直接提供的值
        if 'PaVddSv' in params and params['PaVddSv'] not in ['', None, np.nan]:
            try:
                numeric_values['PaVddSv'] = float(params['PaVddSv'])
            except (ValueError, TypeError):
                pass
        else:
            pa_values = []
            for i in range(8):
                key = f'PaVddSv:{i}'
                if key in params:
                    val = params[key]
                    try:
                        if val not in ['', None, np.nan]:
                            pa_values.append(float(val))
                    except (ValueError, TypeError):
                        pass
            numeric_values['PaVddSv'] = np.nanmean(pa_values) if pa_values else np.nan

        # 3. 处理IDpaSv - 优先使用新名称
        idpa_0_values = []
        idpa_1_values = []

        # 先检查直接提供的合并特征
        if 'IDpaSv.0' in params and params['IDpaSv.0'] not in ['', None, np.nan]:
            try:
                numeric_values['IDpaSv:.0'] = float(params['IDpaSv.0'])
            except (ValueError, TypeError):
                pass
        else:
            # 否则尝试从原始特征合并
            for i in range(8):
                key = f'IDpaSv.{i}.0'  # 新命名格式
                if key in params:
                    val = params[key]
                    try:
                        if val not in ['', None, np.nan]:
                            idpa_0_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

        if 'IDpaSv.1' in params and params['IDpaSv.1'] not in ['', None, np.nan]:
            try:
                numeric_values['IDpaSv:.1'] = float(params['IDpaSv.1'])
            except (ValueError, TypeError):
                pass
        else:
            for i in range(8):
                key = f'IDpaSv.{i}.1'  # 新命名格式
                if key in params:
                    val = params[key]
                    try:
                        if val not in ['', None, np.nan]:
                            idpa_1_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

        # 如果没有直接提供合并特征，则使用合并计算的值
        if 'IDpaSv:.0' not in numeric_values:
            numeric_values['IDpaSv:.0'] = np.nanmean(idpa_0_values) if idpa_0_values else np.nan
        if 'IDpaSv:.1' not in numeric_values:
            numeric_values['IDpaSv:.1'] = np.nanmean(idpa_1_values) if idpa_1_values else np.nan

        # 4. 处理IMpaSv - 同样优先使用新名称
        impa_0_values = []
        impa_1_values = []

        if 'IMpaSv.0' in params and params['IMpaSv.0'] not in ['', None, np.nan]:
            try:
                numeric_values['IMpaSv:.0'] = float(params['IMpaSv.0'])
            except (ValueError, TypeError):
                pass
        else:
            for i in range(8):
                key = f'IMpaSv.{i}.0'  # 新命名格式
                if key in params:
                    val = params[key]
                    try:
                        if val not in ['', None, np.nan]:
                            impa_0_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

        if 'IMpaSv.1' in params and params['IMpaSv.1'] not in ['', None, np.nan]:
            try:
                numeric_values['IMpaSv:.1'] = float(params['IMpaSv.1'])
            except (ValueError, TypeError):
                pass
        else:
            for i in range(8):
                key = f'IMpaSv.{i}.1'  # 新命名格式
                if key in params:
                    val = params[key]
                    try:
                        if val not in ['', None, np.nan]:
                            impa_1_values.append(float(val))
                    except (ValueError, TypeError):
                        pass

        if 'IMpaSv:.0' not in numeric_values:
            numeric_values['IMpaSv:.0'] = np.nanmean(impa_0_values) if impa_0_values else np.nan
        if 'IMpaSv:.1' not in numeric_values:
            numeric_values['IMpaSv:.1'] = np.nanmean(impa_1_values) if impa_1_values else np.nan

        # 5. 处理其他数值型属性
        other_numeric_features = [
            'dpdNomPwr', 'powerClass', 'powerLevel', 'rfPower', 'torGainBackoff',
            'torTemp', 'txAtt', 'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        for feat in other_numeric_features:
            if feat in params:
                val = params[feat]
                try:
                    if feat == 'powerClass' and isinstance(val, str):
                        val = int(val) if val.isdigit() else np.nan
                    if val not in ['', None, np.nan]:
                        numeric_values[feat] = float(val)
                    else:
                        numeric_values[feat] = np.nan
                except (ValueError, TypeError):
                    numeric_values[feat] = np.nan
            else:
                numeric_values[feat] = np.nan

        return numeric_values

    def _preprocess_sample(self, sample_df):
        """预处理单个样本数据"""
        try:
            # 1. 提取特征
            features = {col: [] for col in self.numeric_features + self.categorical_features}

            # 处理数值特征
            numeric_values = self._process_numeric_features(sample_df)
            for feat in self.numeric_features:
                features[feat].append(numeric_values.get(feat, np.nan))

            # 处理分类特征
            for feat in self.categorical_features:
                val = sample_df.get(feat, '')
                features[feat].append(str(val).strip() if val not in [None, np.nan] else '')

            feature_df = pd.DataFrame(features)

            # 2. 处理特殊值(1000/-1000 对应 inf/-inf)
            numeric_data = feature_df[self.numeric_features].copy()
            numeric_data = numeric_data.replace([np.inf, -np.inf], [1000, -1000])

            # 3. 填充空值（全空列填0，其他填中位数）
            empty_cols = numeric_data.columns[numeric_data.isna().all()].tolist()
            numeric_data[empty_cols] = 0

            imputer = SimpleImputer(strategy='median')
            numeric_data_imputed = pd.DataFrame(
                imputer.fit_transform(numeric_data),
                columns=numeric_data.columns
            )

            # 4. 数值特征标准化
            # 4.1 获取训练时实际使用的特征列
            if hasattr(self.scaler, 'feature_names_in_'):
                scaler_features = self.scaler.feature_names_in_
            else:
                # 从元数据获取特征顺序
                if 'fitted_scaler_params' in self.metadata and 'mean' in self.metadata['fitted_scaler_params']:
                    scaler_features = list(self.metadata['fitted_scaler_params']['mean'].keys())
                else:
                    # 最后回退：使用当前所有数值特征（不推荐）
                    scaler_features = [col for col in numeric_data_imputed.columns
                                       if col not in self.metadata.get('removed_zero_variance_features', [])]
                    print("警告: 无法确定标准化特征顺序，使用当前特征顺序")

            # 4.2 验证特征匹配性
            missing_features = set(scaler_features) - set(numeric_data_imputed.columns)
            if missing_features:
                raise ValueError(f"缺少训练时使用的特征: {missing_features}")

            # 4.3 按训练时的特征顺序筛选
            numeric_data_imputed = numeric_data_imputed[scaler_features]

            # 4.4 执行标准化（使用从元数据加载的参数）
            numeric_data_imputed[:] = self.scaler.transform(numeric_data_imputed)

            # 5. 分类特征编码
            X_encoded = self.encoder.transform(feature_df[self.categorical_features])

            # 6. 合并结果
            X_processed = pd.concat([X_encoded, numeric_data_imputed], axis=1)

            # 验证最终特征数量
            expected_features = len(X_encoded.columns) + len(scaler_features)
            if len(X_processed.columns) != expected_features:
                raise ValueError(
                    f"特征数量异常！预期{expected_features}个，实际{X_processed.shape[1]}个\n"
                    f"分类特征: {len(X_encoded.columns)}个, 数值特征: {len(scaler_features)}个"
                )

            return X_processed

        except Exception as e:
            raise RuntimeError(f"样本预处理失败: {str(e)}")

    def process_new_samples(self, input_filename, output_filename=None):
        """处理新样本数据集并保存结果"""
        try:
            # 1. 加载新样本数据
            input_path = os.path.join(self.SAMPLE_DIR, input_filename)
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"输入文件不存在: {input_path}")

            df = pd.read_csv(input_path)
            if len(df) == 0:
                raise ValueError("输入文件为空")

            print(f"成功加载 {len(df)} 条新样本数据")

            # 2. 预处理每个样本
            processed_samples = []
            for _, row in df.iterrows():
                try:
                    processed = self._preprocess_sample(row)
                    processed_samples.append(processed)
                except Exception as e:
                    print(f"处理样本 {row.name} 失败: {str(e)}")
                    continue

            if not processed_samples:
                raise ValueError("所有样本处理失败")

            # 合并所有处理后的样本
            X_processed = pd.concat(processed_samples, axis=0)

            # 3. 保存处理后的特征
            if output_filename is None:
                output_filename = f"processed_{input_filename}"
            output_path = os.path.join(self.SAMPLE_DIR, output_filename)
            X_processed.to_csv(output_path, index=False)
            print(f"处理后的特征已保存到: {output_path}")

            return X_processed

        except Exception as e:
            raise RuntimeError(f"处理新样本失败: {str(e)}")

    def predict_pa_status(self, processed_data):
        """预测PA状态"""
        try:
            # 确保输入是DataFrame
            if not isinstance(processed_data, pd.DataFrame):
                raise ValueError("输入数据必须是DataFrame")

            # 1. XGBoost预测
            # 转换为DMatrix格式
            dmatrix = xgb.DMatrix(processed_data)

            # 预测类别
            xgb_pred_classes = self.xgb_model.predict(dmatrix)

            # 2. TabNet预测
            X_tabnet = processed_data.values.astype(np.float32)

            # 预测类别和概率
            tabnet_pred_classes = self.tabnet_model.predict(X_tabnet)
            tabnet_pred_probabilities = self.tabnet_model.predict_proba(X_tabnet)

            # 映射预测标签到业务名称（根据训练时的labeling_method）
            if self.metadata.get('labeling_method') == 'legacy' or (self.metadata.get('labeling_method') == 'both' and
                                                                    self.metadata.get('pa_status_selection') == 'legacy'):
                label_map = {
                    0: 'Normal',
                    1: 'PA might broken',
                    2: 'PA broken'
                }
            else:
                label_map = {
                    0: 'PA might normal',
                    1: 'PA might broken'
                }

            # 将预测结果添加到DataFrame
            processed_data['Prediction XGBoost'] = xgb_pred_classes.astype(int)
            processed_data['Prediction XGBoost'] = processed_data['Prediction XGBoost'].map(label_map)  # 映射预测标签到业务名称

            processed_data['Prediction tabnet'] = tabnet_pred_classes
            processed_data['Prediction tabnet'] = processed_data['Prediction tabnet'].map(label_map)  # 映射预测标签到业务名称
            processed_data['Prediction Confidence Level tabnet'] = np.max(tabnet_pred_probabilities, axis=1)  # 预测结果的置信概率

            return processed_data

        except Exception as e:
            raise RuntimeError(f"预测PA状态失败: {str(e)}")

    def run_pipeline(self, input_filename):
        """完整处理流程"""
        try:
            # 1. 预处理新样本
            processed_data = self.process_new_samples(input_filename)

            # 2. 预测PA状态
            result_df = self.predict_pa_status(processed_data)

            # 3. 保存预测结果
            output_filename = f"predicted_{input_filename}"
            output_path = os.path.join(self.SAMPLE_DIR, output_filename)
            result_df.to_csv(output_path, index=False)

            print(f"\n{'=' * 40}\n预测完成\n{'=' * 40}")
            print(f"结果已保存到: {output_path}")

            # 打印预测结果统计
            # XGBoost统计
            if 'Prediction XGBoost' in result_df.columns:
                xgb_counts = result_df['Prediction XGBoost'].value_counts()
                print("\nXGBoost预测结果统计:")
                for status, count in xgb_counts.items():
                    print(f"状态 {status}: {count} 样本 ({count / len(result_df):.1%})")

            # TabNet统计
            if 'Prediction tabnet' in result_df.columns:
                tabnet_counts = result_df['Prediction tabnet'].value_counts()
                print("\nTabNet预测结果统计:")
                for status, count in tabnet_counts.items():
                    print(f"状态 {status}: {count} 样本 ({count / len(result_df):.1%})")

            # 一致性分析
            if 'Prediction XGBoost' in result_df.columns and 'Prediction tabnet' in result_df.columns:
                agreement = (result_df['Prediction XGBoost'] == result_df['Prediction tabnet']).mean()
                print(f"\n模型预测一致率: {agreement:.1%}")

            return result_df

        except Exception as e:
            print(f"\n{'=' * 40}\n处理失败\n{'=' * 40}")
            print(f"错误: {str(e)}")
            return None


if __name__ == '__main__':
    # 使用示例
    predictor = PAStatusPredictor()

    # 指定要处理的新样本文件名(位于for_application目录下)
    new_sample_file = "elog_10_27_comb.csv"  # 修改为所用的文件名

    # 运行完整流程
    result = predictor.run_pipeline(new_sample_file)
