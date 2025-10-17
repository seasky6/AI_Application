from typing import Iterator, Optional, List
import itertools
from .base_parser import BaseParser


class TrxStatusParser(BaseParser):
    """
    Trx_status解析器
    """
    def __init__(self, base_parser: BaseParser):
        super().__init__()
        self.base = base_parser
        self.patterns = base_parser.patterns

    def parse_trx_status_entry(
            self,
            serial_number: str,
            product_name: str,
            log_type: str,
            line_iter: Iterator[str]
    ) -> None:
        """
        解析 trx_status
        示例：
        Branch 0
        Date: 2025-04-04 17:41:39,
        HEADER
        { RadioSw          : rev:  NA,
        Drt_lin_conf     : pid:  CAH1611701_1,    rev: R9EB
        TrxCtrl          : rev:  15.1.17.1,       status: , changes: ,
        TxL              : pid:  CXC1124121_9,    rev: R12AB03,    date      : 2024-08-21,        arch: WRL21-64bit,
        Fpga             : pid:  na,              rev: na,         name      : na,                date: na
        Dpl              : pid:  CXC1743843_1,    rev: R7F01,      name      : KRYPTON1.0/ARM,     date: 20240830 }
        ... ...
        解析后：
        'Slogan': Branch 0,
        'Key': HEADER,
        'Value': RadioSw          : rev:  NA,\nDrt_lin_conf     : pid:  CAH1611701_1,    rev: R9EB\n
        'ValueType': str,
        'IsMeasuredValue': False,
        """
        print(f"=== 开始解析trx_status ===")
        print(f"serial: {serial_number}, product: {product_name}")

        try:
            # 处理第一行: Branch line行
            branch_line = next(line_iter).strip()

            m_branch = self.patterns.trx_status_branch.match(branch_line)
            if not m_branch:
                # 如果不是branch line(新的日志条目), 将行放到迭代器并停止收集
                line_iter = itertools.chain([branch_line], line_iter)
                return

            branch_id = m_branch.group(1)
            slogan = f"Branch {branch_id}"
            timestamp = ""

            # 处理第二行：date行
            try:
                date_line = next(line_iter).strip()
                msg_date = self.patterns.trx_status_date.match(date_line)
                if msg_date:
                    timestamp = msg_date.group(1)
                else:
                    # 如果不是Date行(新的日志条目), 将行放到迭代器并停止收集
                    line_iter = itertools.chain([date_line], line_iter)
            except StopIteration:
                pass

            # 后续 section 部分处理
            current_section: Optional[str] = None
            section_content: List[str] = []

            parent_index = self.base.log_index

            # 直到下一个 Branch 或者 trx_status 终止
            for line in line_iter:
                line = line.strip()

                # 查看是否开始新branch
                if self.patterns.trx_status_branch.match(line):
                    # 保存 current section 部分
                    if current_section and section_content:
                        self.base.add_log_entry(
                            serial_number=serial_number,
                            product_name=product_name,
                            log_type=log_type,
                            timestamp=timestamp,
                            log_id='',
                            content='',
                            slogan=slogan,
                            key=current_section,
                            value='\n'.join(section_content),
                            value_type='dict',
                            is_measured_value=False,
                            parent_index=parent_index
                        )

                    # Put the Branch line back for the next call
                    line_iter = itertools.chain([line], line_iter)
                    break

                # 后续 section 部分
                msg_section = self.patterns.trx_status_section.match(line)
                if msg_section:
                    # 保存之前的部分
                    if current_section and section_content:
                        self.base.add_log_entry(
                            serial_number=serial_number,
                            product_name=product_name,
                            log_type=log_type,
                            timestamp=timestamp,
                            log_id='',
                            slogan=slogan,
                            key=current_section,
                            value='\n'.join(section_content),
                            value_type='dict',
                            is_measured_value=False,
                            parent_index=parent_index
                        )

                    # 处理新的部分
                    current_section = msg_section.group(1).strip()
                    section_content = []
                else:
                    # 添加到现有的section_content
                    if line:
                        section_content.append(line)
                        # 当遇section部分（字典结构） - 结尾的‘}’，跳出循环
                        if current_section and current_section.lower() == 'board' and '}' in line:
                            break

            # 保存最后的section
            if current_section and section_content:
                self.base.add_log_entry(
                    serial_number=serial_number,
                    product_name=product_name,
                    log_type=log_type,
                    timestamp=timestamp,
                    log_id='',
                    slogan=slogan,
                    key=current_section,
                    value='\n'.join(section_content),
                    value_type='dict',
                    is_measured_value=False,
                    parent_index=parent_index
                )

        except StopIteration:
            # 结束迭代器
            pass
