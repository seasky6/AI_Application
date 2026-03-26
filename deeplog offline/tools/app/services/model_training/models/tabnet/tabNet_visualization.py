import os
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import LabelEncoder
from collections import Counter
import json
from pytorch_tabnet.tab_model import TabNetClassifier
import torch
import matplotlib
matplotlib.use('TkAgg')  # 在导入 pyplot 之前设置
import matplotlib.pyplot as plt
import seaborn as sns




# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../../'))
DATA_DIR = os.path.join(ROOT_DIR, 'processed_datasets')
MODEL_DIR = os.path.join(ROOT_DIR, 'saved_models')
os.makedirs(MODEL_DIR, exist_ok=True)

# 数据加载函数
def load_dataset(filename):
    df = pd.read_csv(os.path.join(DATA_DIR, filename))
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]
    le = LabelEncoder()
    y = le.fit_transform(y)
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    return X, y

X_train, y_train = load_dataset('train.csv')
X_val, y_val = load_dataset('val.csv')
X_test, y_test = load_dataset('test.csv')

# 类别权重计算
def calculate_class_weights(y):
    class_counts = Counter(y)
    total_samples = len(y)
    n_classes = len(class_counts)
    weights = {
        cls: total_samples / (n_classes * count)
        for cls, count in class_counts.items()
    }
    print(f"类别分布: {class_counts}")
    print(f"计算权重: {weights}")
    return weights

class_weights = calculate_class_weights(y_train)
sample_weights = np.array([class_weights[y] for y in y_train])

# 特征工程
INFERENCE_FEATURES = [
    'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IMpaSv:.0', 'IMpaSv:.1',
    'torTemp', 'txAtt', 'txPmb', 'txTorPmb'
]

class AntiFeatureGenerator:
    def __init__(self, inference_features):
        self.inference_features = inference_features
        self.rng = np.random.RandomState(42)
        self.interaction_pairs = [
            ('DpaVddSv', 'PaVddSv'),
            ('IDpaSv:.0', 'IDpaSv:.1'),
            ('IMpaSv:.0', 'IMpaSv:.1')
        ]

    def transform(self, X):
        X_anti = X.copy()

        # 方法1：添加噪声版本（只对原始推理特征）
        for feat in self.inference_features:
            if feat in X.columns:
                # 高斯噪声（均值=0，标准差=0.1*原特征标准差）
                noise = self.rng.normal(0, 0.1 * X[feat].std(), size=len(X))
                X_anti[f'noisy_{feat}'] = X[feat] + noise

        # 方法2：分位数变换（所有数值特征）
        # 将特征值转换为其在样本中的分位数排名（0到1之间），消除原始值的绝对大小影响，保留相对顺序
        numeric_cols = X.select_dtypes(include=np.number).columns
        for feat in numeric_cols:
            X_anti[f'rank_{feat}'] = X[feat].rank(pct=True)  # 计算百分位排名

        # 方法3：交互特征
        # 通过组合多个原始特征生成新特征，捕捉特征间的协同效应，同时抑制原始特征的影响
        for feat1, feat2 in self.interaction_pairs:
            if all(f in X.columns for f in [feat1, feat2]):
                # 绝对值差异
                X_anti[f'diff_abs_{feat1}_{feat2}'] = (X[feat1] - X[feat2]).abs()
                # 比值（带平滑）
                X_anti[f'ratio_{feat1}_{feat2}'] = X[feat1] / (X[feat2] + 1e-6)
                # 乘积交互
                X_anti[f'product_{feat1}_{feat2}'] = X[feat1] * X[feat2]

        return X_anti

feat_engineer = AntiFeatureGenerator(INFERENCE_FEATURES)

X_train_df = feat_engineer.transform(X_train)
X_val_df = feat_engineer.transform(X_val)
X_test_df = feat_engineer.transform(X_test)

feature_names = X_train_df.columns
X_train, X_val, X_test = X_train_df.values, X_val_df.values, X_test_df.values

