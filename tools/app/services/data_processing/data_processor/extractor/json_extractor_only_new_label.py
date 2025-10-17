import json
import os
import pandas as pd
from datetime import datetime
from collections import defaultdict
import glob
import math


def _add_entry_to_sample(sample, entry):
    """将条目中的参数添加到样本中"""
    key = entry.get('Key', '')
    value = entry.get('Value', '')
    if key and value:
        sample['parameters'][key] = {
            'Value': value,
        }


def _parse_timestamp(timestamp_str):
    """解析时间戳字符串为datetime对象"""
    try:
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except:
        return datetime.min


def _save_samples(samples, output_dir, base_name):
    """保存样本到JSON和Excel文件"""
    # JSON路径
    json_path = os.path.join(output_dir, f'{base_name}_training_sample.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json_data = [{
            'Serial': s['Serial'],
            'ProductName': s['ProductName'],
            'Timestamp': s['Timestamp'],
            'Parameters': s['parameters'],
            'PA Status': s.get('PA Status', 'unknown')  # 添加PA Status
        } for s in samples]
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"保存训练样本到JSON文件: {json_path}")

    # Excel路径
    excel_path = os.path.join(output_dir, f'{base_name}_training_sample.xlsx')

    # 收集所有可能的列名
    all_columns = set()
    for sample in samples:
        all_columns.update(sample['parameters'].keys())

    # 定义列顺序：基础列 -> 参数列（按字母排序） -> PA Status
    base_columns = ['Serial', 'ProductName', 'Timestamp']
    columns_order = base_columns + sorted(all_columns) + ['PA Status']

    excel_data = []
    for sample in samples:
        # 初始列
        row = {
            'Serial': sample['Serial'],
            'ProductName': sample['ProductName'],
            'Timestamp': sample['Timestamp']
        }
        # 参数列
        for param, value in sample['parameters'].items():
            row[param] = value['Value']
        # PA Status列
        row['PA Status'] = sample.get('PA Status', 'unknown')  # 添加PA Status列

        excel_data.append(row)

    df = pd.DataFrame(excel_data, columns=columns_order)
    df.to_excel(excel_path, index=False)
    print(f"保存训练样本到Excel文件: {excel_path}")


