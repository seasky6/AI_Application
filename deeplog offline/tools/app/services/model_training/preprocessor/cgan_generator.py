import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import joblib
import os
import uuid
from typing import Tuple, Dict
import warnings

warnings.filterwarnings('ignore')


class ProductCGANGenerator:
    """基于产品的CGAN数据生成器"""

    def __init__(self, latent_dim=100, device=None):
        """
        初始化CGAN生成器

        Args:
            latent_dim: 潜在空间维度
            device: 计算设备
        """
        self.latent_dim = latent_dim
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.generator = None
        self.discriminator = None
        self.scaler = None
        self.data_min = None
        self.data_max = None
        self.data_range = None
        print(f"CGAN Generator initialized on device: {self.device}")

    def _build_generator(self, output_dim):
        """构建生成器网络"""
        return nn.Sequential(
            nn.Linear(self.latent_dim + 1, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(32, output_dim),
            nn.Tanh()  # 输出在[-1, 1]之间
        )

    @staticmethod
    def _build_discriminator(input_dim):
        """构建判别器网络"""
        return nn.Sequential(
            nn.Linear(input_dim + 1, 64),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Dropout(0.3),
            nn.Linear(32, 16),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(16, 1),
            nn.Sigmoid()  # 确保输出在[0, 1]之间
        )

    @staticmethod
    def prepare_product_data(data: pd.DataFrame, serial_col: str = 'Serial') -> Tuple[pd.DataFrame, Dict]:
        """
        准备产品级别的数据

        Args:
            data: 条目级别的数据
            serial_col: 产品串号列名

        Returns:
            产品级别的聚合数据
            产品到条目的映射关系
        """
        # 检查必要的列是否存在
        if serial_col not in data.columns:
            raise ValueError(f"Serial column '{serial_col}' not found in data")

        # 聚合产品级别的特征
        numeric_features = [col for col in data.columns if col in [
            'DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IDpaSv:.2', 'IDpaSv:.3',
            'IMpaSv:.0', 'IMpaSv:.1', 'IMpaSv:.2', 'IMpaSv:.3',
            'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
            'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
            'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
        ]]

        # 基础列
        base_cols = ['ProductName', 'Timestamp', 'PA Status Repair Info', 'Repair Info Details']
        base_cols = [col for col in base_cols if col in data.columns]

        # 创建产品级别的聚合数据
        aggregation_dict = {}

        # 对基础列使用第一个值
        for col in base_cols:
            aggregation_dict[col] = 'first'

        # 对数值特征使用平均值
        for col in numeric_features:
            if col in data.columns:
                aggregation_dict[col] = 'mean'

        # 确保有聚合操作
        if not aggregation_dict:
            raise ValueError("No aggregation columns found")

        # 执行groupby聚合
        product_data = data.groupby(serial_col).agg(aggregation_dict).reset_index()

        # 重命名聚合列，为数值特征添加_mean后缀
        rename_dict = {}
        for col in numeric_features:
            if col in data.columns:
                rename_dict[col] = f'{col}_mean'

        product_data = product_data.rename(columns=rename_dict)

        # 存储产品到条目的映射
        product_to_entries = {}
        for product_id in data[serial_col].unique():
            product_to_entries[product_id] = data[data[serial_col] == product_id].index.tolist()

        print(f"聚合了 {len(product_data)} 个产品")
        print(f"产品数据列: {product_data.columns.tolist()}")

        return product_data, product_to_entries

    def train(self, minority_data: np.ndarray, labels: np.ndarray,
              epochs: int = 1000, batch_size: int = 32):
        """
        训练CGAN

        Args:
            minority_data: 少数类样本数据
            labels: 少数类标签
            epochs: 训练轮数
            batch_size: 批次大小
        """
        print(f"开始CGAN训练，数据形状: {minority_data.shape}")

        if len(minority_data) == 0:
            print("错误: 训练数据为空")
            return False

        # 检查数据
        print(f"训练数据统计:")
        print(f"  - 形状: {minority_data.shape}")

        # 清理数据中的NaN和无穷值
        nan_count = np.isnan(minority_data).sum()
        inf_count = np.isinf(minority_data).sum()

        print(f"  - NaN值数量: {nan_count}")
        print(f"  - 无穷值数量: {inf_count}")

        if nan_count > 0 or inf_count > 0:
            print("清理数据中的NaN和无穷值...")
            # 使用稳健的方法清理数据
            minority_data = np.nan_to_num(
                minority_data,
                nan=0.0,
                posinf=1.0,
                neginf=-1.0
            )
            print(f"清理后数据形状: {minority_data.shape}")

        # 再次检查数据范围
        data_min = minority_data.min()
        data_max = minority_data.max()
        print(f"清理后数据范围: [{data_min:.4f}, {data_max:.4f}]")

        # 如果数据范围异常，进行修正
        if data_max - data_min > 1e6 or abs(data_min) > 1e6 or abs(data_max) > 1e6:
            print("数据范围异常，进行稳健标准化...")
            # 使用分位数标准化避免极端值影响
            from sklearn.preprocessing import RobustScaler
            self.scaler = RobustScaler(quantile_range=(5, 95))  # 使用5%-95%分位数范围
            minority_data_scaled = self.scaler.fit_transform(minority_data)
        else:
            # 使用MinMaxScaler将数据缩放到[-1, 1]
            self.scaler = MinMaxScaler(feature_range=(-1, 1))
            minority_data_scaled = self.scaler.fit_transform(minority_data)

        print(f"标准化后数据范围: [{minority_data_scaled.min():.4f}, {minority_data_scaled.max():.4f}]")

        # 保存缩放参数用于后续生成
        self.data_min = data_min
        self.data_max = data_max
        self.data_range = data_max - data_min

        # 转换为PyTorch张量
        try:
            real_data = torch.FloatTensor(minority_data_scaled)
            real_labels = torch.FloatTensor(labels).reshape(-1, 1)

            if torch.cuda.is_available():
                self.device = 'cuda'
                real_data = real_data.cuda()
                real_labels = real_labels.cuda()
            else:
                self.device = 'cpu'

            print(f"数据转换为张量，设备: {self.device}")
        except Exception as e:
            print(f"张量转换失败: {e}")
            return False

        # 初始化网络
        try:
            self.generator = self._build_generator(minority_data_scaled.shape[1])
            self.discriminator = self._build_discriminator(minority_data_scaled.shape[1])

            if self.device == 'cuda':
                self.generator = self.generator.cuda()
                self.discriminator = self.discriminator.cuda()

            print("网络初始化完成")
        except Exception as e:
            print(f"网络初始化失败: {e}")
            return False

        # 定义优化器和损失函数
        g_optimizer = optim.Adam(self.generator.parameters(), lr=0.0002, betas=(0.5, 0.999))
        d_optimizer = optim.Adam(self.discriminator.parameters(), lr=0.0002, betas=(0.5, 0.999))
        criterion = nn.BCELoss()

        # 训练
        dataset = TensorDataset(real_data, real_labels)
        dataloader = DataLoader(dataset, batch_size=min(batch_size, len(minority_data_scaled)), shuffle=True)

        print(f"开始训练循环，共 {epochs} 轮...")

        # 训练循环
        for epoch in range(epochs):
            epoch_d_loss = 0
            epoch_g_loss = 0
            batch_count = 0

            for batch_idx, (real_batch, labels_batch) in enumerate(dataloader):
                batch_size_current = real_batch.size(0)

                # 真实和假标签，添加标签平滑
                real_labels_tensor = torch.ones(batch_size_current, 1) * 0.9 + torch.rand(batch_size_current, 1) * 0.1
                fake_labels_tensor = torch.zeros(batch_size_current, 1) + torch.rand(batch_size_current, 1) * 0.1

                if self.device == 'cuda':
                    real_labels_tensor = real_labels_tensor.cuda()
                    fake_labels_tensor = fake_labels_tensor.cuda()

                # ---------------------
                # 训练判别器
                # ---------------------
                self.discriminator.zero_grad()

                # 真实数据
                real_combined = torch.cat([real_batch, labels_batch], 1)
                output_real = self.discriminator(real_combined)

                # 确保输出在有效范围内
                output_real = torch.clamp(output_real, 1e-7, 1 - 1e-7)
                d_real_loss = criterion(output_real, real_labels_tensor)

                # 生成假数据
                noise = torch.randn(batch_size_current, self.latent_dim)
                if self.device == 'cuda':
                    noise = noise.cuda()
                noise_combined = torch.cat([noise, labels_batch], 1)
                fake_data = self.generator(noise_combined)

                # 假数据
                fake_combined = torch.cat([fake_data.detach(), labels_batch], 1)
                output_fake = self.discriminator(fake_combined)

                # 确保输出在有效范围内
                output_fake = torch.clamp(output_fake, 1e-7, 1 - 1e-7)
                d_fake_loss = criterion(output_fake, fake_labels_tensor)

                d_loss = (d_real_loss + d_fake_loss) / 2
                d_loss.backward()
                d_optimizer.step()

                # ---------------------
                # 训练生成器
                # ---------------------
                self.generator.zero_grad()

                # 生成假数据（重新生成）
                noise = torch.randn(batch_size_current, self.latent_dim)
                if self.device == 'cuda':
                    noise = noise.cuda()
                noise_combined = torch.cat([noise, labels_batch], 1)
                fake_data = self.generator(noise_combined)

                # 生成器损失
                fake_combined = torch.cat([fake_data, labels_batch], 1)
                output = self.discriminator(fake_combined)

                # 确保输出在有效范围内
                output = torch.clamp(output, 1e-7, 1 - 1e-7)
                g_loss = criterion(output, real_labels_tensor)

                g_loss.backward()
                g_optimizer.step()

                epoch_d_loss += d_loss.item()
                epoch_g_loss += g_loss.item()
                batch_count += 1

            if (epoch + 1) % 100 == 0:
                avg_d_loss = epoch_d_loss / batch_count if batch_count > 0 else 0
                avg_g_loss = epoch_g_loss / batch_count if batch_count > 0 else 0
                print(f"Epoch [{epoch + 1}/{epochs}] - D Loss: {avg_d_loss:.4f}, G Loss: {avg_g_loss:.4f}")

        print("CGAN训练完成")
        return True

    def generate_samples(self, n_samples: int, label: int = 0) -> np.ndarray:
        """
        生成新的少数类样本

        Args:
            n_samples: 要生成的样本数量
            label: 生成样本的标签

        Returns:
            生成的样本数据
        """
        if self.generator is None:
            print("错误: 生成器未训练，无法生成样本")
            raise ValueError("Generator not trained. Please train the model first.")

        self.generator.eval()

        with torch.no_grad():
            device = next(self.generator.parameters()).device

            # 生成噪声
            noise = torch.randn(n_samples, self.latent_dim).to(device)
            labels = torch.ones(n_samples, 1).to(device) * label

            # 生成数据
            noise_combined = torch.cat([noise, labels], 1)
            generated_data = self.generator(noise_combined)

            # 将数据移回CPU并转换为numpy
            generated_data_np = generated_data.cpu().numpy()

            # 反标准化数据到原始范围
            if self.scaler is not None:
                generated_data_original = self.scaler.inverse_transform(generated_data_np)
            else:
                # 如果没有scaler，尝试使用保存的参数
                if self.data_min is not None and self.data_max is not None:
                    # 假设数据被缩放到[-1, 1]
                    generated_data_original = (generated_data_np + 1) / 2 * (
                                self.data_max - self.data_min) + self.data_min
                else:
                    generated_data_original = generated_data_np

        return generated_data_original

    def generate_product_samples(self, original_data: pd.DataFrame,
                                 target_ratio: float = 1.0,
                                 serial_col: str = 'Serial') -> pd.DataFrame:
        """
        生成产品级别的样本并转换为条目格式

        Args:
            original_data: 原始条目数据
            target_ratio: 目标平衡比例
            serial_col: 产品串号列名

        Returns:
            生成的条目数据
        """
        print("\n=== CGAN数据生成调试信息 ===")
        print(f"原始数据形状: {original_data.shape}")

        # 准备产品级别数据
        product_data, product_to_entries = self.prepare_product_data(original_data, serial_col)

        if 'PA Status Repair Info' not in product_data.columns:
            print("错误: 产品数据中没有PA状态列")
            return pd.DataFrame()

        # 清理PA状态字符串
        product_data['PA_Status_Clean'] = product_data['PA Status Repair Info'].astype(str).str.strip()

        # 识别少数类和多数类
        minority_mask = product_data['PA_Status_Clean'] == 'Normal'
        majority_mask = product_data['PA_Status_Clean'] == 'PA abnormal'

        # 如果没有精确匹配，尝试模糊匹配
        if not minority_mask.any():
            minority_mask = product_data['PA_Status_Clean'].str.contains('normal', case=False, na=False)

        if not majority_mask.any():
            majority_mask = product_data['PA_Status_Clean'].str.contains('abnormal', case=False, na=False)

        minority_data = product_data[minority_mask]
        majority_data = product_data[majority_mask]

        print(f"少数类产品数量 (Normal): {len(minority_data)}")
        print(f"多数类产品数量 (PA abnormal): {len(majority_data)}")

        if len(minority_data) == 0:
            print("错误: 没有识别到少数类产品")
            return pd.DataFrame()

        if len(majority_data) == 0:
            print("错误: 没有识别到多数类产品")
            return pd.DataFrame()

        # 计算需要生成的数量
        target_minority_count = int(len(majority_data) * target_ratio)
        samples_to_generate = max(0, target_minority_count - len(minority_data))

        print(f"目标少数类数量: {target_minority_count}")
        print(f"当前少数类数量: {len(minority_data)}")
        print(f"需要生成的样本数: {samples_to_generate}")

        if samples_to_generate == 0:
            print("少数类已经平衡，不需要生成新样本")
            return pd.DataFrame()

        # 准备训练数据
        numeric_cols = [col for col in minority_data.columns if '_mean' in col and col != 'PA_Status_Clean']
        if not numeric_cols:
            print("错误: 没有数值特征可用于训练")
            return pd.DataFrame()

        print(f"使用 {len(numeric_cols)} 个数值特征进行训练")

        X_train = minority_data[numeric_cols].values
        print(f"训练数据形状: {X_train.shape}")

        # 检查并清理训练数据
        nan_count = np.isnan(X_train).sum()
        inf_count = np.isinf(X_train).sum()

        if nan_count > 0 or inf_count > 0:
            print(f"清理训练数据: {nan_count} 个NaN, {inf_count} 个无穷值")
            X_train = np.nan_to_num(X_train, nan=0.0, posinf=1.0, neginf=-1.0)

        # 训练CGAN
        print("开始CGAN训练...")
        try:
            success = self.train(X_train, np.zeros(len(minority_data)), epochs=500)
            if not success:
                print("CGAN训练失败")
                return pd.DataFrame()
            print("CGAN训练完成")
        except Exception as e:
            print(f"CGAN训练失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

        # 生成新的产品样本
        print(f"生成 {samples_to_generate} 个产品样本...")
        try:
            generated_product_data = self.generate_samples(samples_to_generate)
            print(f"成功生成产品数据，形状: {generated_product_data.shape}")
        except Exception as e:
            print(f"生成样本失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

        # 创建生成的产品DataFrame
        generated_products = []

        for i in range(samples_to_generate):
            product_uuid = str(uuid.uuid4())[:8]

            product_row = {
                'ProductName': f'CGAN_Product_{product_uuid}',
                serial_col: f'CGAN_{product_uuid}',
                'PA Status Repair Info': 'Normal',
                'Repair Info Details': 'CGAN Generated'
            }

            # 添加时间戳
            if 'Timestamp' in product_data.columns and len(original_data) > 0:
                product_row['Timestamp'] = original_data['Timestamp'].iloc[0]

            # 添加数值特征
            for j, col in enumerate(numeric_cols):
                product_row[col] = float(generated_product_data[i, j])

            generated_products.append(product_row)

        generated_product_df = pd.DataFrame(generated_products)
        print(f"创建了 {len(generated_product_df)} 个产品数据行")

        # 将产品数据转换为条目数据
        print("将产品数据转换为条目数据...")
        generated_entries = self._product_to_entries(generated_product_df, original_data)

        print(f"最终生成 {len(generated_entries)} 个条目")
        return generated_entries

    @staticmethod
    def _product_to_entries(product_df: pd.DataFrame,
                            original_data: pd.DataFrame,
                            entries_per_product: int = 3) -> pd.DataFrame:
        """
        将产品数据转换为条目数据

        Args:
            product_df: 产品级别数据
            original_data: 原始数据（用于获取特征分布）
            entries_per_product: 每个产品生成的条目数量

        Returns:
            条目级别的数据
        """
        if len(product_df) == 0:
            return pd.DataFrame()

        generated_entries = []

        for _, product_row in product_df.iterrows():
            # 为每个产品生成多个条目
            for entry_idx in range(entries_per_product):
                # 生成唯一的条目ID
                entry_uuid = str(uuid.uuid4())[:6]

                entry_row = {}

                # 复制产品级别信息
                entry_row['ProductName'] = product_row['ProductName']
                entry_row['Serial'] = product_row['Serial']
                entry_row['Timestamp'] = product_row.get('Timestamp', '')
                entry_row['PA Status Repair Info'] = product_row.get('PA Status Repair Info', 'Normal')
                entry_row['Repair Info Details'] = product_row.get('Repair Info Details', 'CGAN Generated')

                # 处理数值特征 - 简化版本
                numeric_features = ['DpaVddSv', 'PaVddSv', 'IDpaSv:.0', 'IDpaSv:.1', 'IDpaSv:.2', 'IDpaSv:.3',
                                    'IMpaSv:.0', 'IMpaSv:.1', 'IMpaSv:.2', 'IMpaSv:.3',
                                    'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
                                    'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
                                    'txDpdPma', 'txPma', 'txPmb', 'txTorPmb']

                for feat in numeric_features:
                    product_col = f'{feat}_mean'
                    if product_col in product_row:
                        base_value = product_row[product_col]
                        # 添加少量随机噪声
                        if not pd.isna(base_value):
                            noise = np.random.normal(0, abs(base_value) * 0.05)
                            entry_row[feat] = max(0, base_value + noise) if base_value >= 0 else base_value + noise
                        else:
                            entry_row[feat] = 0
                    elif feat in original_data.columns:
                        # 使用原始数据的中位数
                        entry_row[feat] = original_data[feat].median() if not original_data[feat].empty else 0

                # 添加分类特征（使用原始数据的常见值）
                categorical_features = ['autoPeakPhaseCal', 'delayEst', 'delayEstimationEnable', 'desc',
                                        'dpGainLoopEnable', 'dpTsEnable', 'dpd', 'dpdAutoStart', 'gainAutoStart',
                                        'gainStateMachine', 'ganBoostModeEnable', 'ganBoostModeState',
                                        'islastDelEstFracSuccess', 'linearizationStateMachine', 'runMode',
                                        'shpAutoStart', 'shpGanAlgEnabled', 'shpGanAlgFunctionStatus',
                                        'shpGanAlgHwCapablility', 'status', 'statusBit', 'subId', 'torSupported']

                for cat_col in categorical_features:
                    if cat_col in original_data.columns:
                        # 使用原始数据中最常见的值
                        if not original_data[cat_col].empty:
                            mode_val = original_data[cat_col].mode()
                            entry_row[cat_col] = mode_val.iloc[0] if not mode_val.empty else ''

                # 确保输出特征存在
                output_features = ['PA Status Pattern 1', 'PA Status Pattern 2']
                for out_col in output_features:
                    if out_col not in entry_row:
                        entry_row[out_col] = 'Normal'

                # 添加生成标记
                entry_row['Generated'] = True
                entry_row['EntryID'] = f"{product_row['Serial']}_{entry_uuid}"

                generated_entries.append(entry_row)

        result_df = pd.DataFrame(generated_entries)

        # 确保所有原始数据列都存在
        for col in original_data.columns:
            if col not in result_df.columns and col not in ['Generated', 'EntryID']:
                if col in original_data.select_dtypes(include=[np.number]).columns:
                    result_df[col] = 0
                else:
                    result_df[col] = ''

        return result_df
