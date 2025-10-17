import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend
import matplotlib.pyplot as plt


# Data for pie chart
labels = [
    "PA abn.",
    "DC/DC abn.",
    "DPD issue",
    "TRX issue",
    "LTU misfun.",
    "DFE abn.",
    "VSWR err",
    "SW issue"
]
sizes = [60.1, 12, 9, 6.3, 2, 0.8, 1.5, 8.2]  # Percentage of each category
colors = ['gold', 'lightblue', 'lightgreen', 'pink', 'orange', 'purple', 'cyan', 'red']  # Colors for sections
explode = (0.1, 0, 0, 0, 0, 0, 0, 0)  # Explode the largest slice (PA abnormal)

# Create pie chart
plt.figure(figsize=(8, 8))
plt.pie(
    sizes,
    explode=explode,
    labels=labels,
    colors=colors,
    autopct='%1.1f%%',
    shadow=True,
    startangle=90
)

# Add title and display chart
plt.title("Radio Unit Anomaly Distribution", pad=40, fontweight='bold')
plt.axis('equal')  # Equal aspect ratio ensures that the pie is drawn as a circle
plt.show()