class Extractor:
    def __init__(self):
        self.min_time_diff = 5  # 5秒时间差阈值
        self.target_log_ids = {'10', '27'}  # 提取对象log ID
        self.non_target_log_keys = {'Case', 'Event ID', 'Carrier Info', 'Invalid command'}

        # 产品dpa_vdd阈值配置：
        self.product_dpa_vdd_threshold = {
            'Radio 4471 B3': {'dpa_vdd': 20},
            'Radio 2271 B1': {'dpa_vdd': 20},
            'Radio 2271 B7': {'dpa_vdd': 20},
            'Radio 2271 B28': {'dpa_vdd': 40},
            'Radio 2271 B8': {'dpa_vdd': 40},
            'Radio 2271 B8B': {'dpa_vdd': 40},
            'Radio 2271 B20': {'dpa_vdd': 40},
            'Radio 4471 B3B': {'dpa_vdd': 20},
            'Radio 2271 B28A': {'dpa_vdd': 40},
            'Radio 2271 B0C': {'dpa_vdd': 40},
            'Radio 4471 B1': {'dpa_vdd': 20},
            'Radio 4471 B30': {'dpa_vdd': 20},
            'Radio 2271 B3': {'dpa_vdd': 20}
        }

    def _determine_pa_status(self, sample):
        """根据样本参数确定PA状态，处理多分支情况"""
        product_name = sample['ProductName']
        parameters = sample['parameters']

        # 规则1: 检查DpaVddSv和PaVddSv
        def check_rule_voltage():
            # 获取产品对应的dpa_vdd阈值(默认40 V)
            threshold = self.product_dpa_vdd_threshold.get(product_name, {}).get('dpa_vdd', 40)

            # 提取所有 DpaVddSv 和 PaVddSv 的键
            dpa_vdd_keys = [k for k in parameters if k.startswith('DpaVddSv')]
            pa_vdd_keys = [k for k in parameters if k.startswith('PaVddSv')]

            unknown_check_result = False
            voltage_check_result = False

            # 检查 DpaVddSv 是否全为 None 或 ''
            dpa_vdd_all_empty = True
            for key in dpa_vdd_keys:
                value = parameters[key].get('Value', '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    dpa_vdd_all_empty = False
                    break

            # 检查 PaVddSv 是否全为 None 或 ''
            pa_vdd_all_empty = True
            for key in pa_vdd_keys:
                value = parameters[key].get('Value', '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    pa_vdd_all_empty = False
                    break

            # 如果 DpaVddSv 或 PaVddSv 全部为空或不存在，则标记 unknown_check_result = True
            if (dpa_vdd_keys and dpa_vdd_all_empty) or (pa_vdd_keys and pa_vdd_all_empty):
                unknown_check_result = True

            # 检查电压是否低于阈值（单位转换：mV → V）
            for key in parameters:
                if key.startswith('DpaVddSv'):
                    value = parameters[key].get('Value', '')
                    if value not in ('', None):
                        if float(value) / 1000 <= threshold:
                            voltage_check_result = True
                elif key.startswith('PaVddSv'):
                    value = parameters[key].get('Value', '')
                    if value not in ('', None):
                        if float(value) / 1000 <= 40:  # PaVddSv 默认阈值40V
                            voltage_check_result = True

            return unknown_check_result, voltage_check_result

        # 规则2: 检查IDpaSv和IMpaSv
        def check_rule_current():
            # 提取所有 IDpaSv 和 IMpaSv 的键
            idpa_keys = [k for k in parameters if k.startswith('IDpaSv')]
            impa_keys = [k for k in parameters if k.startswith('IMpaSv')]

            unknown_check_result = False
            current_check_result = False

            # 检查 IDpaSv 是否全为 None 或 ''
            idpa_all_empty = True
            for key in idpa_keys:
                value = parameters[key].get('Value', '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    idpa_all_empty = False
                    break

            # 检查 IMpaSv 是否全为 None 或 ''
            impa_all_empty = True
            for key in impa_keys:
                value = parameters[key].get('Value', '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    impa_all_empty = False
                    break

            # 如果 IDpaSv 或 IMpaSv 全部为空或不存在，则标记 unknown_check_result = True
            if (idpa_keys and idpa_all_empty) or (impa_keys and impa_all_empty):
                unknown_check_result = True

            # 检查电流是否低于阈值（IDpaSv < 30, IMpaSv < 50）
            for key in parameters:
                if key.startswith('IDpaSv'):
                    value = parameters[key].get('Value', '')
                    if value not in ('', None):
                        if float(value) < 30:
                            current_check_result = True
                elif key.startswith('IMpaSv'):
                    value = parameters[key].get('Value', '')
                    if value not in ('', None):
                        if float(value) < 50:
                            current_check_result = True

            return unknown_check_result, current_check_result

        # 规则3和4: 检查txPmb, torTemp, txTorPmb, txAtt
        def check_rule_power():
            # 检查 txPmb, torTemp, txTorPmb, txAtt 是否存在
            tx_pmb = parameters.get('txPmb', {}).get('Value')
            tor_temp = parameters.get('torTemp', {}).get('Value')
            tx_tor_pmb = parameters.get('txTorPmb', {}).get('Value')
            tx_att = parameters.get('txAtt', {}).get('Value')

            unknown_check_result = False
            power_check_result = False

            # 检查是否有任何一个参数是空、None、inf 或 -inf
            def is_invalid_value(value):
                if value in ('', None):
                    return True
                try:
                    float_val = float(value)
                    return math.isinf(float_val)  # 检查是否 inf 或 -inf
                except (ValueError, TypeError):
                    return True                   # 如果无法转为 float，视为无效

            if (is_invalid_value(tx_pmb) or
                    is_invalid_value(tor_temp) or
                    is_invalid_value(tx_tor_pmb) or
                    is_invalid_value(tx_att)):
                unknown_check_result = True

            # 如果所有参数有效，则进行功率计算
            if not unknown_check_result:
                try:
                    tx_pmb_val = float(tx_pmb)
                    tor_temp_val = float(tor_temp)
                    tx_tor_pmb_val = float(tx_tor_pmb)
                    tx_att_val = float(tx_att)

                    # 计算 temp_fit_att 和 gain_need
                    temp_fit_att = -0.18 * (tor_temp_val - 35) * 100 + 1200
                    gain_need = (tx_tor_pmb_val - tx_pmb_val) * 100

                    # 检查规则条件
                    if tx_att_val - temp_fit_att < gain_need:
                        power_check_result = True
                except (ValueError, TypeError):
                    unknown_check_result = True  # 如果转换失败，视为无效

            return unknown_check_result, power_check_result

        # 执行所有规则检查
        unknown_check_result1, voltage_check_result1 = check_rule_voltage()
        unknown_check_result2, current_check_result1 = check_rule_current()
        unknown_check_result3, power_check_result1 = check_rule_power()

        # 新增：检查参数键是否存在（避免遗漏未提供参数）
        has_voltage_params = any(k.startswith(('DpaVddSv', 'PaVddSv')) for k in parameters)
        has_current_params = any(k.startswith(('IDpaSv', 'IMpaSv')) for k in parameters)
        has_power_params = all(k in parameters for k in ['txPmb', 'torTemp', 'txTorPmb', 'txAtt'])

        # 确定最终状态
        if not has_voltage_params or not has_current_params or not has_power_params:
            return 'Unknown'  # 完全无参数
        elif unknown_check_result1 or unknown_check_result2 or unknown_check_result3:
            return 'Unknown'
        elif voltage_check_result1:
            return 'PA broken'
        elif current_check_result1 and power_check_result1:
            return 'PA broken'
        elif current_check_result1 or power_check_result1:
            return 'PA might broken'
        else:
            return 'Normal'

    def extract_samples(self, input_dir, output_dir):
        """
        从输入目录中的JSON文件抽取样本，保存到输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        json_files = glob.glob(os.path.join(input_dir, '*_parsed_log.json'))

        # 初始化累积的样本列表
        accumulated_samples = []

        for json_file in json_files:
            print(f"抽取文件: {json_file} 过程中...")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 按serial分组
            serial_groups = defaultdict(list)
            for entry in data:
                if (entry.get('LogType') == 'elog' and str(entry.get('LogID')) in self.target_log_ids and
                        str(entry.get('Key')) not in self.non_target_log_keys):
                    serial_groups[entry['Serial']].append(entry)

            # 处理每个serial的数据
            for serial, entries in serial_groups.items():
                samples = self._extract_serial_samples(serial, entries)
                accumulated_samples.extend(samples)

            # 保存结果
            base_name = 'PDP_submit_pattern_result'
            if accumulated_samples:
                _save_samples(accumulated_samples, output_dir, base_name)
            else:
                print("没有合理的样本对象！")

    def _extract_serial_samples(self, serial, entries):
        """
        处理单个serial的条目，抽取样本
        """
        # 按时间戳排序
        sorted_entries = sorted(entries, key=lambda x: _parse_timestamp(x['Timestamp']))

        samples = []
        current_sample = None
        last_log10_time = None

        for entry in sorted_entries:
            timestamp = _parse_timestamp(entry['Timestamp'])
            log_id = str(entry.get('LogID', ''))

            if log_id == '10':
                # 遇到LogID=10，开始新样本
                if current_sample and last_log10_time and (
                        timestamp - last_log10_time).total_seconds() < self.min_time_diff:
                    # 如果与上一个LogID=10的时间差小于阈值，合并到当前样本
                    _add_entry_to_sample(current_sample, entry)
                else:
                    # 否则创建新样本
                    if current_sample:
                        current_sample['PA Status'] = self._determine_pa_status(current_sample)
                        samples.append(current_sample)
                    current_sample = {
                        'Serial': serial,
                        'ProductName': entry['ProductName'],
                        'Timestamp': entry['Timestamp'],
                        'parameters': {}
                    }
                    _add_entry_to_sample(current_sample, entry)
                last_log10_time = timestamp
            elif log_id == '27' and current_sample:
                # 只处理与当前LogID=10关联的LogID=27
                _add_entry_to_sample(current_sample, entry)

        # 添加最后一个样本
        if current_sample:
            current_sample['PA Status'] = self._determine_pa_status(current_sample)
            samples.append(current_sample)

        return samples


def main():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../'))
    INPUT_DIR = os.path.join(ROOT_DIR, 'files_parsed')
    OUTPUT_DIR = os.path.join(ROOT_DIR, 'files_for_training')

    extractor = Extractor()
    extractor.extract_samples(INPUT_DIR, OUTPUT_DIR)


if __name__ == '__main__':
    main()
