import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# 读取 CSV 文件
train_df = pd.read_csv("C:/Deeplog/tools/processed_datasets/train_gan.csv")
test_df = pd.read_csv("C:/Deeplog/tools/processed_datasets/test_gan.csv")

# 筛选需要的列
cols = ['DpaVddSv', 'PaVddSv', 'PA Status']
train_df = train_df[cols].dropna()
test_df = test_df[cols].dropna()

# 分层采样 ctgan 数据
test_sampled = pd.concat([
    test_df[test_df['PA Status'] == 0].sample(n=20, random_state=42),
    test_df[test_df['PA Status'] == 1].sample(n=45, random_state=42),
    test_df[test_df['PA Status'] == 2].sample(n=200, random_state=42)
])

# 分层采样 train 数据，样本数与 ctgan 对应
train_sampled = pd.concat([
    train_df[train_df['PA Status'] == 0].sample(n=600, random_state=42),
    train_df[train_df['PA Status'] == 1].sample(n=600, random_state=42),
    train_df[train_df['PA Status'] == 2].sample(n=600, random_state=42)
])

# 画图函数
def plot_scatter(train_data, test_data, label):
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection='3d')

    # train：蓝色
    ax.scatter(train_data['DpaVddSv'], train_data['PaVddSv'], train_data['PA Status'],
               c='blue', label='Train', alpha=0.6)

    # ctgan：红色
    ax.scatter(test_data['DpaVddSv'], test_data['PaVddSv'], test_data['PA Status'],
               c='red', label='Test', alpha=0.6)

    ax.set_xlabel('DpaVddSv')
    ax.set_ylabel('PaVddSv')
    ax.set_zlabel('PA Status')
    ax.set_title(f'3D Scatter Plot - {label}')
    ax.legend()
    ax.set_zticks([0, 1, 2])
    plt.tight_layout()
    return fig

# 根据 PA Status 分类分别绘制图
figs = []
for cls in [0, 1, 2]:
    train_subset = train_sampled[train_sampled['PA Status'] == cls]
    test_subset = test_sampled[test_sampled['PA Status'] == cls]
    fig = plot_scatter(train_subset, test_subset, f'PA Status = {cls}')
    figs.append(fig)

plt.show()