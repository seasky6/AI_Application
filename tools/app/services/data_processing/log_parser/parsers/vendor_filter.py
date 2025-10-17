import pandas as pd
import re

class VendorFilter:
    def __init__(self):
        # MACOM厂商识别字典（注意统一大写以增强匹配鲁棒性）
        self.vendor_map = {
            '2271 B7': 'R1E',
            '2271 B1': 'R1D',
            '4461 HP B41H': 'R1B',
            '2271 B3': 'R1E',
            '4471 B30': 'R1C',
            '4471 B7': 'R1D',
            '4471HP B2': 'R1C',
            '4471HP B25': 'R1C',
            '4471HP B66': 'R1C'
        }
        # 统一大小写处理
        self.vendor_map = {k.upper(): v.upper() for k, v in self.vendor_map.items()}

    def _is_macom_vendor(self, row):
        product = str(row['ProductName']).strip().upper()
        rev = str(row['REV']).strip().upper()
        # 去掉前缀，例如 Radio
        cleaned_product = re.sub(r'^(RADIO|HW-)\s*', '', product)
        return self.vendor_map.get(cleaned_product) == rev

    def filter_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """传入 DataFrame，返回剔除 MACOM 厂商后的新 DataFrame"""
        return df[~df.apply(self._is_macom_vendor, axis=1)]

    def filter_excel(self, input_path: str, output_path: str = 'filtered_output.xlsx', removed_path: str = None):
        """从 Excel 文件读取、过滤并保存新文件"""
        df = pd.read_excel(input_path)
        filtered_df = self.filter_dataframe(df)
        filtered_df.to_excel(output_path, index=False)

        # 可选：保存被剔除的行
        if removed_path:
            removed_df = df[df.apply(self._is_macom_vendor, axis=1)]
            removed_df.to_excel(removed_path, index=False)

        print(f"处理完成，过滤后保存为：{output_path}")
