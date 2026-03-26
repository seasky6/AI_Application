from typing import Dict, List, Any, Union
from ..base_parser import BaseParser
import logging

logger = logging.getLogger(__name__)
LogValue = Union[str, int, float, bool, List[int]]


class Elog10Parser:
    """
    Elog10解析器，支持：
    1. ABN格式 主行解析
    2. Case格式 主行解析
    """
    def __init__(self, base_parser: BaseParser):
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse(self, **kwargs: Any) -> None:
        """主解析入口"""
        line = kwargs['content_part']
        if not line:
            return

        parent_index = self.base.log_index + 1
        entry_kwargs = {
            'serial_number': kwargs['serial_number'],
            'product_name': kwargs['product_name'],
            'log_type': kwargs['log_type'],
            'timestamp': kwargs['timestamp'],
            'log_id': kwargs['log_id'],
            'content': line,  # 你的content字段
        }

        if 'ABN:' in line:
            self._parse_abn_format(entry_kwargs, line, parent_index)
        elif 'Case:' in line:
            self._parse_case_format(entry_kwargs, line, parent_index)
        # 针对elog10条目中内容为空的 - e.g. [250128 150053]   10:
        else:
            self.base.add_log_entry(
                **entry_kwargs,
                slogan='',
                key='',
                value='',
                value_type='',
                is_measured_value=False,
                parent_index=parent_index
            )

    def _parse_abn_format(self, entry_kwargs: Dict, line: str, parent_index: int) -> None:
        """完整解析ABN格式"""
        slogan, content = line.split(':', 1)
        slogan = slogan.strip()
        content = content.strip()

        abn_parts = content.split(' ', 2)
        abn_value = abn_parts[1][:-1] if len(abn_parts) > 1 else ''

        self.base.add_log_entry(
            **entry_kwargs,
            slogan=slogan,
            key='ABN',
            value=abn_value,
            value_type='string',
            is_measured_value=False,
            parent_index=parent_index
        )

        if len(abn_parts) > 2:
            for key, value in self.patterns.elog10_abn.findall(abn_parts[2]):
                self.base.add_log_entry(
                    **entry_kwargs,
                    slogan=slogan,
                    key=key.strip(),
                    value=value.strip(),
                    value_type='string',
                    is_measured_value=False,
                    parent_index=parent_index
                )

    def _parse_case_format(self, entry_kwargs: Dict, line: str, parent_index: int) -> None:
        """完整解析Case格式"""
        slogan, content = line.split(':', 1)
        slogan = slogan.strip()
        content = content.strip()

        case_match = self.patterns.elog10_case.search(content)
        if case_match:
            self.base.add_log_entry(
                **entry_kwargs,
                slogan=slogan,
                key='Case',
                value=case_match.group(1),
                value_type='string',
                is_measured_value=False,
                parent_index=parent_index
            )

            if case_match.group(2):
                self.base.add_log_entry(
                    **entry_kwargs,
                    slogan=slogan,
                    key='Event ID',
                    value=case_match.group(2),
                    value_type='string',
                    is_measured_value=False,
                    parent_index=parent_index
                )
