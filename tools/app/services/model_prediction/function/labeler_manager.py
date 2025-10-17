import pandas as pd
import json
from tools.app.services.data_processing.data_processor.labeler.pa_issue_labeler import PaIssueLabeler


class LabelerManager:
    def __init__(self):
        self.labeler = PaIssueLabeler()
        self.labeled_df = None

    @staticmethod
    def load_sample_data(file_path):
        """加载样本数据"""
        try:
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return pd.DataFrame(data)
            elif file_path.endswith('.xlsx'):
                return pd.read_excel(file_path)
            else:
                raise ValueError("不支持的文件格式")
        except Exception as e:
            raise Exception(f"加载样本数据失败: {str(e)}")

    def execute_labeling(self, df, method):
        """执行打标"""
        try:
            # 保存已有的输出特征列
            existing_output_columns = {}
            output_columns = ['PA Status Pattern 1', 'PA Status Pattern 2', 'Symptoms', 'PA Status Repair Info']

            for col in output_columns:
                if col in df.columns:
                    existing_output_columns[col] = df[col].copy()

            # 转换为打标器格式
            samples = self.convert_to_labeler_format(df)

            # 执行打标 - 只使用pattern_1和pattern_2
            if method not in ['pattern_1', 'pattern_2']:
                raise ValueError(f"不支持的打标方法: {method}")

            labeled_samples = self.labeler.label_samples(samples, method)

            # 转换回DataFrame
            self.labeled_df = self.convert_to_dataframe(labeled_samples, method)

            # 恢复已有的输出特征列
            for col, data in existing_output_columns.items():
                # 只有当该列不是当前打标方法生成的时候才恢复
                if (method == 'pattern_1' and col != 'PA Status Pattern 1') or \
                        (method == 'pattern_2' and col not in ['PA Status Pattern 2', 'Symptoms']):
                    self.labeled_df[col] = data

            return self.labeled_df

        except Exception as e:
            raise Exception(f"打标失败: {str(e)}")

    @staticmethod
    def convert_to_labeler_format(df):
        """将DataFrame转换为打标器格式"""
        samples = []

        for idx, row in df.iterrows():
            sample = {
                'Serial': row.get('Serial', f'sample_{idx}'),
                'ProductName': row.get('ProductName', 'Unknown'),
                'Timestamp': row.get('Timestamp', ''),
                'parameters': {}
            }

            # 将所有其他列作为参数
            for col in df.columns:
                if col not in ['Serial', 'ProductName', 'Timestamp', 'PA Status Pattern 1',
                               'PA Status Pattern 2', 'Symptoms', 'PA Status Repair Info']:
                    sample['parameters'][col] = row[col]

            samples.append(sample)

        return samples

    @staticmethod
    def convert_to_dataframe(samples, method):
        """将打标结果转换回DataFrame"""
        data = []

        for sample in samples:
            row_data = {
                'Serial': sample['Serial'],
                'ProductName': sample['ProductName'],
                'Timestamp': sample['Timestamp']
            }

            # 添加参数
            row_data.update(sample['parameters'])

            # 添加打标结果
            if method == 'pattern_1' and 'PA Status Pattern 1' in sample:
                row_data['PA Status Pattern 1'] = sample['PA Status Pattern 1']
            elif method == 'pattern_2' and 'PA Status Pattern 2' in sample:
                row_data['PA Status Pattern 2'] = sample['PA Status Pattern 2']
                if 'Symptoms' in sample:
                    row_data['Symptoms'] = sample['Symptoms']

            data.append(row_data)

        return pd.DataFrame(data)
