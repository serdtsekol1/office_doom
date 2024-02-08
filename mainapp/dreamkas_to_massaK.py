import os

import pandas as pd

from dremkas.settings import DREAM_KAS_API, CURRENT_IDS
from mainapp.dreamkas_Products import turn_number_to_ean_13, Create_barcode_for_product, Delete_barcode_for_product
from mainapp.models import Barcodes


#unit 796 - countable.
#unit 166 - kg
def create_excel_document_for_massaK(file_path):
    data = [['1','2','3','4','5','6','7','8']] # Needed for Massa K program could recognize the stuff.
    #Non logical shenenigans cause fuck it.
    barcodes = Barcodes.objects.filter(barcode__startswith='999999999').order_by('barcode')
    for barcode in barcodes:
        printer_code = barcode.barcode[9:12]
        data_to_append = []
        data_to_append.append(str(printer_code))
        data_to_append.append('000000' + str(printer_code))
        if barcode.product_fk.short_name is not None:
            data_to_append.append(str(barcode.product_fk.short_name))
        else:
            data_to_append.append(str(barcode.product_fk.name))
        price_appended = 0
        type_appended = 0
        if int(barcode.product_fk.type) == 796:
            data_to_append.append('1')
            type_appended = 1
        if int(barcode.product_fk.type) == 166:
            data_to_append.append('0')
            type_appended = 1
        if type_appended == 0:
            print('Unable to create product. No valid type!')
            continue
        for device_id in CURRENT_IDS.split(','):
            price = barcode.product_fk.prices_set.filter(device_id=device_id).first()
            if price is not None:
                data_to_append.append(price.value/100)
                price_appended = 1
                break
        if price_appended == 0:
            print('Unable to create product. No valid price!')
            continue
        data_to_append.append('')
        data_to_append.append('')
        data_to_append.append(printer_code)
        data.append(data_to_append)
    df = pd.DataFrame(data)
    df.to_excel(file_path + 'Файл_для_принтера.xlsx', index=False, header=False)

def create_or_change_massak_codes_for_product(id_out,code):
    # zfill(3) :5 = 005, 55 = 055, 555 = 555
    # zfill(4) :5 = 0005, 55 = 0055, 555 = 0555
    if code.__len__() > 3 or code.isdigit() is False:
        return None, code
    code = str(code).zfill(3)
    product_external = DREAM_KAS_API.get_product_v2(id_out)
    if 'status' in product_external:
        return False, code
    for barcode in product_external['barcodes']:
        if str(barcode).startswith('999999999') and str(barcode).__len__() == 13:
            Delete_barcode_for_product(id_out,barcode)
    for vendorCode in product_external['vendorCodes']:
        if str(vendorCode).startswith('2999') and str(barcode).__len__() == 7:
            Delete_barcode_for_product(id_out,vendorCode)

    # unit 796 - countable, do 1 barcode
    # unit 166 - kg, do 1 barcode and 1 vendorcode.
    if product_external['unit'] == str(796):
        code_to_add = create_massak_code(code,mode=0)
        resp = Create_barcode_for_product(id_out,code_to_add)
        if resp is not False:
            return resp, code_to_add
        return True, code_to_add

    if product_external['unit'] == str(166):
        code_to_add = create_massak_code(code,mode=0)
        resp = Create_barcode_for_product(id_out,code_to_add)
        if resp is not False:
            return resp, code_to_add
        code_to_add = create_massak_code(code,mode=1)
        resp = Create_barcode_for_product(id_out,code_to_add)
        if resp is not False:
            Delete_barcode_for_product(id_out, create_massak_code(code,mode=0))
            return resp, code_to_add
        return True, code_to_add
    return False, code

def check_code_massaK(barcode):
    try:
        int(barcode)
    except:
        return False
    if str(barcode).startswith('999999999') or str(barcode).startswith('2999'):
        return True
    return False
def create_massak_code(code,mode):
    # 0 - barcode
    # 1 - vendorecode, Weighted product
    if mode == 0:
        return(turn_number_to_ean_13(f'999999999{code}'))
    if mode == 1:
        return(f'2999{code}')
    raise ValueError
