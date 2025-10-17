from .base_parser import BaseParser


class ReadParser(BaseParser):
    """
    cs/vs/ts read解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse_read_entry(
            self,
            serial_number: str,
            product_name: str,
            log_type: str,
            log_line: str
    ) -> None:
        """
        示例：
        1. 简单键值对 (AverageSupply : 1.87 A)
        2. 键中包含冒号的 键值对 (DcBias:0 : 0 A)
        """
        entry = log_line.strip()
        if not entry:
            return

        # 分割键和值，从最后一个冒号处分割
        parts = entry.rsplit(':', 1)
        if len(parts) != 2:
            return

        key_part = parts[0].strip()
        raw_value = parts[1].strip()

        # 去除单位部分（最后一个空格后的内容）
        value_parts = raw_value.split()
        if len(value_parts) > 1:
            numeric_value = ' '.join(value_parts[:-1])  # 处理可能的多部分数值（如"-7.062 V"）
        else:
            numeric_value = raw_value

        # 确定值类型
        try:
            if '.' in numeric_value:
                value = float(numeric_value)
                value_type = 'float'
            else:
                value = int(numeric_value)
                value_type = 'int'
        except ValueError:
            value = numeric_value
            value_type = 'string'

        parent_index = self.base.log_index + 1

        self.base.add_log_entry(
            serial_number=str(serial_number),
            product_name=str(product_name),
            log_type=str(log_type),
            timestamp='',  # 空字符串
            log_id='',  # 空字符串
            content=entry,
            slogan='',  # 空字符串
            key=key_part,
            value=value,
            value_type=value_type,
            is_measured_value=True,  # 总是True
            parent_index=parent_index
        )
