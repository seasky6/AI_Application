import re
import os
import pandas as pd
from datetime import datetime
from io import StringIO
from zipfile import ZipFile


class ProactiveLogParser:
    """
    Parser for proactive eNodeB log files.

    These logs are contained in a zip archive whose filename encodes the AuditDate.
    The archive contains a single .log file that includes the SDIC table (which provides
    metadata on connected radios) and the radio logs (output from console commands).

    The parser extracts:
      - AuditDate (from the zip file name),
      - the SDIC table (using parse_sdic_table),
      - and the radio logs (using parse_radio_logs).

    The resulting DataFrame has columns:
      AuditDate, Serial, ProductName, log_type, log_line.
    """

    @staticmethod
    def parse(file_path: str) -> pd.DataFrame:
        """
        Vectorized parsing of a raw .log file contained in a zip archive.
        Extracts AuditDate, the SDIC table, and radio logs.
        Returns a DataFrame with columns: AuditDate, Serial, ProductName, log_type, log_line.
        """
        print(f"DEBUG [Proactive]: Starting to parse proactive log file: {file_path}")

        # Open the ZIP archive.
        with ZipFile(file_path, 'r') as z:
            # Find the first file ending in .log (case-insensitive)
            log_filename = None
            namelist = z.namelist()
            print(f"DEBUG [Proactive]: Files in zip: {namelist}")

            for name in namelist:
                if name.lower().endswith(".log"):
                    log_filename = name
                    break
            if not log_filename:
                error_msg = "No .log file found in the zip archive."
                print(f"DEBUG [Proactive]: {error_msg}")
                raise ValueError(error_msg)

            print(f"DEBUG [Proactive]: Using log file: {log_filename}")

            # Read and decode the .log file from the zip archive.
            with z.open(log_filename) as log_file:
                content = log_file.read().decode("utf-8", errors="ignore")
                lines = content.splitlines()
                print(f"DEBUG [Proactive]: Log file has {len(lines)} lines")
                # 打印前几行内容以供检查
                if lines:
                    print(f"DEBUG [Proactive]: First 5 lines of log file:")
                    for i, line in enumerate(lines[:5]):
                        print(f"DEBUG [Proactive]: Line {i}: {line}")

        # Use pandas vectorized string methods to find the audit date.
        lines_df = pd.Series(lines)

        # 解析审计日期
        try:
            audit_date = parse_audit_date(file_path)
            print(f"DEBUG [Proactive]: Audit date parsed: {audit_date}")
        except Exception as e:
            print(f"DEBUG [Proactive]: Error parsing audit date: {e}")
            # 尝试备用方法提取日期
            audit_date = fallback_parse_audit_date(file_path)
            print(f"DEBUG [Proactive]: Using fallback audit date: {audit_date}")

        # 解析SDIC表
        try:
            sdic_df = parse_sdic_table(lines)
            print(f"DEBUG [Proactive]: SDIC table parsed, shape: {sdic_df.shape}")
            if not sdic_df.empty:
                print(f"DEBUG [Proactive]: SDIC columns: {sdic_df.columns.tolist()}")
                print(f"DEBUG [Proactive]: SDIC head:\n{sdic_df.head()}")
            else:
                print(f"DEBUG [Proactive]: SDIC table is empty")
        except Exception as e:
            print(f"DEBUG [Proactive]: Error parsing SDIC table: {e}")
            # 创建空的SDIC表作为备用
            sdic_df = pd.DataFrame(columns=['LNH', 'BOARD', 'SERIAL'])
            print(f"DEBUG [Proactive]: Using empty SDIC table")

        # 解析SDIC日志
        try:
            radio_logs_df = parse_radio_logs(lines_df, sdic_df)
            print(f"DEBUG [Proactive]: Radio logs parsed, shape: {radio_logs_df.shape}")
            if not radio_logs_df.empty:
                print(f"DEBUG [Proactive]: Radio logs columns: {radio_logs_df.columns.tolist()}")
                print(f"DEBUG [Proactive]: Radio logs head:\n{radio_logs_df.head()}")
            # Ensure AuditDate is set for all rows.
            radio_logs_df["AuditDate"] = audit_date
            return radio_logs_df
        except Exception as e:
            print(f"DEBUG [Proactive]: Error parsing radio logs: {e}")
            # 返回空的DataFrame作为备用
            empty_df = pd.DataFrame(columns=["Serial", "ProductName", "log_type", "log_line"])
            empty_df["AuditDate"] = audit_date
            return empty_df


