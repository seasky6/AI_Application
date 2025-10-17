import math


# 产品dpa_vdd阈值配置, 只限于Milano产品
PRODUCT_DPA_VDD_THRESHOLD = {
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
}


def label_method_pattern_1(sample):
    """
    通过提取elog10， elog27中的参数：DpaVddSv, PaVddSv, IDpaSv, IMpaSv, txPmb, txTorPmb, txAtt, torTemp, 判定PA是否异常
    """
    product_name = sample['ProductName']
    parameters = sample['parameters']

    # 检查产品名称是否在配置列表中
    if product_name not in PRODUCT_DPA_VDD_THRESHOLD:
        raise ValueError(f"产品 '{product_name}' 不在配置列表中，请添加到 PRODUCT_DPA_VDD_THRESHOLD")

    # 规则1: 检查DpaVddSv和PaVddSv
    def _check_rule_voltage():
        # 获取产品对应的dpa_vdd阈值(默认40 V)
        threshold = PRODUCT_DPA_VDD_THRESHOLD[product_name]['dpa_vdd']

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
        return 'PA abnormal'
    elif current_check_result1 and power_check_result1:
        return 'PA abnormal'
    elif current_check_result1 or power_check_result1:
        return 'PA might abnormal'
    else:
        return 'Normal'
