import os
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import LabelEncoder
import json
from collections import Counter
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


# ======================================================================================================================
# LightGBM训练可视化
# ======================================================================================================================
class LightGBMVisualizer:
    def __init__(self, params, feature_names=None, visualization_dir=None):
        self.params = params
        self.feature_names = feature_names
        self.visualization_dir = visualization_dir
        self.training_history = {
            'metrics': [],
            'feature_importance': []
        }

    def record_iteration(self, iteration, eval_result=None):
        """记录每次迭代的信息"""
        if eval_result:
            self.training_history['metrics'].append({
                'iteration': iteration,
                'eval_result': eval_result
            })

    def visualize_training_progress(self, evals_result):
        """可视化训练过程"""
        if not evals_result:
            print("没有训练记录可可视化")
            return

        plt.figure(figsize=(12, 4))

        # 绘制训练和验证损失
        plt.subplot(1, 2, 1)
        if 'train' in evals_result and 'multi_logloss' in evals_result['train']:
            train_loss = evals_result['train']['multi_logloss']
            iterations = list(range(len(train_loss)))
            plt.plot(iterations, train_loss, 'b-', label='Train Loss')

        if 'val' in evals_result and 'multi_logloss' in evals_result['val']:
            val_loss = evals_result['val']['multi_logloss']
            iterations = list(range(len(val_loss)))
            plt.plot(iterations, val_loss, 'r-', label='Validation Loss')

        plt.xlabel('Iteration')
        plt.ylabel('Log Loss')
        plt.title('Training Progress - Loss')
        plt.legend()
        plt.grid(True)

        # 绘制训练和验证错误率
        plt.subplot(1, 2, 2)
        if 'train' in evals_result and 'multi_error' in evals_result['train']:
            train_error = evals_result['train']['multi_error']
            iterations = list(range(len(train_error)))
            plt.plot(iterations, train_error, 'b-', label='Train Error')

        if 'val' in evals_result and 'multi_error' in evals_result['val']:
            val_error = evals_result['val']['multi_error']
            iterations = list(range(len(val_error)))
            plt.plot(iterations, val_error, 'r-', label='Validation Error')

        plt.xlabel('Iteration')
        plt.ylabel('Error Rate')
        plt.title('Training Progress - Error Rate')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        progress_path = os.path.join(self.visualization_dir, 'training_progress.png')
        plt.savefig(progress_path)
        plt.close()

        return progress_path

    def visualize_tree_detailed(self, model, tree_index=0):
        """详细可视化特定树的结构"""
        try:
            # 获取树的文本表示
            tree_dict = model.dump_model()
            if 'tree_info' in tree_dict and tree_index < len(tree_dict['tree_info']):
                tree_info = tree_dict['tree_info'][tree_index]
                tree_text = f"\n{'=' * 60}\n树 {tree_index} 的详细结构:\n{'=' * 60}\n"
                tree_text += self._format_tree_structure(tree_info)

                # 解析树结构信息
                analysis = self._analyze_tree_structure(tree_info)
                return tree_text + "\n" + analysis
            else:
                return f"树索引 {tree_index} 超出范围"
        except Exception as e:
            return f"可视化树结构时出错: {e}"

    def _format_tree_structure(self, tree_info):
        """格式化树结构为可读文本"""

        def format_node(node, depth=0):
            indent = "  " * depth
            if 'leaf_value' in node:
                return f"{indent}叶子节点: 值 = {node['leaf_value']:.4f}\n"
            else:
                result = f"{indent}分裂节点: {self.feature_names[node['split_feature']] if self.feature_names else f'特征{node['split_feature']}'} < {node['threshold']:.4f}\n"
                if 'left_child' in node:
                    result += format_node(node['left_child'], depth + 1)
                if 'right_child' in node:
                    result += format_node(node['right_child'], depth + 1)
                return result

        return format_node(tree_info['tree_structure'])

    def _analyze_tree_structure(self, tree_info):
        """分析树结构并解释LightGBM的工作原理"""
        analysis = f"\n树结构分析:\n" + "-" * 50 + "\n"

        def analyze_node(node, node_count):
            if 'leaf_value' in node:
                analysis = f"叶子节点 {node_count}: 权重 = {node['leaf_value']:.4f}\n"
                analysis += f"  → LightGBM使用直方图算法计算叶子权重\n"
                analysis += f"  → 基于梯度提升的负梯度方向更新\n\n"
                return analysis, node_count + 1, 1, 0
            else:
                left_analysis, node_count, left_leaves, left_splits = analyze_node(node['left_child'], node_count)
                right_analysis, node_count, right_leaves, right_splits = analyze_node(node['right_child'], node_count)

                analysis = f"分裂节点 {node_count}: "
                if self.feature_names:
                    analysis += f"{self.feature_names[node['split_feature']]}"
                else:
                    analysis += f"特征{node['split_feature']}"
                analysis += f" < {node['threshold']:.4f}\n"
                analysis += f"  → 分裂增益 = {node.get('split_gain', 0):.4f}\n"
                analysis += f"  → 默认方向 = {node.get('default_left', 'left')}\n"
                analysis += f"  → 使用直方图找到的最佳分裂点\n\n"

                analysis += left_analysis + right_analysis
                return analysis, node_count + 1, left_leaves + right_leaves, left_splits + right_splits + 1

        full_analysis, total_nodes, total_leaves, total_splits = analyze_node(tree_info['tree_structure'], 0)
        analysis += full_analysis
        analysis += f"\n树统计: 总节点数={total_nodes}, 叶子节点数={total_leaves}, 分裂节点数={total_splits}\n"

        return analysis

    def explain_parameters_effect(self):
        """解释参数对训练的影响"""
        explanation = "\n" + "=" * 60 + "\n"
        explanation += "LightGBM 参数对训练过程的影响分析\n"
        explanation += "=" * 60 + "\n"

        params = self.params

        explanation += f"\n📊 当前模型参数:\n"
        for key, value in params.items():
            explanation += f"  {key}: {value}\n"

        explanation += f"\n🌳 树结构相关参数:\n"
        explanation += f"  1. 叶子数量 (num_leaves={params.get('num_leaves', 31)}):\n"
        explanation += "     - 控制树的复杂度，值越大树越复杂\n"
        explanation += "     - 影响: 更多叶子可以学习更复杂的模式，但容易过拟合\n"

        explanation += f"\n  2. 最大深度 (max_depth={params.get('max_depth', -1)}):\n"
        explanation += "     - 控制树的最大深度，-1表示无限制\n"
        explanation += "     - 影响: 与num_leaves配合控制模型复杂度\n"

        explanation += f"\n  3. 学习率 (learning_rate={params.get('learning_rate', 0.1)}):\n"
        explanation += "     - 控制每棵树的贡献权重\n"
        explanation += "     - 影响: 值越小需要更多树，但可能获得更好的泛化能力\n"

        explanation += f"\n🎯 正则化参数:\n"
        explanation += f"  4. L1正则化 (lambda_l1={params.get('lambda_l1', 0)}):\n"
        explanation += "     - 在损失函数中加入L1正则化项\n"
        explanation += "     - 影响: 促进特征稀疏性，防止过拟合\n"

        explanation += f"\n  5. L2正则化 (lambda_l2={params.get('lambda_l2', 0)}):\n"
        explanation += "     - 在损失函数中加入L2正则化项\n"
        explanation += "     - 影响: 惩罚大的权重值，防止过拟合\n"

        explanation += f"\n  6. 最小增益 (min_gain_to_split={params.get('min_gain_to_split', 0)}):\n"
        explanation += "     - 控制分裂的最小增益阈值\n"
        explanation += "     - 影响: Gain > min_gain_to_split 才进行分裂\n"

        explanation += f"\n  7. 叶子最小数据量 (min_data_in_leaf={params.get('min_data_in_leaf', 20)}):\n"
        explanation += "     - 控制叶子节点所需的最小样本数\n"
        explanation += "     - 影响: 防止创建样本数过少的叶子节点\n"

        explanation += f"\n🔄 采样参数:\n"
        explanation += f"  8. 样本采样 (bagging_fraction={params.get('bagging_fraction', 1)}):\n"
        explanation += "     - 每棵树随机采样的样本比例\n"
        explanation += "     - 影响: 增强模型的随机性和泛化能力\n"

        explanation += f"\n  9. 特征采样 (feature_fraction={params.get('feature_fraction', 1)}):\n"
        explanation += "     - 每棵树随机采样的特征比例\n"
        explanation += "     - 影响: 增强特征选择的多样性\n"

        explanation += f"\n💡 LightGBM 核心算法原理:\n"
        explanation += "  1. 基于梯度提升框架\n"
        explanation += "  2. 使用直方图算法加速训练\n"
        explanation += "  3. 采用叶子生长策略 (leaf-wise)\n"
        explanation += "  4. 支持类别特征直接处理\n"
        explanation += "  5. 使用GOSS(Gradient-based One-Side Sampling)进行数据采样\n"
        explanation += "  6. 使用EFB(Exclusive Feature Bundling)进行特征捆绑\n\n"

        explanation += "节点分裂增益公式 (基于直方图):\n"
        explanation += "  Gain = 1/2 [∑(g_left)²/(∑h_left+λ) + ∑(g_right)²/(∑h_right+λ) - ∑(g_parent)²/(∑h_parent+λ)]\n"
        explanation += "其中: g = 一阶梯度, h = 二阶梯度, λ = L2正则化系数\n"

        return explanation


