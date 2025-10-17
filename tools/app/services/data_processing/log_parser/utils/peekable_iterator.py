from typing import Optional, Any


class PeekableIterator:
    """可查看下一项的迭代器（支持peek和回退）"""
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self._buffer = []

    def __iter__(self):
        return self

    def __next__(self):
        if self._buffer:
            return self._buffer.pop()
        return next(self.iterator)

    def peek(self, default: Optional[Any] = None) -> Optional[Any]:
        """查看下一项但不消耗它"""
        try:
            item = next(self.iterator)
            self._buffer.append(item)
            return item
        except StopIteration:
            return default
