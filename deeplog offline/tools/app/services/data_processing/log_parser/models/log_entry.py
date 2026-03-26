from typing import List, Union, Optional, Literal, TypedDict

# 类型定义
LogValue = Union[str, int, float, bool, List[int]]
LogType = Literal['elog', 'hwlog', 'pareadall', 'csread', 'vsread', 'tsread', 'trx_status']


class LogEntryDict(TypedDict):
    Index: int
    Serial: str
    ProductName: str
    LogType: str
    Timestamp: str
    LogID: str
    Content: str          # 新增Content字段
    Slogan: str
    Key: str
    Value: LogValue
    ValueType: str
    IsMeasuredValue: bool
    ParentIndex: int


class LogEntry:
    """ 解析后的数据对象格式 """
    def __init__(
            self,
            index: int,
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
    ):
        self.index = index
        self.serial_number = serial_number
        self.product_name = product_name
        self.log_type = log_type
        self.timestamp = timestamp
        self.log_id = log_id
        self.content = content   # 新增赋值content
        self.slogan = slogan
        self.key = key
        self.value = value if value is not None else ''
        self.value_type = value_type
        self.is_measured_value = is_measured_value
        self.parent_index = parent_index if parent_index is not None else index

    def log_to_dict(self) -> LogEntryDict:
        return {
            'Index': self.index,
            'Serial': self.serial_number,
            'ProductName': self.product_name,
            'LogType': self.log_type,
            'Timestamp': self.timestamp,
            'LogID': self.log_id,
            'Content': self.content,  # 新增Content字段
            'Slogan': self.slogan,
            'Key': self.key,
            'Value': self.value,
            'ValueType': self.value_type,
            'IsMeasuredValue': self.is_measured_value,
            'ParentIndex': self.parent_index
        }
