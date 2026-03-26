import os
import json
import pandas as pd
from tools.app.services.data_processing.data_processor.labeler.labeling_methods.pattern_analysis_1 import label_method_pattern_1
from tools.app.services.data_processing.data_processor.labeler.labeling_methods.pattern_analysis_2 import label_method_pattern_2
from tools.app.services.data_processing.data_processor.labeler.labeling_methods.repair_info import label_method_repair_info


class BaseLabeler:
    """基础打标器类"""
    def __init__(self):
        self.labeler_name = "BaseLabeler"
        self.description = "基础打标器"
        self.supported_methods = []  # 支持的打标方法

    def label_samples(self, samples, labeling_method='default'):
        """对样本集进行打标 - 需要子类实现"""
        raise NotImplementedError("子类必须实现此方法")

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存样本到JSON和Excel文件 - 需要子类实现"""
        raise NotImplementedError("子类必须实现此方法")

    @staticmethod
    def validate_samples(samples):
        """验证样本数据"""
        if samples is None:
            raise ValueError("样本集不能为空！")

        if not isinstance(samples, (list, tuple)):
            raise ValueError("样本集必须是一个列表或元组")

        return True


class PaIssueLabeler(BaseLabeler):
    """PA问题打标器"""
    def __init__(self):
        super().__init__()
        self.labeler_name = "PaIssueLabeler"
        self.description = "PA问题打标器 - 使用Pattern分析和Repair Info方法标注PA状态"
        self.supported_methods = ['pattern_1', 'pattern_2', 'repair_info']

    def label_samples(self, samples, labeling_method='repair_info'):
        """
        对样本集进行打标
        """
        self.validate_samples(samples)

        if isinstance(labeling_method, str):
            labeling_method = [labeling_method]

        valid_methods = ['pattern_1', 'pattern_2', 'repair_info']
        for method in labeling_method:
            if method not in valid_methods:
                raise ValueError(f"打标方法 '{method}' 无效，请在 {valid_methods} 中选择！")

        # 应用选定的打标方法
        if 'pattern_1' in labeling_method:
            for sample in samples:
                sample['PA Status Pattern 1'] = label_method_pattern_1(sample)

        if 'pattern_2' in labeling_method:
            samples = label_method_pattern_2(samples)

        if 'repair_info' in labeling_method:
            for sample in samples:
                # 直接从样本中获取来源文件路径
                file_path = sample.get('source_file')
                # 获取状态和详细信息
                status, details = label_method_repair_info(sample, file_path)
                sample['PA Status Repair Info'] = status
                sample['Repair Info Details'] = details

        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存样本到JSON和Excel文件"""
        if isinstance(labeling_method, str):
            labeling_method = [labeling_method]

        ################################################################################################################
        # JSON路径
        ################################################################################################################
        json_path = os.path.join(output_dir, f'{base_name}_labeled.json')
        json_data = []
        for s in samples:
            sample_data = {
                'Serial': s['Serial'],
                'ProductName': s['ProductName'],
                'Timestamp': s['Timestamp'],
                'Parameters': {k: v for k, v in s['parameters'].items()}
            }

            if 'pattern_1' in labeling_method:
                sample_data['PA Status Pattern 1'] = s.get('PA Status Pattern 1', 'unknown')
            if 'pattern_2' in labeling_method:
                sample_data['PA Status Pattern 2'] = s.get('PA Status Pattern 2', 'unknown')
                sample_data['Symptoms'] = s.get('Symptoms', '')
            if 'repair_info' in labeling_method:
                sample_data['PA Status Repair Info'] = s.get('PA Status Repair Info', 'unknown')
                sample_data['Repair Info Details'] = s.get('Repair Info Details', '')

            json_data.append(sample_data)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"保存训练样本到JSON文件: {json_path}")

        ################################################################################################################
        # Excel路径
        ################################################################################################################
        excel_path = os.path.join(output_dir, f'{base_name}_labeled.xlsx')
        all_columns = set()
        for sample in samples:
            all_columns.update(sample['parameters'].keys())

        base_columns = ['Serial', 'ProductName', 'Timestamp']
        columns_order = base_columns + sorted(all_columns)

        if 'pattern_1' in labeling_method:
            columns_order.append('PA Status Pattern 1')
        if 'pattern_2' in labeling_method:
            columns_order.extend(['PA Status Pattern 2', 'Symptoms'])
        if 'repair_info' in labeling_method:
            columns_order.extend(['PA Status Repair Info', 'Repair Info Details'])

        excel_data = []
        for sample in samples:
            row = {
                'Serial': sample['Serial'],
                'ProductName': sample['ProductName'],
                'Timestamp': sample['Timestamp']
            }
            row.update(sample['parameters'])
            if 'pattern_1' in labeling_method:
                row['PA Status Pattern 1'] = sample.get('PA Status Pattern 1', 'unknown')
            if 'pattern_2' in labeling_method:
                row['PA Status Pattern 2'] = sample.get('PA Status Pattern 2', 'unknown')
                row['Symptoms'] = sample.get('Symptoms', '')
            if 'repair_info' in labeling_method:
                row['PA Status Repair Info'] = sample.get('PA Status Repair Info', 'unknown')
                row['Repair Info Details'] = sample.get('Repair Info Details', '')

            excel_data.append(row)

        df = pd.DataFrame(excel_data, columns=columns_order)
        df.to_excel(excel_path, index=False)
        print(f"保存训练样本到Excel文件: {excel_path}")


