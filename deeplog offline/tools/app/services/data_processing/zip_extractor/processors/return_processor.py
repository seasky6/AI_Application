import re
import os
import pandas as pd
from zipfile import ZipFile


class ReturnLogParser:
    """
    Parser for Radio Return log files.

    When a Radio is returned, its logs are collected into a zip archive that
    may have a non-uniform directory structure. This parser searches for files
    with the following basenames:

      - parget.txt: Contains metadata (e.g. SYS_HW_MARKET_NAME and SYS_HW_SERIAL)
      - elogread.txt: Log data for log_type "elog"
      - hwlogread.txt: Log data for log_type "hwlog"
      - vsread.txt: Log data for log_type "vsread" (future support)
      - csread.txt: Log data for log_type "csread" (future support)
      - tsread.txt: Log data for log_type "tsread" (future support)
      - trxstatus.txt: Log data for log_type "trx_status" (future support)

    The AuditDate is derived from the zip file's name, using the format:
      <prefix>_YYYYMMDD_hhmmss_Logfiles.zip

    For each log file (other than parget.txt), every line is treated as a log entry.
    Each log entry is recorded with the following columns:
      AuditDate, Serial, ProductName, log_type, log_line.

    Returns:
      A pandas DataFrame with the parsed log entries.
    """

    @staticmethod
    def parse(file_path: str) -> pd.DataFrame:
        print(f"DEBUG: Starting to parse return log file: {file_path}")

        try:
            audit_date = parse_return_date(file_path)
            print(f"DEBUG: Parsed audit date: {audit_date}")
        except Exception as e:
            print(f"DEBUG: Error parsing date: {e}")
            raise

        expected_files = {
            "parget.txt": "metadata",
            "elogread.txt": "elog",
            "hwlogread.txt": "hwlog",
            "vsread.txt": "vsread",
            "csread.txt": "csread",
            "tsread.txt": "tsread",
            "trxstatus.txt": "trx_status",
        }

        metadata = {}
        logs = {expected_files[key]: [] for key in expected_files if expected_files[key] != "metadata"}

        print(f"DEBUG: Expected files to look for: {list(expected_files.keys())}")

        try:
            with ZipFile(file_path, 'r') as z:
                file_list = z.namelist()
                print(f"DEBUG: Files found in zip: {file_list}")

                for name in z.namelist():
                    base = os.path.basename(name)
                    print(f"DEBUG: Processing file: {name}, basename: {base}")

                    if base in expected_files:
                        print(f"DEBUG: Found expected file: {base} -> {expected_files[base]}")
                        with z.open(name) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            print(f"DEBUG: Content length for {base}: {len(content)} characters")

                            if expected_files[base] == "metadata":
                                print(f"DEBUG: Parsing metadata from {base}")
                                metadata = parse_parget(content)
                                print(f"DEBUG: Metadata parsed: {metadata}")
                            else:
                                log_type = expected_files[base]
                                lines = content.splitlines()
                                print(f"DEBUG: Found {len(lines)} lines in {base} for log_type {log_type}")

                                logs[log_type].extend(lines)
                    else:
                        print(f"DEBUG: Skipping file {base} - not in expected files list")
        except Exception as e:
            print(f"DEBUG: Error processing zip file: {e}")
            raise

        serial = metadata.get("SYS_HW_SERIAL")
        raw_product_name = metadata.get("SYS_HW_MARKET_NAME")
        product_name = format_product_name(raw_product_name)

        print(f"DEBUG: Extracted serial: {serial}")
        print(f"DEBUG: Raw product name: {raw_product_name}")
        print(f"DEBUG: Formatted product name: {product_name}")

        # Vectorized creation of DataFrames per log type using list multiplication.
        df_list = []
        for log_type, lines_list in logs.items():
            print(f"DEBUG: Processing log_type {log_type}, found {len(lines_list)} lines")
            if lines_list:
                n = len(lines_list)
                df = pd.DataFrame({
                    "AuditDate": [audit_date] * n,
                    "Serial": [serial] * n,
                    "ProductName": [product_name] * n,
                    "log_type": [log_type] * n,
                    "log_line": lines_list
                })
                df_list.append(df)
                print(f"DEBUG: Created DataFrame for {log_type} with {n} rows")
            else:
                print(f"DEBUG: No lines found for log_type {log_type}")

        if df_list:
            result_df = pd.concat(df_list, ignore_index=True)
            print(f"DEBUG: Final DataFrame shape: {result_df.shape}")
        else:
            result_df = pd.DataFrame(columns=["AuditDate", "Serial", "ProductName", "log_type", "log_line"])
            print("DEBUG: No data found, creating empty DataFrame")
        return result_df