def parse_sdic_table(lines):
    """
    Extracts the SDIC table from the log file which describes the connected Radios.
    The header is identified by the presence of 'FRU' and 'PRODUCTNUMBER'.
    Lines that consist entirely of '=' are skipped.
    The table ends when a line consists entirely of '-' or '*' characters.
    The table is then loaded into a pandas DataFrame using the header row from the table.

    Returns:
      A pandas DataFrame.
    """
    print(f"DEBUG [Proactive]: Parsing SDIC table from {len(lines)} lines")

    # Define possible header formats
    standard_headers = ['LNH', 'BOARD', 'SERIAL']
    alternative_headers = ['XPBOARD', 'SERIAL/NAME', 'MO (LNH)']

    table_lines = []
    header_found = False
    using_alternative_format = False

    print(f"DEBUG [Proactive]: Looking for SDIC table header...")

    for i, line in enumerate(lines):
        stripped = line.strip() if isinstance(line, str) else str(line)
        if not stripped:
            continue

        # 跳过分隔行
        if all(c == '=' for c in stripped):
            continue

        # 表结束检测
        if header_found and all(c in "-*" for c in stripped):
            print(f"DEBUG [Proactive]: End of table detected at line {i}")
            break

        # 头部检测
        if not header_found:
            # 按分号分割行并清理头部
            headers = [h.strip() if isinstance(h, str) else str(h) for h in stripped.split(';') if h and str(h).strip()]
            # print(f"DEBUG [Proactive]: Line {i} headers: {headers}")

            # 检查标准头部
            if all(h in headers for h in standard_headers):
                header_found = True
                actual_headers = headers
                table_lines.append(stripped)
                print(f"DEBUG [Proactive]: Found standard headers: {actual_headers}")
                continue

            # 检查替代头部
            if all(h in headers for h in alternative_headers):
                header_found = True
                using_alternative_format = True
                actual_headers = headers
                table_lines.append(stripped)
                print(f"DEBUG [Proactive]: Found alternative headers: {actual_headers}")
                continue

        if header_found:
            table_lines.append(stripped)

    if not header_found:
        print(f"DEBUG [Proactive]: No valid header found in SDIC table")
        return pd.DataFrame(columns=alternative_headers if using_alternative_format else standard_headers)

    print(f"DEBUG [Proactive]: Found {len(table_lines)} table lines")
    if table_lines:
        print(f"DEBUG [Proactive]: First few table lines: {table_lines[:3]}")

    # 解析表格
    try:
        table_str = "\n".join(table_lines)
        df = pd.read_csv(StringIO(table_str), sep=";", engine="python", dtype=str)
        print(f"DEBUG [Proactive]: Successfully parsed SDIC table with {len(df)} rows")
    except Exception as e:
        print(f"DEBUG [Proactive]: Error parsing SDIC table: {e}")
        return pd.DataFrame(columns=['LNH', 'BOARD', 'SERIAL'])

    # 清理列 - 只对字符串列应用strip
    df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]
    for col in df.select_dtypes(include="object").columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].str.strip()

    # 只选择所需的列
    required_columns = alternative_headers if using_alternative_format else standard_headers
    result_df = pd.DataFrame()
    for col in required_columns:
        if col in df.columns:
            result_df[col] = df[col]
        else:
            result_df[col] = None

    print(f"DEBUG [Proactive]: Final SDIC table shape: {result_df.shape}")
    return result_df


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


