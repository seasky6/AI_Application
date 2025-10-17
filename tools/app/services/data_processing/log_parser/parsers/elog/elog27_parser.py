from typing import Any
from ..base_parser import BaseParser


class Elog27Parser(BaseParser):
    """
    Elog27解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse(self, **kwargs: Any) -> None:
        """
        解析Elog27条目
        示例:
        elog ID=27, content=PA measured values for driver name: PaVddSv:1; value: 45902; branch Id: 1
        解析后:
        'Content': 原始content_part,
        'Slogan': PA measured values for,
        'Key': 'driver name',
        'Value': 'PaVddSv:1',
        'ValueType': string,
        'IsMeasuredValue': false
        ... ...
        """
        content_part = kwargs['content_part']
        pa_measured_values = self.patterns.elog27.search(content_part)
        if not pa_measured_values:
            return

        driver_name, value, branch_id = pa_measured_values.groups()
        parent_index = self.base.log_index + 1

        entry_kwargs = {
            'serial_number': kwargs['serial_number'],
            'product_name': kwargs['product_name'],
            'log_type': kwargs['log_type'],
            'timestamp': kwargs['timestamp'],
            'log_id': kwargs['log_id'],
            'content': kwargs['content_part'],  # 新增原始内容列
            'slogan': 'PA measured values for'
        }

        self.base.add_log_entry(
            **entry_kwargs,
            key=driver_name,
            value=int(value),
            value_type='int',
            is_measured_value=True,
            parent_index=parent_index
        )

        # self.base.add_log_entry(
        #     **entry_kwargs,
        #     key='value',
        #     value=int(value),
        #     value_type='int',
        #     is_measured_value=True,
        #     parent_index=parent_index
        # )
        #
        # self.base.add_log_entry(
        #     **entry_kwargs,
        #     key='branch id',
        #     value=branch_id,
        #     value_type='string',
        #     is_measured_value=False,
        #     parent_index=parent_index
        # )
