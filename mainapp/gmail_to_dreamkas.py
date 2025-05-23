import csv
import datetime
import os
import random
import time
import zipfile

import patoolib
import pandas
import py7zr
import simplegmail
import xlrd
from django.core.files.storage import default_storage
from simplegmail.query import construct_query
from slugify import slugify

from dremkas.settings import DREAM_KAS_API
from mainapp.gmail_invoices import get_gmail_messages, replace_month_to_number
from mainapp.helper import check_EAN13_EAN8, convert_csv_to_excel
from mainapp.models import PresetGmail, Store


def preset_init():
    return


def get_document_and_attachments_from_gmail(message_id, store_id):
    if not os.path.exists("media"):
        os.makedirs("media")
    if not os.path.exists("media/gmail_invoices"):
        os.makedirs("media/gmail_invoices")
    gmail_client_secret = Store.objects.filter(store_id=store_id).first().gmail_client_secret
    if gmail_client_secret is None:
        return "No gmail account set up!"
    # insert gmail stuff here

    try:
        gmail = simplegmail.Gmail(gmail_client_secret)
    except:
        return False
    ###                  ###
    query_params = {
        "id": message_id
    }
    for i in range(20):
        try:
            message = gmail.get_messages(query=construct_query(query_params))[0]
            break
        except:
            time.sleep(i)
            print(f"Попытка получить сообщение неудачна. Следующая попытка через {i} секунд.Попытка {i}/20")
    message = gmail.get_messages(query=construct_query(query_params))[0]
    if message.attachments:
        for attachment in message.attachments:
            attachment.save("media/gmail_invoices/" + attachment.filename, overwrite=True)
            if attachment.filename.endswith(".rar") or attachment.filename.endswith(".zip") or attachment.filename.endswith('.7z') or attachment.filename.endswith('.rar'):
                try:
                    from pyunpack import Archive
                    Archive('media/gmail_invoices/' + attachment.filename).extractall('media/gmail_invoices/')
                    os.remove('media/gmail_invoices/' + attachment.filename)
                except Exception as ex:
                    print(ex)
                    try:
                        os.remove('media/gmail_invoices/' + attachment.filename)
                    except:
                        pass
    try:
        return message.sender.split('<')[1].replace('>', '')
    except:
        return message.sender

def get_supplier_data_for_preset(supplier):
    supplier_data = {}
    supplier_data['supplier_inn'] = supplier.inn
    supplier_data['supplier_name'] = supplier.supplier_name_set.first().name
    supplier_data['supplier_prefix'] = supplier.supplier_prefix
    return supplier_data


def get_prerequisites_for_a_document(pandas_document, preset):
    print('Попытка использовать шаблон: ',preset.preset_name)
    try:
        step = "Получение уник. Инфы в документе"
        print(preset.supplier_unique_information)
        print(preset.supplier_unique_information_row)
        print(preset.supplier_unique_information_col)
        if preset.supplier_unique_information.replace('  ', ' ') not in pandas_document.iloc[
            preset.supplier_unique_information_row,
            preset.supplier_unique_information_col
        ].replace('  ', ' '):
            print('Шаблон', preset.preset_name, 'Уникальная информация поставщика - НЕ ОК')
            return False
        # +         Get Store Destination
        step = "Получение Магазина в документе"
        if preset.document_store_information is not None:
            if preset.document_store_information.replace('  ', ' ').strip() not in pandas_document.iloc[
                preset.document_store_information_row,
                preset.document_store_information_col
            ].replace('  ', ' ').strip():
                print('Шаблон', preset.preset_name, 'Информация о магазине в документе - НЕ ОК')
                return False
        else:
            print('document_store_information is None')
        # Get Date
        step = "Получение даты в документе"
        if preset.document_date_col is not None and preset.document_number_row is not None:
            document_date = pandas_document.iloc[
                preset.document_date_row,
                preset.document_date_col
            ]
            if preset.document_non_regular_date is True:
                if preset.document_date_between_first is not None:
                    document_date = document_date.split(preset.document_date_between_first)[1]
                if preset.document_date_between_second is not None:
                    document_date = document_date.split(preset.document_date_between_second)[0]
                document_date_new = replace_month_to_number(document_date)
                if document_date_new != document_date and document_date_new is not None:
                    document_date = document_date_new
            document_date = datetime.datetime.strptime(document_date.strip(), preset.document_date_format).strftime("%Y-%m-%d")
        else:
            print('Шаблон', preset.preset_name, 'Дата - невозможно разбрать, ставится дефолтная дата - Сегодня.')
            document_date = datetime.date.today().strftime("%Y-%m-%d")
        # Get Number
        step = "Получение номера в документе"
        if preset.document_number_col is not None and preset.document_number_row is not None:
            document_number = pandas_document.iloc[
                preset.document_number_row,
                preset.document_number_col
            ]
            if preset.document_non_regular_number is True:
                if preset.document_number_between_first is not None:
                    document_number = document_number.split(preset.document_number_between_first)[0]
                if preset.document_number_between_second is not None:
                    document_number = document_number.split(preset.document_number_between_second)[1]


        else:
            print('Шаблон', preset.preset_name, 'Невозможно разобрать номер документа')
            document_number = '000-000'
        step = "Получение поставщика в документе"
        document_supplier = DREAM_KAS_API.search_partner_id_by_inn(preset.supplier_inn)
        store_destination = None
        if preset.document_store_information_row is not None and preset.document_store_information_col is not None:
            if preset.document_store_information.replace('  ', ' ').strip() in pandas_document.iloc[preset.document_store_information_row, preset.document_store_information_col].replace('  ',
                                                                                                                                                                                          ' ').strip():
                store_destination = preset.document_store_destination
            else:
                print('Шаблон', preset.preset_name, 'Информация о адресе доставки - НЕ ОК')
                return False
        step = "Получение магазина доставки в документе"
        if store_destination is None:
            store_destination = Store.objects.first().store_id
        return {
            "document_date": document_date,
            "document_number": document_number,
            "document_supplier": document_supplier,
            "store_destination": store_destination
        }
    except Exception as Ex:
        print(Ex)
        print('Шаблон', preset.preset_name, 'НЕ ОК, общая ошибка, Шаг - ',step)
        return False


