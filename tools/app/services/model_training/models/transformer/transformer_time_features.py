import os
import numpy as np
import joblib

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score

from tools.app.utils.json_processor_TimeGAN_choose_label import TrainingDataProcessor


class TransformerDataProcessor(TrainingDataProcessor):
    def prepare_for_transformer(self, seq_len=20):
        """
        Pipeline：
        1. load_and_filter_data()
        2. extract_features()
        3. preprocess_data()
        4. build_timegan_sequences()  -> (X_seq, y_seq, serial_ids)
        """
        # 1. 读入 & 过滤 Unknown 标签
        df_raw = self.load_and_filter_data()

        # 2. 从 JSON 提取数值 + 类别特征（这里不要 drop Timestamp，构序列要用）
        df_features = self.extract_features(df_raw)

        # 3. 编码 + 标准化（注意这里 numeric_features / categorical_features 不包含 Timestamp）
        df_preprocessed, scaler = self.preprocess_data(df_features)

        # 4. 构造固定长度的序列 (N, seq_len, D)
        # 短序列丢弃，只取最后 seq_len 个时间步，且不把 Timestamp 当特征
        X_seq, y_seq, serial_ids = self.build_timegan_sequences(
            df_preprocessed,
            seq_len=seq_len
        )

        return X_seq, y_seq, serial_ids, scaler


# ======================
# 2. Transformer 模型部分
# ======================

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)  # (max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)  # (max_len, 1)
        div_term = torch.exp(torch.arange(0, d_model, 2, dtype=torch.float32) *
                             (-torch.log(torch.tensor(10000.0)) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer('pe', pe)

    def forward(self, x):
        """
        x: (batch_size, seq_len, d_model)
        """
        seq_len = x.size(1)
        x = x + self.pe[:, :seq_len, :]
        return x


class TimeSeriesTransformerEncoder(nn.Module):
    def __init__(
        self,
        input_dim,          # 输入特征维度 D
        num_classes=2,      # 输出类别数
        d_model=128,        # Transformer 内部特征维度
        nhead=20,            # Multi-head attention 头数
        num_layers=3,       # Encoder 堆叠层数
        dim_feedforward=256,
        dropout=0.1,
        pooling='mean'      # 'last' 或 'mean'
    ):
        super().__init__()
        self.input_dim = input_dim
        self.d_model = d_model
        self.pooling = pooling

        # 1. 线性投影: input_dim -> d_model
        self.input_proj = nn.Linear(input_dim, d_model)

        # 输入侧 LayerNorm
        self.input_norm = nn.LayerNorm(d_model)

        # 2. 位置编码
        self.pos_encoder = PositionalEncoding(d_model)

        # 3. Transformer Encoder 堆叠（内部自带 LayerNorm）
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation='gelu'
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        # 最后一层 LayerNorm
        self.final_norm = nn.LayerNorm(d_model)

        # 4. 分类头（可以根据需要换成更深的 MLP）
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes)
        )

    def forward(self, x, src_key_padding_mask=None):
        """
        x: (batch_size, seq_len, input_dim)
        """
        # 1. 映射到 d_model
        x = self.input_proj(x)      # (B, T, d_model)
        x = self.input_norm(x)      # (B, T, d_model)

        # 2. 加位置编码
        x = self.pos_encoder(x)     # (B, T, d_model)

        # 3. Transformer Encoder
        x = self.transformer_encoder(
            x,
            src_key_padding_mask=src_key_padding_mask
        )                           # (B, T, d_model)

        # 3.1 最终 LayerNorm
        x = self.final_norm(x)

        # 4. Pooling
        if self.pooling == 'last':
            h = x[:, -1, :]         # (B, d_model)
        elif self.pooling == 'mean':
            h = x.mean(dim=1)       # (B, d_model)
        else:
            raise ValueError(f"Unsupported pooling type: {self.pooling}")

        # 5. 分类头
        logits = self.classifier(h) # (B, num_classes)
        return logits


# ======================
# 3. Dataset & DataLoader
# ======================

class SequenceDataset(Dataset):
    def __init__(self, X, y):
        """
        X: numpy array, shape (N, T, D)
        y: numpy array, shape (N,)
        """
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def build_loaders(X_train, y_train, X_val, y_val, X_test, y_test,
                  batch_size=64):
    train_loader = DataLoader(SequenceDataset(X_train, y_train),
                              batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(SequenceDataset(X_val, y_val),
                            batch_size=batch_size, shuffle=False, drop_last=False)
    test_loader = DataLoader(SequenceDataset(X_test, y_test),
                             batch_size=batch_size, shuffle=False, drop_last=False)
    return train_loader, val_loader, test_loader


# ======================
# 4. Train / Val / Test 划分 + 保存
# ======================

def split_train_val_test(X, y, test_size=0.15, val_size=0.15, random_state=42):
    """
    将数据分为 Train / Val / Test。
    test_size 和 val_size 是相对于全量数据的占比。
    """
    # Step 1: Train + Temp
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y,
        test_size=(test_size + val_size),
        stratify=y,
        random_state=random_state
    )

    # Step 2: Temp -> Val + Test
    val_ratio = val_size / (test_size + val_size)  # 在 temp 中 val 的占比
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=(1 - val_ratio),
        stratify=y_temp,
        random_state=random_state
    )

    return X_train, X_val, X_test, y_train, y_val, y_test


def save_splits(output_dir, X_train, y_train, X_val, y_val, X_test, y_test):
    os.makedirs(output_dir, exist_ok=True)

    np.savez(os.path.join(output_dir, "train_data.npz"), X=X_train, y=y_train)
    np.savez(os.path.join(output_dir, "val_data.npz"),   X=X_val,   y=y_val)
    np.savez(os.path.join(output_dir, "test_data.npz"),  X=X_test,  y=y_test)

    print(f"Saved train/val/test splits to: {output_dir}")


