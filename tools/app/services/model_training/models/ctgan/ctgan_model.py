import os
import numpy as np
import pandas as pd
from ctgan.synthesizers.ctgan import CTGAN
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report
import json
from collections import Counter

# 1. 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../../'))
DATA_DIR = os.path.join(ROOT_DIR, 'processed_datasets')
MODEL_DIR = os.path.join(ROOT_DIR, 'saved_models')
os.makedirs(MODEL_DIR, exist_ok=True)




# 2. 加载数据函数
def load_dataset(filename):
    df = pd.read_csv(os.path.join(DATA_DIR, filename))
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    return X, y_enc, le

X_train, y_train, le = load_dataset('train.csv')
X_val,   y_val,   _  = load_dataset('val.csv')
X_test,  y_test,  _  = load_dataset('ctgan.csv')

# 3. 动态计算样本权重（可选）
def calculate_class_weights(y):
    freq = Counter(y)
    total = len(y)
    n_cls = len(freq)
    weights = {c: total/(n_cls*cnt) for c,cnt in freq.items()}
    return np.array([weights[y_i] for y_i in y])
sample_weights = calculate_class_weights(y_train)

# 5. 使用 CTGAN 为每个类别单独训练并生成平衡数据
df_gan = pd.DataFrame(X_train)
df_gan['__target__'] = y_train

unique_classes = np.unique(y_train)
samples_per_class = 100  # 可调（也可以设为 ctgan set 中该类的样本数）
syn_list = []

for cls in unique_classes:
    print(f"训练 class {cls} 的 CTGAN...")
    df_cls = df_gan[df_gan['__target__'] == cls].copy()

    # 每个类分别训练自己的 CTGAN
    ctgan = CTGAN(epochs=100, verbose=True)
    ctgan.fit(df_cls)

    # 每类生成样本
    syn_cls = ctgan.sample(samples_per_class)
    syn_list.append(syn_cls)

# 合并所有类别的 synthetic data
syn = pd.concat(syn_list, ignore_index=True)
X_syn = syn.drop(columns='__target__')
y_syn = syn['__target__']

# 7. 下游分类：在合成数据上训练一个 RandomForest（也可以换成任何其它分类器）
# 使用 class_weight='balanced' 来自动处理不平衡问题
clf = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight='balanced' # 关键改动在这里
)
# 然后像之前一样，在合成数据上进行训练
clf.fit(X_syn, y_syn)


# 8. 在真实测试集上评估
y_pred = clf.predict(X_test)
print("="*30 + " 最终评估 " + "="*30)
print(f"准确率: {accuracy_score(y_test, y_pred):.4f}")
print(f"F1 (macro): {f1_score(y_test, y_pred, average='macro'):.4f}")
print(classification_report(y_test, y_pred, digits=4))

# 9. 保存 CTGAN 模型和下游分类器
ctgan.save(os.path.join(MODEL_DIR, 'ctgan_gan_model.pkl'))
import joblib
joblib.dump(clf, os.path.join(MODEL_DIR, 'rf_on_gan.pkl'))

# 10. 保存元数据
meta = {
  'generator': 'CTGAN',
  'target_encoder': dict(zip(le.classes_, le.transform(le.classes_))),
  'eval': {
    'accuracy': accuracy_score(y_test, y_pred),
    'f1_macro': f1_score(y_test, y_pred, average='macro')
  }
}
