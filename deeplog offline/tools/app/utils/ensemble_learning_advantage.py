import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# 设置字体为支持英文或中文的兼容字体，并修改后端以解决PyCharm中的兼容性问题
matplotlib.rcParams['font.family'] = 'Arial'  # 可以改为其他支持中文的字体，如 'SimSun'
matplotlib.use('TkAgg')  # 更换后端以避免 PyCharm 特定问题

# 设置画布大小
plt.figure(figsize=(10, 6))

# 定义集成学习的优点内容及位置
advantages = [
    {"label": "Good at structured data",
     "description": "Excels at analyzing tabular and structured data samples",
     "color": "lightblue", "xy": (0.1, 0.8)},
    {"label": "Feature importance analysis",
     "description": "Supports analysis to understand feature impacts",
     "color": "lightgreen", "xy": (0.6, 0.8)},
    {"label": "High performance",
     "description": "Combines multiple weak learners to enhance accuracy",
     "color": "gold", "xy": (0.1, 0.5)},
    {"label": "Robust to noise",
     "description": "Reduces sensitivity to noisy data",
     "color": "pink", "xy": (0.6, 0.5)},
    {"label": "Wide applicability",
     "description": "Applicable to log analysis, financial markets, healthcare domains",
     "color": "orange", "xy": (0.35, 0.2)},
]

# 绘制模块化内容为圆角矩形
for adv in advantages:
    box = FancyBboxPatch(
        adv["xy"], 0.4, 0.15, boxstyle="round,pad=0.1", color=adv["color"], alpha=0.7
    )
    plt.gca().add_patch(box)
    plt.text(
        adv["xy"][0] + 0.02,
        adv["xy"][1] + 0.1,
        adv["label"],
        fontsize=12,
        fontweight="bold"
    )
    plt.text(
        adv["xy"][0] + 0.02,
        adv["xy"][1] + 0.02,
        adv["description"],
        fontsize=10
    )

# 添加标题并设置格式
plt.title("Key Advantages of Ensemble Methods", fontsize=16, fontweight="bold", pad=20)
plt.axis("off")  # 关闭坐标轴以优化视觉效果
plt.tight_layout()
plt.show()
