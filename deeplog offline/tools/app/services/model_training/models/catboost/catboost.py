import os
import numpy as np
import pandas as pd
import catboost as cb
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
# CatBoost训练可视化
# ======================================================================================================================
class CatBoostVisualizer:
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
        if 'learn' in evals_result and 'MultiClass' in evals_result['learn']:
            train_loss = evals_result['learn']['MultiClass']
            iterations = list(range(len(train_loss)))
            plt.plot(iterations, train_loss, 'b-', label='Train Loss')

        if 'validation' in evals_result and 'MultiClass' in evals_result['validation']:
            val_loss = evals_result['validation']['MultiClass']
            iterations = list(range(len(val_loss)))
            plt.plot(iterations, val_loss, 'r-', label='Validation Loss')

        plt.xlabel('Iteration')
        plt.ylabel('Log Loss')
        plt.title('Training Progress - Loss')
        plt.legend()
        plt.grid(True)

        # 绘制训练和验证准确率
        plt.subplot(1, 2, 2)
        if 'learn' in evals_result and 'Accuracy' in evals_result['learn']:
            train_accuracy = evals_result['learn']['Accuracy']
            iterations = list(range(len(train_accuracy)))
            plt.plot(iterations, train_accuracy, 'b-', label='Train Accuracy')

        if 'validation' in evals_result and 'Accuracy' in evals_result['validation']:
            val_accuracy = evals_result['validation']['Accuracy']
            iterations = list(range(len(val_accuracy)))
            plt.plot(iterations, val_accuracy, 'r-', label='Validation Accuracy')

        plt.xlabel('Iteration')
        plt.ylabel('Accuracy')
        plt.title('Training Progress - Accuracy')
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
            tree_text = f"\n{'=' * 60}\n树 {tree_index} 的详细结构:\n{'=' * 60}\n"

            # CatBoost的树结构需要通过模型API获取
            try:
                # 尝试获取树结构信息
                tree_info = model.get_tree_leaf_weights(tree_index)
                tree_text += f"树 {tree_index} 的叶子权重: {tree_info}\n"

                # 分析树结构
                analysis = self._analyze_tree_structure(model, tree_index)
                return tree_text + "\n" + analysis
            except:
                return tree_text + "无法获取详细的树结构信息\n"

        except Exception as e:
            return f"可视化树结构时出错: {e}"

    def _analyze_tree_structure(self, model, tree_index):
        """分析树结构并解释CatBoost的工作原理"""
        analysis = f"\nCatBoost 树结构分析:\n" + "-" * 50 + "\n"

        analysis += "CatBoost 使用对称树 (Oblivious Trees) 结构:\n"
        analysis += "- 所有分裂都在同一深度进行\n"
        analysis += "- 每个级别的所有节点使用相同的分裂条件\n"
        analysis += "- 这种结构加速预测并减少过拟合\n\n"

        analysis += "核心算法特性:\n"
        analysis += "1. 有序提升 (Ordered Boosting): 解决梯度偏差\n"
        analysis += "2. 类别特征处理: 无需独热编码\n"
        analysis += "3. 对称树结构: 提高预测速度\n"
        analysis += "4. 内置正则化: 防止过拟合\n\n"

        # 获取模型信息
        analysis += f"模型信息:\n"
        analysis += f"- 树的数量: {model.tree_count_}\n"
        analysis += f"- 特征数量: {len(self.feature_names) if self.feature_names else '未知'}\n"

        return analysis

    def explain_parameters_effect(self):
        """解释参数对训练的影响"""
        explanation = "\n" + "=" * 60 + "\n"
        explanation += "CatBoost 参数对训练过程的影响分析\n"
        explanation += "=" * 60 + "\n"

        params = self.params

        explanation += f"\n📊 当前模型参数:\n"
        for key, value in params.items():
            explanation += f"  {key}: {value}\n"

        explanation += f"\n🌳 树结构相关参数:\n"
        explanation += f"  1. 树深度 (depth={params.get('depth', 6)}):\n"
        explanation += "     - 控制对称树的深度\n"
        explanation += "     - 影响: 更深的树可以学习更复杂的模式，但可能过拟合\n"

        explanation += f"\n  2. 学习率 (learning_rate={params.get('learning_rate', 0.03)}):\n"
        explanation += "     - 控制每棵树的贡献权重\n"
        explanation += "     - 影响: 值越小需要更多树，但可能获得更好的泛化能力\n"

        explanation += f"\n  3. 迭代次数 (iterations={params.get('iterations', 1000)}):\n"
        explanation += "     - 控制 boosting 迭代的次数\n"
        explanation += "     - 影响: 值越大模型越复杂，但训练时间更长\n"

        explanation += f"\n🎯 正则化参数:\n"
        explanation += f"  4. L2正则化 (l2_leaf_reg={params.get('l2_leaf_reg', 3)}):\n"
        explanation += "     - 在损失函数中加入L2正则化项\n"
        explanation += "     - 影响: 惩罚大的权重值，防止过拟合\n"

        explanation += f"\n  5. 叶子数惩罚 (leaf_estimation_iterations={params.get('leaf_estimation_iterations', 1)}):\n"
        explanation += "     - 控制叶子值估计的迭代次数\n"
        explanation += "     - 影响: 值越大叶子值估计越精确\n"

        explanation += f"\n  6. 随机强度 (random_strength={params.get('random_strength', 1)}):\n"
        explanation += "     - 控制分裂分数的随机性\n"
        explanation += "     - 影响: 增加随机性可以提高泛化能力\n"

        explanation += f"\n🔄 采样参数:\n"
        explanation += f"  7. 样本采样 (rsm={params.get('rsm', 1)}):\n"
        explanation += "     - 每棵树随机采样的特征比例\n"
        explanation += "     - 影响: 增强特征选择的多样性\n"

        explanation += f"\n  8. 自举样本 (bootstrap_type={params.get('bootstrap_type', 'Bayesian')}):\n"
        explanation += "     - 控制自举采样类型\n"
        explanation += "     - 影响: 贝叶斯自举通常效果更好\n"

        explanation += f"\n💡 CatBoost 核心算法原理:\n"
        explanation += "  1. 有序提升 (Ordered Boosting):\n"
        explanation += "     - 解决预测偏移问题\n"
        explanation += "     - 使用排列来计算梯度\n"
        explanation += "  2. 对称树 (Oblivious Trees):\n"
        explanation += "     - 所有分裂在相同深度\n"
        explanation += "     - 加速预测过程\n"
        explanation += "  3. 类别特征处理:\n"
        explanation += "     - 无需独热编码\n"
        explanation += "     - 基于目标统计量\n\n"

        explanation += "有序提升算法:\n"
        explanation += "  对于每个样本，使用排在该样本之前的样本来计算梯度\n"
        explanation += "  这避免了目标泄漏和预测偏移问题\n"

        return explanation


