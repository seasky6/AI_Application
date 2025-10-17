import os
import json
from datetime import datetime
from collections import defaultdict


def _add_entry_to_sample(sample, entry):
    """将条目中的参数添加到样本中"""
    key = entry.get('Key', '')
    value = entry.get('Value', '')
    if key and value:
        sample['parameters'][key] = value


def _parse_timestamp(timestamp_str):
    """解析时间戳字符串为datetime对象"""
    try:
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except:
        return datetime.min


class BaseExtractor:
    """基础特征抽取器"""
    def __init__(self):
        self.extractor_name = "BaseExtractor"
        self.description = "基础特征抽取器"

    def extract_samples_from_files(self, file_paths, output_dir):
        """从多个文件路径中提取样本 - 需要子类实现"""
        raise NotImplementedError("子类必须实现此方法")

    @staticmethod
    def validate_files(file_paths):
        """验证文件列表"""
        valid_files = []
        for file_path in file_paths:
            if os.path.exists(file_path) and file_path.lower().endswith('.json'):
                valid_files.append(file_path)
            else:
                print(f"跳过无效文件: {file_path}")
        return valid_files


class PaIssueExtractor(BaseExtractor):
    """PA问题特征抽取器"""
    def __init__(self):
        super().__init__()
        self.extractor_name = "PaIssueExtractor"
        self.description = "PA问题特征抽取器 - 提取PA相关的电压、电流、功率等特征"

        self.min_time_diff = 5  # 5秒时间差阈值
        self.target_log_ids = {'10', '16', '27', '52'}  # 提取对象log ID
        self.non_target_log_keys = {'Case', 'Event ID', 'Carrier Info', 'Invalid command'}

    def extract_samples_from_files(self, file_paths, output_dir):
        """
        从输入目录中的JSON文件抽取样本，保存到输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        accumulated_samples = []
        serial_lin_alarm_totals = defaultdict(int)    # 存储每个serial的LinAlarm总和
        serial_samples = defaultdict(list)            # 存储每个serial的所有样本

        valid_files = self.validate_files(file_paths)
        if not valid_files:
            print("没有有效的JSON文件可处理")
            return []

        for json_file in valid_files:
            print(f"处理文件: {os.path.basename(json_file)}")
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 按serial分组
                serial_groups = defaultdict(list)
                for entry in data:
                    if (entry.get('LogType') == 'elog'
                            and str(entry.get('LogID')) in self.target_log_ids
                            and str(entry.get('Key')) not in self.non_target_log_keys):
                        serial_groups[entry['Serial']].append(entry)

                # 处理每个serial的数据
                for serial, entries in serial_groups.items():
                    samples = self._extract_serial_samples(serial, entries, json_file)

                    # 只添加非空样本
                    if samples:
                        total_lin_alarm = sum(sample['temp_lin_alarm'] for sample in samples)  # 计算该serial的LinAlarm总和
                        serial_lin_alarm_totals[serial] = total_lin_alarm

                        # 存储样本以便后续更新
                        for sample in samples:
                            serial_samples[serial].append(sample)

            except Exception as e:
                print(f"处理文件 {json_file} 时出错: {str(e)}")
                continue

        # 更新所有样本的LinAlarm值为对应serial的总和
        for serial, samples in serial_samples.items():
            total_lin_alarm = serial_lin_alarm_totals[serial]
            for sample in samples:
                del sample['temp_lin_alarm']
                sample['parameters']['LinAlarm'] = str(total_lin_alarm)
                accumulated_samples.append(sample)

        print(f"总共提取到 {len(accumulated_samples)} 个有效样本")
        return accumulated_samples

    def _extract_serial_samples(self, serial, entries, source_file_path):    # source_file_path 即被解析的JSON file路径
        """处理单个serial number的日志条目"""
        samples = []      # 存储最终的有效样本
        i = 0             # 当前处理的条目索引
        n = len(entries)

        # 先按时间戳排序
        sorted_entries = sorted(entries, key=lambda x: _parse_timestamp(x['Timestamp']))

        while i < n:
            entry = sorted_entries[i]
            log_type = entry.get('LogType', '')
            log_id = str(entry.get('LogID', ''))

            # 如果不是elog，或不是LogID=10/27，跳过
            if log_type.lower() != 'elog' or log_id not in self.target_log_ids:
                i += 1
                continue

            # 开始一个新的潜在样本
            current_cluster = {
                'Serial': serial,
                'ProductName': entry['ProductName'],
                'Timestamp': entry['Timestamp'],
                'parameters': {},
                'has_log10': False,
                'has_log27': False,
                'log16_timestamps': set(),         # 记录elog16的时间戳(用于去重)
                'log52_on_count': 0,               # 记录elog52 state=ON的次数
            }

            # 处理当前条目
            self._process_entry(current_cluster, entry)

            # 检查后续条目是否属于同一簇
            j = i + 1
            while j < n:
                next_entry = sorted_entries[j]
                next_log_type = next_entry.get('LogType', '')
                next_log_id = str(next_entry.get('LogID', ''))

                # 如果不是elog或不是LogID=10/27，结束当前簇
                if next_log_type.lower() != 'elog' or next_log_id not in self.target_log_ids:
                    break

                # 检查时间差是否超过阈值
                time_diff = (_parse_timestamp(next_entry['Timestamp']) -
                             _parse_timestamp(entry['Timestamp'])).total_seconds()
                if time_diff > self.min_time_diff:
                    break

                # 处理后续条目
                self._process_entry(current_cluster, next_entry)
                j += 1

            # 检查是否同时包含LogID=10和27
            if current_cluster['has_log10'] and current_cluster['has_log27']:
                # 只保留有效字段
                sample = {
                    'Serial': current_cluster['Serial'],
                    'ProductName': current_cluster['ProductName'],
                    'Timestamp': current_cluster['Timestamp'],
                    'parameters': current_cluster['parameters'],
                    'source_file': source_file_path                 # 记录来源文件路径
                }

                # 添加LinAlarm特征，并计算当前样本的 ‘临时’ LinAlarm 值
                lin_alarm_value = len(current_cluster['log16_timestamps']) + current_cluster['log52_on_count']
                sample['temp_lin_alarm'] = lin_alarm_value   # 临时存储
                samples.append(sample)

            # 跳到下一个未处理的条目
            i = j

        return samples

    @staticmethod
    def _process_entry(cluster, entry):
        """处理单个条目，更新簇的状态"""
        log_id = str(entry.get('LogID', ''))

        if log_id == '10':
            cluster['has_log10'] = True
            _add_entry_to_sample(cluster, entry)
        elif log_id == '27':
            cluster['has_log27'] = True
            _add_entry_to_sample(cluster, entry)
        elif log_id == '16':
            # 检查slogan是否 startswith 'Lin. fault port' or 'Lin fault port'
            try:
                slogan = entry.get('Slogan', '')
                if slogan.startswith('Lin. fault port') or slogan.startswith('Lin fault port'):
                    cluster['log16_timestamps'].add(entry['Timestamp'])
            except Exception as e:
                print(f"Error processing log entry: {e}")
        elif log_id == '52':
            # 检查state是否为ON
            if entry.get('Key') == 'state' and entry.get('Value') == 'ON':
                cluster['log52_on_count'] += 1


# 其他问题的提取器实现
class DcdcIssueExtractor(BaseExtractor):
    """DCDC问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "DcdcIssueExtractor"
        self.description = "DCDC问题特征抽取器 - 提取DCDC电源相关的电压、电流、效率等特征"
        self.target_log_ids = {'11', '12', '13'}  # DCDC相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """DCDC问题特征抽取实现"""
        # 这里实现DCDC问题的特征抽取逻辑
        print("DCDC问题特征抽取器 - 功能待实现")
        return []


