import os
import numpy as np
import pandas as pd
import xgboost as xgb
import itertools
import json
import pickle
from datetime import datetime
from collections import defaultdict
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
from scipy.interpolate import griddata
import warnings

warnings.filterwarnings('ignore')

# 绘图相关
import matplotlib

matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns


# ======================================================================================================================
# 参数遍历配置类
# ======================================================================================================================
class ParameterConfig:
    """参数配置类，定义要遍历的参数范围和步长"""

    def __init__(self):
        # 定义参数范围和步长配置
        self.param_configs = {
            # 第1组：收敛与速率影响
            'group1': {
                'name': 'Convergence and Learning Rate',
                'params': {
                    'learning_rate': {
                        'range': [0.01, 1],
                        'step': 0.1,
                        'log_scale': True,  # 使用对数尺度
                        'values': [0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
                    },
                    'n_estimators': {
                        'range': [10, 1000],
                        'step': 100,
                        'log_scale': True,
                        'values': [10, 50, 100, 200, 300, 500, 700, 1000]
                    }
                }
            },

            # 第2组：树的复杂度影响
            'group2': {
                'name': 'Tree Complexity',
                'params': {
                    'max_depth': {
                        'range': [1, 20],
                        'step': 2,
                        'values': list(range(1, 21, 2))
                    },
                    'min_child_weight': {
                        'range': [1, 20],
                        'step': 2,
                        'values': list(range(1, 21, 2))
                    }
                }
            },

            # 第3组：泛化能力
            'group3': {
                'name': 'Generalization Ability',
                'params': {
                    'reg_alpha': {
                        'range': [0, 10],
                        'step': 2,
                        'values': [0, 1, 2, 4, 6, 8, 10]
                    },
                    'reg_lambda': {
                        'range': [0, 10],
                        'step': 2,
                        'values': [0, 1, 2, 4, 6, 8, 10]
                    },
                    'gamma': {
                        'range': [0, 10],
                        'step': 2,
                        'values': [0, 1, 2, 4, 6, 8, 10]
                    }
                }
            },

            # 第4组：随机性与扰动
            'group4': {
                'name': 'Randomness and Disturbance',
                'params': {
                    'subsample': {
                        'range': [0.1, 1],
                        'step': 0.2,
                        'values': [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
                    },
                    'colsample_bytree': {
                        'range': [0.1, 1],
                        'step': 0.2,
                        'values': [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
                    }
                }
            }
        }

        # 固定参数（不进行遍历的参数）
        self.fixed_params = {
            'objective': 'multi:softmax',
            'eval_metric': ['mlogloss', 'merror'],
            'seed': 42,
            'tree_method': 'hist',
            'early_stopping_rounds': 30,
            'num_boost_round': 500
        }

    def generate_param_combinations(self, group_key):
        """生成指定组的参数组合"""
        group_config = self.param_configs[group_key]
        param_values = {}

        for param_name, config in group_config['params'].items():
            if 'values' in config:
                param_values[param_name] = config['values']
            else:
                # 根据范围和步长生成值
                start, end = config['range']
                step = config['step']
                if config.get('log_scale', False):
                    # 对数尺度生成
                    log_start = np.log10(start)
                    log_end = np.log10(end)
                    log_values = np.linspace(log_start, log_end, int((log_end - log_start) / np.log10(1 + step)) + 1)
                    values = 10 ** log_values
                    values = np.round(values, 3)
                else:
                    # 线性尺度生成
                    values = np.arange(start, end + step, step)
                    values = np.round(values, 2)
                param_values[param_name] = values.tolist()

        # 生成所有参数组合
        param_names = list(param_values.keys())
        value_lists = [param_values[name] for name in param_names]

        combinations = []
        for values in itertools.product(*value_lists):
            param_dict = {}
            for name, value in zip(param_names, values):
                param_dict[name] = value
            combinations.append(param_dict)

        return combinations, group_config['name'], param_names


# ======================================================================================================================
# 参数遍历训练器
# ======================================================================================================================
class XGBoostParamTuner:
    """XGBoost参数遍历训练器"""

    def __init__(self, dataset_path, save_dir=None, progress_callback=None, log_callback=None):
        """
        初始化参数遍历训练器

        Args:
            dataset_path: 数据集路径
            save_dir: 结果保存目录
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
        """
        self.dataset_path = dataset_path
        self.save_dir = save_dir or os.path.join(os.getcwd(), 'xgboost_tuning_results')
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 创建保存目录
        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(os.path.join(self.save_dir, 'plots'), exist_ok=True)
        os.makedirs(os.path.join(self.save_dir, 'models'), exist_ok=True)

        # 初始化数据
        self.X_train = None
        self.y_train = None
        self.X_val = None
        self.y_val = None
        self.X_test = None
        self.y_test = None

        # 参数配置
        self.param_config = ParameterConfig()

        # 存储结果
        self.results = {
            'group1': {'data': [], 'best_params': None, 'best_score': 0},
            'group2': {'data': [], 'best_params': None, 'best_score': 0},
            'group3': {'data': [], 'best_params': None, 'best_score': 0},
            'group4': {'data': [], 'best_params': None, 'best_score': 0}
        }

    def log(self, message):
        """日志记录"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        if self.log_callback:
            self.log_callback(log_message)
        else:
            print(log_message)

    def update_progress(self, value, message=None):
        """更新进度"""
        if self.progress_callback:
            if message:
                self.progress_callback(value, message)
            else:
                self.progress_callback(value)

    def load_data(self):
        """加载数据集"""
        try:
            self.log("开始加载数据集...")

            # 加载训练数据
            train_path = os.path.join(self.dataset_path, 'train.csv')
            if not os.path.exists(train_path):
                raise FileNotFoundError(f"训练数据文件不存在: {train_path}")

            df_train = pd.read_csv(train_path)
            self.X_train = df_train.iloc[:, :-1]
            self.y_train = df_train.iloc[:, -1]

            # 确保标签为数值类型
            le = LabelEncoder()
            self.y_train = le.fit_transform(self.y_train)

            # 检查和处理数据
            self.X_train = self.X_train.replace([np.inf, -np.inf], np.nan).fillna(0)

            # 加载验证数据
            val_path = os.path.join(self.dataset_path, 'val.csv')
            if os.path.exists(val_path):
                df_val = pd.read_csv(val_path)
                self.X_val = df_val.iloc[:, :-1]
                self.y_val = df_val.iloc[:, -1]
                self.y_val = le.transform(self.y_val)
                self.X_val = self.X_val.replace([np.inf, -np.inf], np.nan).fillna(0)
            else:
                self.log("警告：验证数据不存在，将使用训练数据分割")
                from sklearn.model_selection import train_test_split
                self.X_train, self.X_val, self.y_train, self.y_val = train_test_split(
                    self.X_train, self.y_train, test_size=0.2, random_state=42
                )

            # 加载测试数据
            test_path = os.path.join(self.dataset_path, 'test.csv')
            if os.path.exists(test_path):
                df_test = pd.read_csv(test_path)
                self.X_test = df_test.iloc[:, :-1]
                self.y_test = df_test.iloc[:, -1]
                self.y_test = le.transform(self.y_test)
                self.X_test = self.X_test.replace([np.inf, -np.inf], np.nan).fillna(0)
            else:
                self.log("警告：测试数据不存在，将使用验证数据作为测试数据")
                self.X_test, self.y_test = self.X_val, self.y_val

            self.log(f"数据加载完成: 训练集={len(self.X_train)}, 验证集={len(self.X_val)}, 测试集={len(self.X_test)}")
            self.log(f"特征数量: {self.X_train.shape[1]}, 类别数: {len(np.unique(self.y_train))}")

            return True

        except Exception as e:
            self.log(f"加载数据失败: {str(e)}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            return False

    def calculate_class_weights(self, y):
        """计算类别权重"""
        from collections import Counter
        class_counts = Counter(y)
        total_samples = len(y)
        n_classes = len(class_counts)

        weights = {
            cls: total_samples / (n_classes * count)
            for cls, count in class_counts.items()
        }

        self.log(f"类别分布: {dict(class_counts)}")
        self.log(f"类别权重: {weights}")

        return weights

    def train_with_params(self, params, group_name, iteration, total_iterations):
        """使用指定参数训练模型"""
        try:
            # 合并固定参数和当前参数
            full_params = self.param_config.fixed_params.copy()
            full_params.update(params)

            # 设置类别数
            full_params['num_class'] = len(np.unique(self.y_train))

            # 计算类别权重
            class_weights = self.calculate_class_weights(self.y_train)
            sample_weights = np.array([class_weights[y] for y in self.y_train])

            # 转换为DMatrix
            dtrain = xgb.DMatrix(self.X_train, label=self.y_train, weight=sample_weights)
            dval = xgb.DMatrix(self.X_val, label=self.y_val)
            dtest = xgb.DMatrix(self.X_test, label=self.y_test)

            # 训练模型
            self.log(f"训练模型 [{iteration}/{total_iterations}]: {params}")

            model = xgb.train(
                full_params,
                dtrain,
                num_boost_round=full_params['num_boost_round'],
                evals=[(dtrain, 'train'), (dval, 'val')],
                early_stopping_rounds=full_params['early_stopping_rounds'],
                verbose_eval=False
            )

            # 评估模型
            y_pred = model.predict(dtest)
            accuracy = accuracy_score(self.y_test, y_pred)
            f1 = f1_score(self.y_test, y_pred, average='macro')

            # 获取最佳迭代次数
            best_iteration = getattr(model, 'best_iteration', full_params['num_boost_round'])

            result = {
                'params': params.copy(),
                'accuracy': float(accuracy),
                'f1_score': float(f1),
                'best_iteration': int(best_iteration),
                'group': group_name
            }

            self.log(f"  结果: accuracy={accuracy:.4f}, f1_score={f1:.4f}, best_iteration={best_iteration}")

            return result

        except Exception as e:
            self.log(f"  训练失败: {str(e)}")
            return None

    def tune_group(self, group_key):
        """遍历调参指定组"""
        self.log(f"\n{'=' * 60}")
        self.log(f"开始调参组: {group_key}")
        self.log(f"{'=' * 60}")

        # 生成参数组合
        combinations, group_name, param_names = self.param_config.generate_param_combinations(group_key)

        self.log(f"参数组: {group_name}")
        self.log(f"参数: {param_names}")
        self.log(f"总参数组合数: {len(combinations)}")

        group_results = []

        # 遍历所有参数组合
        for i, params in enumerate(combinations, 1):
            # 更新进度
            progress = int((i / len(combinations)) * 100)
            self.update_progress(progress, f"调参组 {group_name}: {i}/{len(combinations)}")

            # 训练模型
            result = self.train_with_params(params, group_name, i, len(combinations))

            if result:
                group_results.append(result)

        # 存储结果
        self.results[group_key]['data'] = group_results

        # 找到最佳参数
        if group_results:
            # 按f1_score排序
            group_results_sorted = sorted(group_results, key=lambda x: x['f1_score'], reverse=True)
            best_result = group_results_sorted[0]

            self.results[group_key]['best_params'] = best_result['params']
            self.results[group_key]['best_score'] = best_result['f1_score']

            self.log(f"\n最佳参数组合:")
            for param_name, param_value in best_result['params'].items():
                self.log(f"  {param_name}: {param_value}")
            self.log(f"最佳f1_score: {best_result['f1_score']:.4f}")
            self.log(f"最佳accuracy: {best_result['accuracy']:.4f}")

        return group_results

    def create_3d_plot(self, group_key, score_type='f1_score'):
        """创建三维分布图（仅适用于2参数组）"""
        group_results = self.results[group_key]['data']
        if not group_results or len(group_results[0]['params']) != 2:
            self.log(f"组 {group_key} 参数数量不为2，跳过三维图绘制")
            return

        # 提取数据
        param_names = list(group_results[0]['params'].keys())
        x_values = []
        y_values = []
        z_values = []

        for result in group_results:
            params = result['params']
            x_values.append(params[param_names[0]])
            y_values.append(params[param_names[1]])
            if score_type == 'f1_score':
                z_values.append(result['f1_score'])
            else:
                z_values.append(result['accuracy'])

        # 转换为numpy数组
        x = np.array(x_values)
        y = np.array(y_values)
        z = np.array(z_values)

        # 创建网格数据用于平滑曲面
        xi = np.linspace(min(x), max(x), 50)
        yi = np.linspace(min(y), max(y), 50)
        xi, yi = np.meshgrid(xi, yi)

        # 插值得到网格上的z值
        zi = griddata((x, y), z, (xi, yi), method='cubic')

        # 创建三维图
        fig = plt.figure(figsize=(14, 6))

        # 子图1：三维曲面图
        ax1 = fig.add_subplot(121, projection='3d')
        surf = ax1.plot_surface(xi, yi, zi, cmap='viridis', alpha=0.8, edgecolor='none')

        # 添加散点图显示实际数据点
        ax1.scatter(x, y, z, c='red', s=50, alpha=0.8, edgecolor='black', linewidth=1)

        ax1.set_xlabel(param_names[0], fontsize=12)
        ax1.set_ylabel(param_names[1], fontsize=12)
        ax1.set_zlabel(score_type, fontsize=12)
        ax1.set_title(f'{self.param_config.param_configs[group_key]["name"]} - {score_type} 3D Distribution', fontsize=14)

        # 添加颜色条
        fig.colorbar(surf, ax=ax1, shrink=0.5, aspect=10)

        # 子图2：等高线图
        ax2 = fig.add_subplot(122)
        contour = ax2.contourf(xi, yi, zi, levels=20, cmap='viridis')
        ax2.scatter(x, y, c=z, s=50, cmap='viridis', edgecolor='black', linewidth=1)

        # 标记最佳点
        best_idx = np.argmax(z)
        ax2.scatter(x[best_idx], y[best_idx], c='red', s=100, marker='*', edgecolor='black', linewidth=2,
                    label=f'Optimum Point ({score_type}={z[best_idx]:.3f})')

        ax2.set_xlabel(param_names[0], fontsize=12)
        ax2.set_ylabel(param_names[1], fontsize=12)
        ax2.set_title(f'{self.param_config.param_configs[group_key]["name"]} - {score_type} Contour line', fontsize=14)
        ax2.legend()

        # 添加颜色条
        fig.colorbar(contour, ax=ax2, shrink=0.8, aspect=10)

        plt.tight_layout()

        # 保存图像
        plot_path = os.path.join(self.save_dir, 'plots', f'{group_key}_{score_type}_3d.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.log(f"三维图已保存: {plot_path}")

        return plot_path

    def create_group3_visualization(self):
        """为第3组（3参数）创建可视化"""
        group_results = self.results['group3']['data']
        if not group_results:
            return

        # 提取数据
        param_names = list(group_results[0]['params'].keys())

        # 创建多个2D投影图
        fig = plt.figure(figsize=(16, 12))

        # 获取最佳结果
        best_result = sorted(group_results, key=lambda x: x['f1_score'], reverse=True)[0]

        # 创建6个子图：3个参数的f1_score分布
        for i, param_name in enumerate(param_names):
            # 提取当前参数和对应的f1_score
            param_values = [r['params'][param_name] for r in group_results]
            f1_scores = [r['f1_score'] for r in group_results]

            # 按照当前参数值排序
            sorted_idx = np.argsort(param_values)
            param_values_sorted = np.array(param_values)[sorted_idx]
            f1_scores_sorted = np.array(f1_scores)[sorted_idx]

            # 绘制折线图
            ax = fig.add_subplot(2, 3, i + 1)
            ax.plot(param_values_sorted, f1_scores_sorted, 'b-o', linewidth=2, markersize=6)
            ax.axvline(x=best_result['params'][param_name], color='r', linestyle='--', linewidth=2,
                       label=f'Optimum Value={best_result["params"][param_name]}')

            ax.set_xlabel(param_name, fontsize=12)
            ax.set_ylabel('F1 Score', fontsize=12)
            ax.set_title(f'F1 Score vs {param_name}', fontsize=14)
            ax.grid(True, alpha=0.3)
            ax.legend()

        # 创建散点图矩阵
        ax_matrix = fig.add_subplot(2, 3, 4, projection='3d')

        # 提取三个参数的值
        x = [r['params'][param_names[0]] for r in group_results]
        y = [r['params'][param_names[1]] for r in group_results]
        z = [r['params'][param_names[2]] for r in group_results]
        colors = [r['f1_score'] for r in group_results]

        scatter = ax_matrix.scatter(x, y, z, c=colors, cmap='viridis', s=50, alpha=0.8)

        # 标记最佳点
        ax_matrix.scatter(best_result['params'][param_names[0]],
                          best_result['params'][param_names[1]],
                          best_result['params'][param_names[2]],
                          c='red', s=200, marker='*', edgecolor='black', linewidth=2)

        ax_matrix.set_xlabel(param_names[0], fontsize=12)
        ax_matrix.set_ylabel(param_names[1], fontsize=12)
        ax_matrix.set_zlabel(param_names[2], fontsize=12)
        ax_matrix.set_title('3D - F1 Score Distribution', fontsize=14)

        # 添加颜色条
        fig.colorbar(scatter, ax=ax_matrix, shrink=0.6, aspect=10, label='F1 Score')

        # 创建热力图（reg_alpha vs reg_lambda，gamma取最佳值）
        ax_heatmap = fig.add_subplot(2, 3, 5)

        # 找到最佳gamma值
        best_gamma = best_result['params']['gamma']

        # 提取reg_alpha和reg_lambda的值及其对应的f1_score
        alpha_values = sorted(set([r['params']['reg_alpha'] for r in group_results]))
        lambda_values = sorted(set([r['params']['reg_lambda'] for r in group_results]))

        # 创建矩阵
        heatmap_data = np.zeros((len(lambda_values), len(alpha_values)))

        for r in group_results:
            if abs(r['params']['gamma'] - best_gamma) < 0.1:  # 近似最佳gamma
                alpha_idx = alpha_values.index(r['params']['reg_alpha'])
                lambda_idx = lambda_values.index(r['params']['reg_lambda'])
                heatmap_data[lambda_idx, alpha_idx] = r['f1_score']

        # 绘制热力图
        im = ax_heatmap.imshow(heatmap_data, cmap='viridis', aspect='auto', origin='lower')
        ax_heatmap.set_xlabel('reg_alpha', fontsize=12)
        ax_heatmap.set_ylabel('reg_lambda', fontsize=12)
        ax_heatmap.set_title(f'reg_alpha vs reg_lambda (gamma≈{best_gamma})', fontsize=14)

        # 设置刻度标签
        ax_heatmap.set_xticks(range(len(alpha_values)))
        ax_heatmap.set_xticklabels(alpha_values)
        ax_heatmap.set_yticks(range(len(lambda_values)))
        ax_heatmap.set_yticklabels(lambda_values)

        # 添加颜色条
        fig.colorbar(im, ax=ax_heatmap, shrink=0.8, aspect=10, label='F1 Score')

        # 最佳参数信息
        ax_info = fig.add_subplot(2, 3, 6)
        ax_info.axis('off')

        info_text = f"Optimal Parameter Combination:\n"
        info_text += f"reg_alpha = {best_result['params']['reg_alpha']}\n"
        info_text += f"reg_lambda = {best_result['params']['reg_lambda']}\n"
        info_text += f"gamma = {best_result['params']['gamma']}\n\n"
        info_text += f"Top Score:\n"
        info_text += f"F1 Score = {best_result['f1_score']:.4f}\n"
        info_text += f"Accuracy = {best_result['accuracy']:.4f}"

        ax_info.text(0.1, 0.5, info_text, fontsize=14, verticalalignment='center',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.suptitle('Group 3 Parameter Tuning - Generalization Ability', fontsize=16, fontweight='bold')
        plt.tight_layout()

        # 保存图像
        plot_path = os.path.join(self.save_dir, 'plots', 'group3_visualization.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.log(f"第3组可视化图已保存: {plot_path}")

        return plot_path

    def run_tuning(self):
        """运行完整的参数调优流程"""
        try:
            self.log("=" * 70)
            self.log("开始XGBoost参数调优")
            self.log("=" * 70)

            # 1. 加载数据
            self.update_progress(5, "加载数据...")
            if not self.load_data():
                return False

            # 2. 遍历所有参数组
            total_groups = 4
            for i, group_key in enumerate(['group1', 'group2', 'group3', 'group4']):
                self.update_progress(10 + i * 20, f"调参组 {i + 1}/{total_groups}...")
                self.tune_group(group_key)

            # 3. 创建可视化
            self.update_progress(90, "创建可视化...")

            # 为前两组和第四组创建三维图
            for group_key in ['group1', 'group2', 'group4']:
                # 创建f1_score三维图
                self.create_3d_plot(group_key, 'f1_score')
                # 创建accuracy三维图
                self.create_3d_plot(group_key, 'accuracy')

            # 为第三组创建特殊可视化
            self.create_group3_visualization()

            # 4. 保存结果
            self.update_progress(95, "保存结果...")
            self.save_results()

            # 5. 生成总结报告
            self.update_progress(98, "生成总结报告...")
            self.generate_summary_report()

            self.update_progress(100, "参数调优完成！")
            self.log("\n" + "=" * 70)
            self.log("参数调优完成！")
            self.log("=" * 70)

            return True

        except Exception as e:
            self.log(f"参数调优过程出错: {str(e)}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            return False

    def save_results(self):
        """保存调优结果"""
        try:
            # 保存结果为JSON
            results_path = os.path.join(self.save_dir, 'tuning_results.json')

            # 转换结果为可序列化格式
            serializable_results = {}
            for group_key, group_data in self.results.items():
                serializable_results[group_key] = {
                    'best_params': group_data['best_params'],
                    'best_score': group_data['best_score'],
                    'data_count': len(group_data['data'])
                }

            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)

            # 保存详细结果
            detailed_results_path = os.path.join(self.save_dir, 'detailed_results.pkl')
            with open(detailed_results_path, 'wb') as f:
                pickle.dump(self.results, f)

            self.log(f"调优结果已保存: {results_path}")
            self.log(f"详细结果已保存: {detailed_results_path}")

            return True

        except Exception as e:
            self.log(f"保存结果失败: {str(e)}")
            return False

    def generate_summary_report(self):
        """生成总结报告"""
        try:
            report_path = os.path.join(self.save_dir, 'tuning_summary_report.txt')

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("XGBoost 参数调优总结报告\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"数据集路径: {self.dataset_path}\n")
                f.write(f"保存目录: {self.save_dir}\n\n")

                f.write("数据集统计:\n")
                f.write(f"  训练集样本数: {len(self.X_train)}\n")
                f.write(f"  验证集样本数: {len(self.X_val)}\n")
                f.write(f"  测试集样本数: {len(self.X_test)}\n")
                f.write(f"  特征数量: {self.X_train.shape[1]}\n")
                f.write(f"  类别数量: {len(np.unique(self.y_train))}\n\n")

                f.write("=" * 80 + "\n")
                f.write("各参数组最佳结果\n")
                f.write("=" * 80 + "\n\n")

                # 各组最佳结果
                for group_key in ['group1', 'group2', 'group3', 'group4']:
                    group_data = self.results[group_key]
                    group_name = self.param_config.param_configs[group_key]['name']

                    f.write(f"{group_name} (第{group_key[-1]}组):\n")

                    if group_data['data']:
                        # 按F1 Score排序
                        sorted_by_f1 = sorted(group_data['data'], key=lambda x: x['f1_score'], reverse=True)
                        best_by_f1 = sorted_by_f1[0]

                        # 按Accuracy排序
                        sorted_by_accuracy = sorted(group_data['data'], key=lambda x: x['accuracy'], reverse=True)
                        best_by_accuracy = sorted_by_accuracy[0]

                        f.write(f"  基于F1 Score的最佳结果:\n")
                        f.write(f"    F1 Score: {best_by_f1['f1_score']:.4f}\n")
                        f.write(f"    Accuracy: {best_by_f1['accuracy']:.4f}\n")
                        f.write(f"    最佳迭代次数: {best_by_f1['best_iteration']}\n")
                        f.write(f"    参数:\n")
                        for param_name, param_value in best_by_f1['params'].items():
                            f.write(f"      {param_name}: {param_value}\n")

                        f.write(f"\n  基于Accuracy的最佳结果:\n")
                        f.write(f"    Accuracy: {best_by_accuracy['accuracy']:.4f}\n")
                        f.write(f"    F1 Score: {best_by_accuracy['f1_score']:.4f}\n")
                        f.write(f"    最佳迭代次数: {best_by_accuracy['best_iteration']}\n")

                        # 检查是否为同一组参数
                        if best_by_f1['params'] == best_by_accuracy['params']:
                            f.write(f"    参数: (与F1 Score最佳结果相同)\n")
                        else:
                            f.write(f"    参数:\n")
                            for param_name, param_value in best_by_accuracy['params'].items():
                                f.write(f"      {param_name}: {param_value}\n")

                        f.write(f"\n  总参数组合数: {len(group_data['data'])}\n")

                        # 记录到结果对象中
                        self.results[group_key]['best_f1_params'] = best_by_f1['params']
                        self.results[group_key]['best_f1_score'] = best_by_f1['f1_score']
                        self.results[group_key]['best_f1_accuracy'] = best_by_f1['accuracy']
                        self.results[group_key]['best_accuracy_params'] = best_by_accuracy['params']
                        self.results[group_key]['best_accuracy_score'] = best_by_accuracy['accuracy']
                        self.results[group_key]['best_accuracy_f1'] = best_by_accuracy['f1_score']
                    else:
                        f.write(f"  无调优结果\n")

                    f.write(f"\n")

                # 总体最佳结果
                f.write("=" * 80 + "\n")
                f.write("总体最佳结果\n")
                f.write("=" * 80 + "\n\n")

                # 找出所有组中的最佳结果（基于F1 Score）
                all_best_by_f1 = []
                all_best_by_accuracy = []

                for group_key, group_data in self.results.items():
                    if group_data['data']:
                        # 基于F1 Score
                        best_f1_in_group = max(group_data['data'], key=lambda x: x['f1_score'])
                        all_best_by_f1.append(best_f1_in_group)

                        # 基于Accuracy
                        best_accuracy_in_group = max(group_data['data'], key=lambda x: x['accuracy'])
                        all_best_by_accuracy.append(best_accuracy_in_group)

                if all_best_by_f1:
                    overall_best_f1 = max(all_best_by_f1, key=lambda x: x['f1_score'])
                    overall_best_accuracy = max(all_best_by_accuracy, key=lambda x: x['accuracy'])

                    f.write("基于F1 Score的总体最佳结果:\n")
                    f.write(f"  最佳F1 Score: {overall_best_f1['f1_score']:.4f}\n")
                    f.write(f"  对应的Accuracy: {overall_best_f1['accuracy']:.4f}\n")
                    f.write(f"  来自参数组: {overall_best_f1['group']}\n")
                    f.write(f"  最佳迭代次数: {overall_best_f1['best_iteration']}\n")
                    f.write(f"  参数组合:\n")
                    for param_name, param_value in overall_best_f1['params'].items():
                        f.write(f"    {param_name}: {param_value}\n")

                    f.write(f"\n基于Accuracy的总体最佳结果:\n")
                    f.write(f"  最佳Accuracy: {overall_best_accuracy['accuracy']:.4f}\n")
                    f.write(f"  对应的F1 Score: {overall_best_accuracy['f1_score']:.4f}\n")
                    f.write(f"  来自参数组: {overall_best_accuracy['group']}\n")
                    f.write(f"  最佳迭代次数: {overall_best_accuracy['best_iteration']}\n")

                    # 检查是否为同一组参数
                    if overall_best_f1['params'] == overall_best_accuracy['params']:
                        f.write(f"  参数组合: (与F1 Score最佳结果相同)\n")
                    else:
                        f.write(f"  参数组合:\n")
                        for param_name, param_value in overall_best_accuracy['params'].items():
                            f.write(f"    {param_name}: {param_value}\n")

                    # 综合最佳结果（平衡F1 Score和Accuracy）
                    f.write(f"\n综合最佳结果 (平衡F1 Score和Accuracy):\n")

                    # 计算综合评分：使用F1 Score和Accuracy的加权平均
                    # 这里使用简单的平均值，可以根据需要调整权重
                    for result in all_best_by_f1:
                        result['composite_score'] = (result['f1_score'] + result['accuracy']) / 2

                    overall_best_composite = max(all_best_by_f1, key=lambda x: x['composite_score'])

                    f.write(f"  综合评分: {overall_best_composite['composite_score']:.4f}\n")
                    f.write(f"  (F1 Score: {overall_best_composite['f1_score']:.4f}, ")
                    f.write(f"Accuracy: {overall_best_composite['accuracy']:.4f})\n")
                    f.write(f"  来自参数组: {overall_best_composite['group']}\n")
                    f.write(f"  参数组合:\n")
                    for param_name, param_value in overall_best_composite['params'].items():
                        f.write(f"    {param_name}: {param_value}\n")

                # 推荐参数配置
                f.write("\n" + "=" * 80 + "\n")
                f.write("推荐参数配置\n")
                f.write("=" * 80 + "\n\n")

                # 推荐基于F1 Score的最佳参数
                f.write("推荐配置1 (基于F1 Score最优):\n")
                if 'best_f1_params' in self.results['group1']:
                    recommended_params_f1 = self.param_config.fixed_params.copy()
                    recommended_params_f1['num_class'] = len(np.unique(self.y_train))

                    # 合并所有组的最佳F1参数
                    for group_key in ['group1', 'group2', 'group3', 'group4']:
                        if 'best_f1_params' in self.results[group_key]:
                            recommended_params_f1.update(self.results[group_key]['best_f1_params'])

                    for param_name, param_value in recommended_params_f1.items():
                        if param_name not in ['num_class']:  # 跳过已经显示的参数
                            f.write(f"  {param_name}: {param_value}\n")

                    f.write(f"  num_class: {len(np.unique(self.y_train))}\n")

                    # 预测性能
                    f.write(f"  预期性能:\n")
                    f.write(f"    F1 Score: {overall_best_f1['f1_score']:.4f}\n")
                    f.write(f"    Accuracy: {overall_best_f1['accuracy']:.4f}\n")

                f.write(f"\n推荐配置2 (基于Accuracy最优):\n")
                if 'best_accuracy_params' in self.results['group1']:
                    recommended_params_acc = self.param_config.fixed_params.copy()
                    recommended_params_acc['num_class'] = len(np.unique(self.y_train))

                    # 合并所有组的最佳Accuracy参数
                    for group_key in ['group1', 'group2', 'group3', 'group4']:
                        if 'best_accuracy_params' in self.results[group_key]:
                            recommended_params_acc.update(self.results[group_key]['best_accuracy_params'])

                    for param_name, param_value in recommended_params_acc.items():
                        if param_name not in ['num_class']:  # 跳过已经显示的参数
                            f.write(f"  {param_name}: {param_value}\n")

                    f.write(f"  num_class: {len(np.unique(self.y_train))}\n")

                    # 预测性能
                    f.write(f"  预期性能:\n")
                    f.write(f"    Accuracy: {overall_best_accuracy['accuracy']:.4f}\n")
                    f.write(f"    F1 Score: {overall_best_accuracy['f1_score']:.4f}\n")

                f.write(f"\n推荐配置3 (综合最优):\n")
                if overall_best_composite:
                    recommended_params_composite = self.param_config.fixed_params.copy()
                    recommended_params_composite['num_class'] = len(np.unique(self.y_train))
                    recommended_params_composite.update(overall_best_composite['params'])

                    for param_name, param_value in recommended_params_composite.items():
                        if param_name not in ['num_class']:  # 跳过已经显示的参数
                            f.write(f"  {param_name}: {param_value}\n")

                    f.write(f"  num_class: {len(np.unique(self.y_train))}\n")

                    # 预测性能
                    f.write(f"  预期性能:\n")
                    f.write(f"    综合评分: {overall_best_composite['composite_score']:.4f}\n")
                    f.write(f"    F1 Score: {overall_best_composite['f1_score']:.4f}\n")
                    f.write(f"    Accuracy: {overall_best_composite['accuracy']:.4f}\n")

                # 统计信息
                f.write("\n" + "=" * 80 + "\n")
                f.write("统计信息\n")
                f.write("=" * 80 + "\n\n")

                total_combinations = 0
                f1_scores_all = []
                accuracies_all = []

                for group_key in ['group1', 'group2', 'group3', 'group4']:
                    group_data = self.results[group_key]
                    if group_data['data']:
                        total_combinations += len(group_data['data'])
                        f1_scores_all.extend([r['f1_score'] for r in group_data['data']])
                        accuracies_all.extend([r['accuracy'] for r in group_data['data']])

                if f1_scores_all and accuracies_all:
                    f.write(f"总参数组合数: {total_combinations}\n")
                    f.write(f"F1 Score 统计:\n")
                    f.write(f"  平均值: {np.mean(f1_scores_all):.4f}\n")
                    f.write(f"  标准差: {np.std(f1_scores_all):.4f}\n")
                    f.write(f"  最小值: {np.min(f1_scores_all):.4f}\n")
                    f.write(f"  最大值: {np.max(f1_scores_all):.4f}\n")
                    f.write(f"  中位数: {np.median(f1_scores_all):.4f}\n")

                    f.write(f"\nAccuracy 统计:\n")
                    f.write(f"  平均值: {np.mean(accuracies_all):.4f}\n")
                    f.write(f"  标准差: {np.std(accuracies_all):.4f}\n")
                    f.write(f"  最小值: {np.min(accuracies_all):.4f}\n")
                    f.write(f"  最大值: {np.max(accuracies_all):.4f}\n")
                    f.write(f"  中位数: {np.median(accuracies_all):.4f}\n")

                    # F1 Score和Accuracy的相关性
                    if len(f1_scores_all) > 1:
                        correlation = np.corrcoef(f1_scores_all, accuracies_all)[0, 1]
                        f.write(f"\nF1 Score与Accuracy的相关系数: {correlation:.4f}\n")

                        if correlation > 0.7:
                            f.write("  说明: F1 Score和Accuracy高度正相关\n")
                        elif correlation > 0.3:
                            f.write("  说明: F1 Score和Accuracy中度正相关\n")
                        else:
                            f.write("  说明: F1 Score和Accuracy相关性较弱\n")

            self.log(f"总结报告已保存: {report_path}")

            # 在控制台也输出关键信息
            self.log("\n" + "=" * 80)
            self.log("参数调优关键结果")
            self.log("=" * 80)

            for group_key in ['group1', 'group2', 'group3', 'group4']:
                group_data = self.results[group_key]
                group_name = self.param_config.param_configs[group_key]['name']

                if group_data['data']:
                    self.log(f"\n{group_name}:")

                    # 基于F1 Score的最佳结果
                    best_f1 = max(group_data['data'], key=lambda x: x['f1_score'])
                    self.log(f"  最佳F1 Score: {best_f1['f1_score']:.4f}")
                    self.log(f"    对应Accuracy: {best_f1['accuracy']:.4f}")

                    # 基于Accuracy的最佳结果
                    best_acc = max(group_data['data'], key=lambda x: x['accuracy'])
                    self.log(f"  最佳Accuracy: {best_acc['accuracy']:.4f}")
                    self.log(f"    对应F1 Score: {best_acc['f1_score']:.4f}")

                    if best_f1['params'] == best_acc['params']:
                        self.log(f"  最佳参数: {best_f1['params']}")
                    else:
                        self.log(f"  最佳F1参数: {best_f1['params']}")
                        self.log(f"  最佳Accuracy参数: {best_acc['params']}")

            # 总体最佳结果
            if all_best_by_f1 and all_best_by_accuracy:
                overall_best_f1 = max(all_best_by_f1, key=lambda x: x['f1_score'])
                overall_best_accuracy = max(all_best_by_accuracy, key=lambda x: x['accuracy'])

                self.log("\n" + "-" * 40)
                self.log("总体最佳结果:")
                self.log(f"  最佳F1 Score: {overall_best_f1['f1_score']:.4f}")
                self.log(f"    参数组: {overall_best_f1['group']}")
                self.log(f"    参数: {overall_best_f1['params']}")

                self.log(f"\n  最佳Accuracy: {overall_best_accuracy['accuracy']:.4f}")
                self.log(f"    参数组: {overall_best_accuracy['group']}")
                self.log(f"    参数: {overall_best_accuracy['params']}")

            return True

        except Exception as e:
            self.log(f"生成总结报告失败: {str(e)}")
            return False


# ======================================================================================================================
# 主函数 - 供GUI调用
# ======================================================================================================================
def tune_parameters(dataset_path, save_dir=None, progress_callback=None, log_callback=None):
    """
    参数调优主函数

    Args:
        dataset_path: 数据集目录路径
        save_dir: 结果保存目录
        progress_callback: 进度回调函数
        log_callback: 日志回调函数

    Returns:
        tuple: (success, message, results_dir)
    """
    try:
        tuner = XGBoostParamTuner(
            dataset_path=dataset_path,
            save_dir=save_dir,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

        success = tuner.run_tuning()

        if success:
            return True, "参数调优完成", tuner.save_dir
        else:
            return False, "参数调优失败", None

    except Exception as e:
        error_msg = f"参数调优过程出错: {str(e)}"
        if log_callback:
            log_callback(error_msg)
        return False, error_msg, None


# ======================================================================================================================
# 直接运行时的测试代码
# ======================================================================================================================
if __name__ == '__main__':
    # 测试代码
    print("XGBoost 参数调优工具")
    print("=" * 50)

    # 获取用户输入
    dataset_path = input("请输入数据集路径（包含train.csv, val.csv, test.csv）: ").strip()
    save_dir = input("请输入结果保存路径（按Enter使用默认路径）: ").strip()

    if not dataset_path:
        print("错误：数据集路径不能为空")
        exit(1)

    if not save_dir:
        save_dir = None


    # 简单的进度回调函数
    def simple_progress_callback(value, message=None):
        if message:
            print(f"进度 {value}%: {message}")
        else:
            print(f"进度: {value}%")


    # 简单的日志回调函数
    def simple_log_callback(message):
        print(message)


    # 运行参数调优
    print("\n开始参数调优...")
    success, message, results_dir = tune_parameters(
        dataset_path=dataset_path,
        save_dir=save_dir,
        progress_callback=simple_progress_callback,
        log_callback=simple_log_callback
    )

    if success:
        print(f"\n调优成功！结果保存在: {results_dir}")

        # 显示最佳结果摘要
        summary_path = os.path.join(results_dir, 'tuning_summary_report.txt')
        if os.path.exists(summary_path):
            print("\n最佳结果摘要:")
            print("-" * 50)
            with open(summary_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 只显示关键部分
                for line in lines:
                    if "总体最佳F1 Score" in line or "推荐使用的参数配置" in line or "=" in line:
                        print(line.strip())
    else:
        print(f"\n调优失败: {message}")
