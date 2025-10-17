import torch
import torch.nn as nn
import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # 或者 'Qt5Agg', 'GTK3Agg'
import matplotlib.pyplot as plt


# ----- 1. 模拟数据 ----- #
# 生成一个正弦波，并添加一些随机噪声
def generate_data(seq_length=1000, noise_amplitude=0.1):
    x = np.linspace(0, 20 * np.pi, seq_length)
    y = np.sin(x) + noise_amplitude * np.random.randn(seq_length)
    return y


time_series = generate_data(seq_length=1200)  # 生成1200个点

# 设置输入序列长度
input_size = 20  # 我们会用前20个点去预测第21个点
data_x = []
data_y = []

for i in range(len(time_series) - input_size):
    data_x.append(time_series[i:i + input_size])
    data_y.append(time_series[i + input_size])  # 下一个点作为标签

data_x = np.array(data_x)
data_y = np.array(data_y)

# 划分训练集和测试集
train_size = 1000
train_x = data_x[:train_size]
train_y = data_y[:train_size]
test_x = data_x[train_size:]
test_y = data_y[train_size:]

# 转成 PyTorch 张量
train_x_tensor = torch.tensor(train_x, dtype=torch.float32).unsqueeze(-1)  # (batch, seq_len, 1)
train_y_tensor = torch.tensor(train_y, dtype=torch.float32).unsqueeze(-1)  # (batch, 1)
test_x_tensor = torch.tensor(test_x, dtype=torch.float32).unsqueeze(-1)
test_y_tensor = torch.tensor(test_y, dtype=torch.float32).unsqueeze(-1)


# ----- 2. 定义 LSTM 模型 ----- #
class LSTMTimeSeries(nn.Module):
    def __init__(self, hidden_size=16, num_layers=1):
        super(LSTMTimeSeries, self).__init__()
        # 输入维度为1（因为每个时间步只有1个特征），隐藏层大小可调
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_size,
                            num_layers=num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)  # 最终输出1个值

    def forward(self, x):
        # x 形状: (batch, seq_len, 1)
        out, (h_n, c_n) = self.lstm(x)
        # out的形状: (batch, seq_len, hidden_size)
        # 取最后一个时间步的输出
        last_out = out[:, -1, :]  # (batch, hidden_size)
        out = self.fc(last_out)  # (batch, 1)
        return out


# ----- 2a. 定义 LSTMAttention 模型 ----- #
class LSTMAttention(nn.Module):
    def __init__(self, hidden_size=16, num_layers=1):
        super(LSTMAttention, self).__init__()
        # 输入维度为1（因为每个时间步只有1个特征），隐藏层大小可调
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_size,
                            num_layers=num_layers, batch_first=True)
        self.attention_weights = nn.Linear(hidden_size, 1)
        self.fc = nn.Linear(hidden_size, 1)  # 最终输出1个值

    def forward(self, x):
        # x 形状: (batch, seq_len, 1)
        lstm_out, (h_n, c_n) = self.lstm(x)
        # lstm_out的形状: (batch, seq_len, hidden_size)
        # 注意力机制计算
        attention_scores = self.attention_weights(lstm_out)
        attention_weights = torch.softmax(attention_scores, dim=1)
        # 根据注意力权重加权LSTM输出
        context_vector = (lstm_out * attention_weights).sum(dim=1)  # (batch, hidden_size)
        # 最终输出
        out = self.fc(context_vector)  # (batch, 1)
        return out


model = LSTMAttention(hidden_size=32, num_layers=1)  # 选择模型LSTMTimeSeries或者LSTMAttention
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

# ----- 3. 训练模型 ----- #
epochs = 10
for epoch in range(epochs):
    # 前向传播
    pred = model(train_x_tensor)
    loss = criterion(pred, train_y_tensor)

    # 反向传播和更新
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if (epoch + 1) % 2 == 0:
        print(f"Epoch [{epoch + 1}/{epochs}], Loss: {loss.item():.4f}")

# ----- 4. 测试与可视化 ----- #
model.eval()
with torch.no_grad():
    test_pred = model(test_x_tensor).squeeze(-1).numpy()

# 绘制对比图
plt.figure(figsize=(10, 4))
plt.plot(range(len(time_series)), time_series, label='True Time Series')
plt.axvline(x=train_size + input_size, color='r', linestyle='--', label='Train/Test Split')
plt.plot(range(train_size + input_size, len(time_series)), test_pred, label='Predicted', color='orange')
plt.title("PyTorch LSTM - Time Series Prediction")
plt.legend()
plt.show()
