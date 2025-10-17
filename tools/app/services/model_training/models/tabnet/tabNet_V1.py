# -*- coding: utf-8 -*-
import os
import json
import numpy as np
import pandas as pd
from collections import Counter

from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression

import torch
from pytorch_tabnet.tab_model import TabNetClassifier

# ================================================================================
# 全局开关（按需改动）
# ================================================================================
USE_ADVERSARIAL_FEATURES = False     # 是否启用对抗特征工程（保留你的类，默认关）
USE_LABEL_SMOOTHING = True           # Label Smoothing（抗标签噪声）
USE_MIXUP = True                     # 训练集离线 mixup 增强
MIXUP_RATIO = 0.30                   # mixup 增强比例（0.2~0.5 推荐）
MIXUP_ALPHA = 0.2                    # Beta(alpha, alpha) 的 alpha
USE_MULTI_SEED_ENSEMBLE = False       # 多种子小集成
SEEDS = [42, 2025, 7]                # 想更强可以加更多种子
USE_PLATT_CALIBRATION = True         # 用验证集做 Platt（LR）概率校准

# ================================================================================
# 路径设置
# ================================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../../'))
DATA_DIR = os.path.join(ROOT_DIR, 'processed_datasets')
MODEL_DIR = os.path.join(ROOT_DIR, 'saved_models')
os.makedirs(MODEL_DIR, exist_ok=True)

# ================================================================================
# 数据加载
# ================================================================================
def load_dataset(filename):
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, filename))
        X = df.iloc[:, :-1]
        y = df.iloc[:, -1]
        le = LabelEncoder()
        y = le.fit_transform(y)
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        return X, y
    except Exception as e:
        print(f"加载数据失败: {str(e)}")
        raise

try:
    X_train_df, y_train = load_dataset('train.csv')
    X_val_df, y_val = load_dataset('val.csv')
    X_test_df, y_test = load_dataset('test.csv')
except Exception as e:
    print(f"数据加载错误: {str(e)}")
    raise SystemExit(1)

# ================================================================================
# 类别权重
# ================================================================================
def calculate_class_weights(y):
    class_counts = Counter(y)
    total_samples = len(y)
    n_classes = len(class_counts)
    weights = {cls: total_samples / (n_classes * count) for cls, count in class_counts.items()}
    print(f"类别分布: {class_counts}")
    print(f"计算权重: {weights}")
    return weights

class_weights = calculate_class_weights(y_train)
sample_weights = np.array([class_weights[y] for y in y_train])

# ================================================================================
# 特征工程（保留你的 AntiFeatureGenerator，默认不启用）
# ================================================================================
INFERENCE_FEATURES = [
    'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IMpaSv:.0', 'IMpaSv:.1',
    'torTemp', 'txAtt', 'txPmb', 'txTorPmb'
]

class AntiFeatureGenerator:
    def __init__(self, inference_features, enabled=False):
        self.enabled = enabled
        self.inference_features = inference_features
        self.rng = np.random.RandomState(42)
        self.interaction_pairs = [
            ('DpaVddSv', 'PaVddSv'),
            ('IDpaSv:.0', 'IDpaSv:.1'),
            ('IMpaSv:.0', 'IMpaSv:.1')
        ]

    def transform(self, X):
        if not self.enabled:
            return X
        X_anti = X.copy()

        # --- 如需启用下列三类增强，取消注释即可 ---
        # # 方法1：对原始推理特征加噪声
        # for feat in self.inference_features:
        #     if feat in X.columns:
        #         noise = self.rng.normal(0, 0.1 * (X[feat].std() or 1.0), size=len(X))
        #         X_anti[f'noisy_{feat}'] = X[feat] + noise
        #
        # # 方法2：分位数(rank)特征
        # numeric_cols = X.select_dtypes(include=np.number).columns
        # for feat in numeric_cols:
        #     X_anti[f'rank_{feat}'] = X[feat].rank(pct=True)
        #
        # # 方法3：交互特征
        # for f1, f2 in self.interaction_pairs:
        #     if f1 in X.columns and f2 in X.columns:
        #         X_anti[f'diff_abs_{f1}_{f2}'] = (X[f1] - X[f2]).abs()
        #         X_anti[f'ratio_{f1}_{f2}'] = X[f1] / (X[f2] + 1e-6)
        #         X_anti[f'product_{f1}_{f2}'] = X[f1] * X[f2]

        return X_anti

