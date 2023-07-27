def normalizer_xls(file_name):
    import pandas as pd
    import xlrd
    xls = pd.read_excel('media/No2.xls', header=None)
    book = xlrd.open_workbook('media/No2.xls', formatting_info=True)
    sh = book.sheet_by_index(0)
    for row in range(xls.shape[0]):
        for col in range(xls.shape[1]):
            cell = sh.cell(row, col)
            xf_index = cell.xf_index
            xf = book.xf_list[xf_index]
            format_key = xf.format_key
            format = book.format_map[format_key]
            format_str = format.format_str
            if len(format_str) == format_str.count('0') and isinstance(xls.iloc[row, col], int):
                temp = str(xls.iloc[row, col]).zfill(len(format_str))
                if str(xls.iloc[row, col]) != temp:
                    print(f'r{row} format: {format_str}; \timport: {xls.iloc[row, col]};' + f'\tchanged to: {str(xls.iloc[row, col]).zfill(len(format_str))}')
                    xls.iloc[row, col] = str(xls.iloc[row, col]).zfill(len(format_str))
    xls.to_excel(f"{file_name.replace('.xls', '_temp.xls')}")
    return f"{file_name.replace('.xls', '_temp.xls')}"
