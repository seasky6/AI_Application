import os
import numpy as np
import pandas as pd
import xgboost as xgb
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
# XGBoost训练可视化
# ======================================================================================================================
class XGBoostVisualizer:
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
        # 记录评估指标
        if eval_result:
            self.training_history['metrics'].append({
                'iteration': iteration,
                'eval_result': eval_result
            })

    def visualize_training_progress(self):
        """可视化训练过程"""
        if not self.training_history['metrics']:
            print("没有训练记录可可视化")
            return

        iterations = [m['iteration'] for m in self.training_history['metrics']]
        train_errors = []
        val_errors = []

        for metric in self.training_history['metrics']:
            eval_result = metric['eval_result']
            for dataset_name, dataset_metrics in eval_result.items():
                if 'train' in dataset_name:
                    for metric_name, value in dataset_metrics.items():
                        if 'error' in metric_name:
                            train_errors.append(value)
                elif 'val' in dataset_name:
                    for metric_name, value in dataset_metrics.items():
                        if 'error' in metric_name:
                            val_errors.append(value)

        plt.figure(figsize=(12, 4))

        # 绘制训练和验证误差
        plt.subplot(1, 2, 1)
        if train_errors:
            plt.plot(iterations[:len(train_errors)], train_errors, 'b-', label='Train Error')
        if val_errors:
            plt.plot(iterations[:len(val_errors)], val_errors, 'r-', label='Validation Error')
        plt.xlabel('Iteration')
        plt.ylabel('Error')
        plt.title('Training Progress')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'training_progress.png'))
        plt.close()

        return os.path.join(self.visualization_dir, 'training_progress.png')

    def visualize_tree_detailed(self, model, tree_index=0):
        """详细可视化特定树的结构"""
        try:
            # 获取树的文本表示
            trees_dump = model.get_dump()
            if tree_index < len(trees_dump):
                tree_text = f"\n{'=' * 60}\n树 {tree_index} 的详细结构:\n{'=' * 60}\n{trees_dump[tree_index]}"

                # 解析树结构信息
                analysis = self._analyze_tree_structure(trees_dump[tree_index])

                return tree_text + "\n" + analysis
            else:
                return f"树索引 {tree_index} 超出范围"
        except Exception as e:
            return f"可视化树结构时出错: {e}"

    def _analyze_tree_structure(self, tree_dump):
        """分析树结构并解释XGBoost的工作原理"""
        lines = tree_dump.strip().split('\n')
        analysis = f"\n树结构分析 (共 {len(lines)} 个节点):\n" + "-" * 50 + "\n"

        for i, line in enumerate(lines):
            if 'leaf' in line:
                # 叶子节点
                parts = line.split('leaf=')
                if len(parts) > 1:
                    leaf_value = float(parts[1].split(',')[0])
                    cover_part = line.split('cover=')[1].split(']')[0] if 'cover=' in line else '0'
                    cover = float(cover_part)
                    analysis += f"叶子节点 {i}: 权重 = {leaf_value:.4f}, 覆盖样本数 = {cover:.1f}\n"
                    analysis += f"  → 计算公式: w = -∑g_i / (∑h_i + λ)\n"
                    analysis += f"  → 当前值: {leaf_value:.4f} = -G / (H + {self.params.get('reg_lambda', 1)})\n\n"

            elif '[' in line and ']' in line:
                # 分裂节点
                node_info = self._parse_split_node(line)
                if node_info:
                    analysis += f"分裂节点 {i}: {node_info['feature']} < {node_info['threshold']:.4f}\n"
                    analysis += f"  → 增益 = {node_info.get('gain', 0):.4f}\n"
                    analysis += f"  → 覆盖样本数 = {node_info.get('cover', 0):.1f}\n\n"

        return analysis

    @staticmethod
    def _parse_split_node(line):
        """解析分裂节点信息"""
        try:
            node_info = {}

            # 提取分裂条件
            if '[' in line and ']' in line:
                condition = line.split('[')[1].split(']')[0]
                if '<' in condition:
                    parts = condition.split('<')
                    feature = parts[0].strip()
                    threshold = float(parts[1].strip())
                    node_info['feature'] = feature
                    node_info['threshold'] = threshold

            # 提取增益
            if 'gain=' in line:
                gain_part = line.split('gain=')[1]
                gain_value = float(gain_part.split(',')[0])
                node_info['gain'] = gain_value

            # 提取覆盖度
            if 'cover=' in line:
                cover_part = line.split('cover=')[1]
                cover_value = float(cover_part.split(']')[0])
                node_info['cover'] = cover_value

            return node_info
        except Exception as e:
            return None

    def explain_parameters_effect(self):
        """解释参数对训练的影响"""
        explanation = "\n" + "=" * 60 + "\n"
        explanation += "XGBoost 参数对训练过程的影响分析\n"
        explanation += "=" * 60 + "\n"

        params = self.params

        explanation += f"\n📊 当前模型参数:\n"
        for key, value in params.items():
            explanation += f"  {key}: {value}\n"

        explanation += f"\n🌳 树结构相关参数:\n"
        explanation += f"  1. 最大深度 (max_depth={params.get('max_depth', 6)}):\n"
        explanation += "     - 控制树的复杂度，值越大树越深\n"
        explanation += "     - 影响: 更深的树可以学习更复杂的模式，但容易过拟合\n"

        explanation += f"\n  2. 学习率 (learning_rate={params.get('learning_rate', 0.1)}):\n"
        explanation += "     - 控制每棵树的贡献权重\n"
        explanation += "     - 影响: 值越小需要更多树，但可能获得更好的泛化能力\n"

        explanation += f"\n🎯 正则化参数:\n"
        explanation += f"  3. L2正则化 (reg_lambda={params.get('reg_lambda', 1)}):\n"
        explanation += "     - 在叶子权重计算中惩罚大的权重值\n"
        explanation += "     - 影响: w_j = -∑g_i / (∑h_i + λ)，λ越大叶子权重越小\n"

        explanation += f"\n  4. Gamma (gamma={params.get('gamma', 0)}):\n"
        explanation += "     - 控制分裂的最小增益阈值\n"
        explanation += "     - 影响: Gain > γ 才进行分裂，γ越大树越简单\n"

        explanation += f"\n  5. 最小叶子权重 (min_child_weight={params.get('min_child_weight', 1)}):\n"
        explanation += "     - 控制叶子节点所需的最小样本权重和\n"
        explanation += "     - 影响: 防止创建样本数过少的叶子节点\n"

        explanation += f"\n🔄 采样参数:\n"
        explanation += f"  6. 样本采样 (subsample={params.get('subsample', 1)}):\n"
        explanation += "     - 每棵树随机采样的样本比例\n"
        explanation += "     - 影响: 增强模型的随机性和泛化能力\n"

        explanation += f"\n  7. 特征采样 (colsample_bytree={params.get('colsample_bytree', 1)}):\n"
        explanation += "     - 每棵树随机采样的特征比例\n"
        explanation += "     - 影响: 增强特征选择的多样性\n"

        explanation += f"\n💡 XGBoost 核心算法原理:\n"
        explanation += "  节点分裂增益公式:\n"
        explanation += "    Gain = 1/2 [G_L²/(H_L+λ) + G_R²/(H_R+λ) - (G_L+G_R)²/(H_L+H_R+λ)] - γ\n"
        explanation += "  叶子节点权重公式:\n"
        explanation += "    w_j* = - (∑g_i) / (∑h_i + λ)\n"
        explanation += "  其中: g_i = 一阶梯度, h_i = 二阶梯度, λ = L2正则化系数\n"

        return explanation


