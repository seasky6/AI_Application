import json
import os
import random
from typing import Counter, List, Dict

import joblib
import numpy as np
import pandas as pd
from ctgan import CTGAN
from sklearn.preprocessing import StandardScaler

from tools.app.services.model_training.preprocessor.data_preprocessor import TrainingDataProcessor
from tools.app.utils.json_processor_gan_choose_label import SDV_AVAILABLE


class CTGANTrainingDataProcessor(TrainingDataProcessor):
    """
    在 TrainingDataProcessor 的基础上，增加 CTGAN 过采样训练集
    （只对训练集做过采样，val/test 保持真实分布）
    """

    # 是否启用 GAN
    USE_GAN: bool = True
    # 每个类别目标样本数：'max' = 补到当前最多类的数量；或指定整数
    GAN_SAMPLES_TARGET: str | int = 'max'
    # CTGAN 训练轮数
    GAN_EPOCHS: int = 100
    # CTGAN batch 大小
    GAN_BATCH_SIZE: int = 256
    # 随机种子
    GAN_RANDOM_SEED: int = 42

    def __init__(self):
        super().__init__()

    # ---------------------------- GAN 生成 ---------------------------- #

    def gan_generator_per_class(
        self,
        X_df: pd.DataFrame,
        y_series: pd.Series,
        discrete_columns: List[str]
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        按类别拟合 CTGAN，并把每类补齐到目标数量。
        参数:
            X_df: 已做完数值处理+编码+标准化后的特征（训练集）
            y_series: 标签（0/1）
            discrete_columns: 当作离散变量的列名
        返回:
            X_aug, y_aug: 过采样后的训练集
        """
        if (not self.USE_GAN) or (not SDV_AVAILABLE) or (CTGAN is None):
            print("[GAN] 跳过 CTGAN：未启用或未安装 ctgan")
            return X_df, y_series

        label_col = "__label__"
        df_tr = X_df.copy()
        df_tr[label_col] = y_series.values

        classes = sorted(df_tr[label_col].unique().tolist())
        cnt = Counter(df_tr[label_col].tolist())

        if self.GAN_SAMPLES_TARGET == 'max':
            target_per_class = max(cnt.values())
        else:
            target_per_class = int(self.GAN_SAMPLES_TARGET)

        print(f"[GAN] 原始类分布: {cnt}, 目标每类: {target_per_class}")

        syn_list = []

        random.seed(self.GAN_RANDOM_SEED)
        np.random.seed(self.GAN_RANDOM_SEED)

        for c in classes:
            df_c = df_tr[df_tr[label_col] == c].reset_index(drop=True)
            n_cur = len(df_c)
            n_need = max(0, target_per_class - n_cur)
            if n_need == 0:
                print(f"[GAN] 类别={c} 已经满足目标数量 {n_cur}，不生成")
                continue

            print(f"[GAN] 训练 CTGAN 类别={c}, 现有={n_cur}, 需要生成={n_need}")

            # 这里只保留特征列
            train_df = df_c.drop(columns=[label_col])
            disc_cols_present = [col for col in discrete_columns if col in train_df.columns]

            # 如果样本太少，CTGAN 可能训练不稳定，这里简单跳过
            if len(train_df) < 10:
                print(f"[GAN] 类别={c} 样本太少 (<10)，跳过 CTGAN 生成")
                continue

            ctgan = CTGAN(
                epochs=self.GAN_EPOCHS,
                batch_size=self.GAN_BATCH_SIZE,
                generator_dim=(128, 128),
                discriminator_dim=(128, 128),
                verbose=True,
            )

            ctgan.fit(train_df, discrete_columns=disc_cols_present)
            syn = ctgan.sample(n_need)
            syn[label_col] = c
            syn_list.append(syn)

        if not syn_list:
            print("[GAN] 无需或无法生成：所有类别已满足目标数量或样本过少")
            return X_df, y_series

        syn_all = pd.concat(syn_list, ignore_index=True)
        y_syn = syn_all[label_col].astype(int)
        X_syn = syn_all.drop(columns=[label_col])

        X_aug = pd.concat([X_df, X_syn], axis=0).reset_index(drop=True)
        y_aug = pd.concat([y_series, y_syn], axis=0).reset_index(drop=True)

        print(
            f"[GAN] 合并后训练集大小: {len(X_aug)} "
            f"(原 {len(X_df)} + 合成 {len(X_aug) - len(X_df)})"
        )
        return X_aug, y_aug

    # --------------------- 重写划分 + 保存逻辑 --------------------- #

    def _split_and_save_datasets(
        self,
        X: pd.DataFrame,
        y_dict: Dict[str, pd.Series],
        output_dir: str,
        numeric_feats: List[str],
        categorical_feats: List[str],
        scaler: StandardScaler | None,
        filtered_data: pd.DataFrame,
    ):
        """
        子类版本：在划分 train/val/test 时，对训练集进行 CTGAN 过采样。
        """
        os.makedirs(output_dir, exist_ok=True)

        for output_feat, y in y_dict.items():
            print(f"[GAN] === 处理输出特征: {output_feat} ===")

            # 1. 先划分 train/val/test（用原始数据）
            X_train, X_temp, y_train, y_temp = train_test_split(
                X, y, test_size=0.4, random_state=42, stratify=y
            )
            X_val, X_test, y_val, y_test = train_test_split(
                X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
            )

            # 2. 确定离散特征列（一般是编码后的分类特征，对应 categorical_feats）
            discrete_cols = [col for col in categorical_feats if col in X_train.columns]

            # 3. 调用 GAN 对训练集过采样
            X_train_aug, y_train_aug = self.gan_generator_per_class(
                X_train, y_train, discrete_columns=discrete_cols
            )

            # 4. 保存
            feat_output_dir = os.path.join(output_dir, f"dataset_{output_feat.replace(' ', '_')}")
            os.makedirs(feat_output_dir, exist_ok=True)

            pd.concat([X_train_aug, y_train_aug.rename('target')], axis=1).to_csv(
                os.path.join(feat_output_dir, 'train.csv'), index=False)
            pd.concat([X_val, y_val.rename('target')], axis=1).to_csv(
                os.path.join(feat_output_dir, 'val.csv'), index=False)
            pd.concat([X_test, y_test.rename('target')], axis=1).to_csv(
                os.path.join(feat_output_dir, 'test.csv'), index=False)

            if scaler:
                joblib.dump(scaler, os.path.join(feat_output_dir, 'scaler.pkl'))
            joblib.dump(self.encoder, os.path.join(feat_output_dir, 'encoder.pkl'))

            metadata = {
                'input_features': list(self.selected_input_features),
                'output_feature': output_feat,
                'numeric_features': numeric_feats,
                'categorical_features': categorical_feats,
                'selected_samples_count': len(filtered_data),
                'use_gan': self.USE_GAN,
                'gan_samples_target': self.GAN_SAMPLES_TARGET,
                'gan_epochs': self.GAN_EPOCHS,
                'gan_batch_size': self.GAN_BATCH_SIZE,
            }
            with open(os.path.join(feat_output_dir, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)