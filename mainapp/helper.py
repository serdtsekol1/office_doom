import os

import pandas as pd
import xlrd
import xmltodict
from django.conf.global_settings import DEFAULT_FILE_STORAGE
from django.core.files.storage import default_storage


def delete_file(path):
    """ Deletes file from filesystem. """
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception as ex:
        print(ex)


def normalizer_xls(file_name):
    print (file_name)
    xls = pd.read_excel(file_name, header=None)
    book = xlrd.open_workbook(file_name, formatting_info=True)
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


def send_document(company, file, DREAM_KAS_API):
    try:

        file = default_storage.save(f"files/{file}", file)
        print("send_document_file_done")
        generate_document = getattr(DREAM_KAS_API, f"generate_document_{company}")
        print("send_document_generate_document_done")
        document = generate_document(file)
        print("send_document_document_done")
        partnerid = DREAM_KAS_API.search_partner_id_by_inn(document["inn"])
        print("send_document_partnerid_done")
        result = DREAM_KAS_API.createdocument(document["date"], "Документ Создан Автоматически. Источник - Диадок", partnerid, str(document["doc_id"]), positions=document["positions"])
        print("send_document_result_done")
        print(result)
        return result
    except Exception as ex:
        print(f"{ex=}" + f"generate_document_{company}")
        return None


def open_file_type(file_path, header=None, skiprows=None):
    if file_path.endswith(".xml"):
        with open(f"media/{file_path}", "r", encoding='windows-1251', errors='ignore') as xmlfileObj:
            return xmltodict.parse(xmlfileObj.read())
    if file_path.endswith('.xls'):
        file_path = normalizer_xls(f"media/{file_path}")
        xls = pd.ExcelFile(file_path)
        df = xls.parse(xls.sheet_names[0], header=header, skiprows=skiprows)
        return df.to_dict('index')
    if file_path.endswith('.xlsx'):
        xls = pd.ExcelFile(f"media/{file_path}")
        df = xls.parse(xls.sheet_names[0], header=header, skiprows=skiprows)
        return df.to_dict('index')
    return None