# 训练TabNet模型
clf = TabNetClassifier(
    n_d=32, n_a=32, n_steps=5, gamma=1.5, lambda_sparse=1e-4,
    optimizer_fn=torch.optim.Adam,
    optimizer_params=dict(lr=2e-2),
    scheduler_params={"step_size":10, "gamma":0.9},
    scheduler_fn=torch.optim.lr_scheduler.StepLR,
    mask_type='entmax',
    verbose=1, seed=42
)


clf.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    eval_name=['val'],
    eval_metric=['logloss', 'accuracy'],
    max_epochs=5,
    patience=30,
    batch_size=256,
    virtual_batch_size=64,
    weights=sample_weights,
)



# 测试集预测

y_pred = clf.predict(X_test)

print(f"\n{'=' * 40}\n最终评估\n{'=' * 40}")
print(f"准确率: {accuracy_score(y_test, y_pred):.4f}")
print(f"F1 Score (Macro): {f1_score(y_test, y_pred, average='macro'):.4f}")
print("\n分类报告:")
print(classification_report(y_test, y_pred, digits=4))






# 特征重要性分析函数
def analyze_feature_importance(model, feature_names):
    # TabNet的feature_importances_属性是特征重要性权重
    importance_series = pd.Series(model.feature_importances_, index=feature_names)
    importance_df = importance_series.reset_index()
    importance_df.columns = ['feature', 'weight']
    importance_df = importance_df.sort_values('weight', ascending=False)
    print("\n影响 Top20 特征排名:")
    print(importance_df.head(20))

    # 只筛选实际存在的推理特征
    existing_inference_features = [f for f in INFERENCE_FEATURES if f in importance_df['feature'].values]
    engineered_inference_features = [f for f in importance_df['feature'] if any(inf_f in f for inf_f in INFERENCE_FEATURES)]

    print("\n初始推理特征影响排名:")
    if existing_inference_features:
        print(importance_df[importance_df['feature'].isin(existing_inference_features)].sort_values('weight', ascending=False))
    else:
        print("初始推理特征不存在！")

    print("\n对抗工程处理后特征影响排名:")
    if engineered_inference_features:
        print(importance_df[importance_df['feature'].isin(engineered_inference_features)].sort_values('weight', ascending=False))
    else:
        print("对抗工程处理后的特征不存在！")

    return importance_df

# 调用特征重要性分析
feat_importance = analyze_feature_importance(clf, feature_names)

# 保存模型
clf.save_model(os.path.join(MODEL_DIR, 'tabnet_model'))

# 保存元数据
params_serializable = {k: str(v) for k, v in clf.get_params().items()}
# metadata = {
#     'inference_features': INFERENCE_FEATURES,
#     'feature_importance': importance_df.set_index('feature')['importance'].to_dict(),
#     'eval_metrics': {
#         'accuracy': accuracy_score(y_test, y_pred),
#         'f1_scores': {
#             'macro': f1_score(y_test, y_pred, average='macro'),
#             'micro': f1_score(y_test, y_pred, average='micro'),
#             'weighted': f1_score(y_test, y_pred, average='weighted')
#         }
#     },
#     'model_params': params_serializable
# }





metadata = {
    'preprocessing': {
        'merged_features': {
            'DpaVddSv': '合并所有DpaVddSv参数',
            'PaVddSv': '合并所有PaVddSv参数',
            'IDpaSv:.0': '合并所有IDpaSv:x.0参数',
            'IDpaSv:.1': '合并所有IDpaSv:x.1参数',
            'IMpaSv:.0': '合并所有IMpaSv:x.0参数',
            'IMpaSv:.1': '合并所有IMpaSv:x.1参数'
        }
    },
    'inference_features': INFERENCE_FEATURES,
    'feature_importance': {k: v.to_dict() for k, v in feat_importance.items()},
    'eval_metrics': {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1_scores': {
            'macro': f1_score(y_test, y_pred, average='macro'),
            'micro': f1_score(y_test, y_pred, average='micro'),
            'weighted': f1_score(y_test, y_pred, average='weighted')
        }
    },
    'model_params': params_serializable
}

