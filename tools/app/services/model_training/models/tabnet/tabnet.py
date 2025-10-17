import os
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import LabelEncoder
from collections import Counter
import json
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

# 在导入PyTorch相关模块之前设置环境变量
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

# 延迟导入PyTorch相关模块
try:
    import torch

    # 检查PyTorch版本并设置兼容性选项
    if hasattr(torch, '__version__'):
        torch_version = torch.__version__
        print(f"PyTorch版本: {torch_version}")

        # 对于PyTorch 2.0+，禁用某些可能引起问题的功能
        if torch_version.startswith('2.'):
            torch._dynamo.config.suppress_errors = True
            # 禁用torch.compile相关功能
            os.environ['PYTORCH_DISABLE_COMPILE'] = '1'

    from pytorch_tabnet.tab_model import TabNetClassifier
except ImportError as e:
    print(f"导入PyTorch相关模块失败: {e}")
    # 如果导入失败，提供友好的错误信息
    raise ImportError("无法导入PyTorch或pytorch-tabnet。请确保已正确安装这些库。")


# ======================================================================================================================
# TabNet训练可视化
# ======================================================================================================================
class TabNetVisualizer:
    def __init__(self, params, feature_names=None, visualization_dir=None):
        self.params = params
        self.feature_names = feature_names
        self.visualization_dir = visualization_dir
        self.training_history = {
            'metrics': [],
            'feature_importance': []
        }

    def record_iteration(self, epoch, eval_result=None):
        """记录每次迭代的信息"""
        if eval_result:
            self.training_history['metrics'].append({
                'epoch': epoch,
                'eval_result': eval_result
            })

    def visualize_training_progress(self, history):
        """可视化训练过程"""
        # 检查history对象是否有效
        if not history or 'loss' not in history:
            print("没有训练记录可可视化")
            return

        # 获取实际的history字典
        history_dict = history.history

        # 检查是否有必要的数据
        if not history_dict or 'loss' not in history_dict:
            print("训练记录中没有损失数据")
            return None

        plt.figure(figsize=(12, 4))

        # 绘制训练和验证损失
        plt.subplot(1, 2, 1)
        if 'loss' in history:
            train_loss = history['loss']
            epochs = list(range(len(train_loss)))
            plt.plot(epochs, train_loss, 'b-', label='Train Loss')

        if 'val_0_logloss' in history:
            val_loss = history['val_0_logloss']
            epochs = list(range(len(val_loss)))
            plt.plot(epochs, val_loss, 'r-', label='Validation Loss')

        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training Progress - Loss')
        plt.legend()
        plt.grid(True)

        # 绘制训练和验证准确率
        plt.subplot(1, 2, 2)
        if 'val_0_accuracy' in history:
            val_accuracy = history['val_0_accuracy']
            epochs = list(range(len(val_accuracy)))
            plt.plot(epochs, val_accuracy, 'g-', label='Validation Accuracy')

        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.title('Training Progress - Accuracy')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        progress_path = os.path.join(self.visualization_dir, 'training_progress.png')
        plt.savefig(progress_path)
        plt.close()

        return progress_path

    def visualize_feature_importance(self, feature_importances, top_k=15):
        """可视化特征重要性"""
        if feature_importances is None or len(feature_importances) == 0:
            print("没有特征重要性数据可可视化")
            return

        # 创建特征重要性DataFrame
        importance_df = pd.DataFrame({
            'feature': self.feature_names if self.feature_names else [f'Feature_{i}' for i in
                                                                      range(len(feature_importances))],
            'importance': feature_importances
        }).sort_values('importance', ascending=False)

        # 可视化特征重要性
        plt.figure(figsize=(10, 8))
        top_features = importance_df.head(top_k)
        plt.barh(range(len(top_features)), top_features['importance'])
        plt.yticks(range(len(top_features)), top_features['feature'])
        plt.xlabel('Feature Importance')
        plt.title(f'Top {top_k} Feature Importance - TabNet')
        plt.tight_layout()

        feature_importance_path = os.path.join(self.visualization_dir, 'feature_importance.png')
        plt.savefig(feature_importance_path, dpi=300, bbox_inches='tight')
        plt.close()

        return feature_importance_path, importance_df

    def explain_architecture(self):
        """解释TabNet架构和参数影响"""
        explanation = "\n" + "=" * 60 + "\n"
        explanation += "TabNet 架构和参数影响分析\n"
        explanation += "=" * 60 + "\n"

        params = self.params

        explanation += f"\n📊 当前模型参数:\n"
        for key, value in params.items():
            explanation += f"  {key}: {value}\n"

        explanation += f"\n🏗️ 架构相关参数:\n"
        explanation += f"  1. 决策维度 (n_d={params.get('n_d', 8)}):\n"
        explanation += "     - 控制特征变换的输出维度\n"
        explanation += "     - 影响: 值越大表示更复杂的特征表示，但可能过拟合\n"

        explanation += f"\n  2. 注意力维度 (n_a={params.get('n_a', 8)}):\n"
        explanation += "     - 控制注意力机制的维度\n"
        explanation += "     - 影响: 值越大表示更精细的特征选择，但计算成本更高\n"

        explanation += f"\n  3. 决策步骤 (n_steps={params.get('n_steps', 3)}):\n"
        explanation += "     - 控制序列决策步骤的数量\n"
        explanation += "     - 影响: 更多步骤可以学习更复杂的决策过程\n"

        explanation += f"\n🎯 正则化参数:\n"
        explanation += f"  4. 稀疏性参数 (gamma={params.get('gamma', 1.3)}):\n"
        explanation += "     - 控制特征选择的稀疏性\n"
        explanation += "     - 影响: 值越大特征选择越稀疏，促进特征选择\n"

        explanation += f"\n  5. 稀疏正则化 (lambda_sparse={params.get('lambda_sparse', 1e-3)}):\n"
        explanation += "     - 在损失函数中加入稀疏正则化项\n"
        explanation += "     - 影响: 促进特征选择的稀疏性\n"

        explanation += f"\n🔄 优化参数:\n"
        explanation += f"  6. 学习率 (lr={params.get('optimizer_params', {}).get('lr', 2e-2)}):\n"
        explanation += "     - 控制参数更新的步长\n"
        explanation += "     - 影响: 值越小训练越稳定，但需要更多epoch\n"

        explanation += f"\n  7. 权重衰减 (weight_decay={params.get('optimizer_params', {}).get('weight_decay', 1e-4)}):\n"
        explanation += "     - L2正则化项，防止过拟合\n"
        explanation += "     - 影响: 值越大正则化效果越强\n"

        explanation += f"\n💡 TabNet 核心算法原理:\n"
        explanation += "  1. 基于顺序注意力机制\n"
        explanation += "  2. 在每个决策步骤中进行特征选择\n"
        explanation += "  3. 使用稀疏正则化促进可解释性\n"
        explanation += "  4. 结合了深度学习和可解释性\n"
        explanation += "  5. 支持实例-wise的特征重要性\n\n"

        explanation += "决策步骤流程:\n"
        explanation += "  1. 特征变换: 使用共享的FC层处理输入特征\n"
        explanation += "  2. 注意力选择: 使用sparsemax进行特征选择\n"
        explanation += "  3. 特征处理: 处理选中的特征子集\n"
        explanation += "  4. 决策聚合: 聚合所有步骤的决策\n"
        explanation += "  5. 输出预测: 生成最终预测结果\n"

        return explanation

    @staticmethod
    def analyze_decision_process(model):
        """分析TabNet的决策过程"""
        analysis = "\n" + "=" * 60 + "\n"
        analysis += "TabNet 决策过程分析\n"
        analysis += "=" * 60 + "\n\n"

        if hasattr(model, 'feature_importances_'):
            analysis += f"全局特征重要性已计算，共 {len(model.feature_importances_)} 个特征\n"
        else:
            analysis += "无法获取特征重要性数据\n"

        analysis += f"\n模型架构信息:\n"
        analysis += f"- 决策维度 (n_d): {getattr(model, 'n_d', 'N/A')}\n"
        analysis += f"- 注意力维度 (n_a): {getattr(model, 'n_a', 'N/A')}\n"
        analysis += f"- 决策步骤 (n_steps): {getattr(model, 'n_steps', 'N/A')}\n"
        analysis += f"- 输入维度: {getattr(model, 'input_dim', 'N/A')}\n"
        analysis += f"- 输出维度: {getattr(model, 'output_dim', 'N/A')}\n"

        analysis += f"\nTabNet 核心特性:\n"
        analysis += "1. 可解释性: 通过注意力mask提供特征重要性\n"
        analysis += "2. 特征选择: 自动选择相关特征进行预测\n"
        analysis += "3. 端到端训练: 无需手工特征工程\n"
        analysis += "4. 处理表格数据: 专门为表格数据设计\n"

        return analysis


