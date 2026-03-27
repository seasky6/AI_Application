import os
import json
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
import xgboost as xgb

# =========================
# 1) 特征清单（与训练对齐）
# =========================
DEFAULT_NUMERIC_FEATURES = [
    'DpaVddSv', 'PaVddSv',
    'IDpaSv:.0', 'IDpaSv:.1', 'IDpaSv:.2', 'IDpaSv:.3',
    'IMpaSv:.0', 'IMpaSv:.1', 'IMpaSv:.2', 'IMpaSv:.3',
    'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
    'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
    'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
]

DEFAULT_CATEGORICAL_FEATURES = [
    'autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable', 'desc',
    'dpGainLoopEnable', 'dpTsEnable', 'dpd', 'dpdAutoStart', 'gainAutoStart',
    'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState',
    'islastDelEstFracSuccess', 'linearizationStateMachine', 'runMode',
    'shpAutoStart', 'shpGanAlgEnabled', 'shpGanAlgFunctionStatus',
    'shpGanAlgHwCapablility', 'status', 'statusBit', 'subId', 'torSupported'
]

# =========================
# 2) 分类编码映射（与前端一致）
# =========================
BOOL_TEMPLATE = {
    'true': 1, 'false': 0,
    'TRUE': 1, 'FALSE': 0,
    'True': 1, 'False': 0,
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
    '': -1,
}

ENCODING_MAP: Dict[str, Dict[str, int]] = {
    'desc': {
        'linearization failure': 0,
        'ramping timeout': 1,
        'ramping timeout.': 1,
        'supervision': 2,
        'tuning timeout': 3,
        'Tuning timeout.': 3,
        'Wait for data timeout': 4,
        '': -1
    },
    'dpd': {'off': 0, 'on': 1, '': -1},
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
        '': -1
    },
    'ganBoostModeState': {'BOOST': 0, 'NORMAL': 1, '': -1},
    'linearizationStateMachine': {
        'CtrlLinStateStarted=started': 0,
        'CtrlLinStateStartLate=started': 1,
        'ns=stopped': 2,
        '': -1
    },
    'runMode': {'2D': 0, 'BF': 1, '': -1},
    'status': {'DPD_STATUS_FAIL': 0, 'DPD_STATUS_OK': 1, '': -1},
    'statusBit': {
        'DPD_SCHD_MEAS_STATUS_EGR_SRL_ERR_B': 0,
        'DPD_SCHD_MEAS_STATUS_EXT_EVC_IDLE_B': 0,
        'DPD_SCHD_MEAS_STATUS_TOR_ADC_ERR_B': 0,
        'EGR_SRL_ERR': 0, 'EXT_EVC_IDLE': 0, 'EXT_TDD_TX_OFF': 0, 'TOR_ADC_ERR': 0,
        'DPD_SCHD_MEAS_STATUS_EXT_DPD_IDLE_B': 1,
        'EXT_DPD_IDLE': 2,
        'EGR_SRL_ERR | EXT_DPD_IDLE': 3,
        'EGR_SRL_ERR | EXT_DPD_IDLE | TOR_ADC_ERR': 4,
        'EXT_DPD_IDLE | EXT_EVC_IDLE': 5,
        'EXT_DPD_IDLE | EXT_TDD_TX_OFF': 6,
        'NA': -1, '': -1
    },
    'subId': {
        'ext-bb-data-missing': 0,
        'lin-other': 1, 'lin-ramping': 2, 'lin-sv': 3, 'lin-sv-high-freq-fault': 4, 'lin-tuning': 5,
        '': -1
    }
}

BOOL_CATEGORICAL_FEATURES = [
    'autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable',
    'dpGainLoopEnable', 'dpTsEnable', 'dpdAutoStart', 'gainAutoStart',
    'ganBoostModeEnable', 'islastDelEstFracSuccess', 'shpAutoStart',
    'shpGanAlgEnabled', 'shpGanAlgFunctionStatus', 'shpGanAlgHwCapablility',
    'torSupported'
]

