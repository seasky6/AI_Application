import re


class Patterns:
    """
    用到的所有正则表达式
    """
    def __init__(self):
        self.elog = re.compile(r'\[(\d{6})\s(\d{6})\]\s+(\d+):\s(.+)')
        self.elog10_abn = re.compile(r'(\w+)=([^,]+)')
        self.elog10_case = re.compile(r'Case:(\d+)(?:\s+Event\s+ID:(\d+))?')
        self.elog10_carrier = re.compile(r'^\d+_[ud]l_')
        self.elog16 = re.compile(r'^(.*?)\s*;\s*(\w+):([^;]+);\s*(\w+):([^;]+);\s*(\w+):([^;]+)$')
        self.elog27 = re.compile(r'PA measured values for driver name:\s*([^;]+);\s*value:\s*(\d+);\s*branch Id:\s*(\d)')
        self.elog42 = re.compile(r'Temperature:\s*(.+)')
        self.elog43 = re.compile(r'PA current:\s*(.+)')
        self.elog52 = re.compile(r'^([^:]+):\s*([^;]+);\s*(\w+):\s*(\d+)$')
        self.hwlog = re.compile(r'(\d+)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.+)')
        self.pareadall = re.compile(r'^(Invalid command):\s*(.+)$')
        self.trx_status_branch = re.compile(r'(?i)branch\s*(\d+)')
        self.trx_status_date = re.compile(r'Date:\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})')
        self.trx_status_section = re.compile(r'^(Header|HW|Calibration info|Supervision|Diagnostic|DPD|Board)$', re.IGNORECASE)