# ======================================================================================================================
# 自定义回调函数用于记录训练过程
# ======================================================================================================================
class LightGBMTrainingCallback:
    def __init__(self, visualizer, log_callback=None):
        self.visualizer = visualizer
        self.log_callback = log_callback
        self.best_score = {}
        self.evals_result = {}

    def __call__(self, env):
        """LightGBM回调函数"""
        iteration = env.iteration
        evaluation_result_list = env.evaluation_result_list

        # 记录评估结果
        eval_result = {}
        for item in evaluation_result_list:
            data_name, metric_name, value, _ = item
            if data_name not in eval_result:
                eval_result[data_name] = {}
            eval_result[data_name][metric_name] = value

        self.visualizer.record_iteration(iteration, eval_result)

        # 记录到evals_result用于绘图
        for data_name, metrics in eval_result.items():
            if data_name not in self.evals_result:
                self.evals_result[data_name] = {}
            for metric_name, value in metrics.items():
                if metric_name not in self.evals_result[data_name]:
                    self.evals_result[data_name][metric_name] = []
                self.evals_result[data_name][metric_name].append(value)

        # 记录最佳分数
        for data_name, metrics in eval_result.items():
            if 'multi_logloss' in metrics:
                current_score = metrics['multi_logloss']
                if data_name not in self.best_score or current_score < self.best_score[data_name]:
                    self.best_score[data_name] = current_score

        # 日志输出
        if self.log_callback and iteration % 20 == 0:
            log_message = f"\n迭代 {iteration}:"
            for data_name, metrics in eval_result.items():
                log_message += f"\n  {data_name}: "
                for metric_name, value in metrics.items():
                    log_message += f"{metric_name}={value:.4f} "
            self.log_callback(log_message)