# ======================================================================================================================
# 自定义回调函数用于记录训练过程
# ======================================================================================================================
class TabNetTrainingCallback:
    def __init__(self, visualizer, log_callback=None):
        self.visualizer = visualizer
        self.log_callback = log_callback
        self.best_score = float('inf')
        self.history = {
            'loss': [],
            'val_0_logloss': [],
            'val_0_accuracy': []
        }

    def __call__(self, epoch, logs):
        """TabNet回调函数"""
        # 记录训练历史
        if 'loss' in logs:
            self.history['loss'].append(logs['loss'])
        if 'val_0_logloss' in logs:
            self.history['val_0_logloss'].append(logs['val_0_logloss'])
        if 'val_0_accuracy' in logs:
            self.history['val_0_accuracy'].append(logs['val_0_accuracy'])

        # 记录评估结果
        eval_result = {}
        for key, value in logs.items():
            if key.startswith('val_'):
                dataset_name = 'val'
                metric_name = key.replace('val_0_', '')
                if dataset_name not in eval_result:
                    eval_result[dataset_name] = {}
                eval_result[dataset_name][metric_name] = value

        self.visualizer.record_iteration(epoch, eval_result)

        # 记录最佳分数
        if 'val_0_logloss' in logs and logs['val_0_logloss'] < self.best_score:
            self.best_score = logs['val_0_logloss']

        # 日志输出
        if self.log_callback and epoch % 10 == 0:
            log_message = f"\nEpoch {epoch}:"
            for dataset_name, metrics in eval_result.items():
                log_message += f"\n  {dataset_name}: "
                for metric_name, value in metrics.items():
                    log_message += f"{metric_name}={value:.4f} "
            self.log_callback(log_message)


