import re
from typing import Union, Tuple, List
from .base_parser import BaseParser
from .elog.elog10_parser import Elog10Parser
from .elog.elog16_parser import Elog16Parser
from .elog.elog27_parser import Elog27Parser
from .elog.elog42_43_parser import Elog42and43Parser
from .elog.elog52_parser import Elog52Parser
from tools.app.services.data_processing.log_parser.utils.parse_timestamp import parse_timestamp
import logging


logger = logging.getLogger(__name__)
LogValue = Union[str, int, float, bool, List[int]]


def _process_value(value: str) -> Tuple[LogValue, str, bool]:
    """智能处理各种值类型"""
    lower_val = value.lower()
    if lower_val == 'true':
        return True, 'bool', False
    if lower_val == 'false':
        return False, 'bool', False

    unit_patterns = [
        (r'^(\d+)W$', 'int'),
        (r'^([\d.]+)\s*dBm', 'float'),
        (r'^(\d+)\s*\[', 'float')
    ]

    for pattern, vtype in unit_patterns:
        match = re.match(pattern, value)
        if match:
            try:
                num = float(match.group(1)) if vtype == 'float' else int(match.group(1))
                if '[' in value:
                    num = round(num * 0.1, 1)
                return num, vtype, True
            except ValueError:
                continue

    try:
        return int(value), 'int', True
    except ValueError:
        try:
            return float(value), 'float', True
        except ValueError:
            return value, 'string', False


class ElogParser(BaseParser):
    """
    Elog主解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns
        self._product_elog_map = {}  # 用于存储产品序列号

    def _find_matching_elog10_entry(self, serial_number: str) -> tuple:
        """
        根据序列号查找匹配的elog ID=10条目的时间戳和父索引
        返回 (timestamp, parent_index) 元组
        """
        # 如果已经有缓存，直接返回
        if serial_number in self._product_elog_map:
            return self._product_elog_map[serial_number]

        # 否则查找最近的elog10条目
        for idx, entry in enumerate(reversed(self.base.log_entries)):
            if entry.serial_number == serial_number and entry.log_id == '10':
                # 存储时间戳和原始索引（非反向索引）
                result = (entry.timestamp, entry.index)
                self._product_elog_map[serial_number] = result
                return result

        return '', -1  # 如果没有找到匹配的elog10条目，返回空字符串和-1

    # ElogParser 解析器外部方法
    def parse_elog_entry(
            self,
            serial_number: str,
            product_name: str,
            log_type: str,
            log_line: str
    ) -> None:
        """
        解析elog条目
        """
        TERMINATION_PHRASES = {
            'End of log',
            'END',
            'WARNING: /fruacc/lhsh is deprecated and might not work. Registered COLIs might be missing and supported COLIs could fail to execute. please use LDN to adress and execute COLIs.',
            'Example:',
            'ManagedElement=1,Equipment=1,FieldReplaceableUnit=1 /fruacc/vii'
        }
        if log_line.strip() in TERMINATION_PHRASES:
            return

        base_match = self.patterns.elog.match(log_line)

        # 处理elog10的纯键值对条目
        if not base_match:
            line = log_line

            if line.startswith('####'):
                line = line[4:].strip()

            # 获取匹配的elog10时间戳
            timestamp, parent_index = self._find_matching_elog10_entry(serial_number)

            # 处理Carrier Info内容
            if ':' not in line:
                self.base.add_log_entry(
                    serial_number=serial_number,
                    product_name=product_name,
                    log_type=log_type,
                    timestamp=timestamp,
                    log_id='10',
                    content=line,
                    slogan='Event trace',
                    key='Carrier Info',
                    value=line,
                    value_type='string',
                    is_measured_value=False,
                    parent_index=parent_index
                )
            # 处理一般键值对
            else:
                key, value = line.split(':', 1)
                processed_val, val_type, is_measured = _process_value(value.strip())

                self.base.add_log_entry(
                    serial_number=serial_number,
                    product_name=product_name,
                    log_type=log_type,
                    timestamp=timestamp,
                    log_id='10',
                    content=line,
                    slogan='Event trace',
                    key=key,
                    value=processed_val,
                    value_type=val_type,
                    is_measured_value=is_measured,
                    parent_index=parent_index
                )
            return

        # 处理elog10的标准format条目
        date_str, time_str, log_id, content_part = base_match.groups()
        timestamp = parse_timestamp(date_str, time_str)
        current_index = self.base.log_index + 1

        # 如果是elog10条目，缓存它的时间戳
        if log_id == '10':
            self._product_elog_map[serial_number] = (timestamp, current_index)

        parsers = {
            '10': Elog10Parser(self.base),
            '16': Elog16Parser(self.base),
            '27': Elog27Parser(self.base),
            '42': Elog42and43Parser(self.base),
            '43': Elog42and43Parser(self.base),
            '52': Elog52Parser(self.base)
        }

        if log_id in parsers:
            parsers[log_id].parse(
                serial_number=serial_number,
                product_name=product_name,
                log_type=log_type,
                timestamp=timestamp,
                log_id=log_id,
                content_part=content_part
            )
        else:
            self.base.add_log_entry(
                serial_number=serial_number,
                product_name=product_name,
                log_type=log_type,
                timestamp=timestamp,
                log_id=log_id,
                content=content_part,
                slogan=content_part,
                key='',
                value='',
                value_type='',
                is_measured_value=False,
                parent_index=current_index
            )
