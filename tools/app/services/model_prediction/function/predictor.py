import pandas as pd
import numpy as np
import json
import joblib
import os
import xgboost as xgb
import lightgbm as lgb
from pytorch_tabnet.tab_model import TabNetClassifier
import catboost as cb
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.base import BaseEstimator, TransformerMixin


class FeatureEncoder(BaseEstimator, TransformerMixin):
    def __init__(self):
        # 预定义所有特征的编码映射
        self.mappings = {
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
                'ctrlgainstateramping=starting': 1,
                'CtrlGainStateTuned=started': 2,
                'CtrlGainStateTuning=paused': 3,
                'CtrlGainStateTuning=starting': 4,
                'CtrlGainStateWait=starting': 5,
                'CtrlGainStateDcComp=starting': 6,
                'CtrlGainStateSbpsPause=starting': 7,
                'CtrlGainStateStart=starting': 8,
                'ns=stopped': 9,
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
            'runMode': {
                '2D': 0,
                'BF': 1,
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
            'statusBit': {
                'DPD_SCHD_MEAS_STATUS_EGR_SRL_ERR_B': 0,
                'DPD_SCHD_MEAS_STATUS_EXT_EVC_IDLE_B': 0,
                'DPD_SCHD_MEAS_STATUS_TOR_ADC_ERR_B': 0,
                'EGR_SRL_ERR': 0,
                'EXT_EVC_IDLE': 0,
                'EXT_TDD_TX_OFF': 0,
                'TOR_ADC_ERR': 0,
                'DPD_SCHD_MEAS_STATUS_EXT_DPD_IDLE_B': 1,
                'EXT_DPD_IDLE': 2,
                'EGR_SRL_ERR | EXT_DPD_IDLE': 3,
                'EGR_SRL_ERR | EXT_DPD_IDLE | TOR_ADC_ERR': 4,
                'EXT_DPD_IDLE | EXT_EVC_IDLE': 5,
                'EXT_DPD_IDLE | EXT_TDD_TX_OFF': 6,
                'NA': -1,
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
                'TRUE': 1, 'FALSE': 0,
                'True': 1, 'False': 0,
                'true': 1, 'false': 0,
                'YES': 1, 'NO': 0,
                'Yes': 1, 'No': 0,
                'yes': 1, 'no': 0,
                'ON': 1, 'OFF': 0,
                'On': 1, 'Off': 0,
                'on': 1, 'off': 0,
                '1': 1, '0': 0,
                'ENABLED': 1, 'DISABLED': 0,
                'Enabled': 1, 'Disabled': 0,
                'enabled': 1, 'disabled': 0,
                'ENABLE': 1, 'DISABLE': 0,
                'Enable': 1, 'Disable': 0,
                'enable': 1, 'disable': 0,
                '': -1,  # 空字符串
                np.nan: -1,  # NaN值
                None: -1  # None值
            },
        }

        self.bool_categorical_features = ['autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable',
                                          'dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart', 'gainAutoStart',
                                          'ganBoostModeEnable', 'islastDelEstFracSuccess', 'shpAutoStart',
                                          'shpGanAlgEnabled', 'shpGanAlgFunctionStatus', 'shpGanAlgHwCapablility',
                                          'torSupported']

        # 初始化布尔型特征的映射（继承模板）
        for bool_feature in self.bool_categorical_features:
            self.mappings[bool_feature] = self.mappings['bool_template'].copy()

        # 记录未知值的映射
        self.unknown_mappings = {}

    def fit(self, X, y=None):
        """适应新数据，发现新的未知值"""
        return self

    def transform(self, X):
        """转换特征数据"""
        if X.empty:
            return X

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
                if feature in self.bool_categorical_features:
                    # 统一转换为字符串并标准化
                    str_vals = X[feature].astype(str).str.strip()

                    # 应用映射，未知值映射为-1
                    X_encoded[feature] = str_vals.map(lambda x: self.mappings[feature].get(x, -1))

                # 处理其他分类特征
                else:
                    cleaned = X[feature].apply(clean_text)
                    # 应用映射，未知值映射为-1
                    X_encoded[feature] = cleaned.map(lambda x: self.mappings[feature].get(x, -1))

        # 处理未映射到的值（用-1表示）
        for col in X_encoded.columns:
            if col in self.mappings:
                X_encoded[col] = X_encoded[col].fillna(-1).astype(int)

        return X_encoded

    def fit_transform(self, X, y=None):
        """适应并转换数据"""
        return self.fit(X, y).transform(X)


class Predictor:
    def __init__(self):
        self.scaler = None
        self.encoder = None
        self.metadata = None
        self.model_path = None
        self.model = None
        self.model_type = None
        self.model_features = None
        self.sample_file = None
        self.preprocess_config = None
        self.results_df = None

        # 定义特征分组（与TrainingDataProcessor保持一致）
        self.numeric_features = [
            'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IDpaSv:.2', 'IDpaSv:.3',
            'IMpaSv:.0', 'IMpaSv:.1', 'IMpaSv:.2', 'IMpaSv:.3',
            'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
            'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
            'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]

        self.categorical_features = [
            'autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable', 'desc', 'dpGainLoopEnable', 'dpTsEnable',
            'dpd', 'dpdAutoStart', 'gainAutoStart', 'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState',
            'islastDelEstFracSuccess', 'linearizationStateMachine', 'runMode', 'shpAutoStart', 'shpGanAlgEnabled',
            'shpGanAlgFunctionStatus', 'shpGanAlgHwCapablility', 'status', 'statusBit', 'subId', 'torSupported'
        ]

    def set_model_file(self, model_path, model_type="auto"):
        """设置模型文件"""
        self.model_path = model_path
        self.model_type = model_type

    def set_sample_file(self, sample_path):
        """设置样本文件"""
        self.sample_file = sample_path

    def set_preprocess_config(self, config_path):
        """设置预处理配置"""
        self.preprocess_config = config_path
        print(f"设置预处理配置路径: {config_path}")

    def load_preprocessor(self):
        """加载预处理对象（参考csv_application的加载方式）"""
        if not self.preprocess_config:
            return False, "未提供预处理配置路径"

        try:
            config_dir = self.preprocess_config

            # 1. 加载特征元数据
            metadata_path = os.path.join(config_dir, 'metadata.json')
            if not os.path.exists(metadata_path):
                return False, f"元数据文件不存在: {metadata_path}"

            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            print(f"成功加载metadata: {metadata_path}")

            # 从metadata中获取特征信息
            if 'input_features' in self.metadata:
                self.model_features = self.metadata['input_features']
                print(f"从metadata中获取特征列表: {len(self.model_features)} 个特征")

            # 2. 加载特征编码器
            encoder_path = os.path.join(config_dir, 'encoder.pkl')
            if not os.path.exists(encoder_path):
                return False, f"编码器文件不存在: {encoder_path}"

            # 使用自定义类加载encoder
            try:
                self.encoder = joblib.load(encoder_path)
            except (ModuleNotFoundError, AttributeError) as e:
                print(f"标准加载失败: {e}，尝试使用自定义类加载...")
                # 如果标准加载失败，使用自定义类重新创建encoder
                self.encoder = FeatureEncoder()
                print("使用本地定义的FeatureEncoder类")

            print(f"成功加载encoder: {encoder_path}")

            # 3. 初始化标准化器并加载参数
            self.scaler = StandardScaler()

            # 从元数据获取标准化参数
            if 'fitted_scaler_params' in self.metadata:
                scaler_params = self.metadata['fitted_scaler_params']

                if 'mean' in scaler_params and scaler_params['mean']:
                    feature_names = list(scaler_params['mean'].keys())
                    # 设置特征顺序
                    self.scaler.feature_names_in_ = np.array(feature_names)
                    # 设置均值和标准差
                    self.scaler.mean_ = np.array([scaler_params['mean'][f] for f in feature_names])
                    self.scaler.scale_ = np.array([scaler_params['scale'][f] for f in feature_names])
                    print(f"从元数据加载标准化参数，特征数量: {len(feature_names)}")
                else:
                    # 回退到加载scaler.pkl文件
                    scaler_path = os.path.join(config_dir, 'scaler.pkl')
                    if os.path.exists(scaler_path):
                        scaler_data = joblib.load(scaler_path)
                        self.scaler = scaler_data
                        print(f"从pkl文件加载scaler: {scaler_path}")
                    else:
                        return False, "元数据中缺少标准化参数且找不到scaler.pkl文件"
            else:
                # 兼容旧版本：直接加载scaler.pkl
                scaler_path = os.path.join(config_dir, 'scaler.pkl')
                if os.path.exists(scaler_path):
                    self.scaler = joblib.load(scaler_path)
                    print(f"从pkl文件加载scaler: {scaler_path}")
                else:
                    return False, "找不到标准化器文件且元数据中无参数"

            return True, "预处理对象加载成功"

        except Exception as e:
            return False, f"加载预处理对象失败: {str(e)}"

    def load_model(self):
        """加载模型"""
        try:
            if self.model_type == "auto":
                # 根据文件扩展名自动判断
                if self.model_path.endswith('.json'):
                    self.model_type = 'xgboost'
                elif self.model_path.endswith('.txt'):
                    self.model_type = 'lightgbm'
                elif self.model_path.endswith('.zip'):
                    self.model_type = 'tabnet'
                elif self.model_path.endswith('.cbm'):
                    self.model_type = 'catboost'
                elif self.model_path.endswith(('.pkl', '.joblib', '.model')):
                    self.model_type = 'sklearn'
                else:
                    return False, "无法自动识别模型类型，请手动指定模型类型"

            print(f"加载 {self.model_type} 模型，文件: {self.model_path}")

            if self.model_type == "xgboost":
                self.model = xgb.Booster()
                self.model.load_model(self.model_path)
                print("XGBoost 模型加载成功")

            elif self.model_type == "lightgbm":
                self.model = lgb.Booster(model_file=self.model_path)
                print("LightGBM 模型加载成功")

            elif self.model_type == "tabnet":
                self.model = TabNetClassifier()
                self.model.load_model(self.model_path)
                print("TabNet 模型加载成功")

            elif self.model_type == "catboost":
                self.model = cb.CatBoostClassifier()
                self.model.load_model(self.model_path)
                print("CatBoost 模型加载成功")

            elif self.model_type == "sklearn":
                # 支持多种scikit-learn模型格式
                self.model = joblib.load(self.model_path)
                print("Scikit-learn 模型加载成功")

            else:
                return False, f"不支持的模型类型: {self.model_type}"

            return True, f"{self.model_type.upper()} 模型加载成功"

        except Exception as e:
            error_msg = f"加载模型失败: {str(e)}"
            print(error_msg)
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return False, error_msg

    def process_numeric_features(self, X):
        """处理数值特征（参考csv_application的方式）"""
        if not hasattr(self, 'scaler') or self.scaler is None:
            print("警告: 未找到scaler，跳过数值特征标准化")
            return X

        # 识别数值特征
        numeric_feats = []
        if self.metadata and 'numeric_features' in self.metadata:
            numeric_feats = self.metadata['numeric_features']
        else:
            # 如果没有元数据，使用默认的数值特征
            numeric_feats = [feat for feat in self.numeric_features if feat in X.columns]

        if not numeric_feats:
            print("警告: 未找到数值特征，跳过数值特征处理")
            return X

        print(f"处理 {len(numeric_feats)} 个数值特征")

        # 替换inf/-inf（与训练时保持一致）
        X[numeric_feats] = X[numeric_feats].replace([np.inf, -np.inf], [1000, -1000])

        # 填充空值（使用训练时的策略）
        # 检查哪些特征有非空值
        features_with_values = []
        features_without_values = []

        for feat in numeric_feats:
            if X[feat].notna().any():  # 检查是否有非空值
                features_with_values.append(feat)
            else:
                features_without_values.append(feat)

        # 只对有值的特征使用Imputer（与训练时保持一致）
        if features_with_values:
            # 使用中位数填充（与训练时保持一致）
            imputer = SimpleImputer(strategy='median')
            X[features_with_values] = imputer.fit_transform(X[features_with_values])

        # 对没有值的特征填充0（与训练时保持一致）
        if features_without_values:
            X[features_without_values] = 0

        # 应用标准化（使用训练时保存的scaler）
        if self.scaler is not None:
            # 确保特征顺序与训练时一致
            if hasattr(self.scaler, 'feature_names_in_'):
                scaler_features = self.scaler.feature_names_in_
                # 只选择训练时使用的特征
                available_features = [f for f in scaler_features if f in X.columns]
                X[available_features] = self.scaler.transform(X[available_features])
            else:
                # 回退到原始方式
                X[features_with_values] = self.scaler.transform(X[features_with_values])
            print("数值特征标准化完成")

        return X

    def process_categorical_features(self, X):
        """处理分类特征（参考csv_application的方式）"""
        if not hasattr(self, 'encoder') or self.encoder is None:
            print("警告: 未找到encoder，跳过分类特征编码")
            return X

        # 识别分类特征
        categorical_feats = []
        if self.metadata and 'categorical_features' in self.metadata:
            categorical_feats = self.metadata['categorical_features']
        else:
            # 如果没有元数据，使用默认的分类特征
            categorical_feats = [feat for feat in self.categorical_features if feat in X.columns]

        if not categorical_feats:
            print("警告: 未找到分类特征，跳过分类特征处理")
            return X

        # 只对存在的分类特征进行处理
        existing_categorical_feats = [feat for feat in categorical_feats if feat in X.columns]
        if not existing_categorical_feats:
            return X

        print(f"处理 {len(existing_categorical_feats)} 个分类特征")

        X_processed = X.copy()

        for feat in existing_categorical_feats:
            try:
                # 步骤1: 转换为字符串，处理所有可能的NaN值
                X_processed[feat] = X_processed[feat].astype(str)

                # 步骤2: 统一处理各种缺失值表示:cite[3]
                missing_patterns = [
                    'nan', 'NaN', 'None', 'none', 'null', 'Null', 'NULL',
                    'N/A', 'n/a', '<NA>', 'NaT', '', ' ', '  '
                ]

                for pattern in missing_patterns:
                    X_processed[feat] = X_processed[feat].replace(pattern, 'Missing')

                # 步骤3: 处理浮点数转换问题（如 0.0 -> '0'）
                def clean_numeric_string(value):
                    if value == 'Missing':
                        return 'Missing'
                    try:
                        # 尝试转换为浮点数检查是否为数值
                        float_val = float(value)
                        # 如果是整数浮点数，转换为整数字符串
                        if float_val.is_integer():
                            return str(int(float_val))
                        else:
                            # 对于真正的浮点数，保留但记录警告
                            print(f"警告: 特征 {feat} 包含非整数值: {value}")
                            return value
                    except (ValueError, TypeError):
                        return value

                X_processed[feat] = X_processed[feat].apply(clean_numeric_string)

                # 调试信息
                unique_vals = X_processed[feat].unique()[:5]
                print(f"特征 '{feat}' 处理后的样例值: {list(unique_vals)}")

            except Exception as e:
                print(f"处理特征 {feat} 时出错: {str(e)}")
                # 确保至少是字符串类型
                X_processed[feat] = X_processed[feat].astype(str).fillna('Missing')

        # 应用特征编码
        try:
            X_encoded = self.encoder.transform(X_processed[existing_categorical_feats])
            X_encoded.index = X_processed.index

            # 删除原始分类特征，添加编码后的特征
            X_processed = X_processed.drop(existing_categorical_feats, axis=1)
            X_processed = pd.concat([X_processed, X_encoded], axis=1)

            print("分类特征编码完成")

        except Exception as e:
            print(f"特征编码失败: {str(e)}")
            # 如果编码失败，至少确保分类特征是字符串类型
            for feat in existing_categorical_feats:
                X_processed[feat] = X_processed[feat].astype(str).fillna('Missing')

        return X_processed

    def align_features(self, X):
        """对齐特征，确保推理数据只包含模型训练时使用的特征"""
        if self.model_features is None:
            print("警告: 未找到模型特征列表，使用所有可用特征")
            return X

        # 获取当前数据中的所有特征
        available_features = X.columns.tolist()

        # 找出模型需要但数据中缺失的特征
        missing_features = set(self.model_features) - set(available_features)

        # 找出数据中有但模型不需要的特征
        extra_features = set(available_features) - set(self.model_features)

        if missing_features:
            print(f"警告: 数据中缺失以下特征: {list(missing_features)}")
        if extra_features:
            print(f"警告: 数据中有以下额外特征: {list(extra_features)}")

        # 创建对齐后的特征矩阵
        X_aligned = pd.DataFrame(index=X.index)

        # 添加模型需要的特征
        for feature in self.model_features:
            if feature in X.columns:
                X_aligned[feature] = X[feature]
            else:
                # 用0填充缺失特征
                X_aligned[feature] = 0
                print(f"用0填充缺失特征: {feature}")

        print(f"特征对齐完成: 输入 {len(X.columns)} 个特征 -> 对齐后 {len(X_aligned.columns)} 个特征")
        return X_aligned

    def apply_preprocessing(self, X):
        """应用与训练时相同的预处理步骤"""
        # 首先处理数值特征
        X = self.process_numeric_features(X)

        # 然后处理分类特征
        X = self.process_categorical_features(X)

        return X

    @staticmethod
    def validate_and_convert_dtypes(X):
        """验证并转换数据类型，确保所有特征都是数值类型"""
        # 确保所有列都是数值类型
        for col in X.columns:
            if X[col].dtype == 'object':
                # 尝试转换为数值类型
                try:
                    X[col] = pd.to_numeric(X[col], errors='coerce')
                except:
                    # 如果转换失败，使用标签编码
                    X[col] = X[col].astype('category').cat.codes

            # 确保没有NaN值
            if X[col].isna().any():
                X[col] = X[col].fillna(0)

        return X

    @staticmethod
    def convert_prediction_to_label(predictions):
        """将预测结果转换为标签 (0: PA abnormal, 1: Normal)"""
        labels = []
        for pred in predictions:
            if pred == 1:
                labels.append("Normal")
            else:
                labels.append("PA abnormal")
        return labels

    def validate_features_before_prediction(self, X):
        """在预测前验证特征数据类型"""
        print("=== 特征数据类型验证 ===")

        # 检查分类特征
        categorical_feats = []
        if self.metadata and 'categorical_features' in self.metadata:
            categorical_feats = self.metadata['categorical_features']
        else:
            categorical_feats = [feat for feat in self.categorical_features if feat in X.columns]

        for feat in categorical_feats:
            if feat in X.columns:
                dtype = X[feat].dtype
                sample_values = X[feat].iloc[:3].tolist()
                print(f"特征 '{feat}': 类型={dtype}, 样例值={sample_values}")

                # 立即修复发现的问题
                if dtype in ['float64', 'float32']:
                    print(f"  → 修复: 将浮点特征转换为字符串")
                    X[feat] = X[feat].astype(str)
                    # 清理浮点数表示
                    X[feat] = X[feat].str.replace(r'\.0$', '', regex=True)

        return X

    def run_prediction(self):
        """运行预测"""
        try:
            # 加载模型
            success, message = self.load_model()
            if not success:
                return False, message

            # 加载预处理对象
            if self.preprocess_config:
                success, message = self.load_preprocessor()
                if not success:
                    return False, f"预处理对象加载失败: {message}"

            # 加载样本数据
            if self.sample_file.endswith('.csv'):
                sample_df = pd.read_csv(self.sample_file)
            else:
                return False, "只支持CSV格式的样本文件"

            print(f"成功加载样本数据: {len(sample_df)} 条记录")

            # 准备特征数据
            non_feature_columns = ['PA Status Pattern 1', 'PA Status Pattern 2', 'Symptoms', 'PA Status Repair Info',
                                   'Serial', 'ProductName', 'Timestamp']
            feature_columns = [col for col in sample_df.columns if col not in non_feature_columns]
            X = sample_df[feature_columns]

            print(f"原始特征数量: {len(X.columns)}")

            # 🔧 关键修复：在预处理前验证和修复特征类型
            X = self.validate_features_before_prediction(X)

            # 处理缺失值和无限值
            X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

            # 对于分类特征，用 'Missing' 填充；对于数值特征，用 0 填充
            categorical_feats = []
            if self.metadata and 'categorical_features' in self.metadata:
                categorical_feats = [f for f in self.metadata['categorical_features'] if f in X.columns]

            for col in X.columns:
                if col in categorical_feats:
                    X[col] = X[col].fillna('Missing')
                else:
                    X[col] = X[col].fillna(0)

            # 对齐特征
            X_aligned = self.align_features(X)

            # 应用预处理（数值特征标准化和分类特征编码）
            X_processed = self.apply_preprocessing(X_aligned)

            # 最终验证和转换数据类型
            X_final = self.validate_and_convert_dtypes(X_processed)

            # 确保所有数据都是浮点型
            X_final = X_final.astype(np.float32)

            print(f"最终特征数量: {len(X_final.columns)}")
            print(f"最终特征数据类型: {X_final.dtypes.unique()}")

            # CatBoost 预测
            if self.model_type == "catboost":
                print("执行 CatBoost 预测...")

                # 🔧 重要：对于CatBoost，需要确保没有分类特征泄漏到最终数据中
                # 因为我们已经进行了编码，所有特征都应该是数值型

                # 最终检查是否有任何非数值数据
                for col in X_final.columns:
                    if X_final[col].dtype == 'object':
                        print(f"警告: 特征 {col} 仍然是对象类型，尝试强制转换")
                        try:
                            X_final[col] = pd.to_numeric(X_final[col], errors='coerce').fillna(0)
                        except:
                            X_final[col] = 0

                predictions = self.model.predict(X_final)

            else:
                # 其他模型的预测逻辑保持不变
                predictions = self._predict_other_models(X_final)

            # 创建结果DataFrame
            self.results_df = sample_df.copy()
            self.results_df['预测结果'] = predictions
            self.results_df['预测标签'] = self.convert_prediction_to_label(predictions)

            return True, "预测完成"

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"预测错误详情: {error_details}")
            return False, f"预测过程中出错: {str(e)}"

    def _predict_other_models(self, X_final):
        """其他模型的预测方法"""
        if self.model_type == "xgboost":
            dmatrix = xgb.DMatrix(X_final)
            predictions = self.model.predict(dmatrix)
            if len(predictions.shape) > 1:
                predictions = np.argmax(predictions, axis=1)
        elif self.model_type == "lightgbm":
            predictions = self.model.predict(X_final, num_iteration=self.model.best_iteration)
            if len(predictions.shape) > 1:
                predictions = np.argmax(predictions, axis=1)
        elif self.model_type == "tabnet":
            predictions = self.model.predict(X_final.values)
        elif self.model_type == "sklearn":
            if hasattr(self.model, 'predict_proba'):
                proba_predictions = self.model.predict_proba(X_final)
                if len(proba_predictions.shape) > 1 and proba_predictions.shape[1] > 1:
                    predictions = np.argmax(proba_predictions, axis=1)
                else:
                    predictions = (proba_predictions > 0.5).astype(int).flatten()
            else:
                predictions = self.model.predict(X_final)
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

        return predictions

    def get_accuracy_report(self):
        """获取准确性报告"""
        if self.results_df is None:
            return "没有可用的预测结果"

        report = ""

        # 样本层面准确性
        report += "1. 样本层面准确性:\n"
        report += "-" * 30 + "\n"

        # 检查所有输出特征列并生成准确性报告
        output_columns = ['PA Status Pattern 1', 'PA Status Pattern 2', 'PA Status Repair Info']

        for col in output_columns:
            if col in self.results_df.columns:
                # 确保标签是数值类型
                y_true = self.results_df[col].copy()

                # 将标签转换为数值
                if y_true.dtype == 'object':
                    # 使用与训练时相同的转换规则
                    def convert_label(label):
                        label_str = str(label).strip()
                        if 'Normal' in label_str:
                            return 1
                        else:
                            return 0

                    y_true = y_true.apply(convert_label)

                accuracy = accuracy_score(
                    y_true,
                    self.results_df['预测结果']
                )
                report += f"与 {col} 比较:\n"
                report += f"  准确率: {accuracy:.4f}\n"

                # 详细分类报告
                class_report = classification_report(
                    y_true,
                    self.results_df['预测结果'],
                    digits=4
                )
                report += "\n详细分类报告:\n"
                report += class_report + "\n"

        return report

    def clear_results(self):
        """清空结果"""
        self.results_df = None
        self.model = None
        self.model_features = None
        self.scaler = None
        self.encoder = None
        self.metadata = None