MISSING_TOKENS = {'nan', 'NaN', 'None', 'none', 'null', 'Null', 'NULL', 'N/A', 'n/a', '<NA>', 'NaT', ''}


def norm_cat_key(v: Any) -> str:
    if v is None:
        return ''
    s = str(v).trim() if hasattr(str(v), 'trim') else str(v).strip()
    return '' if s in MISSING_TOKENS else s


# =========================
# 3) 模型容器
# =========================
def process_categorical(df: pd.DataFrame, categorical_cols: List[str]) -> pd.DataFrame:
    if not categorical_cols:
        return df
    d = df.copy()
    exist = [c for c in categorical_cols if c in d.columns]
    for c in exist:
        if c in BOOL_CATEGORICAL_FEATURES:
            d[c] = d[c].map(lambda v: BOOL_TEMPLATE.get(norm_cat_key(v), -1))
        else:
            mp = ENCODING_MAP.get(c)
            d[c] = d[c].map(lambda v: mp.get(norm_cat_key(v), -1) if mp else -1)
    return d


class XGBBundle:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.booster: Optional[xgb.Booster] = None
        self.metadata: Dict[str, Any] = {}
        self.input_features: List[str] = []
        self.scaler_mean: Dict[str, float] = {}
        self.scaler_scale: Dict[str, float] = {}
        self.booster_feature_names: List[str] = []

    def load(self):
        # 1) 模型文件（兼容 .json/.josn）
        model_path = None
        for name in ['xgboost_model.json', 'xgboost_model.josn']:
            p = os.path.join(self.base_dir, name)
            if os.path.exists(p):
                model_path = p
                break
        if not model_path:
            raise FileNotFoundError(f'[XGBBundle] model json not found in {self.base_dir}')

        booster = xgb.Booster()
        booster.load_model(model_path)
        self.booster = booster

        # 2) booster 内部记录的特征名
        try:
            self.booster_feature_names = booster.feature_names or []
        except Exception:
            self.booster_feature_names = []
        print(f'[XGBBundle] Loaded model: {model_path}')
        print(
            f'  - booster.feature_names (len={len(self.booster_feature_names)}): {self.booster_feature_names[:10]}{" ..." if len(self.booster_feature_names) > 10 else ""}')

        # 3) metadata.json
        meta_path = os.path.join(self.base_dir, 'metadata.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            self.input_features = self.metadata.get('input_features', [])
            scaler = self.metadata.get('fitted_scaler_params', {})
            self.scaler_mean = scaler.get('mean', {}) or {}
            self.scaler_scale = scaler.get('scale', {}) or {}
            print(f'[XGBBundle] Loaded metadata: {meta_path}')
            print(
                f'  - metadata.input_features (len={len(self.input_features)}): {self.input_features[:10]}{" ..." if len(self.input_features) > 10 else ""}')
            print(f'  - scaler params: mean={len(self.scaler_mean)}, scale={len(self.scaler_scale)}')
        else:
            print(f'[XGBBundle] metadata.json not found in {self.base_dir}; fallback to defaults')

    def preferred_order(self, num_cols: List[str], cat_cols: List[str]) -> List[str]:
        """选择最终对齐顺序：booster.feature_names > metadata.input_features > 默认清单"""
        if self.booster_feature_names:
            print('[Align] Using booster.feature_names as the expected order.')
            return self.booster_feature_names
        if self.input_features:
            print('[Align] Using metadata.input_features as the expected order.')
            return self.input_features
        print('[Align] Using default (numeric+categorical) order.')
        return num_cols + cat_cols

    def process_numeric(self, df: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
        if not numeric_cols:
            return df
        d = df.copy()
        exist = [c for c in numeric_cols if c in d.columns]
        if not exist:
            return d
        d[exist] = d[exist].replace([np.inf, -np.inf], [1000, -1000])
        for c in exist:
            d[c] = pd.to_numeric(d[c], errors='coerce')
        d[exist] = d[exist].fillna(0)
        if self.scaler_mean and self.scaler_scale:
            mean = np.array([self.scaler_mean.get(c, 0.0) for c in exist], dtype='float64')
            scale = np.array([self.scaler_scale.get(c, 1.0) for c in exist], dtype='float64')
            scale[scale == 0] = 1.0
            vals = d[exist].values.astype('float64')
            d[exist] = (vals - mean) / scale
        return d

    def align_features(self, df: pd.DataFrame, num_cols: List[str], cat_cols: List[str]) -> pd.DataFrame:
        """对齐到期望顺序，并打印差异。"""
        order = self.preferred_order(num_cols, cat_cols)

        # 补齐缺失列（对齐前最后兜底）
        for c in order:
            if c not in df.columns:
                df[c] = 0  # 安全兜底，分类会在 process_categorical 设为 -1；此处只保证列存在
        # 丢弃多余列
        extra = [c for c in df.columns if c not in order]
        if extra:
            print(f'[Align] Dropping extra columns not in expected order: {extra}')

        # 打印差异（顺序）
        current = [c for c in df.columns if c in order]
        if len(current) != len(order) or any(a != b for a, b in zip(current, order)):
            # 定位首个不一致点
            first_diff = None
            for i, (a, b) in enumerate(zip(current, order)):
                if a != b:
                    first_diff = i
                    break
            print('[Align] Feature order mismatch detected.')
            print(f'  - current.head(10): {current[:10]}{" ..." if len(current) > 10 else ""}')
            print(f'  - expected.head(10): {order[:10]}{" ..." if len(order) > 10 else ""}')
            if first_diff is not None:
                print(
                    f'  - first different index: {first_diff}, current="{current[first_diff]}", expected="{order[first_diff]}"')
            # 直接以 expected 顺序重排：
            df = df[order]
        else:
            # 顺序一致，仍然保证只保留 expected
            df = df[order]

        X = df.astype('float32')
        return X

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.booster is None:
            raise RuntimeError('[XGBBundle] booster not loaded!')
        dmat = xgb.DMatrix(
            X.values,
            feature_names=X.columns.tolist()
        )
        preds = self.booster.predict(dmat)
        if isinstance(preds, np.ndarray) and preds.ndim == 2 and preds.shape[1] > 1:
            preds = np.argmax(preds, axis=1)
        elif preds.ndim == 1:
            lo, hi = float(np.min(preds)), float(np.max(preds))
            if 0.0 <= lo <= hi <= 1.0:
                preds = (preds >= 0.5).astype(np.int32)
            else:
                preds = preds.astype(np.int32)
        else:
            preds = np.array(preds).astype(np.int32)
        return preds


# =========================
# 4) 双模型运行时（对外接口）
# =========================
class DualModelRuntime:
    def __init__(self, base_models_dir: str):
        self.normal = XGBBundle(os.path.join(base_models_dir, 'normal'))
        self.cgan = XGBBundle(os.path.join(base_models_dir, 'cgan'))
        self.num_cols = DEFAULT_NUMERIC_FEATURES
        self.cat_cols = DEFAULT_CATEGORICAL_FEATURES

    def load(self):
        self.normal.load()
        self.cgan.load()
        print('[DualModelRuntime] Models loaded.')

        # 打印 metadata vs default 差异（辅助诊断）
        if self.normal.input_features:
            nf = set(self.normal.input_features)
            expected = set(self.num_cols + self.cat_cols)
            only_in_meta = sorted(list(nf - expected))
            only_in_default = sorted(list(expected - nf))
            if only_in_meta:
                print(f'[DualModelRuntime] metadata.input_features 包含默认清单外列: {only_in_meta}')
            if only_in_default:
                print(f'[DualModelRuntime] 默认清单包含 metadata 未列出列: {only_in_default}')

    @staticmethod
    def _to_label(arr: np.ndarray) -> List[str]:
        return ['PA Normal' if int(v) == 1 else 'PA Abnormal' for v in arr.tolist()]

    @staticmethod
    def _major(labels: List[str]) -> str:
        pa = sum(1 for x in labels if x == 'PA Abnormal')
        nor = len(labels) - pa
        return 'PA Abnormal' if pa > nor else 'PA Normal'

    @staticmethod
    def _final(nm: str, cm: str) -> str:
        if nm == 'PA Abnormal' and cm == 'PA Abnormal':
            return 'PA Abnormal'
        if nm != cm:
            return 'May PA Abnormal'
        return 'PA Normal'

    def _prep(self, rows: List[Dict[str, Any]]) -> pd.DataFrame:
        df = pd.DataFrame(rows)

        print(f'[Prep] Incoming columns ({len(df.columns)}): {list(df.columns)}')
        print(f'[Prep] Incoming shape: {df.shape}')

        # 先做数值/分类处理（只处理存在的列）
        df = self.normal.process_numeric(df, self.num_cols)
        df = process_categorical(df, self.cat_cols)

        # === 补齐缺失列 ===
        missing_num = [c for c in self.num_cols if c not in df.columns]
        missing_cat = [c for c in self.cat_cols if c not in df.columns]
        if missing_num:
            print(f'[Prep] Missing numeric -> fill 0: {missing_num}')
            for c in missing_num:
                df[c] = 0
        if missing_cat:
            print(f'[Prep] Missing categorical -> fill -1: {missing_cat}')
            for c in missing_cat:
                df[c] = -1

        # 若存在“全空”的列，再次兜底
        for c in self.num_cols:
            if c in df.columns and df[c].isna().all():
                print(f'[Prep] Column all NaN (numeric) -> fill 0: {c}')
                df[c] = 0
        for c in self.cat_cols:
            if c in df.columns and df[c].isna().all():
                print(f'[Prep] Column all NaN (categorical) -> fill -1: {c}')
                df[c] = -1

        print(
            f'[Prep] Columns after fill ({len(df.columns)}): {list(df.columns)[:12]}{" ..." if len(df.columns) > 12 else ""}')

        # 对齐顺序（优先 booster.feature_names）
        X = self.normal.align_features(df, self.num_cols, self.cat_cols)
        print(f'[Prep] X.shape after align: {X.shape}')
        print(f'[Prep] X.columns.head(12): {list(X.columns[:12])}{" ..." if X.shape[1] > 12 else ""}')
        return X

    def predict(self, rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not rows:
            return [], []

        X = self._prep(rows)
        # normal / cgan 统一按 normal 的顺序
        y_n = self.normal.predict(X)
        # 确保 cgan Booster 也看到相同顺序（用相同列构造 DMatrix）
        y_c = self.cgan.predict(X)

        nL = self._to_label(y_n)
        cL = self._to_label(y_c)

        # 条目级
        entries: List[Dict[str, Any]] = []
        for r, nl, cl in zip(rows, nL, cL):
            entries.append({
                'serial': r.get('Serial', ''),
                'productName': r.get('ProductName', ''),
                'timestamp': r.get('Timestamp', ''),
                'sourceFile': r.get('SourceFile', ''),
                'normalLabel': nl,
                'cganLabel': cl
            })

        # 产品级聚合
        by: Dict[str, List[Dict[str, Any]]] = {}
        for e in entries:
            k = f"{e['serial']}||{e['productName']}"
            by.setdefault(k, []).append(e)

        summaries: List[Dict[str, Any]] = []
        for _, items in by.items():
            n = len(items)
            normal_pa = sum(1 for it in items if it['normalLabel'] == 'PA Abnormal')
            cgan_pa = sum(1 for it in items if it['cganLabel'] == 'PA Abnormal')
            normal_major = self._major([it['normalLabel'] for it in items])
            cgan_major = self._major([it['cganLabel'] for it in items])
            final = self._final(normal_major, cgan_major)

            summaries.append({
                'serial': items[0]['serial'],
                'productName': items[0]['productName'],
                'distribution': {
                    'normal': {'paAbnormalPct': normal_pa / n, 'normalPct': 1 - (normal_pa / n)},
                    'cgan': {'paAbnormalPct': cgan_pa / n, 'normalPct': 1 - (cgan_pa / n)}
                },
                'normalModelMajority': normal_major,
                'cganModelMajority': cgan_major,
                'finalDecision': final
            })

        return entries, summaries
