from typing import Optional, TypedDict


class AlarmEntryDict(TypedDict):
    Index: int
    Serial: str
    ProductName: str
    PartName: str
    ProductNo: str
    HWrev: str
    Production: str
    Alarm_time: str
    Alarm_Name: str
    AdditionalInfo: str
    ParentIndex: int


class AlarmEntry:
    def __init__(
            self,
            index: int,
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
    ):
        self.index = index
        self.serial = serial
        self.product_name = product_name
        self.part_name = part_name
        self.production_no = production_no
        self.hw_rev = hw_rev
        self.production_time = production_time
        self.alarm_time = alarm_time
        self.alarm_name = alarm_name
        self.additional_info = additional_info
        self.parent_index = parent_index if parent_index is not None else index

    def alarm_to_dict(self) -> AlarmEntryDict:
        return {
            "Index": self.index,
            "Serial": self.serial,
            "ProductName": self.product_name,
            "PartName": self.part_name,
            "ProductionNo": self.production_no,
            "HWRev": self.hw_rev,
            "ProductionTime": self.production_time,
            "AlarmTime": self.alarm_time,
            "AlarmName": self.alarm_name,
            "AdditionalInfo": self.additional_info,
            "ParentIndex": self.parent_index
        }
