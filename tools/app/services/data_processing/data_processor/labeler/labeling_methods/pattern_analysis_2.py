import pandas as pd


def _convert_to_numeric(series, default=0):
    """将Series转换为数值类型，处理字符串和空值"""
    try:
        return pd.to_numeric(series, errors='coerce').fillna(default)
    except:
        return pd.Series([default] * len(series), index=series.index)


def _add_symptom(current_symptoms, new_symptom):
    """添加症状到症状列表，如果有多个症状则用逗号+空格分隔"""
    if not current_symptoms:
        return new_symptom
    else:
        return current_symptoms + ', ' + new_symptom


def _mark_lin_fault(df):
    """
    Hu Di 提供的新打标方法：新增的参数用于新pattern判定：statusBit, Lin alarm, dpdRestartCounter
    """
    # 复制数据以避免修改原始数据
    lin_fault = df.copy()

    # 初始化新列，默认值为Normal
    lin_fault['PA Status Pattern 2'] = 'Normal'

    # 电压阈值（单位：mV）
    PAVDD_TH, DPAVDD_TH = 38000, 26000  # 38V和26V，转换为mV

    # 确保数值列是数值类型
    numeric_columns = ['PaVddSv', 'DpaVddSv', 'txDpdPma', 'txPma', 'txTorPmb',
                       'txPmb', 'txAtt', 'torTemp', 'torGainBackoff', 'LinAlarm',
                       'dpdRestartCounter']

    for col in numeric_columns:
        if col in lin_fault.columns:
            lin_fault[col] = _convert_to_numeric(lin_fault[col])

    # 创建列来存储 PA症状描述
    lin_fault['Symptoms'] = ''

    # 1. 标记PaVdd drop
    if 'PaVddSv' in lin_fault.columns and 'DpaVddSv' in lin_fault.columns:
        mask_vdd_low = ((lin_fault['PaVddSv'] < PAVDD_TH) | (lin_fault['DpaVddSv'] < DPAVDD_TH))
        lin_fault.loc[mask_vdd_low, 'Symptoms'] = lin_fault.loc[mask_vdd_low, 'Symptoms'].apply(
            lambda x: _add_symptom(x, 'PaVdd drop'))

    # 2. 标记DPD gain异常
    if 'txDpdPma' in lin_fault.columns and 'txPma' in lin_fault.columns:
        DPD_GAIN_THRESHOLD = -2
        dpd_gain = lin_fault['txDpdPma'] - lin_fault['txPma']
        mask_dpd = (lin_fault['txDpdPma'] > -25) & (dpd_gain > DPD_GAIN_THRESHOLD)
        lin_fault.loc[mask_dpd, 'Symptoms'] = lin_fault.loc[mask_dpd, 'Symptoms'].apply(
            lambda x: _add_symptom(x, 'DPD gain abn'))

    # 3. 标记Tx gain异常
    TX_GAIN_THRESHOLD = 3

    # 计算tx_gain_dev
    if all(col in lin_fault.columns for col in ['txTorPmb', 'txPmb', 'txAtt', 'torTemp']):
        # 处理torGainBackoff，如果不存在则使用默认值0
        tor_gain_backoff = lin_fault['torGainBackoff'] if 'torGainBackoff' in lin_fault.columns else 0

        tx_gain_dev = (lin_fault['txTorPmb'] - lin_fault['txPmb'] +
                       (lin_fault['txAtt'] - tor_gain_backoff - 1200) / 100 +
                       1.6 * (lin_fault['torTemp'] - 350) / 100)

        # 检查statusBit是否包含DPD_IDLE（如果存在该列）
        if 'statusBit' in lin_fault.columns:
            mask_dpd_idle = lin_fault['statusBit'].astype(str).str.contains('DPD_IDLE', na=False)
        else:
            mask_dpd_idle = pd.Series([False] * len(lin_fault), index=lin_fault.index)

        mask_high = (tx_gain_dev > TX_GAIN_THRESHOLD) & ~mask_dpd_idle & (lin_fault['txTorPmb'] > -55)
        mask_low = (tx_gain_dev < -TX_GAIN_THRESHOLD) & ~mask_dpd_idle & (lin_fault['txPmb'] > -55)

        lin_fault.loc[mask_high, 'Symptoms'] = lin_fault.loc[mask_high, 'Symptoms'].apply(
            lambda x: _add_symptom(x, 'Tx gain high'))
        lin_fault.loc[mask_low, 'Symptoms'] = lin_fault.loc[mask_low, 'Symptoms'].apply(
            lambda x: _add_symptom(x, 'Tx gain low'))

        # 4. 标记PA异常（多个Lin alarm + Tx gain low）
        if 'LinAlarm' in lin_fault.columns:
            mask_multi_lin_fault = lin_fault['LinAlarm'] > 2
            mask_pa_abn = mask_low & mask_multi_lin_fault
            lin_fault.loc[mask_pa_abn, 'PA Status Pattern 2'] = 'PA abnormal'

    # 5. 标记DPD idle
    if 'statusBit' in lin_fault.columns and 'branch' in lin_fault.columns:
        try:
            # 按Serial和branch分组，检查是否所有statusBit都包含EXT_DPD_IDLE
            serial_branch_groups = lin_fault.groupby(['Serial', 'branch'])
            all_idle_mask = serial_branch_groups['statusBit'].transform(
                lambda x: x.astype(str).str.contains('EXT_DPD_IDLE', na=False).all() if len(x) > 0 else False
            )
            lin_fault.loc[all_idle_mask, 'Symptoms'] = lin_fault.loc[all_idle_mask, 'Symptoms'].apply(
                lambda x: _add_symptom(x, 'DPD idle'))
        except:
            pass  # 如果分组失败，跳过

    # 6. 标记DPD重启
    if 'dpdRestartCounter' in lin_fault.columns and 'branch' in lin_fault.columns:
        try:
            # 按Serial和branch分组，计算dpdRestartCounter的中位数
            restart_median = lin_fault.groupby(['Serial', 'branch'])['dpdRestartCounter'].transform('median')
            mask_restart = restart_median > 4
            lin_fault.loc[mask_restart, 'Symptoms'] = lin_fault.loc[mask_restart, 'Symptoms'].apply(
                lambda x: _add_symptom(x, 'DPD restart'))
        except:
            pass  # 如果分组失败，跳过

    # 7. 标记PA异常lin（DPD重启、PaVdd drop和多Lin故障的组合）
    try:
        if ('dpdRestartCounter' in lin_fault.columns and
                'LinAlarm' in lin_fault.columns and
                'branch' in lin_fault.columns):

            # 获取有DPD重启的序列号
            restart_median = lin_fault.groupby(['Serial', 'branch'])['dpdRestartCounter'].transform('median')
            dpd_restart_serials = lin_fault[restart_median > 4]['Serial'].unique()

            # 获取有PaVdd drop的序列号
            if 'PaVddSv' in lin_fault.columns and 'DpaVddSv' in lin_fault.columns:
                mask_vdd_low = ((lin_fault['PaVddSv'] < PAVDD_TH) | (lin_fault['DpaVddSv'] < DPAVDD_TH))
                vdd_drop_serials = lin_fault[mask_vdd_low]['Serial'].unique()
            else:
                vdd_drop_serials = []

            # 获取有多个Lin故障的序列号
            if 'LinAlarm' in lin_fault.columns:
                multi_lin_serials = lin_fault[lin_fault['LinAlarm'] > 2]['Serial'].unique()
            else:
                multi_lin_serials = []

            # 找出同时满足三个条件的序列号
            pa_abn_serials = set(dpd_restart_serials) & set(vdd_drop_serials) & set(multi_lin_serials)
            mask_pa_abn_lin = lin_fault['Serial'].isin(pa_abn_serials)
            lin_fault.loc[mask_pa_abn_lin, 'PA Status Pattern 2'] = 'PA abnormal lin'
    except:
        pass  # 如果组合条件处理失败，跳过

    return lin_fault


def label_method_pattern_2(samples):
    """
    新增的参数用于新pattern判定：statusBit, dpdRestartCounter, Lin alarm (统计单个SN对应的radio lin fault (elog16),
    fault LED state=ON (elog52) 出现的总数)
    """
    if samples is None:
        raise ValueError("样本集不能为空！")

    if not isinstance(samples, (list, tuple)):
        raise ValueError("样本集必须是一个列表或元组")

    # 首先将样本转换为DataFrame格式以便处理
    df_data = []
    for sample in samples:
        row_data = {
            'Serial': sample['Serial'],
            'ProductName': sample['ProductName'],
            'Timestamp': sample['Timestamp'],
            'branch': sample.get('branch', ''),
            'PA Status Pattern 2': sample.get('PA Status Pattern 2', '')
        }
        # 添加所有参数
        row_data.update(sample['parameters'])
        df_data.append(row_data)

    df = pd.DataFrame(df_data)

    # 应用新的打标方法
    df = _mark_lin_fault(df)

    # 将结果更新回样本
    for i, sample in enumerate(samples):
        if i < len(df):
            sample['PA Status Pattern 2'] = df.iloc[i]['PA Status Pattern 2']
            sample['Symptoms'] = df.iloc[i]['Symptoms']

    return samples