def get_products_from_a_document(pandas_document, preset):
    nds = ["0%", "10%", "20%", "30%", "Без НДС"]
    amount_type = ["шт", "шт.", "штук", "упак.", "упак", "кг", "гр", "г", "кг.", "гр.", "г."]
    conditions = 0
    if preset.product_name_col is not None:
        conditions = conditions + 1
    if preset.product_code_col is not None:
        conditions = conditions + 1
    if preset.product_amount_type_col is not None:
        conditions = conditions + 1
    if preset.product_amount_col is not None:
        conditions = conditions + 1
    if preset.product_nds_col is not None:
        conditions = conditions + 1
    if preset.product_sum_col is not None:
        conditions = conditions + 1
    if preset.product_start_row is not None:
        start_row = int(preset.product_start_row)
    else:
        start_row = 0
    goods_list = []
    step = 'start'
    for i in range(start_row, pandas_document.shape[0]):
        try:
            product_code = None
            met_conditions = 0
            step = 'get product name'
            if preset.product_name_col is not None:
                product_name = str(pandas_document.iloc[i, preset.product_name_col])
                met_conditions = met_conditions + 1
            step = 'get product code'
            if preset.product_code_col is not None:
                product_code = str(pandas_document.iloc[i, preset.product_code_col])
                met_conditions = met_conditions + 1
            step = 'get product amount'
            if preset.product_amount_type_col is not None:
                if str(pandas_document.iloc[i, preset.product_amount_type_col]) in amount_type:
                    met_conditions = met_conditions + 1
            step = 'get product nds'
            if preset.product_nds_col is not None:
                if str(pandas_document.iloc[i, preset.product_nds_col]) in nds:
                    met_conditions = met_conditions + 1
            step = 'get product amount'
            product_amount = float(pandas_document.iloc[i, preset.product_amount_col])
            met_conditions = met_conditions + 1
            step = 'get product sum'
            import re
            product_sum = float(re.sub(r'[^\d,\.]', '', str(pandas_document.iloc[i, preset.product_sum_col])).replace(',', '.'))
            met_conditions = met_conditions + 1
            if met_conditions == conditions:
                good = {
                    "product_name": product_name,
                    "product_code": product_code if product_code is not None else None,
                    "product_amount": product_amount,
                    "product_sum": product_sum
                }
                goods_list.append(good)
        except:
            print(slugify(preset.preset_name))
            print(f'error {step}')
            continue
    return goods_list


