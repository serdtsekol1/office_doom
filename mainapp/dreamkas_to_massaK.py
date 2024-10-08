import os
import datetime as dt
import pandas as pd

from dremkas.settings import DREAM_KAS_API, CURRENT_IDS
from mainapp.dreamkas_Products import turn_number_to_ean_13, Create_barcode_for_product, Delete_barcode_for_product
from mainapp.models import Barcodes, Product, Store


def debug_remove_printer_code_from_long_not_accepted_products():
    list_of_devices = []
    for store in Store.objects.all():
        for device in store.store_devices:
            list_of_devices.append(device)
    print(list_of_devices)
    date_from = dt.datetime.now() - dt.timedelta(days=90)
    date_now = dt.datetime.now() - dt.timedelta(days=1)
    date_from_year, date_from_month, date_from_day = date_from.year, date_from.month, date_from.day
    date_to_year, date_to_month, date_to_day = date_now.year, date_now.month, date_now.day
    receipts  = DREAM_KAS_API.get_receipts(date_from_year, date_from_month, date_from_day, date_to_year, date_to_month, date_to_day, list_of_devices)

    unique_ids = set()
    for receipt_collection in receipts:
        for receipt_subcollection in receipt_collection:
            for receipt_dict in receipt_subcollection['data']:
                for position in receipt_dict['positions']:
                    unique_ids.add(position['id'])
    del receipts
    del receipt_collection
    del receipt_subcollection
    del receipt_dict
    del position

    list_of_deleted_products = []
    for product in Product.objects.filter(barcodes__barcode__startswith=999999999):
        import datetime
        httpres = DREAM_KAS_API.get_product_history(product.id_out)
        httpres2 = DREAM_KAS_API.get_product_v2(product.id_out)
        if (datetime.datetime.now() - datetime.datetime.strptime(httpres2['updatedAt'], "%Y-%m-%dT%H:%M:%S.%fZ")).days > 90:

            try:
                if (datetime.datetime.now() - datetime.datetime.strptime(httpres.json()[0]['document']['acceptedAt'], '%Y-%m-%d')).days > 90:
                    if product.id_out not in unique_ids:
                        print('deleting', product.name, product.barcodes_set.filter(barcode__startswith=999999999).first().barcode)
                        list_of_deleted_products.append([product.name, product.barcodes_set.filter(barcode__startswith=999999999).first().barcode[9:12]])
                        create_or_change_massak_codes_for_product(product.id_out,'')
                    #print(product.name, 'Deleted code for Massa K. Days passed since last invoice - ', (datetime.datetime.now() - datetime.datetime.strptime(httpres.json()[0]['document']['acceptedAt'], '%Y-%m-%d')).days )
                #else:
                    #list_of_deleted_products.append(product.name)
                    #print(product.name, 'Days since last invoice:', (datetime.datetime.now() - datetime.datetime.strptime(httpres.json()[0]['document']['acceptedAt'], '%Y-%m-%d')).days)
            except:
                if httpres.status_code == 200:
                    if product.id_out not in unique_ids:
                        print('deleting', product.name, product.barcodes_set.filter(barcode__startswith=999999999).first().barcode)
                        list_of_deleted_products.append([product.name, product.barcodes_set.filter(barcode__startswith=999999999).first().barcode[9:12]])
                        create_or_change_massak_codes_for_product(product.id_out, '')
                    #print(product.name, 'Deleted code for Massa K. No invoice')
                        list_of_deleted_products.append(product.name)
    for deleted_product in list_of_deleted_products:
        print(deleted_product[0], 'deleted. Code:' , deleted_product[1])

#unit 796 - countable.
#unit 166 - kg
def create_excel_document_for_massaK(store_id):
    data = [['1','2','3','4','5','6','7','8']] # Needed for Massa K program could recognize the stuff.
    #Non logical shenenigans cause fuck it.
    barcodes = Barcodes.objects.filter(barcode__startswith='999999999').order_by('barcode')
    for barcode in barcodes:
        printer_code = barcode.barcode[9:12]
        data_to_append = []
        data_to_append.append(str(printer_code))
        if int(barcode.product_fk.type) == 796:
            data_to_append.append(str(printer_code))
        if int(barcode.product_fk.type) == 166:
            data_to_append.append('000000'+str(printer_code))
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
        for device_id in Store.objects.get(store_id=store_id).store_devices:
            price = barcode.product_fk.prices_set.filter(device_id=device_id).first()
            if price is not None:
                data_to_append.append(price.value/100)
                price_appended = 1
                break
        if price_appended == 0:
            print('Unable to create product. No valid price!')
            continue
        if data_to_append[3] == '0':
            if barcode.product_fk.contents is not None:
                data_to_append.append(barcode.product_fk.contents)
            else:
                data_to_append.append('')
            if barcode.product_fk.expiry_duration is not None:
                data_to_append.append(barcode.product_fk.expiry_duration)
            else:
                data_to_append.append('')
        else:
            data_to_append.append('')
            data_to_append.append('')
        data_to_append.append(printer_code)
        data.append(data_to_append)
        if data_to_append[3] == '0':
            # new_data_to_append = data_to_append.copy()  # Make a copy of data_to_append
            # new_data_to_append[0] = '1' + new_data_to_append[0]
            # new_data_to_append[1] = str(printer_code)
            # new_data_to_append[3] = '1'
            # new_data_to_append[7] = '1' + new_data_to_append[7]
            # data.append(new_data_to_append)
            new_data_to_append = data_to_append.copy()  # Make a copy of data_to_append
            new_data_to_append[0] = '1' + new_data_to_append[0]
            new_data_to_append[1] = str(printer_code)
            new_data_to_append[3] = '1'
            new_data_to_append[5] = ''
            new_data_to_append[6] = ''
            new_data_to_append[7] = '1' + new_data_to_append[7]
            data.append(new_data_to_append)
    df = pd.DataFrame(data)
    df.to_excel('Файл_для_принтера.xlsx', index=False, header=False)
