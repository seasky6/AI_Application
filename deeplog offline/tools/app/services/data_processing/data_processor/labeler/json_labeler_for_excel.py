import os
import math
import pandas as pd
import numpy as np
from typing import List, Dict, Any


class Labeler:
    def __init__(self):
        # 产品 dpa_vdd 阈值
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

    def label_samples(self, samples, labeling_method='legacy'):
        if samples is None:
            raise ValueError("样本集不能为空！")
        if not isinstance(samples, (list, tuple)):
            raise ValueError("样本集必须是一个列表或元组")
        if labeling_method not in ['legacy']:
            raise ValueError("本脚本仅支持 legacy 打标")

        for sample in samples:
            sample['PA Status Legacy'] = self._determine_pa_status(sample)
        return samples

    # —— 下面是“legacy”打标逻辑（原样保留）——
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
                if value not in ('', None):
                    dpa_vdd_all_empty = False
                    break

            # 检查 PaVddSv 是否全为 None 或 ''
            pa_vdd_all_empty = True
            for key in pa_vdd_keys:
                value = parameters.get(key, '')
                if value not in ('', None):
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

            idpa_all_empty = True
            for key in idpa_keys:
                value = parameters.get(key, '')
                if value not in ('', None):
                    idpa_all_empty = False
                    break

            impa_all_empty = True
            for key in impa_keys:
                value = parameters.get(key, '')
                if value not in ('', None):
                    impa_all_empty = False
                    break

            if (idpa_keys and idpa_all_empty) or (impa_keys and impa_all_empty):
                unknown_check_result = True

            # IDpaSv < 30, IMpaSv < 50
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

        # 规则3/4: 检查 txPmb, torTemp, txTorPmb, txAtt
        def _check_rule_power():
            tx_pmb = parameters.get('txPmb', '')
            tor_temp = parameters.get('torTemp', '')
            tx_tor_pmb = parameters.get('txTorPmb', '')
            tx_att = parameters.get('txAtt', '')

            unknown_check_result = False
            power_check_result = False

            def is_invalid_value(value):
                if value in ('', None):
                    return True
                try:
                    float_val = float(value)
                    return math.isinf(float_val)
                except (ValueError, TypeError):
                    return True

            if (is_invalid_value(tx_pmb) or
                is_invalid_value(tor_temp) or
                is_invalid_value(tx_tor_pmb) or
                is_invalid_value(tx_att)):
                unknown_check_result = True

            if not unknown_check_result:
                try:
                    tx_pmb_val = float(tx_pmb)
                    tor_temp_val = float(tor_temp)
                    tx_tor_pmb_val = float(tx_tor_pmb)
                    tx_att_val = float(tx_att)

                    temp_fit_att = -0.18 * (tor_temp_val - 35) * 100 + 1200
                    gain_need = (tx_tor_pmb_val - tx_pmb_val) * 100

                    if tx_att_val - temp_fit_att < gain_need:
                        power_check_result = True
                except (ValueError, TypeError):
                    unknown_check_result = True

            return unknown_check_result, power_check_result

        # 执行所有规则检查
        unknown_check_result1, voltage_check_result1 = _check_rule_voltage()
        unknown_check_result2, current_check_result1 = _check_rule_current()
        unknown_check_result3, power_check_result1 = _check_rule_power()

        # 参数键存在性检查
        has_voltage_params = any(k.startswith(('DpaVddSv', 'PaVddSv')) for k in parameters)
        has_current_params = any(k.startswith(('IDpaSv', 'IMpaSv')) for k in parameters)
        has_power_params = all(k in parameters for k in ['txPmb', 'torTemp', 'txTorPmb', 'txAtt'])

        if not has_voltage_params or not has_current_params or not has_power_params:
            return 'Unknown'
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


def build_samples_from_new_excel_legacy(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    按 legacy 规则，从新表中提取打标所需字段构造 samples。
    其余原始列不会参与打标，但会在最终导出中原样保留（我们从 df 原表出发再拼状态列）。
    """
    # 基础字段名
    serial_col = 'Serial'
    product_col = 'ProductName'
    # legacy 历史里叫 Timestamp；此处优先用 elog_time_e10，其次 elog_time_e27，没有则空
    ts_candidates = ['elog_time_e10', 'elog_time_e27']

    # 选择会被 legacy 逻辑用到的列名（若不存在也不报错，后面会给空值）
    needed_cols_exact = ['txPmb', 'torTemp', 'txTorPmb', 'txAtt', 'DpaVddSv', 'PaVddSv']
    # 电流类可能有分路后缀：IDpaSv.0 / IDpaSv.1 / IMpaSv.0 / IMpaSv.1
    # legacy 用 startswith('IDpaSv') / startswith('IMpaSv')，所以这些命名都能匹配
    dynamic_prefixes = ['IDpaSv', 'IMpaSv']

    # 规范列名空白
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    samples: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        # Timestamp 选择
        ts_val = ''
        for c in ts_candidates:
            if c in df.columns:
                v = row.get(c, '')
                if pd.notna(v) and v != '':
                    ts_val = v
                    break

        # parameters 只收集 legacy 需要的键
        params: Dict[str, Any] = {}

        # 精确列
        for c in needed_cols_exact:
            if c in df.columns:
                v = row.get(c, '')
                if pd.isna(v):
                    v = ''
                params[c] = v

        # 动态前缀列（把所有以这些前缀开头的列都带上）
        for col in df.columns:
            for pfx in dynamic_prefixes:
                if col.startswith(pfx):
                    v = row.get(col, '')
                    if pd.isna(v):
                        v = ''
                    params[col] = v

        # 电压类也允许多分支名：以 DpaVddSv 或 PaVddSv 开头的都带上
        for col in df.columns:
            if col.startswith('DpaVddSv') or col.startswith('PaVddSv'):
                v = row.get(col, '')
                if pd.isna(v):
                    v = ''
                params[col] = v

        # 构造 sample
        samples.append({
            'Serial': row.get(serial_col, ''),
            'ProductName': row.get(product_col, ''),
            'Timestamp': ts_val,
            'parameters': params
        })

    return samples


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_xlsx = os.path.join(script_dir, 'elog10_27_comb.xlsx')
    output_xlsx = os.path.join(script_dir, 'elog10_27_comb_labeled.xlsx')

    if not os.path.exists(input_xlsx):
        raise FileNotFoundError(f'未找到输入文件：{input_xlsx}')

    # 读入原始表
    df_raw = pd.read_excel(input_xlsx, dtype=object)
    df_raw.columns = [str(c).strip() for c in df_raw.columns]

    # 构建 samples（仅含 legacy 所需字段）
    samples = build_samples_from_new_excel_legacy(df_raw)

    # 打标（legacy）
    labeler = Labeler()
    labeled = labeler.label_samples(samples, labeling_method='legacy')

    # 把“状态列”拼回原始表，原列不动
    pa_status = [s.get('PA Status Legacy', 'unknown') for s in labeled]
    df_out = df_raw.copy()
    df_out['PA Status Legacy'] = pa_status

    # 导出
    df_out.to_excel(output_xlsx, index=False)
    print(f'已生成：{output_xlsx}')


if __name__ == '__main__':
    # pandas 显示/缺失统一
    pd.options.display.max_columns = None
    main()
