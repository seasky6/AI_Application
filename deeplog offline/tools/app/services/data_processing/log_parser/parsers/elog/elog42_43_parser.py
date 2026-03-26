from typing import Any
from ..base_parser import BaseParser


class Elog42and43Parser(BaseParser):
    """
    Elog42,43解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse(self, **kwargs: Any) -> None:
        """
        解析Elog42, 43条目
        Elog42示例：
        elog ID=42, content=Temperature: T_Mpa_A 493;393;553;445,T_Mpa_B 495;395;570;446,T_Mpa_C 493;388;563;442,
        T_Mpa_D 470;375;533;426
        解析后:
        'Content': 原始content_part,
        'Slogan': Temperature,
        'Key': T_Mpa_A,
        'Value': [493, 393, 553, 445],
        'ValueType': List[int],
        'IsMeasuredValue': True,
        ... ...

        Elog43示例：
        elog ID=43, content=PA current: I_Mpa0_B 328;162;546;254,I_Mpa1_B 103;33;237;76,I_Mpa2_B 102;33;238;76
        解析后:
        'Content': 原始content_part,
        'Slogan': PA current,
        'Key': I_Mpa0_B,
        'Value': [328, 162, 546, 254],
        'ValueType': List[int],
        'IsMeasuredValue': True,
        ... ...
        """
        content_part = kwargs['content_part']
        pattern = self.patterns.elog42 if kwargs['log_id'] == '42' else self.patterns.elog43
        match = pattern.search(content_part)
        if not match:
            return

        data = match.group(1)
        entries = data.split(',')
        if not entries:
            return

        parent_index = self.base.log_index + 1

        slogan = 'Temperature' if kwargs['log_id'] == '42' else 'PA current'

        entry_kwargs = {
            'serial_number': kwargs['serial_number'],
            'product_name': kwargs['product_name'],
            'log_type': kwargs['log_type'],
            'timestamp': kwargs['timestamp'],
            'log_id': kwargs['log_id'],
            'content': content_part,  # 新增content字段
            'slogan': slogan
        }

        try:
            for entry in entries:
                key, values = entry.strip().split(' ')
                if values == 'count_0':
                    values_list = values
                    self.base.add_log_entry(
                        **entry_kwargs,
                        key=key,
                        value=values_list,
                        value_type='str',
                        is_measured_value=False,
                        parent_index=parent_index
                    )
                else:
                    values_list = list(map(int, values.split(';')))
                    self.base.add_log_entry(
                        **entry_kwargs,
                        key=key,
                        value=values_list,
                        value_type='List[int]',
                        is_measured_value=True,
                        parent_index=parent_index
                    )

        except ValueError as e:
            print(f"错误解析值: {e}")