def create_or_change_short_name_for_product(id_out,name):
    product_internal = Product.objects.filter(id_out=id_out).first()
    if product_internal is None:
        return False
    if name == '':
        product_internal.short_name = None
    else:
        product_internal.short_name = name
    product_internal.save()
    return True
def create_or_change_expiry_duration_for_product(id_out,duration):
    product_internal = Product.objects.filter(id_out=id_out).first()
    if product_internal is None:
        return False
    if duration == '':
        product_internal.expiry_duration = None
    else:
        product_internal.expiry_duration = int(duration)
    product_internal.save()
    return True
def create_or_change_contents_for_product(id_out,contents):
    product_internal = Product.objects.filter(id_out=id_out).first()
    if product_internal is None:
        return False
    if contents == '':
        product_internal.contents = None
    else:
        product_internal.contents = contents
    product_internal.save()
    return True
def debug_redo_all_codes_back():
    for product in Product.objects.filter(barcodes__barcode__startswith=999999999):
        product_external = DREAM_KAS_API.get_product_v2(product.id_out)
        code_exists = False
        for barcode in product_external['barcodes']:
            if str(barcode).startswith('999999999') and str(barcode).__len__() == 13:
                code_exists = True
                break
        if code_exists == False:
            print(product.id_out, product.barcodes_set.filter(barcode__startswith=999999999).first().barcode[9:12])
            create_or_change_massak_codes_for_product(product.id_out, product.barcodes_set.filter(barcode__startswith=999999999).first().barcode[9:12])




def create_or_change_massak_codes_for_product(id_out,code):
    # zfill(3) :5 = 005, 55 = 055, 555 = 555
    # zfill(4) :5 = 0005, 55 = 0055, 555 = 0555
    if code == '':
        product_external = DREAM_KAS_API.get_product_v2(id_out)
        for barcode in product_external['barcodes']:
            if str(barcode).startswith('999999999') and str(barcode).__len__() == 13:
                Delete_barcode_for_product(id_out, barcode)
        for vendorCode in product_external['vendorCodes']:
            if str(vendorCode).startswith('2999') and str(vendorCode).__len__() == 7:
                Delete_barcode_for_product(id_out, vendorCode)
        return True, code
    if code.__len__() > 3 or code.isdigit() is False:
        return None, code
    code = str(code).zfill(3)
    product_external = DREAM_KAS_API.get_product_v2(id_out)
    if 'status' in product_external:
        return None, code
    for barcode in product_external['barcodes']:
        if str(barcode).startswith('999999999') and str(barcode).__len__() == 13:
            Delete_barcode_for_product(id_out,barcode)
    for vendorCode in product_external['vendorCodes']:
        if str(vendorCode).startswith('2999') and str(vendorCode).__len__() == 7:
            Delete_barcode_for_product(id_out,vendorCode)

    # unit 796 - countable, do 1 barcode
    # unit 166 - kg, do 1 barcode and 1 vendorcode.
    if product_external['unit'] == str(796):
        code_to_add = create_massak_code(code,mode=0)
        resp = Create_barcode_for_product(id_out,code_to_add)
        if resp is not True:
            return resp, code
        return True, code_to_add

    if product_external['unit'] == str(166):
        code_to_add = create_massak_code(code,mode=0)
        resp = Create_barcode_for_product(id_out,code_to_add)
        if resp is not True:
            return resp, code
        code_to_add = create_massak_code(code,mode=1)
        resp = Create_barcode_for_product(id_out,code_to_add)
        if resp is not True:
            Delete_barcode_for_product(id_out, create_massak_code(code, mode=0))
            return resp, code
        return True, code
    if product_external['unit'] != str(166) and product_external['unit'] != str(796):
        print("Товар имеет некорректную единицу измерения. Поставьте либо ШТ либо КГ!")
        return False, "Товар имеет некорректную единицу измерения. Поставьте либо ШТ либо КГ!"
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
def get_massak_code_from_code(code):
    if code.isdigit() is False:
        return None
    if code.__len__() != 13 and code.__len__() != 7:
        return None
    if code.__len__() == 13:
        return str(code)[9:12]
    if code.__len__() == 7:
        return str(code)[4:7]
    return

def get_all_products_with_old_code_for_massa_k():
    barcodes = Barcodes.objects.filter(barcode__startswith='999999999').order_by('barcode')
    data = []
    for barcode in barcodes:
        data_to_append = []
        print(barcode)
        data_to_append.append(barcode.product_fk.id_out)
        data_to_append.append(barcode.product_fk.name)
        data_to_append.append(barcode.barcode[9:12])
        data.append(data_to_append)
    df = pd.DataFrame(data)
    df.to_excel("Z:\Файл_для_принтера.xlsx", index=False, header=False)
    return