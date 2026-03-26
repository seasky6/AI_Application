from typing import Any
from ..base_parser import BaseParser


class Elog52Parser(BaseParser):
    """
    Elog52解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse(self, **kwargs: Any) -> None:
        """
        解析Elog52条目
        示例:
        Format description: <time stamp> <log id>: <slogan>: <state>; client: <id>
        Example:
        [171122 162310] 52: Fault led state: ON; client: 301
        解析后:
        'Content': 原始content_part,
        'Slogan': 'Fault led state',
        'Key': 'state',
        'Value': 'ON',
        'ValueType': string,
        'IsMeasuredValue': false,
        'Key': 'client',
        'Value': '301',
        'ValueType': string,
        'IsMeasuredValue': false,
        """
        content_part = kwargs['content_part']
        pa_measured_values = self.patterns.elog52.search(content_part)
        if not pa_measured_values:
            return

        slogan, state_value, client, client_value = pa_measured_values.groups()
        parent_index = self.base.log_index + 1

        entry_kwargs = {
            'serial_number': kwargs['serial_number'],
            'product_name': kwargs['product_name'],
            'log_type': kwargs['log_type'],
            'timestamp': kwargs['timestamp'],
            'log_id': kwargs['log_id'],
            'content': kwargs['content_part'],  # 新增原始内容列
            'slogan': slogan
        }

        self.base.add_log_entry(
            **entry_kwargs,
            key='state',
            value=str(state_value),
            value_type='str',
            is_measured_value=False,
            parent_index=parent_index
        )

        self.base.add_log_entry(
            **entry_kwargs,
            key=client,
            value=str(client_value),
            value_type='str',
            is_measured_value=False,
            parent_index=parent_index
        )
