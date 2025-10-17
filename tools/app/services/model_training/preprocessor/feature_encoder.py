from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np
import pandas as pd


# 非数值型特征值编码
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

            # 具体布尔型特征（继承模板并扩展）
            'autoPeakPhaseCal': {},
            'delayEst': {},
            'delayEstimationEnable': {},
            'dpGainLoopEnable': {},
            'dpTsEnable': {},
            'dpdAutoStart': {},
            'gainAutoStart': {},
            'ganBoostModeEnable': {},
            'islastDelEstFracSuccess': {},
            'shpAutoStart': {},
            'shpGanAlgEnabled': {},
            'shpGanAlgFunctionStatus': {},
            'shpGanAlgHwCapablility': {},
            'torSupported': {},
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

        # 打印未知值警告
        self._warn_unknown_values()

        return X_encoded

    def _warn_unknown_values(self):
        """警告未知值"""
        if self.unknown_mappings:
            print("警告: 发现以下特征的未知值:")
            for feature, unknown_values in self.unknown_mappings.items():
                print(f"  {feature}: {list(unknown_values)[:5]}")  # 只显示前5个
                if len(unknown_values) > 5:
                    print(f"    ... 还有 {len(unknown_values) - 5} 个未知值")

    def get_feature_info(self):
        """获取特征编码信息"""
        info = {
            'mapped_features': list(self.mappings.keys()),
            'unknown_mappings': {k: list(v) for k, v in self.unknown_mappings.items()}
        }
        return info

    def fit_transform(self, X, y=None):
        """适应并转换数据"""
        return self.fit(X, y).transform(X)


# 兼容性包装器，用于处理可能缺少的特征
class RobustFeatureEncoder(FeatureEncoder):
    """增强版特征编码器，处理缺失特征"""

    def transform(self, X):
        """转换特征数据，处理缺失特征"""
        if X.empty:
            return X

        X_encoded = X.copy()

        # 只处理存在的特征
        available_features = [feat for feat in X.columns if feat in self.mappings]

        for feature in available_features:
            if feature in self.mappings:
                # 特殊处理布尔型特征
                if feature in self.bool_categorical_features:
                    # 统一转换为字符串并标准化
                    str_vals = X[feature].astype(str).str.strip()
                    X_encoded[feature] = str_vals.map(self.mappings[feature])
                else:
                    # 处理其他分类特征
                    def clean_text(text):
                        if pd.isna(text) or text is None:
                            return np.nan
                        return str(text).strip()

                    cleaned = X[feature].apply(clean_text)
                    X_encoded[feature] = cleaned.map(self.mappings[feature])

        # 处理未映射到的值（用-1表示）
        for col in available_features:
            if col in self.mappings:
                X_encoded[col] = X_encoded[col].fillna(-1).astype(int)

        return X_encoded
