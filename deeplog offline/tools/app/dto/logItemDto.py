from pydantic import BaseModel
from typing import Optional, Any

class LogItemDto(BaseModel):
    index: int
    timestamp: str
    elog_id: str
    key: Optional[str] = ''
    value: Optional[Any] = ''
    value_type: Optional[str] = ''
    is_measured_value: bool = False
    parent_index: Optional[int] = None
    content: str

    # 补充逻辑：默认 parent_index = index
    def set_defaults(self):
        if self.parent_index is None:
            self.parent_index = self.index