def parse_return_date(file_path: str) -> str:
    """
    Extracts the AuditDate (Return Date) from the zip file's name.

    The file name are expected to have the formats:
      format_1: YYYY-MM-DD_hh.mm.ss-<Serial>.zip
      format_2: <Serial>_YYYY-MM-DD_hh.mm.ss-<Serial>.zip
      format_3: <Serial>_YYYY-MM-DD hh.mm.ss - <Serial>.zip

    For example:
      "2025-02-14_15.44.50-E23F294124.zip" yields "2025-02-14T15:44:50".
      "CN39651926_2025-09-16_15.42.02-CN39651926.zip" yields "2025-09-16T15:42:02".
      "TU8U02JSH2_2025-06-18 23.18.28 - TU8U02JSH2"

    Returns:
      A string representing the audit date in ISO format ("YYYY-MM-DDTHH:MM:SS").
    """
    base = os.path.basename(file_path)
    print(f"DEBUG: Parsing date from filename: {base}")

    # 尝试匹配 format_1 格式: YYYY-MM-DD_hh.mm.ss-<Serial>.zip
    format_1 = r"^(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})-.*\.zip$"
    m_1 = re.match(format_1, base)
    if m_1:
        date_part = m_1.group(1)
        time_part = m_1.group(2).replace('.', ':')
        result = f"{date_part}T{time_part}"
        print(f"DEBUG: Date parsed successfully using format_1: {result}")
        return result

    # 尝试匹配 format_2 格式: <Serial>_YYYY-MM-DD_hh.mm.ss-<Serial>.zip
    format_2 = r"^.*_(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})-.*\.zip$"
    m_2 = re.match(format_2, base)
    if m_2:
        date_part = m_2.group(1)
        time_part = m_2.group(2).replace('.', ':')
        result = f"{date_part}T{time_part}"
        print(f"DEBUG: Date parsed successfully using format_2: {result}")
        return result

    # 尝试匹配 format_3 格式: <Serial>_YYYY-MM-DD hh.mm.ss - <Serial>.zip
    format_3 = r"^.*_(\d{4}-\d{2}-\d{2}) (\d{2}\.\d{2}\.\d{2})\s*-\s*.*\.zip$"
    m_3 = re.match(format_3, base)
    if m_3:
        date_part = m_3.group(1)
        time_part = m_3.group(2).replace('.', ':')
        result = f"{date_part}T{time_part}"
        print(f"DEBUG: Date parsed successfully using format_3: {result}")
        return result

    # 两种format都不匹配
    error_msg = f"Filename {base} does not match any expected return log format."
    print(f"DEBUG: Date parsing failed: {error_msg}")
    print(f"DEBUG: Patterns tried: {format_1} and {format_2} and {format_3}")
    raise ValueError(error_msg)


def parse_parget(content: str) -> dict:
    """
    Parses the content of a parget.txt file containing radio metadata.

    Expected format for each line is:
      'KEY' = 'VALUE'

    Lines not matching this pattern (such as warnings) are ignored.

    Returns:
      A dictionary mapping metadata keys to their corresponding values.
    """
    print(f"DEBUG: Starting to parse parget content, length: {len(content)}")
    meta = {}
    meta_pattern = re.compile(r"'([^']+)'\s*=\s*'([^']+)'")

    lines = content.splitlines()
    print(f"DEBUG: parget.txt has {len(lines)} lines")

    for i, line in enumerate(lines):
        match = meta_pattern.search(line)
        if match:
            key, value = match.groups()
            key = key.strip()
            value = value.strip()
            meta[key] = value
            print(f"DEBUG: Line {i}: Found metadata - '{key}' = '{value}'")
        else:
            print(f"DEBUG: Line {i}: No match - '{line}'")

    print(f"DEBUG: Final metadata dict: {meta}")
    return meta