with open(os.path.join(MODEL_DIR, 'tabnet_metadata.json'), 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\n模型保存到 {MODEL_DIR}")


##########从这边开始#######
# 获取并可视化掩码图
# 选择测试集前20条样本
X_explain = X_test[:20]
y_explain = y_test[:20]

explain_matrix, masks = clf.explain(X_explain)  # masks 是长度为 n_steps 的列表，每个元素形状为 (num_samples, num_features)


# masks是一个长度为n_steps的列表，每个元素shape为(num_samples, num_features)

plt.figure(figsize=(20, 4))
sample_idx = [0]  # 选择第1个样本绘制
n_steps = len(masks)
for sample in sample_idx:
    for step in range(n_steps):
        plt.subplot(1, n_steps, step+1)
        plt.bar(range(len(feature_names)), masks[step][sample])
        plt.title(f'Step {step+1} Mask')
        plt.xlabel('Feature Index')
        plt.ylabel('Mask Value')
        plt.xticks(rotation=90)

    plt.tight_layout()
    plt.figure()







num_samples = masks[0].shape[0]
num_steps = len(masks)
num_features = masks[0].shape[1]

# 构造热力图数据
masks_concat = np.zeros((num_samples * num_steps, num_features))
for step in range(num_steps):
    masks_concat[step*num_samples:(step+1)*num_samples, :] = masks[step]

# 构建行标签，只保留每一步第一个和最后一个样本标签，其他为空字符串
row_labels = [f'Sample {i+1} Step {j+1}' for j in range(num_steps) for i in range(num_samples)]

# 计算纵轴需要显示标签的位置和对应标签
yticks_pos = []
yticks_labels = []
for step in range(num_steps):
    first_idx = step * num_samples
    last_idx = (step + 1) * num_samples - 1
    yticks_pos.extend([first_idx, last_idx])
    yticks_labels.extend([row_labels[first_idx], row_labels[last_idx]])

sns.heatmap(masks_concat, cmap='viridis', yticklabels=False)
plt.xlabel('Features')
plt.ylabel('Samples')
plt.yticks(ticks=yticks_pos, labels=yticks_labels)
plt.title('Feature Importance Masks for Samples and Steps')
plt.xticks(rotation=90)
plt.tight_layout()
# plt.show()


for step in range(num_steps):
    plt.figure(figsize=(10, 5))  # 为每一步分配足够的高度
    # plt.subplot(num_steps, 1, step + 1)
    sns.heatmap(masks[step], cmap='viridis',
                xticklabels=feature_names, yticklabels=[f'Sample {i+1}' for i in range(num_samples)])
    plt.title(f'Feature Importance Mask - Step {step + 1}')
    # plt.xlabel('Features')
    # plt.ylabel('Samples')
    plt.xticks(rotation=90)
plt.tight_layout()
plt.show()



# ######## 特征对全局的影响可视化 ##########


# masks 是长度为 n_steps 的列表，每个元素形状为 (num_samples, num_features)
num_samples = masks[0].shape[0]
num_steps = len(masks)

# 构建决策过程字典
decision_process = {}

for sample_idx in range(num_samples):
    sample_key = f'Sample_{sample_idx + 1}'
    decision_process[sample_key] = {}
    for step_idx in range(num_steps):
        step_key = f'Step_{step_idx + 1}'
        feature_importances = masks[step_idx][sample_idx]
        # 过滤掉重要性为0的特征（可选）
        used_features = {feature_names[i]: float(feature_importances[i])
                         for i in range(len(feature_names)) if feature_importances[i] > 1e-6}
        # 按重要性排序
        used_features = dict(sorted(used_features.items(), key=lambda item: item[1], reverse=True))
        decision_process[sample_key][step_key] = used_features
# 保存到 JSON 文件
output_path = os.path.join(MODEL_DIR, 'Decision-making_process.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(decision_process, f, indent=2, ensure_ascii=False)

print(f'每个样本每一步决策所用特征及其重要程度已保存到 {output_path}')
######################到这里都是画图代码#############