# ======================
# 5. 评估函数（Val & Test 通用）
# ======================

def evaluate_on_loader(model, loader, device):
    model.eval()

    all_probs = []
    all_targets = []

    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            logits = model(X_batch)
            probs = F.softmax(logits, dim=1)[:, 1]

            all_probs.append(probs.cpu().numpy())
            all_targets.append(y_batch.cpu().numpy())

    all_probs = np.concatenate(all_probs)
    all_targets = np.concatenate(all_targets)
    preds = (all_probs >= 0.5).astype(int)

    metrics = {
        "acc": accuracy_score(all_targets, preds),
        "f1": f1_score(all_targets, preds),
        "auc": roc_auc_score(all_targets, all_probs)
    }
    return metrics


# ======================
# 6. 总训练函数：带 Train / Val / Test
# ======================

def train_transformer_encoder(
    input_dir,
    output_dir,
    seq_len=20,
    batch_size=64,
    num_epochs=50,
    lr=1e-4,
    device=None
):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    # ---------- 1. 数据准备 ----------
    processor = TransformerDataProcessor(input_dir, output_dir)
    X_seq, y_seq, serial_ids, scaler = processor.prepare_for_transformer(seq_len=seq_len)

    print(f"Total sequences: {X_seq.shape[0]}, seq_len={X_seq.shape[1]}, feature_dim={X_seq.shape[2]}")

    # Train / Val / Test 三分
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(
        X_seq, y_seq, test_size=0.15, val_size=0.15, random_state=42
    )

    save_splits(output_dir, X_train, y_train, X_val, y_val, X_test, y_test)

    train_loader, val_loader, test_loader = build_loaders(
        X_train, y_train, X_val, y_val, X_test, y_test,
        batch_size=batch_size
    )

    print(f"Train samples: {len(X_train)}, Val samples: {len(X_val)}, Test samples: {len(X_test)}")

    # ---------- 2. 定义模型 ----------
    feature_cols = processor.numeric_features + processor.categorical_features
    input_dim = len(feature_cols)

    model = TimeSeriesTransformerEncoder(
        input_dim=input_dim,
        num_classes=2,
        d_model=128,
        nhead=8,
        num_layers=3,
        dim_feedforward=256,
        dropout=0.1,
        pooling='last'
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    criterion = nn.CrossEntropyLoss()

    best_val_auc = 0.0
    best_model_path = os.path.join(output_dir, "transformer_encoder_best.pt")

    # ---------- 3. 训练循环 ----------
    for epoch in range(num_epochs):
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0
        train_probs_list, train_targets_list = [], []

        for batch_X, batch_y in train_loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            logits = model(batch_X)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * batch_X.size(0)
            preds = logits.argmax(dim=1)
            train_correct += (preds == batch_y).sum().item()
            train_total += batch_X.size(0)

            probs = F.softmax(logits, dim=1)[:, 1]
            train_probs_list.append(probs.detach().cpu().numpy())
            train_targets_list.append(batch_y.detach().cpu().numpy())

        train_loss /= train_total
        train_acc = train_correct / train_total
        train_probs = np.concatenate(train_probs_list)
        train_targets = np.concatenate(train_targets_list)
        train_preds_bin = (train_probs >= 0.5).astype(int)
        train_f1 = f1_score(train_targets, train_preds_bin, average='binary')
        try:
            train_auc = roc_auc_score(train_targets, train_probs)
        except ValueError:
            train_auc = float('nan')

        # ---------- 验证 ----------
        val_metrics = evaluate_on_loader(model, val_loader, device)
        val_loss = 0.0  # 如需 val_loss，可在 evaluate_on_loader 里扩展，这里先跳过

        print(
            f"Epoch [{epoch+1}/{num_epochs}] "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} "
            f"F1: {train_f1:.4f} AUC: {train_auc:.4f} | "
            f"Val Acc: {val_metrics['acc']:.4f} "
            f"F1: {val_metrics['f1']:.4f} AUC: {val_metrics['auc']:.4f}"
        )

        # 用验证集 AUC 选择最佳模型
        if val_metrics["auc"] > best_val_auc:
            best_val_auc = val_metrics["auc"]
            torch.save(model.state_dict(), best_model_path)
            print(f"🏅Saved best model! val_auc={best_val_auc:.4f}")

    # ---------- 4. 加载最佳模型，评估 Test ----------
    print("\n===== Loading best model and running Test evaluation =====")
    model.load_state_dict(torch.load(best_model_path, map_location=device))

    test_metrics = evaluate_on_loader(model, test_loader, device)
    print(f"[Test] Acc: {test_metrics['acc']:.4f} "
          f"F1: {test_metrics['f1']:.4f} "
          f"AUC: {test_metrics['auc']:.4f}")

    # ---------- 5. 保存 scaler ----------
    scaler_path = os.path.join(output_dir, "transformer_scaler.pkl")
    joblib.dump(scaler, scaler_path)
    print(f"Scaler saved to {scaler_path}")
    print(f"Best model saved to: {best_model_path}")

    return model, scaler, test_metrics


# ======================
# 7. main
# ======================

if __name__ == "__main__":
    input_dir = "/tools/data/files_for_training"
    output_dir = "/tools/data/processed_dataset"

    model, scaler, test_metrics = train_transformer_encoder(
        input_dir=input_dir,
        output_dir=output_dir,
        seq_len=20,
        batch_size=64,
        num_epochs=200,
        lr=1e-4
    )
