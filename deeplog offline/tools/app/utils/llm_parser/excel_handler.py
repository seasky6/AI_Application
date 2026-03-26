import pandas as pd


def parse_excel_sheet( file_path, sheet_name, column_name):
    """
    解析Excel中的日志文件
    """
    try:
        # 读取指定工作表
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        if df.empty:
            print('警告：输入文件为空！')

        # 检查是否存在 ‘log_line’ 列
        if column_name not in df.columns:
            print('错误：输入文件没有“log_line”列！')
            print('现有列名：', df.columns.tolist())

        line_iter = iter(df[column_name])
        return line_iter

    except Exception as e:
        print(f"处理过程中出错: {str(e)}")