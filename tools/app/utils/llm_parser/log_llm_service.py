import os
import traceback

from app.dto.logItemDto import LogItemDto
from app.services.log_parser.elog_parser.excel_parser_mode2 import ExcelParser
from app.services.log_parser.llm_parser.excel_handler import parse_excel_sheet
from app.services.log_parser.llm_parser.llm_parser import process_log, load_patterns
from app.util.get_path import get_output_files_path


def get_log_dto_by_llm()->list[LogItemDto]:
    patterns = load_patterns()
    log_item_dto_list = []
    input_dir = get_output_files_path('input_files')
    input_file =  input_dir+'/'+'Input file after PDP processing.xlsx'

    # 检查输入文件是否存在
    if os.path.exists(input_file):
        try:
            # 解析指定工作表和对应列
            line_iter = parse_excel_sheet(file_path=input_file, sheet_name='Submit Pattern Lines - 3', column_name='log_line')
            line_id = 1
            for entry in line_iter:
                log_item_dto_one_line = process_log(entry, patterns,line_id)
                line_id+=1
                if(log_item_dto_one_line):

                    log_item_dto_list.extend(log_item_dto_one_line)
                else:
                    print("skip to handle %s:"%log_item_dto_one_line)
            return log_item_dto_list
        except Exception as e:
            print(f"解析过程中发生错误: {str(e)}")
            traceback.print_exc()
            return  []
    else:
        print(f"输入文件不存在: {input_file}")
        traceback.print_exc()

        return  []
if __name__ == '__main__':
    result_list = get_log_dto_by_llm()
    x =1