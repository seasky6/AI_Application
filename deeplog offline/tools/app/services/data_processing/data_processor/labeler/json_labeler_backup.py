import math
import os
import json


class Labeler:
    def __init__(self):
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
            'Radio 2271 B3': {'dpa_vdd': 20},
            'Radio 4490 44B1 44B3 C': {'dpa_vdd': 20},
            'Radio 4490 B1B3': {'dpa_vdd': 20}
        }

    def label_samples(self, samples, labeling_method='both'):
        """
        对样本集进行打标
        :param samples: 样本列表
        :param labeling_method: 打标方法 ('legacy', 'new', 'both')
            -> legacy: 通过check log中对应参数的pattern来打标
            -> new: 通过check log获取的方式来打标
        :return: 打标后的样本列表
        """
        if samples is None:
            raise ValueError("样本集不能为空！")

        if not isinstance(samples, (list, tuple)):  # 检查是否为可迭代对象
            raise ValueError("样本集必须是一个列表或元组")

        if labeling_method not in ['legacy', 'new', 'both']:
            raise ValueError("打标方法请在 'legacy', 'new' or 'both' 中选择！")

        for sample in samples:
            if labeling_method == 'legacy':
                sample['PA Status Legacy'] = self._determine_pa_status(sample)
            elif labeling_method == 'new':
                sample['PA Status New'] = self._determine_pa_status_new(sample)
            else:
                sample['PA Status Legacy'] = self._determine_pa_status(sample)
                sample['PA Status New'] = self._determine_pa_status_new(sample)

        return samples

    # 利用PA log pattern给sample打标
    def _determine_pa_status(self, sample):
        """根据样本参数确定PA状态，处理多分支情况"""
        product_name = sample['ProductName']
        parameters = sample['parameters']

        # 规则1: 检查DpaVddSv和PaVddSv
        def _check_rule_voltage():
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
                value = parameters.get(key, '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    dpa_vdd_all_empty = False
                    break

            # 检查 PaVddSv 是否全为 None 或 ''
            pa_vdd_all_empty = True
            for key in pa_vdd_keys:
                value = parameters.get(key, '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    pa_vdd_all_empty = False
                    break

            # 如果 DpaVddSv 或 PaVddSv 全部为空或不存在，则标记 unknown_check_result = True
            if (dpa_vdd_keys and dpa_vdd_all_empty) or (pa_vdd_keys and pa_vdd_all_empty):
                unknown_check_result = True

            # 检查电压是否低于阈值（单位转换：mV → V）
            for key, value in parameters.items():
                if key.startswith('DpaVddSv'):
                    if value not in ('', None):
                        try:
                            if float(value) / 1000 <= threshold:
                                voltage_check_result = True
                        except (ValueError, TypeError):
                            continue
                elif key.startswith('PaVddSv'):
                    if value not in ('', None):
                        try:
                            if float(value) / 1000 <= 40:  # PaVddSv 默认阈值40V
                                voltage_check_result = True
                        except (ValueError, TypeError):
                            continue

            return unknown_check_result, voltage_check_result

        # 规则2: 检查IDpaSv和IMpaSv
        def _check_rule_current():
            # 提取所有 IDpaSv 和 IMpaSv 的键
            idpa_keys = [k for k in parameters if k.startswith('IDpaSv')]
            impa_keys = [k for k in parameters if k.startswith('IMpaSv')]

            unknown_check_result = False
            current_check_result = False

            # 检查 IDpaSv 是否全为 None 或 ''
            idpa_all_empty = True
            for key in idpa_keys:
                value = parameters.get(key, '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    idpa_all_empty = False
                    break

            # 检查 IMpaSv 是否全为 None 或 ''
            impa_all_empty = True
            for key in impa_keys:
                value = parameters.get(key, '')
                if value not in ('', None):  # 只要有一个有效值，就不是全空
                    impa_all_empty = False
                    break

            # 如果 IDpaSv 或 IMpaSv 全部为空或不存在，则标记 unknown_check_result = True
            if (idpa_keys and idpa_all_empty) or (impa_keys and impa_all_empty):
                unknown_check_result = True

            # 检查电流是否低于阈值（IDpaSv < 30, IMpaSv < 50）
            for key, value in parameters.items():
                if key.startswith('IDpaSv'):
                    if value not in ('', None):
                        try:
                            if float(value) < 30:
                                current_check_result = True
                        except (ValueError, TypeError):
                            continue
                elif key.startswith('IMpaSv'):
                    if value not in ('', None):
                        try:
                            if float(value) < 50:
                                current_check_result = True
                        except (ValueError, TypeError):
                            continue

            return unknown_check_result, current_check_result

        # 规则3和4: 检查txPmb, torTemp, txTorPmb, txAtt
        def _check_rule_power():
            # 检查 txPmb, torTemp, txTorPmb, txAtt 是否存在
            tx_pmb = parameters.get('txPmb', '')
            tor_temp = parameters.get('torTemp', '')
            tx_tor_pmb = parameters.get('txTorPmb', '')
            tx_att = parameters.get('txAtt', '')

            unknown_check_result = False
            power_check_result = False

            # 检查是否有任何一个参数是 空, None, inf, 或 -inf
            def is_invalid_value(value):
                if value in ('', None):
                    return True
                try:
                    float_val = float(value)
                    return math.isinf(float_val)  # 检查是否 inf 或 -inf
                except (ValueError, TypeError):
                    return True  # 如果无法转为 float，视为无效

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
        unknown_check_result1, voltage_check_result1 = _check_rule_voltage()
        unknown_check_result2, current_check_result1 = _check_rule_current()
        unknown_check_result3, power_check_result1 = _check_rule_power()

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

    # 利用log日志获取的方式给sample打标
    @staticmethod
    def _determine_pa_status_new(sample):
        """根据样本的Serial确定新的PA状态"""
        serial = sample['Serial']
        product_name = sample['ProductName']

        # 定义产品集
        milano_products = ['Radio 2271 B1', 'Radio 2271 B28']

        stockholm_products = ['Radio 4490 B1B3']

        dublin_products = []

        try:
            SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
            ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '../../../../'))
            INPUT_DIR = os.path.join(ROOT_DIR, 'files_parsed')

            # 初始化状态
            pa_status_new = 'Unknown'

            # 检查产品类型
            if product_name in milano_products:
                # 读取Milano文件
                milano_repair_path = os.path.join(INPUT_DIR, 'Milano_Repair_PA_Issue.txt')
                milano_repair_nff_path = os.path.join(INPUT_DIR, 'Milano_Repair_Other_NFF.txt')

                if os.path.exists(milano_repair_path):
                    with open(milano_repair_path, 'r') as f:
                        milano_repair_serials = {line.strip() for line in f if line.strip()}
                else:
                    print(f"警告: Milano repair文件 '{milano_repair_path}' 未找到")
                    milano_repair_serials = set()

                if os.path.exists(milano_repair_nff_path):
                    with open(milano_repair_nff_path, 'r') as f:
                        milano_repair_nff_serials = {line.strip() for line in f if line.strip()}
                else:
                    print(f"警告: Milano repair NFF文件 '{milano_repair_nff_path}' 未找到")
                    milano_repair_nff_serials = set()

                if serial in milano_repair_serials:
                    pa_status_new = 'PA might broken'
                elif serial in milano_repair_nff_serials:
                    pa_status_new = 'PA might normal'
                # 否则保持 Unknown

            elif product_name in stockholm_products:
                # 读取Stockholm文件
                stockholm_repair_path = os.path.join(INPUT_DIR, 'Stockholm_Repair_PAX_Replaced.txt')
                stockholm_repair_nff_path = os.path.join(INPUT_DIR, 'Stockholm_Repair_NFF.txt')

                if os.path.exists(stockholm_repair_path):
                    with open(stockholm_repair_path, 'r') as f:
                        stockholm_repair_serials = {line.strip() for line in f if line.strip()}
                else:
                    print(f"警告: Stockholm repair文件 '{stockholm_repair_path}' 未找到")
                    stockholm_repair_serials = set()

                if os.path.exists(stockholm_repair_nff_path):
                    with open(stockholm_repair_nff_path, 'r') as f:
                        stockholm_repair_nff_serials = {line.strip() for line in f if line.strip()}
                else:
                    print(f"警告: Stockholm repair NFF文件 '{stockholm_repair_nff_path}' 未找到")
                    stockholm_repair_nff_serials = set()

                if serial in stockholm_repair_serials:
                    pa_status_new = 'PA might broken'
                elif serial in stockholm_repair_nff_serials:
                    pa_status_new = 'PA might normal'
                # 否则保持 Unknown

            elif product_name in dublin_products:
                # 可以添加Dublin产品的处理逻辑
                pass
            else:
                print(f"警告: 未知产品类型 '{product_name}' PA Status New 标注成 Unknown")

        except Exception as e:
            print(f"PA Status new 判定错误 {serial}: {str(e)}")
            pa_status_new = 'Unknown'

        return pa_status_new

    @staticmethod
    def save_samples(samples, output_dir, base_name, labeling_method='both'):
        """保存样本到JSON和Excel文件"""
        if labeling_method not in ['legacy', 'new', 'both']:
            raise ValueError("打标方法请在 'legacy', 'new' or 'both' 中选择！")

        # JSON路径
        json_path = os.path.join(output_dir, f'{base_name}_training_sample.json')

        # 构建JSON数据，根据labeling_method决定包含哪些PA状态列
        json_data = []
        for s in samples:
            sample_data = {
                'Serial': s['Serial'],
                'ProductName': s['ProductName'],
                'Timestamp': s['Timestamp'],
                'Parameters': {k: v for k, v in s['parameters'].items()}  # 直接存储键值对
            }
            if labeling_method == 'legacy':
                sample_data['PA Status Legacy'] = s.get('PA Status Legacy', 'unknown')
            elif labeling_method == 'new':
                sample_data['PA Status New'] = s.get('PA Status New', 'unknown')
            else:  # 'both'
                sample_data['PA Status Legacy'] = s.get('PA Status Legacy', 'unknown')
                sample_data['PA Status New'] = s.get('PA Status New', 'unknown')
            json_data.append(sample_data)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"保存训练样本到JSON文件: {json_path}")

        # Excel路径
        excel_path = os.path.join(output_dir, f'{base_name}_training_sample.xlsx')
        import pandas as pd

        # 收集所有可能的参数列名
        all_columns = set()
        for sample in samples:
            all_columns.update(sample['parameters'].keys())

        # 定义基础列顺序
        base_columns = ['Serial', 'ProductName', 'Timestamp']
        columns_order = base_columns + sorted(all_columns)

        # 根据labeling_method添加PA状态列
        if labeling_method == 'legacy':
            columns_order.append('PA Status Legacy')
        elif labeling_method == 'new':
            columns_order.append('PA Status New')
        else:  # 'both'
            columns_order.extend(['PA Status Legacy', 'PA Status New'])

        excel_data = []
        for sample in samples:
            # 基础列
            row = {
                'Serial': sample['Serial'],
                'ProductName': sample['ProductName'],
                'Timestamp': sample['Timestamp']
            }
            # 参数列
            row.update(sample['parameters'])
            # PA状态列
            if labeling_method == 'legacy':
                row['PA Status Legacy'] = sample.get('PA Status Legacy', 'unknown')
            elif labeling_method == 'new':
                row['PA Status New'] = sample.get('PA Status New', 'unknown')
            else:  # 'both'
                row['PA Status Legacy'] = sample.get('PA Status Legacy', 'unknown')
                row['PA Status New'] = sample.get('PA Status New', 'unknown')
            excel_data.append(row)

        df = pd.DataFrame(excel_data, columns=columns_order)
        df.to_excel(excel_path, index=False)
        print(f"保存训练样本到Excel文件: {excel_path}")
