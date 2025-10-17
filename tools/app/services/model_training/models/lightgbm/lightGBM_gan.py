import os
import numpy as np
import pandas as pd
import lightgbm as lgb
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import LabelEncoder
from collections import Counter
import json

def load_dataset(filename, data_dir):
    try:
        df = pd.read_csv(os.path.join(data_dir, filename))
        X = df.iloc[:, :-1]
        y = df.iloc[:, -1]
        le = LabelEncoder()
        y = le.fit_transform(y)

        # 处理空值和无限值，填充为0
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        return X, y
    except Exception as e:
        print(f"加载数据失败: {str(e)}")
        raise

def calculate_class_weights(y):
    class_counts = Counter(y)
    total_samples = len(y)
    n_classes = len(class_counts)
    weights = {cls: total_samples / (n_classes * count) for cls, count in class_counts.items()}
    print(f"类别分布: {class_counts}")
    print(f"计算权重: {weights}")
    return weights

class AntiFeatureGenerator:
    def __init__(self, inference_features):
        self.inference_features = list(inference_features)
        self.rng = np.random.RandomState(42)
        self.interaction_pairs = [
            ('DpaVddSv', 'PaVddSv'),
            ('IDpaSv:.0', 'IDpaSv:.1'),
            ('IMpaSv:.0', 'IMpaSv:.1')
        ]

    def transform(self, X):
        X_anti = X.copy()
        # for feat in self.inference_features:
        #     if feat in X.columns:
        #         noise = self.rng.normal(0, 0.1 * X[feat].std(), size=len(X))
        #         X_anti[f'noisy_{feat}'] = X[feat] + noise
        #
        # numeric_cols = X.select_dtypes(include=np.number).columns
        # for feat in numeric_cols:
        #     X_anti[f'rank_{feat}'] = X[feat].rank(pct=True)
        #
        # for feat1, feat2 in self.interaction_pairs:
        #     if all(f in X.columns for f in [feat1, feat2]):
        #         X_anti[f'diff_abs_{feat1}_{feat2}'] = (X[feat1] - X[feat2]).abs()
        #         X_anti[f'ratio_{feat1}_{feat2}'] = X[feat1] / (X[feat2] + 1e-6)
        #         X_anti[f'product_{feat1}_{feat2}'] = X[feat1] * X[feat2]

        return X_anti

def clean_feature_names(df):
    df = df.copy()
    df.columns = [c.replace(':', '_').replace('.', '_').replace(' ', '_') for c in df.columns]
    return df

def main():
    # 路径设置与第二个代码保持一致
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../../'))
    DATA_DIR = os.path.join(ROOT_DIR, 'processed_datasets')

    home_dir = os.path.expanduser("~")
    MODEL_DIR = os.path.join(home_dir, "lgb_models")  # 这里改为用户目录下的 lgb_models 文件夹
    os.makedirs(MODEL_DIR, exist_ok=True)

    # 加载数据
    X_train, y_train = load_dataset('train_gan.csv', DATA_DIR)
    X_val, y_val = load_dataset('val_gan.csv', DATA_DIR)
    X_test, y_test = load_dataset('test_gan.csv', DATA_DIR)

    # 推理特征
    INFERENCE_FEATURES = [
        'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IMpaSv:.0', 'IMpaSv:.1',
        'torTemp', 'txAtt', 'txPmb', 'txTorPmb'
    ]

    # 对抗性特征工程
    feat_engineer = AntiFeatureGenerator(INFERENCE_FEATURES)
    X_train = feat_engineer.transform(X_train)
    X_val = feat_engineer.transform(X_val)
    X_test = feat_engineer.transform(X_test)

    X_train = clean_feature_names(X_train)
    X_val = clean_feature_names(X_val)
    X_test = clean_feature_names(X_test)

    INFERENCE_FEATURES_CLEAN = [f.replace(':', '_').replace('.', '_').replace(' ', '_') for f in INFERENCE_FEATURES]

    # # 计算类别权重
    # class_weights = calculate_class_weights(y_train)
    #
    # sample_class_weights = np.array([class_weights[label] for label in y_train])

    y_train_series = pd.Series(y_train)
    # 对应类别设置权重
    sample_class_weights = y_train_series.map({0: 4.5, 1: 2.0, 2: 1.0})


    # 计算对抗性样本权重
    def calculate_anti_weights(X, inference_features):
        strength = X[inference_features].abs().mean(axis=1)
        weights = 1.0 - 0.5 * (strength - strength.min()) / (strength.max() - strength.min())
        return np.clip(weights, 0.3, 1.0)

    train_weights = calculate_anti_weights(X_train, INFERENCE_FEATURES_CLEAN)

    # 组合最终权重
    final_train_weights = train_weights * sample_class_weights

    # 创建 lightgbm 数据集
    lgb_train = lgb.Dataset(X_train, label=y_train, weight=final_train_weights)
    lgb_val = lgb.Dataset(X_val, label=y_val, reference=lgb_train)

    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': ['multi_logloss', 'multi_error'],
        'learning_rate': 0.03,
        'num_leaves': 96,
        'max_depth': 10,
        'min_data_in_leaf': 10,
        'min_gain_to_split': 0.05,
        'lambda_l1': 0.01,
        'lambda_l2': 0.1,
        'subsample': 0.9,
        'colsample_bytree': 0.9,
        'seed': 42,
        'verbose': -1,
        # 'is_unbalance': True  # 可测试
        # 'drop_rate' : 0.3,
        # 'skip_drop' : 0.4,
    }



    # 训练
    model = lgb.train(
        params,
        lgb_train,
        num_boost_round=500,
        valid_sets=[lgb_train, lgb_val],
        valid_names=['train', 'val'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=30),
            lgb.log_evaluation(period=20)
        ]
    )

    # 评估
    def evaluate(model, X, y_true):
        y_prob = model.predict(X, num_iteration=model.best_iteration)
        y_pred = np.argmax(y_prob, axis=1)
        print(f"\n{'='*40}\nFinal Evaluation\n{'='*40}")
        print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
        print(f"F1 Score (Macro): {f1_score(y_true, y_pred, average='macro'):.4f}")
        print("\nClassification Report:")
        print(classification_report(y_true, y_pred, zero_division=0))
        return y_pred

    test_pred = evaluate(model, X_test, y_test)

    # 特征重要性分析
    def analyze_feature_importance(model):
        importance = model.feature_importance(importance_type='split')
        features = model.feature_name()
        df_imp = pd.DataFrame({'feature': features, 'importance': importance}).sort_values(by='importance', ascending=False)
        print("\nTop 20 Features:")
        print(df_imp.head(20))
        return df_imp

    feat_importance = analyze_feature_importance(model)

    # 保存模型和元数据
    model_path = os.path.join(MODEL_DIR, 'lgb_anti_model.json')
    model.save_model(model_path)

    metadata = {
        'inference_features': INFERENCE_FEATURES_CLEAN,
        'feature_importance': feat_importance.set_index('feature')['importance'].to_dict(),
        'eval_metrics': {
            'accuracy': accuracy_score(y_test, test_pred),
            'f1_score_macro': f1_score(y_test, test_pred, average='macro'),
            'f1_score_micro': f1_score(y_test, test_pred, average='micro'),
            'f1_score_weighted': f1_score(y_test, test_pred, average='weighted'),
        },
        'model_params': params
    }

    with open(os.path.join(MODEL_DIR, 'model_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n模型保存到 {MODEL_DIR}")

if __name__ == '__main__':
    main()