def format_product_name(board_value):
    """
    Simplifies the raw board name:

    - If the board name starts with "AIR", remove the prefix and return
      "AIR " followed by the raw remainder.

    - If the board name starts with "RRU", remove the prefix and return
      "Radio " followed by the raw remainder.

    - Otherwise, returns the board value unchanged.

    This allows the ProductRegistry (which now normalizes keys) to handle
    product names with or without spaces.
    """
    if not board_value or pd.isna(board_value):
        return ""

    # 去掉board值中的空格符和'*'
    board_value = board_value.strip().rstrip('*')

    # 如果已经是Radio开头，进行清理
    if board_value.startswith("Radio"):
        # 提取Radio后面的部分
        radio_remainder = board_value[5:].strip()

        # 按空格分割，第一部分是型号，其余是波段部分
        parts = radio_remainder.split()
        if not parts:
            return board_value

        model_part = parts[0]
        band_parts = parts[1:] if len(parts) > 1 else []

        # 处理波段部分
        clean_bands = []
        for part in band_parts:
            # 跳过单独的"C"
            if part == "C":
                continue

            # 处理包含"44B"的情况
            if "44B" in part:
                # 提取所有B段
                bands = re.findall(r'B\d+', part)
                clean_bands.extend(bands)
            else:
                # 直接添加其他波段部分
                clean_bands.append(part)

        # 合并波段部分
        if clean_bands:
            band_part = "".join(clean_bands)
            return f"Radio {model_part} {band_part}"
        else:
            return f"Radio {model_part}"

    elif board_value.startswith("AIR"):
        return "AIR" + board_value[3:].strip()
    elif board_value.startswith("RRU"):
        remainder = board_value[3:]

        # 处理特殊case: RRUS12B3*
        if remainder.startswith("S12B3"):
            return "Radio S12 B3"

        # 处理包含"HP"的特殊格式: RRU4471HPB1 -> Radio 4471HP B1
        hp_match = re.search(r'^(\d{4}HP)(.*)$', remainder)
        if hp_match:
            model_part = hp_match.group(1)  # 4471HP
            band_part = hp_match.group(2)  # B1

            # 处理更复杂的HP格式: RRU4490HP44B144B3C -> Radio 4490HP B1B3
            # 提取所有B段并处理
            bands = re.findall(r'B\d+', band_part)

            # 清理每个B段：去掉前面的数字和末尾的C
            clean_bands = []
            for band in bands:
                # 提取B后面的数字部分
                band_digits = re.search(r'B(\d+)', band).group(1)

                # 去掉数字部分末尾的C（如果有）
                clean_digits = band_digits.rstrip('C')

                # 如果数字部分长度大于1，可能包含需要去掉的前缀数字
                # 例如："144" -> 去掉前面的"44"，保留"1"
                if len(clean_digits) > 1:
                    # 尝试找到数字部分的实际波段值
                    # 通常波段值是1-2位数字，前面的数字是重复的
                    # 例如：在"144"中，波段值可能是"1"或"44"
                    # 我们需要根据上下文判断

                    # 方法1：假设波段值总是最后1-2位数字
                    # 对于"144"，我们取"44"
                    # 但对于"B1"，我们希望保留"1"

                    # 方法2：更智能的方法 - 检查数字是否包含重复模式
                    # 例如："144"中的"44"是重复的，所以波段值应该是"1"
                    if len(clean_digits) >= 3 and clean_digits[1:] == clean_digits[1] * (len(clean_digits) - 1):
                        # 如果数字部分从第二位开始都是相同的数字，可能是重复模式
                        clean_digits = clean_digits[0]  # 取第一位作为波段值
                    elif len(clean_digits) == 2 and clean_digits[0] == clean_digits[1]:
                        # 如果两位数字相同，取一位即可
                        clean_digits = clean_digits[0]
                    # 否则保留所有数字

                clean_bands.append(f"B{clean_digits}")

            # 合并B段
            clean_band_part = ''.join(clean_bands)
            return f"Radio {model_part} {clean_band_part}"

        # 初始化变量
        model_number = ''
        i = 0
        n = len(remainder)

        # 提取Radio型号： 常规是前4位数字
        while i < n and len(model_number) < 4:
            if remainder[i].isdigit():
                model_number += remainder[i]
            i += 1

        # 如果不符合常规方式，则不解析直接返回所有值
        if not model_number:
            return 'Radio ' + remainder

        model_prefix = model_number[:2]
        remaining_str = remainder[i:]  # 去掉model number后剩余的部分

        # 找出所有B的位置
        b_indices = [idx for idx, ch in enumerate(remaining_str) if ch == 'B']

        if not b_indices:
            return f"Radio {model_number}"

        # 处理第一个B之前的部分
        first_b_pos = b_indices[0]
        if first_b_pos >= 2 and remaining_str[first_b_pos - 2:first_b_pos] == model_prefix:
            remaining_str = remaining_str[:first_b_pos - 2] + remaining_str[first_b_pos:]
            b_indices = [idx - 2 for idx in b_indices]  # 更新B的位置

        # 处理多个B之间的情况
        for i in range(len(b_indices) - 1):
            start = b_indices[i] + 1
            end = b_indices[i + 1]
            between_str = remaining_str[start:end]

            # 检查是否包含model_prefix
            if model_prefix in between_str:
                # 找到最后一个model_prefix出现的位置
                last_pos = between_str.rfind(model_prefix)
                # 去掉这个model_prefix
                between_str = between_str[:last_pos] + between_str[last_pos + len(model_prefix):]
                # 更新剩余字符串
                remaining_str = remaining_str[:start] + between_str + remaining_str[end:]
                # 更新后续B的位置
                b_indices[i + 1:] = [idx - len(model_prefix) for idx in b_indices[i + 1:]]

        # 提取所有B段
        bands = []
        current_pos = 0
        while True:
            b_pos = remaining_str.find('B', current_pos)
            if b_pos == -1:
                break
            # 找到B段结束位置（下一个B或字符串结尾）
            next_b = remaining_str.find('B', b_pos + 1)
            if next_b == -1:
                band = remaining_str[b_pos:]
                # 去掉末尾的C
                if band.endswith('C'):
                    band = band[:-1]
                bands.append(band)
                break
            else:
                bands.append(remaining_str[b_pos:next_b])
                current_pos = next_b

        # 合并bands
        band_part = ''.join(bands)
        return f"Radio {model_number} {band_part}"
    else:
        return board_value.strip()