def parse_audit_date(file_path: str) -> str:
    """
    Extracts the AuditDate from the zip file's name.
    Expected format: <prefix>_YYYYMMDD_hhmmss_Logfiles.zip
    Returns the date as "YYYY-MM-DD THH:MM:SS".
    """
    base = os.path.basename(file_path)
    print(f"DEBUG [Proactive]: Parsing audit date from filename: {base}")

    patterns = [
        r".*_(\d{8})_(\d{6})_Logfiles\.zip$",
        r".*_(\d{8})_(\d{6})_logfiles\.zip$",
    ]

    for i, pattern in enumerate(patterns):
        print(f"DEBUG [Proactive]: Trying pattern {i}: {pattern}")
        m = re.match(pattern, base, re.IGNORECASE)
        if m:
            print(f"DEBUG [Proactive]: Pattern {i} matched: {m.groups()}")
            try:
                if len(m.groups()) == 2:
                    date_part = m.group(1)  # e.g. "20241118" or "2024-11-18"
                    time_part = m.group(2)  # e.g. "121415" or "12.14.15"

                    # 标准化日期格式
                    if '-' in date_part:
                        # 已经是YYYY-MM-DD格式
                        date_str = date_part
                    else:
                        # 转换为YYYY-MM-DD格式
                        date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"

                    # 标准化时间格式
                    if '.' in time_part:
                        # 已经是HH.MM.SS格式，转换为HH:MM:SS
                        time_str = time_part.replace('.', ':')
                    else:
                        # 转换为HH:MM:SS格式
                        time_str = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"

                    result = f"{date_str}T{time_str}"
                    print(f"DEBUG [Proactive]: Date parsed successfully: {result}")
                    return result
            except Exception as e:
                print(f"DEBUG [Proactive]: Error processing pattern {i}: {e}")
                continue

        # 如果所有模式都失败
    error_msg = f"Filename {base} does not match any expected pattern."
    print(f"DEBUG [Proactive]: {error_msg}")
    raise ValueError(error_msg)


def fallback_parse_audit_date(file_path: str) -> str:
    """
    Fallback method to extract audit date when the primary method fails.
    """
    base = os.path.basename(file_path)
    print(f"DEBUG [Proactive]: Fallback parsing date from filename: {base}")

    # 尝试从文件名中提取任何看起来像日期的部分
    # 查找8位数字序列（可能代表YYYYMMDD）
    date_match = re.search(r'(\d{8})', base)
    if date_match:
        date_part = date_match.group(1)
        date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        print(f"DEBUG [Proactive]: Extracted date from filename: {date_str}")
    else:
        # 使用文件修改时间作为备用
        mtime = os.path.getmtime(file_path)
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        print(f"DEBUG [Proactive]: Using file modification date: {date_str}")

    # 查找6位数字序列（可能代表HHMMSS）
    time_match = re.search(r'(\d{6})', base)
    if time_match and time_match != date_match:
        time_part = time_match.group(1)
        time_str = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
        print(f"DEBUG [Proactive]: Extracted time from filename: {time_str}")
    else:
        # 使用当前时间作为备用
        time_str = "00:00:00"
        print(f"DEBUG [Proactive]: Using default time: {time_str}")

    result = f"{date_str}T{time_str}"
    print(f"DEBUG [Proactive]: Fallback date parsed: {result}")
    return result