class DigitalIssueExtractor(BaseExtractor):
    """数字问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "DigitalIssueExtractor"
        self.description = "数字问题特征抽取器 - 提取数字电路相关的时序、逻辑状态等特征"
        self.target_log_ids = {'14', '15', '16'}  # 数字电路相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """数字问题特征抽取实现"""
        print("数字问题特征抽取器 - 功能待实现")
        return []


class DpdIssueExtractor(BaseExtractor):
    """DPD问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "DpdIssueExtractor"
        self.description = "DPD问题特征抽取器 - 提取数字预失真相关的参数和性能指标"
        self.target_log_ids = {'20', '21', '22'}  # DPD相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """DPD问题特征抽取实现"""
        print("DPD问题特征抽取器 - 功能待实现")
        return []


class FuIssueExtractor(BaseExtractor):
    """FU问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "FuIssueExtractor"
        self.description = "FU问题特征抽取器 - 提取频率单元相关的频率稳定度、相位噪声等特征"
        self.target_log_ids = {'30', '31', '32'}  # 频率单元相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """FU问题特征抽取实现"""
        print("FU问题特征抽取器 - 功能待实现")
        return []


class LtuIssueExtractor(BaseExtractor):
    """LTU问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "LtuIssueExtractor"
        self.description = "LTU问题特征抽取器 - 提取线性化技术单元相关的特征参数"
        self.target_log_ids = {'40', '41', '42'}  # LTU相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """LTU问题特征抽取实现"""
        print("LTU问题特征抽取器 - 功能待实现")
        return []


class NffIssueExtractor(BaseExtractor):
    """NFF问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "NffIssueExtractor"
        self.description = "NFF问题特征抽取器 - 提取无故障发现相关的测试和诊断特征"
        self.target_log_ids = {'50', '51', '52'}  # NFF相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """NFF问题特征抽取实现"""
        print("NFF问题特征抽取器 - 功能待实现")
        return []


class SwIssueExtractor(BaseExtractor):
    """软件问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "SwIssueExtractor"
        self.description = "软件问题特征抽取器 - 提取软件相关的日志、状态、性能指标"
        self.target_log_ids = {'60', '61', '62'}  # 软件相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """软件问题特征抽取实现"""
        print("软件问题特征抽取器 - 功能待实现")
        return []


class TrxIssueExtractor(BaseExtractor):
    """TRX问题特征抽取器"""

    def __init__(self):
        super().__init__()
        self.extractor_name = "TrxIssueExtractor"
        self.description = "TRX问题特征抽取器 - 提取收发器相关的射频性能和配置参数"
        self.target_log_ids = {'70', '71', '72'}  # TRX相关的日志ID

    def extract_samples_from_files(self, file_paths, output_dir):
        """TRX问题特征抽取实现"""
        print("TRX问题特征抽取器 - 功能待实现")
        return []