# ======================================================================================================================
# TabNet训练模块
# ======================================================================================================================
class TabNetTrainer:
    def __init__(self, dataset_path, model_save_path, progress_callback=None, log_callback=None):
        self.dataset_path = dataset_path
        self.model_save_path = model_save_path
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 创建必要的目录
        self.visualization_dir = os.path.join(model_save_path, 'tabnet_visualizations')
        os.makedirs(self.visualization_dir, exist_ok=True)
        os.makedirs(model_save_path, exist_ok=True)

        # 初始化数据
        self.X_train = None
        self.y_train = None
        self.X_val = None
        self.y_val = None
        self.X_test = None
        self.y_test = None
        self.model = None
        self.visualizer = None
        self.callback = None
        self.feature_names = None

    def log(self, message):
        """日志记录"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def update_progress(self, value):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(value)

    # ================================================================================
    # 加载数据
    def load_dataset(self, filename):
        """加载数据集"""
        try:
            file_path = os.path.join(self.dataset_path, filename)
            self.log(f"正在加载数据: {file_path}")

            df = pd.read_csv(file_path)
            X = df.iloc[:, :-1]  # 所有特征
            y = df.iloc[:, -1]  # 目标列（假设已编码）
            le = LabelEncoder()
            y = le.fit_transform(y)  # 确保标签为0,1

            # 检查空值('', None)或无限值(inf, -inf)
            X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
            return X, y
        except Exception as e:
            self.log(f"加载数据失败: {str(e)}")
            raise

    # ================================================================================
    # 计算输出特征类别权重
    @staticmethod
    def calculate_class_weights(y):
        """动态计算输出特征类别权重 - 少数类别获得更高权重"""
        class_counts = Counter(y)
        total_samples = len(y)
        n_classes = len(class_counts)

        # 计算权重：权重与类别频率成反比
        weights = {
            cls: total_samples / (n_classes * count)
            for cls, count in class_counts.items()
        }
        return weights

    # ================================================================================
    # 简化的优化器配置（避免兼容性问题）
    @staticmethod
    def _get_safe_optimizer_config():
        """获取安全的优化器配置，避免PyTorch版本兼容性问题"""
        # 使用更稳定的优化器和参数
        config = {
            'n_d': 16,  # 降低复杂度以加快训练
            'n_a': 16,
            'n_steps': 3,
            'gamma': 1.5,
            'lambda_sparse': 1e-3,
            'optimizer_fn': torch.optim.Adam,  # 使用Adam而不是AdamW
            'optimizer_params': dict(lr=2e-2, weight_decay=1e-5),  # 简化参数
            'scheduler_fn': None,  # 不使用复杂的调度器
            'scheduler_params': None,
            'mask_type': 'entmax',  # 使用更稳定的mask类型
            'clip_value': 1.0,
            'verbose': 1,
            'seed': 42
        }
        return config

    # ================================================================================
    # 模型训练
    # ================================================================================
    def train(self, custom_params=None):
        """训练TabNet模型"""
        try:
            self.update_progress(10)
            self.log("开始加载训练数据...")

            # 1. 加载数据
            self.X_train, self.y_train = self.load_dataset('train.csv')
            self.X_val, self.y_val = self.load_dataset('val.csv')
            self.X_test, self.y_test = self.load_dataset('test.csv')

            self.update_progress(30)
            self.log("数据加载完成")

            # 2. 计算输出特征类别权重
            class_weights = self.calculate_class_weights(self.y_train)
            sample_weights = np.array([class_weights[y] for y in self.y_train])

            self.log(f"类别分布: {Counter(self.y_train)}")
            self.log(f"计算权重: {class_weights}")

            # 3. 保存特征名
            self.feature_names = self.X_train.columns.tolist()

            # 转换为numpy数组（TabNet要求）
            self.X_train, self.X_val, self.X_test = self.X_train.values, self.X_val.values, self.X_test.values

            self.update_progress(40)
            self.log("开始训练TabNet模型...")

            # 4. 使用安全的模型参数配置
            params = self._get_safe_optimizer_config()

            # 如果提供了自定义参数，则覆盖默认值
            if custom_params:
                for key, value in custom_params.items():
                    if key in params:
                        params[key] = value
                        self.log(f"使用自定义参数 {key}: {value}")

            # 5. 创建可视化器
            self.visualizer = TabNetVisualizer(
                params,
                feature_names=self.feature_names,
                visualization_dir=self.visualization_dir
            )

            # 6. 创建回调函数
            self.callback = TabNetTrainingCallback(self.visualizer, log_callback=self.log)

            self.log("模型参数:")
            for key, value in params.items():
                if key not in ['optimizer_fn', 'scheduler_fn']:  # 避免打印函数对象
                    self.log(f"  {key}: {value}")

            # 7. 创建并训练模型
            self.log("初始化TabNet模型...")

            # 简化模型初始化，避免复杂配置
            self.model = TabNetClassifier(
                n_d=params['n_d'],
                n_a=params['n_a'],
                n_steps=params['n_steps'],
                gamma=params['gamma'],
                lambda_sparse=params['lambda_sparse'],
                optimizer_fn=params['optimizer_fn'],
                optimizer_params=params['optimizer_params'],
                mask_type=params['mask_type'],
                clip_value=params['clip_value'],
                verbose=params['verbose'],
                seed=params['seed']
            )

            self.log("开始模型训练...")
            self.model.fit(
                X_train=self.X_train,
                y_train=self.y_train,
                eval_set=[(self.X_val, self.y_val)],
                eval_name=['val'],
                eval_metric=['logloss', 'accuracy'],
                max_epochs=50,  # 减少epoch数量
                patience=15,  # 减少早停耐心
                batch_size=512,  # 增加batch size
                virtual_batch_size=128,
                weights=sample_weights
            )

            self.update_progress(70)
            self.log("模型训练完成")

            # 8. 评估模型
            self.evaluate_model()

            self.update_progress(80)

            # 9. 特征重要性分析
            self.analyze_feature_importance()

            self.update_progress(85)

            # 10. 生成训练可视化
            self.generate_visualizations()

            self.update_progress(95)

            # 11. 保存模型
            self.save_model()

            self.update_progress(100)
            self.log("TabNet训练完成！")

            return True, "TabNet模型训练完成"

        except Exception as e:
            self.log(f"训练过程中出错: {str(e)}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            return False, f"训练失败: {str(e)}"

    # ================================================================================
    # 评估模型
    def evaluate_model(self):
        """评估模型性能"""
        self.log("正在评估模型性能...")

        y_pred = self.model.predict(self.X_test)

        accuracy = accuracy_score(self.y_test, y_pred)
        f1_macro = f1_score(self.y_test, y_pred, average='macro')
        f1_micro = f1_score(self.y_test, y_pred, average='micro')
        f1_weighted = f1_score(self.y_test, y_pred, average='weighted')

        self.log(f"准确率: {accuracy:.4f}")
        self.log(f"F1 Score (Macro): {f1_macro:.4f}")
        self.log(f"F1 Score (Micro): {f1_micro:.4f}")
        self.log(f"F1 Score (Weighted): {f1_weighted:.4f}")

        # 详细的分类报告
        report = classification_report(self.y_test, y_pred, digits=4)
        self.log("分类报告:")
        for line in report.split('\n'):
            self.log(f"  {line}")

    # ================================================================================
    # 特征重要性分析
    def analyze_feature_importance(self):
        """分析特征重要性"""
        self.log("正在分析特征重要性...")

        if hasattr(self.model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)

            self.log("Top20 特征重要性排名:")
            for i, (_, row) in enumerate(importance_df.head(20).iterrows()):
                self.log(f"  {i + 1:2d}. {row['feature']}: {row['importance']:.6f}")

            return importance_df
        else:
            self.log("无法获取特征重要性数据")
            return None

    # ================================================================================
    # 保存文本报告
    def save_text_reports(self, importance_df):
        """保存评估结果和特征重要性到文本文件"""
        try:
            # 评估报告文件路径
            eval_report_path = os.path.join(self.visualization_dir, 'evaluation_report.txt')

            # 1. 准备模型评估报告内容
            with open(eval_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("TabNet 模型评估报告\n")
                f.write("=" * 60 + "\n\n")

                # 模型基本信息
                f.write("模型基本信息:\n")
                f.write(f"训练数据路径: {self.dataset_path}\n")
                f.write(f"模型保存路径: {self.model_save_path}\n")
                f.write(f"训练样本数: {len(self.X_train)}\n")
                f.write(f"验证样本数: {len(self.X_val)}\n")
                f.write(f"测试样本数: {len(self.X_test)}\n")
                f.write(f"特征数量: {len(self.feature_names)}\n")
                f.write(f"类别数量: {len(np.unique(self.y_train))}\n")

                # 模型评估结果
                y_pred = self.model.predict(self.X_test)

                accuracy = accuracy_score(self.y_test, y_pred)
                f1_macro = f1_score(self.y_test, y_pred, average='macro')
                f1_micro = f1_score(self.y_test, y_pred, average='micro')
                f1_weighted = f1_score(self.y_test, y_pred, average='weighted')

                f.write("\n" + "=" * 40 + "\n")
                f.write("模型性能评估\n")
                f.write("=" * 40 + "\n")
                f.write(f"准确率 (Accuracy): {accuracy:.4f}\n")
                f.write(f"F1 Score (Macro): {f1_macro:.4f}\n")
                f.write(f"F1 Score (Micro): {f1_micro:.4f}\n")
                f.write(f"F1 Score (Weighted): {f1_weighted:.4f}\n")

                # 详细的分类报告
                f.write("\n详细分类报告:\n")
                report = classification_report(self.y_test, y_pred, digits=4)
                f.write(report)

            self.log(f"评估报告已保存到: {eval_report_path}")

            # 特征重要性报告文件路径
            feature_report_path = os.path.join(self.visualization_dir, 'feature_importance_report.txt')

            # 2. 准备特征重要性分析报告
            with open(feature_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("特征重要性排名报告\n")
                f.write("=" * 60 + "\n\n")

                if importance_df is not None:
                    f.write("Top 50 特征重要性排名:\n")
                    f.write("-" * 50 + "\n")
                    f.write(f"{'排名':<4} {'特征名称':<30} {'重要性':<15}\n")
                    f.write("-" * 50 + "\n")

                    for i, (_, row) in enumerate(importance_df.head(50).iterrows()):
                        f.write(f"{i + 1:<4} {row['feature']:<30} {row['importance']:.6f}\n")

                    # 特征统计信息
                    f.write("\n特征重要性统计:\n")
                    f.write(f"总特征数量: {len(importance_df)}\n")
                    f.write(f"平均重要性: {importance_df['importance'].mean():.6f}\n")
                    f.write(f"重要性标准差: {importance_df['importance'].std():.6f}\n")
                    f.write(f"最大重要性: {importance_df['importance'].max():.6f}\n")
                    f.write(f"最小重要性: {importance_df['importance'].min():.6f}\n")

                    # 重要性分布
                    f.write("\n重要性分布:\n")
                    bins = [0, 0.001, 0.005, 0.01, 0.05, 0.1, float('inf')]
                    labels = ['0-0.001', '0.001-0.005', '0.005-0.01', '0.01-0.05', '0.05-0.1', '0.1+']
                    importance_df['bin'] = pd.cut(importance_df['importance'], bins=bins, labels=labels, right=False)
                    distribution = importance_df['bin'].value_counts().sort_index()

                    for bin_label, count in distribution.items():
                        f.write(f"  重要性 {bin_label}: {count} 个特征\n")
                else:
                    f.write("无法获取特征重要性数据\n")

            self.log(f"特征重要性报告已保存到: {feature_report_path}")

            # 决策过程报告文件路径
            decision_process_path = os.path.join(self.visualization_dir, 'decision_process_analysis.txt')

            # 3. 准备决策过程分析报告
            with open(decision_process_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("TabNet 决策过程分析\n")
                f.write("=" * 60 + "\n\n")

                # 架构分析
                decision_analysis = self.visualizer.analyze_decision_process(self.model)
                f.write(decision_analysis)

            self.log(f"决策过程分析报告已保存到: {decision_process_path}")

            # 训练过程总结报告文件路径
            training_summary_path = os.path.join(self.visualization_dir, 'training_process_summary.txt')

            # 4. 准备训练过程总结报告
            with open(training_summary_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("TabNet 训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                # 参数影响解释
                architecture_explanation = self.visualizer.explain_architecture()
                f.write(architecture_explanation)
                f.write("\n\n")

                # 训练过程总结
                f.write("=" * 60 + "\n")
                f.write("训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                if hasattr(self.model, 'history'):
                    history = self.model.history
                    f.write(f"总训练轮数: {len(history.get('loss', []))}\n")
                    if 'val_0_logloss' in history:
                        best_val_loss = min(history['val_0_logloss'])
                        f.write(f"最佳验证损失: {best_val_loss:.4f}\n")
                    if 'val_0_accuracy' in history:
                        best_val_accuracy = max(history['val_0_accuracy'])
                        f.write(f"最佳验证准确率: {best_val_accuracy:.4f}\n")

                f.write("\n每轮迭代过程:\n")
                f.write("1. 前向传播: 通过特征变换层和注意力机制\n")
                f.write("2. 特征选择: 使用sparsemax进行稀疏特征选择\n")
                f.write("3. 决策步骤: 在多个步骤中逐步处理特征\n")
                f.write("4. 损失计算: 计算预测损失和稀疏正则化损失\n")
                f.write("5. 反向传播: 更新模型参数\n")
                f.write("6. 学习率调整: 根据调度器调整学习率\n\n")

                # TabNet 核心算法原理
                f.write("=" * 60 + "\n")
                f.write("TabNet 核心算法原理\n")
                f.write("=" * 60 + "\n\n")

                f.write("TabNet 核心特性:\n")
                f.write("1. 顺序注意力机制: 在多个决策步骤中选择特征\n")
                f.write("2. 特征变换: 使用全连接层学习特征表示\n")
                f.write("3. 稀疏正则化: 促进特征选择的稀疏性和可解释性\n")
                f.write("4. 实例-wise特征重要性: 为每个样本提供特征重要性\n")
                f.write("5. 端到端训练: 无需特征工程的深度学习\n\n")

                f.write("损失函数组成:\n")
                f.write("  Total Loss = Prediction Loss + λ_sparse * Sparsity Loss\n")
                f.write("其中:\n")
                f.write("  Prediction Loss: 预测误差（如交叉熵）\n")
                f.write("  Sparsity Loss: 特征选择mask的稀疏性惩罚\n")
                f.write("  λ_sparse: 稀疏正则化系数\n")

            self.log(f"训练过程总结报告已保存到: {training_summary_path}")

            return True

        except Exception as e:
            self.log(f"保存文本报告时出错: {str(e)}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            return False

    # ================================================================================
    # 生成训练可视化
    def generate_visualizations(self):
        """生成训练可视化"""
        self.log("正在生成训练可视化...")

        # 训练进度可视化
        self.log("开始生成训练进度图...")
        if hasattr(self.model, 'history'):
            try:
                # 安全地访问history对象
                progress_path = self.visualizer.visualize_training_progress(self.model.history)
                if progress_path:
                    self.log(f"训练进度图已保存到: {progress_path}")
                else:
                    self.log("无法生成训练进度图")
            except Exception as e:
                self.log(f"生成训练进度图时出错: {str(e)}")
        else:
            self.log("警告: 无法获取训练历史数据")

        # 特征重要性分析
        self.log("开始生成特征重要性图...")
        if hasattr(self.model, 'feature_importances_'):
            try:
                feature_importance_path, importance_df = self.visualizer.visualize_feature_importance(
                    self.model.feature_importances_
                )
                self.log(f"特征重要性图已保存到: {feature_importance_path}")
            except Exception as e:
                self.log(f"生成特征重要性图时出错: {str(e)}")
                importance_df = None
        else:
            importance_df = None
            self.log("警告: 无法获取特征重要性数据")

        # 保存文本报告
        self.log("开始保存文本报告...")
        try:
            self.save_text_reports(importance_df)
        except Exception as e:
            self.log(f"保存文本报告时出错: {str(e)}")

        # 参数影响解释
        try:
            architecture_explanation = self.visualizer.explain_architecture()
            for line in architecture_explanation.split('\n'):
                self.log(f"  {line}")
        except Exception as e:
            self.log(f"解释参数影响时出错: {str(e)}")

        # 决策过程分析
        try:
            decision_analysis = self.visualizer.analyze_decision_process(self.model)
            lines = decision_analysis.split('\n')
            for line in lines[:15]:  # 只显示前15行
                self.log(f"  {line}")
            if len(lines) > 15:
                self.log("  ... (详细信息已保存)")
        except Exception as e:
            self.log(f"分析决策过程时出错: {str(e)}")

        # 额外显示TabNet算法原理
        self.log(f"\n{'=' * 60}")
        self.log("TabNet 训练过程总结")
        self.log(f"{'=' * 60}")

        if hasattr(self.model, 'history') and hasattr(self.model.history, 'history'):
            history_dict = self.model.history.history
            self.log(f"总训练轮数: {len(history_dict.get('loss', []))}")
            if 'val_0_logloss' in history_dict:
                best_val_loss = min(history_dict['val_0_logloss'])
                self.log(f"最佳验证损失: {best_val_loss:.4f}")
            if 'val_0_accuracy' in history_dict:
                best_val_accuracy = max(history_dict['val_0_accuracy'])
                self.log(f"最佳验证准确率: {best_val_accuracy:.4f}")

        self.log(f"\nTabNet 核心优势:")
        self.log("1. 可解释性: 提供特征重要性解释")
        self.log("2. 特征选择: 自动选择相关特征")
        self.log("3. 处理表格数据: 专门为表格数据设计")
        self.log("4. 深度学习: 利用深度网络学习复杂模式")
        self.log("5. 端到端训练: 无需手工特征工程")

    # ================================================================================
    # 辅助函数：转换NumPy数据类型为Python原生类型
    def _convert_numpy_types(self, obj):
        """递归地将NumPy数据类型转换为Python原生类型"""
        if isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(v) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(self._convert_numpy_types(v) for v in obj)
        elif isinstance(obj, (np.int32, np.int64, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float32, np.float64, np.float16)):
            return float(obj)
        elif isinstance(obj, (np.bool_)):
            return bool(obj)
        elif isinstance(obj, (np.ndarray)):
            return obj.tolist()
        else:
            return obj

    # ================================================================================
    # 保存模型和元数据
    def save_model(self):
        """保存模型和元数据"""
        self.log("正在保存模型和元数据...")

        # 保存模型
        model_path = os.path.join(self.model_save_path, 'tabnet_model.zip')
        self.model.save_model(model_path)

        # 评估最终模型
        y_pred = self.model.predict(self.X_test)

        # 准备元数据
        metadata = {
            'feature_importance': {},
            'eval_metrics': {
                'accuracy': accuracy_score(self.y_test, y_pred),
                'f1_scores': {
                    'macro': f1_score(self.y_test, y_pred, average='macro'),
                    'micro': f1_score(self.y_test, y_pred, average='micro'),
                    'weighted': f1_score(self.y_test, y_pred, average='weighted')
                }
            },
            'model_params': {}
        }

        # 添加特征重要性
        if hasattr(self.model, 'feature_importances_'):
            metadata['feature_importance'] = dict(zip(
                self.feature_names,
                self.model.feature_importances_
            ))

        # 添加模型参数（转换为字符串）
        if hasattr(self.model, 'get_params'):
            model_params = self.model.get_params()
            metadata['model_params'] = {k: str(v) for k, v in model_params.items()}

        # 转换NumPy数据类型为Python原生类型
        metadata = self._convert_numpy_types(metadata)

        # 保存元数据
        metadata_path = os.path.join(self.model_save_path, 'tabnet_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.log(f"模型已保存到: {model_path}")
        self.log(f"元数据已保存到: {metadata_path}")


# ================================================================================
# 训练函数 - 供GUI调用
# ================================================================================
def train(dataset_path, model_save_path, progress_callback=None, log_callback=None, custom_params=None):
    """
    训练TabNet模型的主函数

    Args:
        dataset_path: 训练数据集目录路径
        model_save_path: 模型保存路径
        progress_callback: 进度回调函数
        log_callback: 日志回调函数
        custom_params: 自定义参数字典

    Returns:
        tuple: (success, message)
    """
    try:
        trainer = TabNetTrainer(
            dataset_path=dataset_path,
            model_save_path=model_save_path,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

        return trainer.train(custom_params)

    except Exception as e:
        error_msg = f"TabNet训练失败: {str(e)}"
        if log_callback:
            log_callback(error_msg)
        return False, error_msg


# ================================================================================
# 直接运行时的测试代码
# ================================================================================
if __name__ == '__main__':
    # 测试代码
    dataset_path = input("请输入数据集路径: ").strip()
    model_save_path = input("请输入模型保存路径: ").strip()

    if not dataset_path or not model_save_path:
        print("路径不能为空")
        exit(1)

    success, message = train(dataset_path, model_save_path)

    if success:
        print(f"训练成功: {message}")
    else:
        print(f"训练失败: {message}")