def parse_radio_logs(lines_df, sdic_df):
    """
    Parses radio logs based on the SDIC table format.
    Handles two formats:
    1. Standard format: {'LNH', 'BOARD', 'SERIAL'}
       - Command pattern: "coli>/fruacc/lhsh <LNH> <log_type> [read|status]"
    2. Alternative format: {'MO (LNH)', 'XPBOARD', 'SERIAL/NAME'}
       - Command pattern: "$ lhsh <LNH> <log_type> [read|status]"
    """
    print(f"DEBUG [Proactive]: Parsing radio logs, SDIC shape: {sdic_df.shape}")

    # Create a DataFrame from the Series with the original order preserved
    df = pd.DataFrame({"line": lines_df})

    # Determine SDIC format type
    sdic_format = 'standard'
    if 'MO (LNH)' in sdic_df.columns or 'XPBOARD' in sdic_df.columns or 'SERIAL/NAME' in sdic_df.columns:
        sdic_format = 'alternative'
        print(f"DEBUG [Proactive]: Using alternative SDIC format")

    # Initialize columns
    df["command"] = None
    df["raw_log_type"] = None
    df["command_LNH"] = None

    if sdic_format == 'standard':
        # Identify command lines and extract LNH and raw_log_type.
        # The command can be: coli>/fruacc/lhsh <LNH> <log_type> [read|status]
        cmd_pattern = r"coli>/fruacc/lhsh\s+(\S+)\s+(\S+)(?:\s+(read|status))?"
        df["command"] = df["line"].str.extract(cmd_pattern, expand=False)[0]                  # e.g. BXP_7
        df["raw_log_type"] = df["line"].str.extract(cmd_pattern, expand=False)[1].str.lower()  # e.g. trx
        print(f"DEBUG [Proactive]: Found {df['command'].notna().sum()} command lines (standard format)")
    else:
        # Alternative format: $ lhsh <LNH> <log_type> [read|status]
        cmd_pattern = r"\$ lhsh\s+(\S+)\s+(\S+)(?:\s+(read|status))?"
        df["command"] = df["line"].str.extract(cmd_pattern, expand=False)[0]                  # e.g. 000100/port_0_dev_6
        df["raw_log_type"] = df["line"].str.extract(cmd_pattern, expand=False)[1].str.lower()  # e.g. sfp
        print(f"DEBUG [Proactive]: Found {df['command'].notna().sum()} command lines (alternative format)")

    # Map raw log type to our standard type.
    log_type_map = {
        "cs": "csread",
        "vs": "vsread",
        "ts": "tsread",
        "elog": "elog",
        "hwlog": "hwlog",
        "trx": "trx_status",
    }
    df["log_type"] = df["raw_log_type"].map(log_type_map)

    # Forward-fill the command context columns so that every output line
    # gets the most recent command's LNH and log_type.
    df["command"] = df["command"].ffill().astype(object)
    df["log_type"] = df["log_type"].ffill().astype(object)

    # Identify output lines that start with an LNH followed by a colon and a space.
    out_pattern = r"^(\S+):\s+(.*)"
    out_extracted = df["line"].str.extract(out_pattern, expand=True)

    # 对 standard format 直接使用提取值
    if sdic_format == 'standard':
        df["out_LNH"] = out_extracted[0]  # e.g. BXP_7
    else:
        # 对 alternative format 转换提取值
        df["out_LNH"] = out_extracted[0].str.replace(
            r'^(\d{4})p(\d+)d(\d+)$',
            lambda m: f"{m.group(1)}00/port_{m.group(2)}_dev_{m.group(3)}",
            regex=True
        )                                 # e.g. original: 0001p1d7; updated: 000100/port_1_dev_7 (align with 'command')

    df["log_line"] = out_extracted[1]

    # Now filter to the rows that are output lines (i.e. where log_line is not null)
    df_output = df[(df["log_line"].notna()) & (df["log_type"].notna())].copy()
    print(f"DEBUG [Proactive]: Found {len(df_output)} output lines before LNH matching")

    # Only keep rows where the output line's LNH matches the command's LNH.
    df_output = df_output[df_output["out_LNH"] == df_output["command"]]
    print(f"DEBUG [Proactive]: Found {len(df_output)} output lines after LNH matching")

    df_output = df_output.rename(columns={"command": "LNH"}).reset_index(drop=True)

    # Merge with the SDIC table (assume sdic_df has a column "LNH")
    if sdic_format == 'alternative':
        # For alternative format, ensure we're using the correct columns
        if 'MO (LNH)' in sdic_df.columns:
            # 提取括号内的内容，没有括号的设为空字符串
            sdic_df['LNH'] = sdic_df['MO (LNH)'].apply(
                lambda x: x.split('(')[1].split(')')[0] if '(' in x and ')' in x else ''
            )
            sdic_df.drop('MO (LNH)', axis=1, inplace=True)

        if 'XPBOARD' in sdic_df.columns:
            sdic_df = sdic_df.rename(columns={'XPBOARD': 'BOARD'})

        if 'SERIAL/NAME' in sdic_df.columns:
            sdic_df = sdic_df.rename(columns={'SERIAL/NAME': 'SERIAL'})

    # 合并SDIC数据
    if not sdic_df.empty:
        df_output = df_output.merge(sdic_df, left_on="LNH", right_on="LNH", how="left")
        print(f"DEBUG [Proactive]: After merging with SDIC, shape: {df_output.shape}")
    else:
        print(f"DEBUG [Proactive]: SDIC table is empty, skipping merge")
        df_output["BOARD"] = None
        df_output["SERIAL"] = None

    # 应用产品名称格式化器到BOARD列
    df_output["ProductName"] = df_output["BOARD"].apply(format_product_name)
    df_output["Serial"] = df_output["SERIAL"]

    # 选择所需的列
    df_final = df_output[["Serial", "ProductName", "log_type", "log_line"]]

    print(f"DEBUG [Proactive]: Final radio logs shape: {df_final.shape}")
    return df_final
