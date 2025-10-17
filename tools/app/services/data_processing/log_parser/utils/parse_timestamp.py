from datetime import datetime


# 时间戳格式：e.g., [240816 152959] -> date_str = 240816， time_str = 152959
def parse_timestamp(date_str: str, time_str: str) -> str:
    """解析时间戳"""
    try:
        date_str = datetime.strptime(date_str, "%y%m%d").strftime("%Y-%m-%d")
        time_str = datetime.strptime(time_str, "%H%M%S").strftime("%H:%M:%S")
        return f'{date_str} {time_str}'
    except ValueError as e:
        raise ValueError(f'时间戳格式不正确: {date_str} {time_str}') from e
