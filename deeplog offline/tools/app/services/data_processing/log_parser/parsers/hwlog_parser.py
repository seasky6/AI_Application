from .base_parser import BaseParser
from tools.app.services.data_processing.log_parser.utils.parse_timestamp import parse_timestamp


class HWlogParser(BaseParser):
    """
    HWlog解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse_hwlog_entry(
            self,
            serial_number: str,
            product_name: str,
            log_type: str,
            log_line: str
    ) -> None:
        """
        解析 hwlog
        示例：

        """
        entry = log_line.strip()
        # 跳过标题行
        if entry.startswith('no') and 'logid' in entry and 'time' in entry and 'msg' in entry:
            return
        if set(entry) <= {'-', ' '}:
            return

        parent_index = self.base.log_index + 1

        m = self.patterns.hwlog.match(entry)
        if m:
            no, hwlog_id, date_str, time_str, msg = m.groups()
            date_str = date_str.replace('-', '')
            time_str = time_str.replace(':', '')
            timestamp = parse_timestamp(date_str, time_str)

            # 拼接no到slogan
            slogan_str = f"no {no}"
            self.base.add_log_entry(
                serial_number=serial_number,
                product_name=product_name,
                log_type=log_type,
                timestamp=timestamp,
                log_id=hwlog_id,
                content='',
                slogan=slogan_str,
                key='msg',
                value=msg,
                value_type='string',
                is_measured_value=False,
                parent_index=parent_index,
            )