# 其他问题的打标器实现
class DcdcIssueLabeler(BaseLabeler):
    """DCDC问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "DcdcIssueLabeler"
        self.description = "DCDC问题打标器 - 使用电压稳定性分析和效率计算方法标注DCDC状态"
        self.supported_methods = ['voltage_analysis', 'efficiency_calc']

    def label_samples(self, samples, labeling_method='voltage_analysis'):
        """DCDC问题打标实现"""
        print("DCDC问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存DCDC问题样本"""
        print("DCDC问题打标器保存功能 - 功能待实现")


class DigitalIssueLabeler(BaseLabeler):
    """数字问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "DigitalIssueLabeler"
        self.description = "数字问题打标器 - 使用时序分析和逻辑状态验证方法标注数字电路状态"
        self.supported_methods = ['timing_analysis', 'logic_verification']

    def label_samples(self, samples, labeling_method='timing_analysis'):
        """数字问题打标实现"""
        print("数字问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存数字问题样本"""
        print("数字问题打标器保存功能 - 功能待实现")


class DpdIssueLabeler(BaseLabeler):
    """DPD问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "DpdIssueLabeler"
        self.description = "DPD问题打标器 - 使用线性度分析和预失真效果评估方法标注DPD状态"
        self.supported_methods = ['linearity_analysis', 'predistortion_eval']

    def label_samples(self, samples, labeling_method='linearity_analysis'):
        """DPD问题打标实现"""
        print("DPD问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存DPD问题样本"""
        print("DPD问题打标器保存功能 - 功能待实现")


class FuIssueLabeler(BaseLabeler):
    """FU问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "FuIssueLabeler"
        self.description = "FU问题打标器 - 使用频率稳定度分析和相位噪声评估方法标注频率单元状态"
        self.supported_methods = ['frequency_stability', 'phase_noise']

    def label_samples(self, samples, labeling_method='frequency_stability'):
        """FU问题打标实现"""
        print("FU问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存FU问题样本"""
        print("FU问题打标器保存功能 - 功能待实现")


class LtuIssueLabeler(BaseLabeler):
    """LTU问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "LtuIssueLabeler"
        self.description = "LTU问题打标器 - 使用线性化性能分析和参数优化方法标注LTU状态"
        self.supported_methods = ['linearization_perf', 'parameter_optimization']

    def label_samples(self, samples, labeling_method='linearization_perf'):
        """LTU问题打标实现"""
        print("LTU问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存LTU问题样本"""
        print("LTU问题打标器保存功能 - 功能待实现")


class NffIssueLabeler(BaseLabeler):
    """NFF问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "NffIssueLabeler"
        self.description = "NFF问题打标器 - 使用故障诊断和测试验证方法标注NFF状态"
        self.supported_methods = ['fault_diagnosis', 'test_verification']

    def label_samples(self, samples, labeling_method='fault_diagnosis'):
        """NFF问题打标实现"""
        print("NFF问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存NFF问题样本"""
        print("NFF问题打标器保存功能 - 功能待实现")


class SwIssueLabeler(BaseLabeler):
    """软件问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "SwIssueLabeler"
        self.description = "软件问题打标器 - 使用日志分析和性能监控方法标注软件状态"
        self.supported_methods = ['log_analysis', 'performance_monitor']

    def label_samples(self, samples, labeling_method='log_analysis'):
        """软件问题打标实现"""
        print("软件问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存软件问题样本"""
        print("软件问题打标器保存功能 - 功能待实现")


class TrxIssueLabeler(BaseLabeler):
    """TRX问题打标器"""

    def __init__(self):
        super().__init__()
        self.labeler_name = "TrxIssueLabeler"
        self.description = "TRX问题打标器 - 使用射频性能分析和配置验证方法标注收发器状态"
        self.supported_methods = ['rf_performance', 'config_verification']

    def label_samples(self, samples, labeling_method='rf_performance'):
        """TRX问题打标实现"""
        print("TRX问题打标器 - 功能待实现")
        return samples

    def save_samples(self, samples, output_dir, base_name, labeling_method=None):
        """保存TRX问题样本"""
        print("TRX问题打标器保存功能 - 功能待实现")