# ======================================================================================================================
# LightGBM训练模块
# ======================================================================================================================
class LightGBMTrainer:
    def __init__(self, dataset_path, model_save_path, progress_callback=None, log_callback=None):
        self.dataset_path = dataset_path
        self.model_save_path = model_save_path
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 创建必要的目录
        self.visualization_dir = os.path.join(model_save_path, 'lightgbm_visualizations')
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

    @staticmethod
    def clean_feature_names(df):
        """清理特征名称"""
        df = df.copy()
        df.columns = [c.replace(':', '_').replace('.', '_').replace(' ', '_') for c in df.columns]
        return df

    # ================================================================================
    # 加载数据
    def load_dataset(self, filename):
        """加载数据集"""
        try:
            file_path = os.path.join(self.dataset_path, filename)
            self.log(f"正在加载数据: {file_path}")

            df = pd.read_csv(file_path)
            X = df.iloc[:, :-1]          # 所有特征
            y = df.iloc[:, -1]           # 目标列（假设已编码）
            le = LabelEncoder()
            y = le.fit_transform(y)      # 确保标签为0,1

            # 检查空值('', None)或无限值(inf, -inf)
            X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
            X = self.clean_feature_names(X)
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
    # 模型训练
    # ================================================================================
    def train(self, custom_params=None):
        """训练LightGBM模型"""
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

            # 3. 创建LightGBM数据集
            lgb_train = lgb.Dataset(
                self.X_train,
                label=self.y_train,
                weight=sample_weights,
                feature_name=self.X_train.columns.tolist()
            )
            lgb_val = lgb.Dataset(
                self.X_val,
                label=self.y_val,
                reference=lgb_train,
                feature_name=self.X_train.columns.tolist()
            )

            # 模型参数
            params = {
                'objective': 'multiclass',
                'num_class': len(np.unique(self.y_train)),
                'metric': ['multi_logloss', 'multi_error'],
                'learning_rate': 0.1,
                'num_leaves': 31,
                'max_depth': -1,
                'min_data_in_leaf': 20,
                'min_gain_to_split': 0.0,
                'lambda_l1': 0.0,
                'lambda_l2': 0.0,
                'feature_fraction': 1.0,
                'bagging_fraction': 1.0,
                'bagging_freq': 0,
                'seed': 42,
                'verbose': -1,
            }

            # 如果提供了自定义参数，则覆盖默认值
            if custom_params:
                for key, value in custom_params.items():
                    if key in params:
                        params[key] = value
                        self.log(f"使用自定义参数 {key}: {value}")

            # 4. 创建可视化器
            self.visualizer = LightGBMVisualizer(
                params,
                feature_names=self.X_train.columns.tolist(),
                visualization_dir=self.visualization_dir
            )

            # 5. 创建回调函数
            self.callback = LightGBMTrainingCallback(self.visualizer, log_callback=self.log)

            self.update_progress(40)
            self.log("开始训练LightGBM模型...")
            self.log("模型参数:")
            for key, value in params.items():
                self.log(f"  {key}: {value}")

            # 6. 训练模型
            self.model = lgb.train(
                params,
                lgb_train,
                num_boost_round=500,
                valid_sets=[lgb_train, lgb_val],
                valid_names=['train', 'val'],
                callbacks=[
                    self.callback,
                    lgb.early_stopping(stopping_rounds=30),
                    lgb.log_evaluation(period=20)
                ]
            )

            self.update_progress(70)
            self.log("模型训练完成")

            # 7. 评估模型
            self.evaluate_model()

            self.update_progress(80)

            # 8. 特征重要性分析
            self.analyze_feature_importance()

            self.update_progress(85)

            # 9. 生成训练可视化
            self.generate_visualizations()

            self.update_progress(95)

            # 10. 保存模型
            self.save_model()

            self.update_progress(100)
            self.log("LightGBM训练完成！")

            return True, "LightGBM模型训练完成"

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

        y_prob = self.model.predict(self.X_test, num_iteration=self.model.best_iteration)
        y_pred = np.argmax(y_prob, axis=1)

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

        importance = self.model.feature_importance(importance_type='split')
        features = self.model.feature_name()
        importance_df = pd.DataFrame({
            'feature': features,
            'importance': importance
        }).sort_values('importance', ascending=False)

        self.log("Top20 特征重要性排名:")
        for i, (_, row) in enumerate(importance_df.head(20).iterrows()):
            self.log(f"  {i + 1:2d}. {row['feature']}: {row['importance']}")

        # 可视化特征重要性
        plt.figure(figsize=(10, 8))
        top_features = importance_df.head(15)
        plt.barh(range(len(top_features)), top_features['importance'])
        plt.yticks(range(len(top_features)), top_features['feature'])
        plt.xlabel('Feature Importance (split)')
        plt.title('Top 15 Feature Importance - LightGBM')
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'feature_importance.png'),
                    dpi=300, bbox_inches='tight')
        plt.close()

        self.log(f"特征重要性图已保存到: {os.path.join(self.visualization_dir, 'feature_importance.png')}")

    # ================================================================================
    # 保存文本报告
    def save_text_reports(self):
        """保存评估结果和特征重要性到文本文件"""
        try:
            # 评估报告文件路径
            eval_report_path = os.path.join(self.visualization_dir, 'evaluation_report.txt')

            # 1. 准备模型评估报告内容
            with open(eval_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("LightGBM 模型评估报告\n")
                f.write("=" * 60 + "\n\n")

                # 模型基本信息
                f.write("模型基本信息:\n")
                f.write(f"训练数据路径: {self.dataset_path}\n")
                f.write(f"模型保存路径: {self.model_save_path}\n")
                f.write(f"训练样本数: {len(self.X_train)}\n")
                f.write(f"验证样本数: {len(self.X_val)}\n")
                f.write(f"测试样本数: {len(self.X_test)}\n")
                f.write(f"特征数量: {len(self.X_train.columns)}\n")
                f.write(f"类别数量: {len(np.unique(self.y_train))}\n")

                # 模型评估结果
                y_prob = self.model.predict(self.X_test, num_iteration=self.model.best_iteration)
                y_pred = np.argmax(y_prob, axis=1)

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

                # 训练信息
                f.write("\n" + "=" * 40 + "\n")
                f.write("训练信息\n")
                f.write("=" * 40 + "\n")
                f.write(f"总训练轮数: {self.model.current_iteration()}\n")
                f.write(f"最佳迭代轮数: {self.model.best_iteration}\n")
                f.write(f"最佳验证分数: {self.model.best_score}\n")

            self.log(f"评估报告已保存到: {eval_report_path}")

            # 特征重要性报告文件路径
            feature_report_path = os.path.join(self.visualization_dir, 'feature_importance_report.txt')

            # 2. 准备特征重要性分析报告
            with open(feature_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("特征重要性排名报告\n")
                f.write("=" * 60 + "\n\n")

                importance = self.model.feature_importance(importance_type='split')
                features = self.model.feature_name()
                importance_df = pd.DataFrame({
                    'feature': features,
                    'importance': importance
                }).sort_values('importance', ascending=False)

                f.write("Top 50 特征重要性排名:\n")
                f.write("-" * 50 + "\n")
                f.write(f"{'排名':<4} {'特征名称':<30} {'重要性(分裂次数)':<15}\n")
                f.write("-" * 50 + "\n")

                for i, (_, row) in enumerate(importance_df.head(50).iterrows()):
                    f.write(f"{i + 1:<4} {row['feature']:<30} {row['importance']:<15}\n")

                # 特征统计信息
                f.write("\n特征重要性统计:\n")
                f.write(f"总特征数量: {len(importance_df)}\n")
                f.write(f"平均重要性: {importance_df['importance'].mean():.2f}\n")
                f.write(f"重要性标准差: {importance_df['importance'].std():.2f}\n")
                f.write(f"最大重要性: {importance_df['importance'].max():.2f}\n")
                f.write(f"最小重要性: {importance_df['importance'].min():.2f}\n")

                # 重要性分布
                f.write("\n重要性分布:\n")
                bins = [0, 1, 5, 10, 20, 50, 100, float('inf')]
                labels = ['0-1', '1-5', '5-10', '10-20', '20-50', '50-100', '100+']
                importance_df['bin'] = pd.cut(importance_df['importance'], bins=bins, labels=labels, right=False)
                distribution = importance_df['bin'].value_counts().sort_index()

                for bin_label, count in distribution.items():
                    f.write(f"  重要性 {bin_label}: {count} 个特征\n")

            self.log(f"特征重要性报告已保存到: {feature_report_path}")

            # 决策树结构报告文件路径
            tree_structure_path = os.path.join(self.visualization_dir, 'decision_tree_structures.txt')

            # 3. 准备决策树结构报告
            with open(tree_structure_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("LightGBM 决策树结构分析\n")
                f.write("=" * 60 + "\n\n")

                # 可视化前几棵树的结构
                f.write("决策树结构分析 (前3棵树):\n")
                f.write("-" * 50 + "\n\n")

                for i in range(min(3, self.model.current_iteration())):
                    tree_analysis = self.visualizer.visualize_tree_detailed(self.model, tree_index=i)
                    f.write(tree_analysis)
                    f.write("\n" + "=" * 50 + "\n\n")

            self.log(f"决策树结构报告已保存到: {tree_structure_path}")

            # 训练过程总结报告文件路径
            training_summary_path = os.path.join(self.visualization_dir, 'training_process_summary.txt')

            # 4. 准备训练过程总结报告
            with open(training_summary_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("LightGBM 训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                # 参数影响解释
                params_explanation = self.visualizer.explain_parameters_effect()
                f.write(params_explanation)
                f.write("\n\n")

                # 训练过程总结
                f.write("=" * 60 + "\n")
                f.write("训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"总训练轮数: {self.model.current_iteration()}\n")
                f.write(f"最佳迭代轮数: {self.model.best_iteration}\n")
                f.write(f"最终验证分数: {self.model.best_score}\n\n")

                f.write("每轮迭代过程:\n")
                f.write("1. 使用直方图算法计算特征分裂点\n")
                f.write("2. 基于梯度信息选择最佳分裂特征和阈值\n")
                f.write("3. 采用叶子生长策略构建决策树\n")
                f.write("4. 更新模型预测值\n")
                f.write("5. 计算验证集性能\n\n")

                # LightGBM 核心算法原理
                f.write("=" * 60 + "\n")
                f.write("LightGBM 核心算法原理\n")
                f.write("=" * 60 + "\n\n")

                f.write("LightGBM 核心特性:\n")
                f.write("1. 基于梯度提升框架 (Gradient Boosting)\n")
                f.write("2. 使用直方图算法 (Histogram-based) 加速训练\n")
                f.write("3. 叶子生长策略 (Leaf-wise) - 与深度生长策略相比更高效\n")
                f.write("4. 单边梯度采样 (GOSS) - 保留大梯度样本，随机采样小梯度样本\n")
                f.write("5. 互斥特征捆绑 (EFB) - 将稀疏特征捆绑减少特征维度\n\n")

                f.write("节点分裂增益公式:\n")
                f.write("  Gain = 1/2 [∑(g_left)²/(∑h_left+λ) + ∑(g_right)²/(∑h_right+λ) - ∑(g_parent)²/(∑h_parent+λ)]\n\n")

                f.write("其中:\n")
                f.write("  g = 一阶梯度 (负梯度方向)\n")
                f.write("  h = 二阶梯度 (Hessian矩阵)\n")
                f.write("  λ = L2正则化系数\n")

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
        if hasattr(self.callback, 'evals_result'):
            progress_path = self.visualizer.visualize_training_progress(self.callback.evals_result)
            self.log(f"训练进度图已保存到: {progress_path}")
        else:
            self.log("警告: 无法获取训练进度数据")

        # 特征重要性分析
        self.log("开始生成特征重要性图...")
        self.analyze_feature_importance()

        # 保存文本报告
        self.log("开始保存文本报告...")
        self.save_text_reports()

        # 可视化前几棵决策树结构
        self.log("可视化决策树结构...")
        for i in range(min(3, self.model.current_iteration())):
            tree_analysis = self.visualizer.visualize_tree_detailed(self.model, tree_index=i)
            # 只记录前几行，避免日志过长
            lines = tree_analysis.split('\n')
            for line in lines[:10]:  # 只显示前10行
                self.log(f"  {line}")
            if len(lines) > 10:
                self.log("  ... (树结构详细信息已保存)")

        # 参数影响解释
        params_explanation = self.visualizer.explain_parameters_effect()
        for line in params_explanation.split('\n'):
            self.log(f"  {line}")

        # 额外显示LightGBM算法原理
        self.log(f"\n{'=' * 60}")
        self.log("LightGBM 训练过程总结")
        self.log(f"{'=' * 60}")
        self.log(f"总训练轮数: {self.model.current_iteration()}")
        self.log(f"最佳迭代轮数: {self.model.best_iteration}")
        self.log(f"最终验证分数: {self.model.best_score}")
        self.log(f"\nLightGBM 核心优势:")
        self.log("1. 使用直方图算法，训练速度更快")
        self.log("2. 叶子生长策略，精度更高")
        self.log("3. 内存消耗更低")
        self.log("4. 支持并行学习")
        self.log("5. 可直接处理类别特征")

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
        model_path = os.path.join(self.model_save_path, 'lightgbm_model.txt')
        self.model.save_model(model_path)

        # 评估最终模型
        y_prob = self.model.predict(self.X_test, num_iteration=self.model.best_iteration)
        y_pred = np.argmax(y_prob, axis=1)

        # 准备元数据
        metadata = {
            'feature_importance': dict(zip(self.model.feature_name(),
                                           self.model.feature_importance(importance_type='split'))),
            'eval_metrics': {
                'accuracy': accuracy_score(self.y_test, y_pred),
                'f1_scores': {
                    'macro': f1_score(self.y_test, y_pred, average='macro'),
                    'micro': f1_score(self.y_test, y_pred, average='micro'),
                    'weighted': f1_score(self.y_test, y_pred, average='weighted')
                }
            },
            'model_params': self.model.params,
            'training_info': {
                'best_iteration': self.model.best_iteration,
                'total_iterations': self.model.current_iteration(),
                'best_score': self.model.best_score
            }
        }

        # 转换NumPy数据类型为Python原生类型
        metadata = self._convert_numpy_types(metadata)

        # 保存元数据
        metadata_path = os.path.join(self.model_save_path, 'lightgbm_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.log(f"模型已保存到: {model_path}")
        self.log(f"元数据已保存到: {metadata_path}")


# ================================================================================
# 训练函数 - 供GUI调用
# ================================================================================
def train(dataset_path, model_save_path, progress_callback=None, log_callback=None, custom_params=None):
    """
    训练LightGBM模型的主函数

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
        trainer = LightGBMTrainer(
            dataset_path=dataset_path,
            model_save_path=model_save_path,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

        return trainer.train(custom_params)

    except Exception as e:
        error_msg = f"LightGBM训练失败: {str(e)}"
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