if USE_ADVERSARIAL_FEATURES:
    print("\n启用对抗特征工程...")
    feat_engineer = AntiFeatureGenerator(INFERENCE_FEATURES, enabled=True)
    X_train_df = feat_engineer.transform(X_train_df)
    X_val_df   = feat_engineer.transform(X_val_df)
    X_test_df  = feat_engineer.transform(X_test_df)
else:
    print("\n禁用对抗特征工程，使用原始特征...")

# 保存特征名（用于特征重要性输出）
feature_names = X_train_df.columns.tolist()

# 转 numpy（tabnet 要求）
X_train = X_train_df.values
X_val   = X_val_df.values
X_test  = X_test_df.values

# ================================================================================
# 训练增强：Label Smoothing & Mixup（工具函数）
# ================================================================================
import torch.nn.functional as F

def ce_with_label_smoothing(y_pred, y_true, eps=0.05):
    """y_pred: (N, C) logits; y_true: (N,) int64"""
    C = y_pred.size(1)
    with torch.no_grad():
        tgt = torch.full_like(y_pred, eps/(C-1))
        tgt.scatter_(1, y_true.view(-1,1), 1-eps)
    logp = F.log_softmax(y_pred, dim=1)
    return -(tgt * logp).sum(1).mean()

def mixup_offline(X, y, sample_w=None, ratio=0.3, alpha=0.2, rng=None):
    """离线 mixup：返回增强后的 X, y, sample_weights（若提供）"""
    rng = np.random.RandomState(2025) if rng is None else rng
    n = len(X)
    m = int(n * ratio)
    idx1 = rng.randint(0, n, size=m)
    idx2 = rng.randint(0, n, size=m)
    lam = rng.beta(alpha, alpha, size=m)
    X_aug = lam[:, None] * X[idx1] + (1 - lam)[:, None] * X[idx2]
    # 简化：保留硬标签（取 idx1 的标签），无需改 loss
    y_aug = y[idx1]
    if sample_w is not None:
        sw_aug = sample_w[idx1]  # 对应复制 idx1 的权重
        sample_w = np.concatenate([sample_w, sw_aug])
    X = np.vstack([X, X_aug])
    y = np.concatenate([y, y_aug])
    return X, y, sample_w

# ================================================================================
# 构建模型（复用你的参数）
# ================================================================================
def build_model(seed, use_label_smoothing):
    loss_fn = ce_with_label_smoothing if use_label_smoothing else None
    clf = TabNetClassifier(
        n_d=28, n_a=28, n_steps=5,
        gamma=1.8,
        lambda_sparse=5e-4,
        optimizer_fn=torch.optim.AdamW,
        optimizer_params=dict(lr=1.5e-3, weight_decay=3e-4),
        scheduler_fn=torch.optim.lr_scheduler.CosineAnnealingLR,
        scheduler_params={'T_max': 30, 'eta_min': 1e-5},
        mask_type='sparsemax',
        clip_value=1.0,
        # loss_fn=loss_fn,
        verbose=0, seed=seed
    )
    return clf

# ================================================================================
# 训练集增强（可选）
# ================================================================================
Xtr, ytr = X_train, y_train
sw_tr = sample_weights.copy()

if USE_MIXUP:
    Xtr, ytr, sw_tr = mixup_offline(
        Xtr, ytr, sample_w=sw_tr,
        ratio=MIXUP_RATIO, alpha=MIXUP_ALPHA
    )

