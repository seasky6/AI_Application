from typing import Any
from ..base_parser import BaseParser


class Elog16Parser(BaseParser):
    """
    Elog16解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse(self, **kwargs: Any) -> None:
        """
        解析Elog16条目
        示例:
        event log entry: 16: Lin. fault port CLin. fault port C On ; fault:1122; localId:65535; faultImpact:0x1000000
        解析后:
        'Content': 原始content_part,
        'Slogan': 'Lin. fault port CLin. fault port C On',
        'Key': 'fault',
        'Value': '1122',
        'ValueType': string,
        'IsMeasuredValue': false,
        'Key': 'localId',
        'Value': '65535',
        'ValueType': string,
        'IsMeasuredValue': false,
        'Key': 'faultImpact'
        'Value': '0x1000000'
        'ValueType': string,
        'IsMeasuredValue': false
        """
        content_part = kwargs['content_part']
        pa_measured_values = self.patterns.elog16.search(content_part)
        if not pa_measured_values:
            return

        slogan, fault, fault_value, local_id, local_id_value, fault_impact, fault_impact_value = pa_measured_values.groups()
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
            key=fault,
            value=str(fault_value),
            value_type='str',
            is_measured_value=False,
            parent_index=parent_index
        )

        self.base.add_log_entry(
            **entry_kwargs,
            key=local_id,
            value=str(local_id_value),
            value_type='str',
            is_measured_value=False,
            parent_index=parent_index
        )

        self.base.add_log_entry(
            **entry_kwargs,
            key=fault_impact,
            value=str(fault_impact_value),
            value_type='str',
            is_measured_value=False,
            parent_index=parent_index
        )