# ======================================================================================================================
# 自定义回调函数用于记录训练过程
# ======================================================================================================================
class CatBoostTrainingCallback:
    def __init__(self, visualizer, log_callback=None):
        self.visualizer = visualizer
        self.log_callback = log_callback
        self.best_score = {}
        self.evals_result = {}

    def after_iteration(self, info):
        """CatBoost回调函数"""
        iteration = info.iteration
        metrics = info.metrics

        # 记录评估结果
        eval_result = {}
        for dataset_name, dataset_metrics in metrics.items():
            eval_result[dataset_name] = {}
            for metric_name, metric_value in dataset_metrics.items():
                eval_result[dataset_name][metric_name] = metric_value

        self.visualizer.record_iteration(iteration, eval_result)

        # 记录到evals_result用于绘图
        for dataset_name, dataset_metrics in metrics.items():
            if dataset_name not in self.evals_result:
                self.evals_result[dataset_name] = {}
            for metric_name, metric_value in dataset_metrics.items():
                if metric_name not in self.evals_result[dataset_name]:
                    self.evals_result[dataset_name][metric_name] = []
                self.evals_result[dataset_name][metric_name].append(metric_value)

        # 日志输出
        if self.log_callback and iteration % 20 == 0:
            log_message = f"\n迭代 {iteration}:"
            for dataset_name, dataset_metrics in eval_result.items():
                log_message += f"\n  {dataset_name}: "
                for metric_name, metric_value in dataset_metrics.items():
                    log_message += f"{metric_name}={metric_value:.4f} "
            self.log_callback(log_message)

        return True  # 继续训练


