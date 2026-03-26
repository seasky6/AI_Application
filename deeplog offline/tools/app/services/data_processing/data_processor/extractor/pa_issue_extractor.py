import os
import json
from datetime import datetime
from collections import defaultdict


def _add_entry_to_sample(sample, entry):
    """将条目中的参数添加到样本中"""
    key = entry.get('Key', '')
    value = entry.get('Value', '')
    if key and value is not None:  # 允许值为0
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
        # 只过滤明确不需要的键
        self.non_target_log_keys = {'Case', 'Event ID', 'Carrier Info', 'Invalid command'}

    def extract_samples_from_files(self, file_paths, output_dir):
        """
        从输入目录中的JSON文件抽取样本，保存到输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        accumulated_samples = []
        serial_lin_alarm_totals = defaultdict(int)  # 存储每个serial的LinAlarm总和
        serial_samples = defaultdict(list)  # 存储每个serial的所有样本

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
                    if entry.get('LogType') == 'elog' and str(entry.get('LogID')) in self.target_log_ids:
                        # 只过滤明确不需要的键
                        key = str(entry.get('Key', ''))
                        if key not in self.non_target_log_keys:
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

    def _extract_serial_samples(self, serial, entries, source_file_path):
        """处理单个serial number的日志条目 - 升级版：支持多对配对"""
        samples = []  # 存储最终的有效样本

        # 先按时间戳排序
        sorted_entries = sorted(entries, key=lambda x: _parse_timestamp(x['Timestamp']))

        # 按时间窗口分组
        time_windows = self._group_entries_by_time_window(sorted_entries)

        # 处理每个时间窗口
        for window_entries in time_windows:
            window_samples = self._process_time_window(serial, window_entries, source_file_path)
            samples.extend(window_samples)

        return samples

    def _group_entries_by_time_window(self, sorted_entries):
        """将条目按5秒时间窗口分组"""
        if not sorted_entries:
            return []

        time_windows = []
        current_window = []
        base_time = _parse_timestamp(sorted_entries[0]['Timestamp'])

        for entry in sorted_entries:
            entry_time = _parse_timestamp(entry['Timestamp'])
            time_diff = (entry_time - base_time).total_seconds()

            if time_diff <= self.min_time_diff:
                current_window.append(entry)
            else:
                if current_window:
                    time_windows.append(current_window)
                current_window = [entry]
                base_time = entry_time

        if current_window:
            time_windows.append(current_window)

        return time_windows

    def _process_time_window(self, serial, window_entries, source_file_path):
        """处理单个时间窗口内的条目，生成多个样本"""
        samples = []

        # 分离不同类型的日志
        log10_entries = []
        log27_entries = []
        log16_entries = []
        log52_entries = []

        for entry in window_entries:
            log_id = str(entry.get('LogID', ''))
            if log_id == '10':
                log10_entries.append(entry)
            elif log_id == '27':
                log27_entries.append(entry)
            elif log_id == '16':
                log16_entries.append(entry)
            elif log_id == '52':
                log52_entries.append(entry)

        # 按时间戳分组，相同时间戳的视为同一日志
        log10_groups = self._group_entries_by_timestamp(log10_entries)
        log27_groups = self._group_entries_by_timestamp(log27_entries)

        # 尝试配对：按时间顺序配对最近的log10和log27
        paired_samples = self._pair_log10_log27(serial, log10_groups, log27_groups, source_file_path)

        # 为每个配对样本分配log16和log52计数
        if paired_samples:
            # 使用最初代码的LinAlarm计算逻辑
            log16_timestamps = set()
            log52_on_count = 0

            # 计算当前窗口内的LinAlarm
            for entry in log16_entries:
                try:
                    slogan = entry.get('Slogan', '')
                    if slogan.startswith('Lin. fault port') or slogan.startswith('Lin fault port'):
                        log16_timestamps.add(entry['Timestamp'])
                except Exception as e:
                    print(f"Error processing log16 entry: {e}")

            for entry in log52_entries:
                if entry.get('Key') == 'state' and entry.get('Value') == 'ON':
                    log52_on_count += 1

            lin_alarm_value = len(log16_timestamps) + log52_on_count

            # 为当前窗口内的所有样本分配相同的LinAlarm值
            for sample in paired_samples:
                sample['temp_lin_alarm'] = lin_alarm_value
                samples.append(sample)

        return samples

    @staticmethod
    def _group_entries_by_timestamp(entries):
        """按时间戳分组条目，相同时间戳的归为一组"""
        groups = defaultdict(list)
        for entry in entries:
            timestamp = entry['Timestamp']
            groups[timestamp].append(entry)
        return groups

    def _pair_log10_log27(self, serial, log10_groups, log27_groups, source_file_path):
        """配对log10和log27，生成样本"""
        samples = []

        # 获取按时间排序的组
        sorted_log10_timestamps = sorted(log10_groups.keys())
        sorted_log27_timestamps = sorted(log27_groups.keys())

        # 如果没有log10或log27，直接返回空列表
        if not sorted_log10_timestamps or not sorted_log27_timestamps:
            return samples

        # 为每个log10找到其后5秒内的所有log27
        for log10_ts in sorted_log10_timestamps:
            log10_time = _parse_timestamp(log10_ts)

            # 找到这个log10之后5秒内的所有log27
            matching_log27_groups = []
            for log27_ts in sorted_log27_timestamps:
                log27_time = _parse_timestamp(log27_ts)
                time_diff = (log27_time - log10_time).total_seconds()

                # 如果时间差在0到5秒之间，则匹配
                if 0 <= time_diff <= self.min_time_diff:
                    matching_log27_groups.append(log27_groups[log27_ts])
                # 如果时间差超过5秒，停止查找（因为log27是按时间排序的）
                elif time_diff > self.min_time_diff:
                    break

            # 如果找到了匹配的log27，创建样本
            if matching_log27_groups:
                sample = self._create_sample_from_multiple_log27(
                    serial,
                    log10_groups[log10_ts],
                    matching_log27_groups,
                    source_file_path
                )
                samples.append(sample)

        return samples

    def _create_sample_from_multiple_log27(self, serial, log10_entries, log27_groups_list, source_file_path):
        """从单个log10和多个log27组创建样本"""
        # 使用log10的时间戳作为样本时间戳
        timestamp = log10_entries[0]['Timestamp']

        sample = {
            'Serial': serial,
            'ProductName': log10_entries[0]['ProductName'],
            'Timestamp': timestamp,
            'parameters': {},
            'source_file': source_file_path
        }

        # 添加log10参数
        for entry in log10_entries:
            self._add_parameter_to_sample(sample, entry)

        # 添加所有匹配的log27参数
        for log27_group in log27_groups_list:
            for entry in log27_group:
                self._add_parameter_to_sample(sample, entry)

        return sample

    @staticmethod
    def _add_parameter_to_sample(sample, entry):
        """通用参数添加方法：动态处理特征名称"""
        key = entry.get('Key', '')
        value = entry.get('Value', '')

        if not key or value is None:
            return

        # 直接添加参数到样本，不进行任何过滤
        # 如果键已存在，则覆盖值；如果不存在，则创建新键
        sample['parameters'][key] = value


# ======================================================================================================================
# Placeholder - 其他问题的提取器实现
# ======================================================================================================================
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