# ================================================================================
# 训练 & 集成
# ================================================================================
models = []
val_probs_list = []
test_probs_list = []
feat_imps = []

seeds = SEEDS if USE_MULTI_SEED_ENSEMBLE else [42]

for sd in seeds:
    clf = build_model(sd, USE_LABEL_SMOOTHING)
    clf.fit(
        Xtr, ytr,
        eval_set=[(X_val, y_val)],
        eval_name=['val'],
        eval_metric=['logloss', 'accuracy'],
        max_epochs=120, patience=30,
        batch_size=512, virtual_batch_size=64,
        weights=sw_tr
    )
    models.append(clf)
    val_probs_list.append(clf.predict_proba(X_val)[:, 1])
    test_probs_list.append(clf.predict_proba(X_test)[:, 1])
    feat_imps.append(clf.feature_importances_)

# 集成概率 = 多模型平均
val_prob = np.mean(val_probs_list, axis=0)
test_prob = np.mean(test_probs_list, axis=0)
feat_importance_mean = np.mean(np.vstack(feat_imps), axis=0)

# ================================================================================
# 概率校准（Platt），用验证集概率拟合 LR，再作用于 test
# ================================================================================
if USE_PLATT_CALIBRATION:
    lr_cal = LogisticRegression(max_iter=1000)
    lr_cal.fit(val_prob.reshape(-1, 1), y_val)
    val_prob = lr_cal.predict_proba(val_prob.reshape(-1, 1))[:, 1]
    test_prob = lr_cal.predict_proba(test_prob.reshape(-1, 1))[:, 1]

# 用 0.5 阈值（可根据 val_prob 扫描阈值）
y_val_pred = (val_prob >= 0.5).astype(int)
y_test_pred = (test_prob >= 0.5).astype(int)

# ================================================================================
# 评估
# ================================================================================
print(f"\n{'=' * 40}\n最终评估（Test）\n{'=' * 40}")
print(f"准确率: {accuracy_score(y_test, y_test_pred):.4f}")
print(f"F1 Score (Macro): {f1_score(y_test, y_test_pred, average='macro'):.4f}")
print("\n分类报告:")
print(classification_report(y_test, y_test_pred, digits=4))

# ================================================================================
# 特征重要性（集成平均）
# ================================================================================
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': feat_importance_mean
}).sort_values('importance', ascending=False)

print("\n影响Top20特征排名（集成平均）:")
print(importance_df.head(20))

# ================================================================================
# 保存模型与元数据
# ================================================================================
model_suffix = 'gen'  # generalized
# 保存第一个模型（其余可按需保存或只存参数）
models[0].save_model(os.path.join(MODEL_DIR, f'tabnet_{model_suffix}_model.zip'))

params_serializable = {k: str(v) for k, v in models[0].get_params().items()}
metadata = {
    'preprocessing': {
        'adversarial_features_enabled': USE_ADVERSARIAL_FEATURES,
        'mixup': {'enabled': USE_MIXUP, 'ratio': MIXUP_RATIO, 'alpha': MIXUP_ALPHA},
        'label_smoothing': USE_LABEL_SMOOTHING,
    },
    'ensemble': {
        'enabled': USE_MULTI_SEED_ENSEMBLE,
        'seeds': SEEDS,
        'platt_calibration': USE_PLATT_CALIBRATION
    },
    'inference_features': INFERENCE_FEATURES,
    'feature_importance': importance_df.set_index('feature')['importance'].to_dict(),
    'eval_metrics': {
        'accuracy': accuracy_score(y_test, y_test_pred),
        'f1_scores': {
            'macro': f1_score(y_test, y_test_pred, average='macro'),
            'micro': f1_score(y_test, y_test_pred, average='micro'),
            'weighted': f1_score(y_test, y_test_pred, average='weighted')
        }
    },
    'model_params': params_serializable
}

with open(os.path.join(MODEL_DIR, f'tabnet_{model_suffix}_metadata.json'), 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\n模型与元数据已保存到 {MODEL_DIR}")