# ======================================================================================================================
# 自定义回调函数用于记录训练过程
# ======================================================================================================================
class TrainingCallback(xgb.callback.TrainingCallback):
    def __init__(self, visualizer, verbose_eval, log_callback=None):
        super().__init__()
        self.visualizer = visualizer
        self.verbose_eval = verbose_eval
        self.log_callback = log_callback
        self.iteration = 0

    def after_iteration(self, model, epoch, evals_log):
        self.iteration = epoch
        # 将evals_log转换为record_iteration需要的格式
        eval_result = {}
        for dataset, metrics in evals_log.items():
            eval_result[dataset] = {}
            for metric_name, values in metrics.items():
                eval_result[dataset][metric_name] = values[-1]  # 取最新值

        self.visualizer.record_iteration(epoch, eval_result)

        if self.verbose_eval and epoch % self.verbose_eval == 0:
            log_message = f"\n迭代 {epoch}:"
            for dataset, metrics in eval_result.items():
                log_message += f"\n  {dataset}: "
                for metric_name, value in metrics.items():
                    log_message += f"{metric_name}={value:.4f} "

            if self.log_callback:
                self.log_callback(log_message)

        return False  # 继续训练


# ======================================================================================================================
# XGBoost训练模块
# ======================================================================================================================
class XGBoostTrainer:
    def __init__(self, dataset_path, model_save_path, progress_callback=None, log_callback=None):
        self.dataset_path = dataset_path
        self.model_save_path = model_save_path
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 创建必要的目录
        self.visualization_dir = os.path.join(model_save_path, 'xgboost_visualizations')
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
            X = df.iloc[:, :-1]          # 所有特征
            y = df.iloc[:, -1]           # 目标列（假设已编码）
            le = LabelEncoder()
            y = le.fit_transform(y)      # 确保标签为0,1

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
        print(f"类别分布: {class_counts}")
        print(f"计算权重: {weights}")
        return weights

    # ================================================================================
    # 模型训练
    # ================================================================================
    def train(self, custom_params=None):
        """训练XGBoost模型"""
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

            # 3. 转换为DMatrix并应用权重
            dtrain = xgb.DMatrix(self.X_train, label=self.y_train, weight=sample_weights)
            dval = xgb.DMatrix(self.X_val, label=self.y_val)
            dtest = xgb.DMatrix(self.X_test, label=self.y_test)

            # 模型参数
            params = {
                'objective': 'multi:softmax',
                'num_class': len(np.unique(self.y_train)),
                'eval_metric': ['mlogloss', 'merror'],
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'gamma': 0,
                'reg_alpha': 0,
                'reg_lambda': 1,
                'min_child_weight': 1,
                'seed': 42,
                'tree_method': 'hist',
            }

            # 如果提供了自定义参数，则覆盖默认值
            if custom_params:
                for key, value in custom_params.items():
                    if key in params:
                        params[key] = value
                        self.log(f"使用自定义参数 {key}: {value}")

            # 4. 创建可视化器
            self.visualizer = XGBoostVisualizer(
                params,
                feature_names=self.X_train.columns.tolist(),
                visualization_dir=self.visualization_dir
            )

            self.update_progress(40)
            self.log("开始训练XGBoost模型...")
            self.log("模型参数:")
            for key, value in params.items():
                self.log(f"  {key}: {value}")

            # 5. 创建回调函数
            callback = TrainingCallback(self.visualizer, verbose_eval=20, log_callback=self.log)

            # 6. 训练模型
            self.model = xgb.train(
                params,
                dtrain,
                num_boost_round=500,
                evals=[(dtrain, 'train'), (dval, 'val')],
                early_stopping_rounds=30,
                verbose_eval=False,
                callbacks=[callback]
            )

            self.update_progress(70)
            self.log("模型训练完成")

            # 7. 评估模型
            self.evaluate_model(dtest)

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
            self.log("XGBoost训练完成！")

            return True, "XGBoost模型训练完成"

        except Exception as e:
            self.log(f"训练过程中出错: {str(e)}")
            return False, f"训练失败: {str(e)}"

    # ================================================================================
    # 评估模型
    # F1 Score: 精确率（Precision）和召回率（Recall）的调和平均数，范围在 [0, 1]，值越高表示模型性能越好
    #   精确率：预测为正的样本中实际为正的比例（避免误报）
    #   召回率：实际为正的样本中被正确预测的比例 (避免漏报）
    # Macro 平均：对每个类别单独计算 F1，然后取所有类别的算术平均值（平等对待每个类，无论样本数量）
    #   接近 0.5：模型有一定区分能力，但存在明显错误
    #   超过 0.7：通常认为性能较好
    #   超过 0.9：优秀（但需警惕过拟合）
    def evaluate_model(self, dtest):
        """评估模型性能"""
        self.log("正在评估模型性能...")

        y_pred = self.model.predict(dtest)

        accuracy = accuracy_score(self.y_test, y_pred)
        f1_macro = f1_score(self.y_test, y_pred, average='macro')

        self.log(f"准确率: {accuracy:.4f}")
        self.log(f"F1 Score (Macro): {f1_macro:.4f}")

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

        importance = self.model.get_score(importance_type='weight')
        importance_df = pd.DataFrame.from_dict(importance, orient='index', columns=['weight'])
        importance_df = importance_df.sort_values('weight', ascending=False)

        self.log("Top20 特征重要性排名:")
        for i, (feature, row) in enumerate(importance_df.head(20).iterrows()):
            self.log(f"  {i + 1:2d}. {feature}: {row['weight']}")

        # 可视化特征重要性
        plt.figure(figsize=(10, 8))
        top_features = importance_df.head(15)
        plt.barh(range(len(top_features)), top_features['weight'])
        plt.yticks(range(len(top_features)), top_features.index)
        plt.xlabel('Feature Importance (weight)')
        plt.title('Top 15 Feature Importance')
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'feature_importance.png'),
                    dpi=300, bbox_inches='tight')
        plt.close()

        self.log(f"特征重要性图已保存到: {os.path.join(self.visualization_dir, 'feature_importance.png')}")

    # ================================================================================
    # 模型评估结果，特征重要性分析，模型训练细节文本
    def save_text_reports(self):
        """保存评估结果和特征重要性到文本文件"""
        try:
            # 评估报告文件路径
            eval_report_path = os.path.join(self.visualization_dir, 'evaluation_report.txt')

            # 1. 准备模型评估报告内容
            with open(eval_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("XGBoost 模型评估报告\n")
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
                dtest = xgb.DMatrix(self.X_test, label=self.y_test)
                y_pred = self.model.predict(dtest)

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
                f.write(f"总训练轮数: {self.model.num_boosted_rounds()}\n")
                best_iteration = getattr(self.model, 'best_iteration', self.model.num_boosted_rounds())
                f.write(f"最佳迭代轮数: {best_iteration}\n")
                best_score = getattr(self.model, 'best_score', 'N/A')
                f.write(f"最佳验证分数: {best_score}\n")

            self.log(f"评估报告已保存到: {eval_report_path}")

            # 特征重要性报告文件路径
            feature_report_path = os.path.join(self.visualization_dir, 'feature_importance_report.txt')

            # 2. 准备特征重要性分析报告
            with open(feature_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("特征重要性排名报告\n")
                f.write("=" * 60 + "\n\n")

                importance = self.model.get_score(importance_type='weight')
                if importance:
                    importance_df = pd.DataFrame.from_dict(importance, orient='index', columns=['weight'])
                    importance_df = importance_df.sort_values('weight', ascending=False)

                    f.write("Top 50 特征重要性排名:\n")
                    f.write("-" * 50 + "\n")
                    f.write(f"{'排名':<4} {'特征名称':<30} {'重要性(权重)':<15}\n")
                    f.write("-" * 50 + "\n")

                    for i, (feature, row) in enumerate(importance_df.head(50).iterrows()):
                        f.write(f"{i + 1:<4} {feature:<30} {row['weight']:<15}\n")

                    # 特征统计信息
                    f.write("\n特征重要性统计:\n")
                    f.write(f"总特征数量: {len(importance_df)}\n")
                    f.write(f"平均重要性: {importance_df['weight'].mean():.2f}\n")
                    f.write(f"重要性标准差: {importance_df['weight'].std():.2f}\n")
                    f.write(f"最大重要性: {importance_df['weight'].max():.2f}\n")
                    f.write(f"最小重要性: {importance_df['weight'].min():.2f}\n")

                    # 重要性分布
                    f.write("\n重要性分布:\n")
                    bins = [0, 1, 5, 10, 20, 50, 100, float('inf')]
                    labels = ['0-1', '1-5', '5-10', '10-20', '20-50', '50-100', '100+']
                    importance_df['bin'] = pd.cut(importance_df['weight'], bins=bins, labels=labels, right=False)
                    distribution = importance_df['bin'].value_counts().sort_index()

                    for bin_label, count in distribution.items():
                        f.write(f"  重要性 {bin_label}: {count} 个特征\n")
                else:
                    f.write("无法获取特征重要性数据\n")

            self.log(f"特征重要性报告已保存到: {feature_report_path}")

            # 决策树结构报告文件路径
            tree_structure_path = os.path.join(self.visualization_dir, 'decision_tree_structures.txt')

            # 3. 准备决策树结构报告
            with open(tree_structure_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("XGBoost 决策树结构分析\n")
                f.write("=" * 60 + "\n\n")

                # 可视化前几棵树的结构
                f.write("决策树结构分析 (前3棵树):\n")
                f.write("-" * 50 + "\n\n")

                for i in range(min(3, self.model.num_boosted_rounds())):
                    tree_analysis = self.visualizer.visualize_tree_detailed(self.model, tree_index=i)
                    f.write(tree_analysis)
                    f.write("\n" + "=" * 50 + "\n\n")

            self.log(f"决策树结构报告已保存到: {tree_structure_path}")

            # 训练过程总结报告文件路径
            training_summary_path = os.path.join(self.visualization_dir, 'training_process_summary.txt')

            # 4. 准备训练过程总结报告
            with open(training_summary_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("XGBoost 训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                # 参数影响解释
                params_explanation = self.visualizer.explain_parameters_effect()
                f.write(params_explanation)
                f.write("\n\n")

                # 训练过程总结
                f.write("=" * 60 + "\n")
                f.write("训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"总训练轮数: {self.model.num_boosted_rounds()}\n")
                best_iteration = getattr(self.model, 'best_iteration', self.model.num_boosted_rounds())
                f.write(f"最佳迭代轮数: {best_iteration}\n")
                best_score = getattr(self.model, 'best_score', 'N/A')
                f.write(f"最终验证误差: {best_score}\n\n")

                f.write("每轮迭代过程:\n")
                f.write("1. 计算一阶梯度(g)和二阶梯度(h)\n")
                f.write("2. 贪心地选择最佳分裂点（最大化增益）\n")
                f.write("3. 构建新的决策树\n")
                f.write("4. 计算叶子节点权重\n")
                f.write("5. 将新树添加到模型中\n\n")

                # XGBoost 核心算法原理
                f.write("=" * 60 + "\n")
                f.write("XGBoost 核心算法原理\n")
                f.write("=" * 60 + "\n\n")

                f.write("节点分裂增益公式:\n")
                f.write("  Gain = 1/2 [G_L²/(H_L+λ) + G_R²/(H_R+λ) - (G_L+G_R)²/(H_L+H_R+λ)] - γ\n\n")

                f.write("叶子节点权重公式:\n")
                f.write("  w_j* = - (∑g_i) / (∑h_i + λ)\n\n")

                f.write("其中:\n")
                f.write("  g_i = 一阶梯度\n")
                f.write("  h_i = 二阶梯度\n")
                f.write("  λ = L2正则化系数\n")
                f.write("  γ = 分裂增益阈值\n")

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
        progress_path = self.visualizer.visualize_training_progress()
        self.log(f"训练进度图已保存到: {progress_path}")

        # 特征重要性分析
        self.log("开始生成特征重要性图...")
        self.analyze_feature_importance()

        # 保存文本报告
        self.log("开始保存文本报告...")
        self.save_text_reports()

        # 可视化前几棵决策树结构
        self.log("可视化决策树结构...")
        for i in range(min(3, self.model.num_boosted_rounds())):
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

        # 额外显示XGBoost算法原理
        self.log(f"\n{'=' * 60}")
        self.log("XGBoost 训练过程总结")
        self.log(f"{'=' * 60}")
        self.log(f"总训练轮数: {self.model.num_boosted_rounds()}")
        best_iteration = getattr(self.model, 'best_iteration', self.model.num_boosted_rounds())
        self.log(f"最佳迭代轮数: {best_iteration}")
        best_score = getattr(self.model, 'best_score', 'N/A')
        self.log(f"最终验证误差: {best_score}")
        self.log(f"\n每轮迭代中:")
        self.log("1. 计算一阶梯度(g)和二阶梯度(h)")
        self.log("2. 贪心地选择最佳分裂点（最大化增益）")
        self.log("3. 构建新的决策树")
        self.log("4. 计算叶子节点权重")
        self.log("5. 将新树添加到模型中")

    # ================================================================================
    # 保存模型和元数据
    def save_model(self):
        """保存模型和元数据"""
        self.log("正在保存模型和元数据...")

        # 保存模型
        model_path = os.path.join(self.model_save_path, 'xgboost_model.json')
        self.model.save_model(model_path)

        # 评估最终模型
        dtest = xgb.DMatrix(self.X_test, label=self.y_test)
        y_pred = self.model.predict(dtest)

        # 准备元数据
        metadata = {
            'feature_importance': self.model.get_score(importance_type='weight'),
            'eval_metrics': {
                'accuracy': accuracy_score(self.y_test, y_pred),
                'f1_scores': {
                    'macro': f1_score(self.y_test, y_pred, average='macro'),
                    'micro': f1_score(self.y_test, y_pred, average='micro'),
                    'weighted': f1_score(self.y_test, y_pred, average='weighted')
                }
            },
            'model_params': {
                'objective': 'multi:softmax',
                'num_class': len(np.unique(self.y_train)),
                'max_depth': 5,
                'learning_rate': 0.1,
                'subsample': 0.9,
                'colsample_bytree': 0.9,
                'gamma': 2,
                'reg_lambda': 5,
                'reg_alpha': 1,
                'min_child_weight': 3
            },
            'training_info': {
                'best_iteration': getattr(self.model, 'best_iteration', self.model.num_boosted_rounds()),
                'total_iterations': self.model.num_boosted_rounds()
            }
        }

        # 保存元数据
        metadata_path = os.path.join(self.model_save_path, 'xgboost_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.log(f"模型已保存到: {model_path}")
        self.log(f"元数据已保存到: {metadata_path}")


# ================================================================================
# 训练函数 - 供GUI调用
# ================================================================================
def train(dataset_path, model_save_path, progress_callback=None, log_callback=None, custom_params=None):
    """
    训练XGBoost模型的主函数

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
        trainer = XGBoostTrainer(
            dataset_path=dataset_path,
            model_save_path=model_save_path,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

        return trainer.train(custom_params)

    except Exception as e:
        error_msg = f"XGBoost训练失败: {str(e)}"
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