# ======================================================================================================================
# CatBoost训练模块
# ======================================================================================================================
class CatBoostTrainer:
    def __init__(self, dataset_path, model_save_path, progress_callback=None, log_callback=None):
        self.dataset_path = dataset_path
        self.model_save_path = model_save_path
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 创建必要的目录
        self.visualization_dir = os.path.join(model_save_path, 'catboost_visualizations')
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

    def _identify_categorical_features(self, X):
        """识别类别特征 - 修复版本"""
        categorical_features = []
        for col in X.columns:
            # 只识别真正的类别特征：object类型或category类型
            if X[col].dtype == 'object' or X[col].dtype.name == 'category':
                categorical_features.append(col)
            # 对于数值类型，只有当唯一值数量很少且不是连续数值时才视为类别特征
            elif X[col].nunique() <= 10 and self._is_categorical_numeric(X[col]):
                categorical_features.append(col)
        return categorical_features

    @staticmethod
    def _is_categorical_numeric(series):
        """判断数值列是否应该被视为类别特征"""
        # 检查是否主要是整数值
        if series.dtype in ['int64', 'int32']:
            return True
        # 对于浮点数，检查是否主要是整数值（没有小数部分）
        elif series.dtype in ['float64', 'float32']:
            # 检查是否所有值都是整数（或接近整数）
            if (series.dropna() % 1 == 0).all():
                return True
        return False

    @staticmethod
    def _prepare_categorical_features(X, categorical_features):
        """预处理类别特征，确保它们是字符串类型"""
        X_prepared = X.copy()
        for col in categorical_features:
            if col in X_prepared.columns:
                # 将类别特征转换为字符串，处理NaN值
                X_prepared[col] = X_prepared[col].astype(str)
                # 将NaN字符串替换为具体的缺失值表示
                X_prepared[col] = X_prepared[col].replace('nan', 'Missing')
                X_prepared[col] = X_prepared[col].replace('NaN', 'Missing')
                X_prepared[col] = X_prepared[col].replace('', 'Missing')
        return X_prepared

    # ================================================================================
    # 模型训练
    # ================================================================================
    def train(self, custom_params=None):
        """训练CatBoost模型"""
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

            # 3. 识别类别特征
            categorical_features = self._identify_categorical_features(self.X_train)

            self.log(f"识别到 {len(categorical_features)} 个类别特征: {categorical_features}")

            # 4. 预处理类别特征 - 新增步骤
            if categorical_features:
                self.log("预处理类别特征...")
                self.X_train = self._prepare_categorical_features(self.X_train, categorical_features)
                self.X_val = self._prepare_categorical_features(self.X_val, categorical_features)
                self.X_test = self._prepare_categorical_features(self.X_test, categorical_features)

            # 模型参数 - 简化版本，避免复杂配置
            params = {
                'iterations': 500,  # 减少迭代次数
                'learning_rate': 0.05,
                'depth': 6,
                'l2_leaf_reg': 3,
                'random_strength': 1,
                'loss_function': 'MultiClass',
                'eval_metric': 'MultiClass',
                'verbose': False,
                'random_seed': 42,
                'allow_writing_files': False,
                'task_type': 'CPU'  # 明确指定任务类型
            }

            # 如果提供了自定义参数，则覆盖默认值
            if custom_params:
                for key, value in custom_params.items():
                    if key in params:
                        params[key] = value
                        self.log(f"使用自定义参数 {key}: {value}")

            # 5. 创建可视化器
            self.visualizer = CatBoostVisualizer(
                params,
                feature_names=self.X_train.columns.tolist(),
                visualization_dir=self.visualization_dir
            )

            self.update_progress(40)
            self.log("开始训练CatBoost模型...")
            self.log("模型参数:")
            for key, value in params.items():
                self.log(f"  {key}: {value}")

            # 6. 创建并训练模型
            self.model = cb.CatBoostClassifier(**params)

            # 使用更简单的fit方法，避免复杂回调
            self.model.fit(
                self.X_train, self.y_train,
                eval_set=(self.X_val, self.y_val),
                verbose=100,  # 每100次迭代输出一次进度
                plot=False,
                sample_weight=sample_weights,
                cat_features=categorical_features if categorical_features else None
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
            self.log("CatBoost训练完成！")

            return True, "CatBoost模型训练完成"

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
        y_pred_proba = self.model.predict_proba(self.X_test)

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

        importance = self.model.get_feature_importance()
        features = self.X_train.columns.tolist()
        importance_df = pd.DataFrame({
            'feature': features,
            'importance': importance
        }).sort_values('importance', ascending=False)

        self.log("Top20 特征重要性排名:")
        for i, (_, row) in enumerate(importance_df.head(20).iterrows()):
            self.log(f"  {i + 1:2d}. {row['feature']}: {row['importance']:.6f}")

        # 可视化特征重要性
        plt.figure(figsize=(10, 8))
        top_features = importance_df.head(15)
        plt.barh(range(len(top_features)), top_features['importance'])
        plt.yticks(range(len(top_features)), top_features['feature'])
        plt.xlabel('Feature Importance')
        plt.title('Top 15 Feature Importance - CatBoost')
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'feature_importance.png'),
                    dpi=300, bbox_inches='tight')
        plt.close()

        self.log(f"特征重要性图已保存到: {os.path.join(self.visualization_dir, 'feature_importance.png')}")

        return importance_df

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
                f.write("CatBoost 模型评估报告\n")
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

                # 训练信息
                f.write("\n" + "=" * 40 + "\n")
                f.write("训练信息\n")
                f.write("=" * 40 + "\n")
                f.write(f"总训练轮数: {self.model.tree_count_}\n")
                f.write(f"最佳迭代轮数: {self.model.get_best_iteration()}\n")
                f.write(f"最佳验证分数: {self.model.get_best_score()}\n")

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
                    bins = [0, 0.1, 0.5, 1, 5, 10, float('inf')]
                    labels = ['0-0.1', '0.1-0.5', '0.5-1', '1-5', '5-10', '10+']
                    importance_df['bin'] = pd.cut(importance_df['importance'], bins=bins, labels=labels, right=False)
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
                f.write("CatBoost 决策树结构分析\n")
                f.write("=" * 60 + "\n\n")

                # 可视化前几棵树的结构
                f.write("决策树结构分析 (前3棵树):\n")
                f.write("-" * 50 + "\n\n")

                for i in range(min(3, self.model.tree_count_)):
                    tree_analysis = self.visualizer.visualize_tree_detailed(self.model, tree_index=i)
                    f.write(tree_analysis)
                    f.write("\n" + "=" * 50 + "\n\n")

            self.log(f"决策树结构报告已保存到: {tree_structure_path}")

            # 训练过程总结报告文件路径
            training_summary_path = os.path.join(self.visualization_dir, 'training_process_summary.txt')

            # 4. 准备训练过程总结报告
            with open(training_summary_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("CatBoost 训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                # 参数影响解释
                params_explanation = self.visualizer.explain_parameters_effect()
                f.write(params_explanation)
                f.write("\n\n")

                # 训练过程总结
                f.write("=" * 60 + "\n")
                f.write("训练过程总结\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"总训练轮数: {self.model.tree_count_}\n")
                f.write(f"最佳迭代轮数: {self.model.get_best_iteration()}\n")
                f.write(f"最终验证分数: {self.model.get_best_score()}\n\n")

                f.write("每轮迭代过程:\n")
                f.write("1. 计算梯度: 使用有序提升算法避免预测偏移\n")
                f.write("2. 构建对称树: 所有节点在同一深度使用相同分裂条件\n")
                f.write("3. 叶子值估计: 使用牛顿方法计算叶子节点值\n")
                f.write("4. 模型更新: 将新树添加到集成模型中\n")
                f.write("5. 验证评估: 计算验证集性能\n\n")

                # CatBoost 核心算法原理
                f.write("=" * 60 + "\n")
                f.write("CatBoost 核心算法原理\n")
                f.write("=" * 60 + "\n\n")

                f.write("CatBoost 核心特性:\n")
                f.write("1. 有序提升 (Ordered Boosting): 解决梯度偏差和预测偏移\n")
                f.write("2. 对称树 (Oblivious Trees): 加速预测并减少过拟合\n")
                f.write("3. 类别特征处理: 无需独热编码，基于目标统计量\n")
                f.write("4. 内置正则化: 多种技术防止过拟合\n")
                f.write("5. 数值稳定性: 对异常值鲁棒\n\n")

                f.write("有序提升算法步骤:\n")
                f.write("  1. 对训练数据进行随机排列\n")
                f.write("  2. 对于每个样本，只使用排在其前面的样本计算梯度\n")
                f.write("  3. 这避免了目标泄漏和预测偏移问题\n")

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
        try:
            # 使用更安全的方法获取训练历史
            if hasattr(self.model, 'get_evals_result'):
                evals_result = self.model.get_evals_result()
                if evals_result:
                    progress_path = self.visualizer.visualize_training_progress(evals_result)
                    self.log(f"训练进度图已保存到: {progress_path}")
                else:
                    self.log("警告: 无法获取训练进度数据")
            else:
                self.log("警告: 模型没有训练历史数据")
        except Exception as e:
            self.log(f"生成训练进度图时出错: {str(e)}")

        # 特征重要性分析
        self.log("开始生成特征重要性图...")
        try:
            importance_df = self.analyze_feature_importance()
        except Exception as e:
            self.log(f"生成特征重要性图时出错: {str(e)}")
            importance_df = None

        # 保存文本报告
        self.log("开始保存文本报告...")
        try:
            self.save_text_reports(importance_df)
        except Exception as e:
            self.log(f"保存文本报告时出错: {str(e)}")

        # 可视化前几棵决策树结构
        self.log("可视化决策树结构...")
        try:
            if hasattr(self.model, 'tree_count_'):
                tree_count = self.model.tree_count_
                for i in range(min(3, tree_count)):
                    tree_analysis = self.visualizer.visualize_tree_detailed(self.model, tree_index=i)
                    # 只记录前几行，避免日志过长
                    lines = tree_analysis.split('\n')
                    for line in lines[:5]:  # 减少显示行数
                        self.log(f"  {line}")
                    if len(lines) > 5:
                        self.log("  ... (树结构详细信息已保存)")
        except Exception as e:
            self.log(f"可视化决策树结构时出错: {str(e)}")

        # 参数影响解释
        try:
            params_explanation = self.visualizer.explain_parameters_effect()
            # 限制输出长度
            lines = params_explanation.split('\n')
            for line in lines[:20]:
                self.log(f"  {line}")
            if len(lines) > 20:
                self.log("  ... (详细信息已保存)")
        except Exception as e:
            self.log(f"解释参数影响时出错: {str(e)}")

        # 额外显示CatBoost算法原理
        self.log(f"\n{'=' * 60}")
        self.log("CatBoost 训练过程总结")
        self.log(f"{'=' * 60}")
        if hasattr(self.model, 'tree_count_'):
            self.log(f"总训练轮数: {self.model.tree_count_}")
        if hasattr(self.model, 'get_best_iteration'):
            self.log(f"最佳迭代轮数: {self.model.get_best_iteration()}")
        if hasattr(self.model, 'get_best_score'):
            self.log(f"最终验证分数: {self.model.get_best_score()}")

        self.log(f"\nCatBoost 核心优势:")
        self.log("1. 有序提升: 解决预测偏移问题")
        self.log("2. 对称树结构: 预测速度快")
        self.log("3. 类别特征处理: 无需预处理")
        self.log("4. 数值稳定性: 对异常值鲁棒")

    # ================================================================================
    # 辅助函数：转换数据类型为Python原生类型
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
        model_path = os.path.join(self.model_save_path, 'catboost_model.cbm')
        self.model.save_model(model_path)

        # 评估最终模型
        y_pred = self.model.predict(self.X_test)

        # 准备元数据
        metadata = {
            'feature_importance': dict(zip(
                self.X_train.columns.tolist(),
                self.model.get_feature_importance()
            )),
            'eval_metrics': {
                'accuracy': accuracy_score(self.y_test, y_pred),
                'f1_scores': {
                    'macro': f1_score(self.y_test, y_pred, average='macro'),
                    'micro': f1_score(self.y_test, y_pred, average='micro'),
                    'weighted': f1_score(self.y_test, y_pred, average='weighted')
                }
            },
            'model_params': self.model.get_params(),
            'training_info': {
                'tree_count': self.model.tree_count_,
                'best_iteration': self.model.get_best_iteration(),
                'best_score': self.model.get_best_score()
            }
        }

        # 转换数据类型为Python原生类型
        metadata = self._convert_numpy_types(metadata)

        # 保存元数据
        metadata_path = os.path.join(self.model_save_path, 'catboost_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.log(f"模型已保存到: {model_path}")
        self.log(f"元数据已保存到: {metadata_path}")


# ================================================================================
# 训练函数 - 供GUI调用
# ================================================================================
def train(dataset_path, model_save_path, progress_callback=None, log_callback=None, custom_params=None):
    """
    训练CatBoost模型的主函数

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
        trainer = CatBoostTrainer(
            dataset_path=dataset_path,
            model_save_path=model_save_path,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

        return trainer.train(custom_params)

    except Exception as e:
        error_msg = f"CatBoost训练失败: {str(e)}"
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
