from typing import List, Union, Optional
from tools.app.services.data_processing.log_parser.models.log_entry import LogEntry
from tools.app.services.data_processing.log_parser.models.alarm_entry import AlarmEntry
from tools.app.services.data_processing.log_parser.utils.log_patterns import Patterns


class BaseParser:
    """
    解析器基类
    """
    def __init__(self):
        self.log_entries: List[LogEntry] = []
        self.alarm_entries: List[AlarmEntry] = []
        self.log_index: int = 0
        self.alarm_index: int = 0
        self.patterns = Patterns()

    def reset_for_new_serial(self):
        """
        重置解析器状态以处理新的serial
        保留log_index和alarm_index的累计值
        """
        # 不需要清空log_entries和alarm_entries，因为我们要累积所有条目
        # 只需重置其他与serial相关的临时状态（如果有）
        pass

    # 主解析器 log_entry 的内部方法
    def _create_log_entry(
            self,
            serial_number: str,
            product_name: str,
            log_type: str,
            timestamp: str,
            log_id: str,
            content: str = '',  # 新增content字段
            slogan: str = '',
            key: str = '',
            value: Union[str, int, float, bool, List[int]] = '',
            value_type: str = '',
            is_measured_value: bool = False,
            parent_index: Optional[int] = None,
    ) -> LogEntry:
        self.log_index += 1
        return LogEntry(
            index=self.log_index,
            serial_number=serial_number,
            product_name=product_name,
            log_type=log_type,
            timestamp=timestamp,
            log_id=log_id,
            content=content,  # 新增content字段
            slogan=slogan,
            key=key,
            value=value,
            value_type=value_type,
            is_measured_value=is_measured_value,
            parent_index=parent_index if parent_index is not None else self.log_index
        )

    # 主解析器 log_entry 的外部方法
    def add_log_entry(
            self,
            serial_number: str,
            product_name: str,
            log_type: str,
            timestamp: str,
            log_id: str,
            content: str = '',  # 新增content字段（默认值为空，不影响之前调用）
            slogan: str = '',
            key: str = '',
            value: Union[str, int, float, bool, List[int]] = '',
            value_type: str = '',
            is_measured_value: bool = False,
            parent_index: Optional[int] = None,
    ) -> None:
        self.log_entries.append(self._create_log_entry(
            serial_number=serial_number,
            product_name=product_name,
            log_type=log_type,
            timestamp=timestamp,
            log_id=log_id,
            content=content,  # 新增content字段
            slogan=slogan,
            key=key,
            value=value,
            value_type=value_type,
            is_measured_value=is_measured_value,
            parent_index=parent_index
        ))

    # 主解析器 alarm_entry 的内部方法
    def _create_alarm_entry(
            self,
            serial: str,
            product_name: str,
            part_name: str,
            production_no: str,
            hw_rev: str,
            production_time: str,
            alarm_time: str,
            alarm_name: str,
            additional_info: str,
            parent_index: Optional[int] = None,
    ) -> AlarmEntry:
        self.alarm_index += 1
        return AlarmEntry(
            index=self.alarm_index,
            serial=serial,
            product_name=product_name,
            part_name=part_name,
            production_no=production_no,
            hw_rev=hw_rev,
            production_time=production_time,
            alarm_time=alarm_time,
            alarm_name=alarm_name,
            additional_info=additional_info,
            parent_index=parent_index if parent_index is not None else self.alarm_index
        )

    # 主解析器 alarm_entry 的外部方法
    def add_alarm_entry(
            self,
            serial_number: str,
            product_name: str,
            part_name: str,
            production_no: str,
            hw_rev: str,
            production_time: str,
            alarm_time: str,
            alarm_name: str,
            additional_info: str,
            parent_index: int
    ) -> None:
        self.alarm_entries.append(self._create_alarm_entry(
            serial=serial_number,
            product_name=product_name,
            part_name=part_name,
            production_no=production_no,
            hw_rev=hw_rev,
            production_time=production_time,
            alarm_time=alarm_time,
            alarm_name=alarm_name,
            additional_info=additional_info,
            parent_index=parent_index
        ))
