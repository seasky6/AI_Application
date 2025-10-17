from .base_parser import BaseParser


class PareadallParser(BaseParser):
    """
    pa-read-all解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse_pareadall_entry(
            self,
            serial_number: str,
            product_name: str,
            log_type: str,
            log_line: str
    ) -> None:
        """
        示例：
        Invalid command: pa
        Execute 'help' for available commands
        解析后：
        'Slogan': Execute 'help' for available commands,
        'Key':  Invalid command,
        'Value': pa,
        'ValueType': string,
        'IsMeasuredValue': False,
        """
        line = log_line.strip()

        parent_index = self.base.log_index + 1

        m_invalid = self.patterns.pareadall.match(line)
        if m_invalid:
            key = m_invalid.group(1)
            value = m_invalid.group(2)
            slogan = "Execute 'help' for available commands"
            self.base.add_log_entry(
                serial_number=serial_number,
                product_name=product_name,
                log_type=log_type,
                timestamp='',
                log_id='',
                content='',
                slogan=slogan,
                key=key,
                value=value,
                value_type='string',
                is_measured_value=False,
                parent_index=parent_index
            )