def search_product_thorough(prefix, product_name, product_code, product_amount, product_sum, priority=0):
    # 0 - default
    # 1 - Name
    found_product = None
    productcode = None
    try:
        if check_EAN13_EAN8(product_code):
            print("Product is EAC8/13")
            found_product = DREAM_KAS_API.search_goods(str(product_code).strip())
    except:
        print("EAC8/13 check, product not found or error")
        pass
    if found_product is None and product_code is not None:
        try:
            found_product = DREAM_KAS_API.search_goods(prefix + str(product_code))
            if productcode is None:
                productcode = prefix + str(product_code)
        except:
            pass
    if found_product is None:
        try:
            tempproductcode = ""
            for word in slugify(product_name).split("-"):
                tempproductcode = tempproductcode + word[0]
                try:
                    tempproductcode = tempproductcode + word[1]
                except:
                    pass
                try:
                    tempproductcode = tempproductcode + word[3]
                except:
                    pass
            found_product = DREAM_KAS_API.search_goods(prefix + tempproductcode)
            if productcode is None:
                productcode = prefix + tempproductcode
            if priority == 1:
                productcode = prefix + tempproductcode
        except:
            pass
    new_position = {
        "name": None if found_product else productcode,
        "barcodeControl": None,
        "amount": round(float(product_amount) * 1000),
        "costWithTax": round(round(float(product_sum) / float(product_amount), 2) * 100),
        "sumCost": round(float(product_sum) * 100),
        "product": None,
        "barcode": None,
        "productId": found_product.get("id", None) if found_product else None,
        "marks": None,
        "marksChecked": None,
        "egaisAlc": None,
        "egaisCode": None,
        "egaisVolume": None,
        "egaisTypeCode": None,
        "egaisIsPacked": None
    }
    return new_position


def create_document_from_excel(excel_attachment, msg_sender):
    if excel_attachment.endswith('.pdf'):
        return False
    nds = ["0%", "10%", "20%", "30%", "Без НДС"]
    amount_type = ["шт", "шт.", "штук", "упак.", "упак", "кг", "гр", "г"]
    # mode:
    # 0 - by code, if availible
    # 1 - by name.
    file_path = 'media/gmail_invoices/' + excel_attachment
    if excel_attachment.lower().endswith('.csv'):
        file_path = convert_csv_to_excel(file_path)
    try:
        try:
            wb = xlrd.open_workbook(file_path, encoding_override='cp1251')
            pandas_document = pandas.read_excel(wb, keep_default_na=False, header=None)
        except:
            try:
                pandas_document = pandas.read_excel(file_path, engine='openpyxl').fillna('')
            except:
                try:
                    pandas_document = pandas.read_excel(file_path, engine='openpyxl').fillna('')
                except:
                    temp_file_path = 'temp_file.xlsx'
                    with zipfile.ZipFile(file_path, 'r') as z:
                        with zipfile.ZipFile(temp_file_path, 'w') as new_z:
                            for item in z.infolist():
                                if item.filename == 'xl/SharedStrings.xml':
                                    # Rename the file
                                    new_z.writestr('xl/sharedStrings.xml', z.read(item.filename))
                                else:
                                    new_z.writestr(item, z.read(item.filename))

                    # Replace the original file with the modified one
                    os.replace(temp_file_path, file_path)
                    pandas_document = pandas.read_excel(file_path, engine='openpyxl').fillna('')
    except Exception as Ex:
        print(Ex)
        return False

    for preset in PresetGmail.objects.filter(supplier_mail=msg_sender):
        prerequisites = get_prerequisites_for_a_document(pandas_document, preset)
        if not prerequisites:
            continue
        else:
            document_info = {
                "document_date": prerequisites['document_date'],
                "document_number": prerequisites['document_number'],
                "document_supplier": prerequisites['document_supplier'],
                "store_destination": prerequisites['store_destination'],
            }

        # Get goods from document
        products_list = get_products_from_a_document(pandas_document, preset)
        if products_list == [] or products_list is None:
            print(slugify(preset.preset_name))
            print('0 goods error')
            continue

        resulting_goods_list = []
        for product in products_list:
            resulting_good = search_product_thorough(
                prefix=preset.supplier_prefix,
                product_name=product["product_name"],
                product_code=product["product_code"],
                product_amount=product["product_amount"],
                product_sum=product["product_sum"],
                priority=preset.product_priority)
            resulting_goods_list.append(resulting_good)

        try:
            result = DREAM_KAS_API.createdocument(
                document_info["document_date"],
                "Документ Создан Автоматически. Источник - Почта",
                document_info["document_supplier"],
                str(document_info["document_number"]),
                positions=resulting_goods_list,
                target_store_id=document_info['store_destination'],
            )
            return 'https://kabinet.dreamkas.ru/app/#!/documents/card~2F' + result['id']
        #### this except is for lulz!
        except:
            pass
