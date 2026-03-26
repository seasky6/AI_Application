import matplotlib
import matplotlib.pyplot as plt
import textwrap

# Switch to a robust backend to avoid errors in PyCharm
matplotlib.use("TkAgg")  # Ensure compatibility with PyCharm's backend

# Define ensemble learning advantages and their importance levels
advantages = [
    {"label": "Good at tabular data", "description": "Analyzing tabular and structured data samples", "value": 5},
    {"label": "Feature weight analysis", "description": "Supports to understand feature impacts", "value": 4},
    {"label": "High performance", "description": "Integrate multiple sub-learners to enhance accuracy", "value": 3},
    {"label": "Robust to noise", "description": "Reduces sensitivity to noisy data", "value": 2},
    {"label": "Wide applicability", "description": "Applicable in log analysis, finance, healthcare", "value": 1},
]

# Prepare data for the bar chart
labels = [adv["label"] for adv in advantages]
values = [adv["value"] for adv in advantages]
descriptions = [adv["description"] for adv in advantages]

# Create the bar chart
plt.figure(figsize=(14, 8))
bars = plt.bar(labels, values, color=['lightblue', 'lightgreen', 'gold', 'pink', 'orange'])

# Add descriptions above each bar
for bar, description in zip(bars, descriptions):
    # bar_width = bar.get_width() * 50  # 动态计算每行字符数，50为调整因子
    # wrapped_description = textwrap.fill(description, width=int(bar_width))  # 自动换行
    plt.text(
        bar.get_x() + bar.get_width() / 2,  # Center the text above the bar
        bar.get_height() + 0.1,  # Position text slightly above the bar's top
        description,
        ha='center',
        va='bottom',
        fontsize=14
    )

# Customize the title and axis labels
plt.title("Key Advantages of Ensemble Methods", fontsize=20, fontweight="bold", pad=20)
plt.ylabel("Importance", fontsize=14)
plt.xlabel("Advantages", fontsize=14)

# 增加x和y轴边框的间距
plt.xlim(-0.5, len(labels) - 0.5)  # 在x轴范围两侧各扩展1单位，避免边框覆盖文本
plt.ylim(0, max(values) + 0.5)       # y轴范围顶部增加1单位，用于显示顶部的描述文本

# Optimize layout and display the plot
plt.tight_layout()
plt.show()
