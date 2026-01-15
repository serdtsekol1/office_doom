from datetime import timedelta
import random
from django.utils.dateformat import date
from dremkas.settings import DIADOC_API, DREAM_KAS_API
import os
import pandas as pd
from slugify import slugify
from dremkas.settings import KONTUR_MARKET_API_KEY,KONTUR_MARKET_SHOP_ID,KONTUR_MARKET_ORG_ID,KONTUR_MARKET_RETAIL_OUTLET_ID
from mainapp.gmail_to_dreamkas import get_prerequisites_for_a_document, get_products_from_a_document
from mainapp.helper import check_EAN13_EAN8, convert_csv_to_excel
import datetime
import xlrd
import pandas
import json
import time
import zipfile
import barcodenumber
from mainapp.models import Barcodes, PresetGmail, Store, kontur_barcode, kontur_invoices, kontur_products, kontur_suppliers
from mainapp.models import kontur_invoices as kontur_invoices_objects

if DIADOC_API is not None:
    session = DIADOC_API.session
def get_last_digit_for_barcode(barcode):
    counter = 0
    odds = 0
    evens = 0
    barcode = str(barcode)
    for digit in barcode:
        n = int(digit)
        if counter % 2 == 1:
            evens = evens + n
        else:
            odds = odds + n
        counter += 1
    total = odds + evens * 3
    check = (10 - (total % 10)) % 10
    return barcode + str(check)
def kontur_form_barcode_for_massa_k(range_1=None,range_2=None):
    if range_1 is None or range_2 is None:
        range_1 = 7000
        range_2 = 9999
    randomcode = random.randint(range_1,range_2)
    doesntExist = False
    while doesntExist == False:
        if kontur_barcode.objects.filter(barcode=get_last_digit_for_barcode(f'28999999{randomcode}')).exists():
            randomcode = random.randint(range_1,range_2)
        else:
            doesntExist = True
    return get_last_digit_for_barcode(f'28999999{randomcode}')
def kontur_add_barcode_for_massa_k(product_id, code_for_massa_k,range_1=None,range_2=None):
    if code_for_massa_k is None:
        barcode = kontur_form_barcode_for_massa_k(int(range_1),int(range_2))
    else:
        barcode = str(code_for_massa_k).zfill(4)
    json_data = {
        "cardId":product_id,
        "barCode":barcode
        }
    resp = session.post(f'https://market.kontur.ru/api/v107/{KONTUR_MARKET_ORG_ID}/{KONTUR_MARKET_RETAIL_OUTLET_ID}/{KONTUR_MARKET_SHOP_ID}/Cards/AddBarCode', json=json_data)
def kontur_add_barcode_v107(product_id, barcode):
    json_data = {
        "cardId":product_id,
        "barCode":barcode
        }
    resp = session.post(f'https://market.kontur.ru/api/v107/{KONTUR_MARKET_ORG_ID}/{KONTUR_MARKET_RETAIL_OUTLET_ID}/{KONTUR_MARKET_SHOP_ID}/Cards/AddBarCode', json=json_data)
def kontur_update_products(product_id=None):
    print('Start updating products')
    if product_id is not None:
        products = [kontur_market_get_product(KONTUR_MARKET_SHOP_ID,product_id)]
    else:
        products = kontur_market_get_products(KONTUR_MARKET_SHOP_ID)
    if products.__len__() == 0 or 'shopId' not in products[0]:
        return False
    existing_barcodes = kontur_barcode.objects.all()
    existing_barcodes_map = {}
    for barcode in existing_barcodes:
        existing_barcodes_map[barcode.barcode] = barcode
    existing_products = kontur_products.objects.all()
    existing_products_map = {}
    for product in existing_products:
        existing_products_map[product.product_id] = product
    objs_to_create = []
    objs_to_update = []
    for product in products:
        if product['id'] not in existing_products_map:
            price = product.get('sellPricePerUnit', None)
            if price is not None:
                price = float(price.replace(',','.'))
            objs_to_create.append(kontur_products(
                product_id=product['id'],
                product_name=product['name'],
                product_sell_price=price,
            ))
        else:
            price = product.get('sellPricePerUnit', None)
            if price is not None:
                price = float(price.replace(',','.'))
            kontur_product = existing_products_map[product['id']]
            kontur_product.product_name = product['name']
            kontur_product.product_sell_price = price
            objs_to_update.append(kontur_product)
    kontur_products.objects.bulk_create(objs_to_create)
    kontur_products.objects.bulk_update(objs_to_update, ['product_name', 'product_sell_price'])
    print('Products updated')
    barcodes_to_create = []
    barcodes_to_update = []
    barcodes_external = []
    for product in products:
        barcodes = product.get('barcodes')
        if barcodes is None or barcodes.__len__() == 0:
            continue
        for barcode in product['barcodes']:
            barcodes_external.append(barcode)
            product_obj = existing_products_map[product['id']]
            if product_obj is not None:
                if barcode not in existing_barcodes_map:
                    barcodes_to_create.append(kontur_barcode(
                        kontur_product_fk=product_obj,
                        barcode=barcode,
                    ))
                else:
                    kontur_barcode_obj = existing_barcodes_map[barcode]
                    kontur_barcode_obj.kontur_product_fk = product_obj
                    barcodes_to_update.append(kontur_barcode_obj)
    kontur_barcode.objects.bulk_create(barcodes_to_create)
    kontur_barcode.objects.bulk_update(barcodes_to_update, ['kontur_product_fk'])
    print('Barcodes updated')
    if product_id is not None:
        return True
    barcodes_internal = kontur_barcode.objects.all()
    for barcode in barcodes_internal:
        if barcode.barcode not in barcodes_external:
            print('Deleting barcode', barcode.barcode)
            barcode.delete()
    print('Barcodes deleted')
    return True
def kontur_get_suppliers():
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.get(f'https://api.kontur.ru/market/v1/shops/{KONTUR_MARKET_SHOP_ID}/contractors?', headers=headers)
    try:
        for item in resp.json():
            kontur_suppliers.objects.update_or_create(supplier_id=item['id'], defaults={
                                                     'supplier_inn': item.get('inn'),
                                                     'supplier_kpp': item.get('kpp'),
                                                     'supplier_name' : item.get('name'),
                                                 })
    except:
        print('Error Updating Suppliers')
        return False
    return True
def kontur_get_invoice(invoice_id):
    if invoice_id is None or invoice_id == '' or type(invoice_id) != str:
        return None
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.get(f'https://market.kontur.ru/api/v107/{KONTUR_MARKET_ORG_ID}/{KONTUR_MARKET_RETAIL_OUTLET_ID}/{KONTUR_MARKET_SHOP_ID}/StoreWayBills/Read?wayBillId={invoice_id}')
    try:
        return resp.json()
    except:
        return False
def kontur_update_invoice(invoice_id):
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    invoice = session.get(f'https://api.kontur.ru/market/v1/shops/{KONTUR_MARKET_SHOP_ID}/incoming-waybills/{invoice_id}', headers=headers).json()
    invoice_sum = 0
    try:
        for position in invoice['positions']:
            invoice_sum = invoice_sum + float(position['quantity']) * float(position['buyPricePerUnit'].replace(',','.'))    
    except:
        invoice_sum = None
    supplier_obj = kontur_suppliers.objects.filter(supplier_id=invoice['supplierId']).first()
    kontur_invoice, status = kontur_invoices.objects.update_or_create(invoice_id=invoice['id'], defaults={
                                                'invoice_number': invoice['number'],
                                                'invoice_date': datetime.datetime.strptime(invoice['receiveDate'], "%Y-%m-%dT%H:%M:%SZ").date(),
                                                'invoice_supplier' : supplier_obj,
                                                'invoice_sum': invoice_sum,
                                                'invoice_positions': invoice['positions']
                                            })

def kontur_get_invoices(date_from='', date_to='',scan=False):
    if scan == True:
        days = 1
    else:
        days = 10
    if date_from == '':
        date_from = str(date.today() - timedelta(days=days))
    if date_to == '':
       date_to = str(date.today())
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    create_counter = 0
    update_counter = 0
    resp = session.get(f'https://api.kontur.ru/market/v1/shops/{KONTUR_MARKET_SHOP_ID}/incoming-waybills?receiveDateFrom={date_from}&receiveDateTo={date_to}&limit=250',headers=headers)
    resp_items = resp.json()['items']
                
    for item in resp_items:
        invoice_sum = 0
        try:
            for position in item['positions']:
                invoice_sum = invoice_sum + float(position['quantity']) * float(position['buyPricePerUnit'].replace(',','.'))    
        except:
            invoice_sum = None
            
        detailed_invoice = session.get(f'https://market.kontur.ru/api/v107/{KONTUR_MARKET_ORG_ID}/{KONTUR_MARKET_RETAIL_OUTLET_ID}/{KONTUR_MARKET_SHOP_ID}/StoreWayBills/Read?wayBillId={item["id"]}')
        detailed_invoice_json = None
        try:
            detailed_invoice_json = detailed_invoice.json()
        except:
            pass
        invoice_draft_or_accepted = None
        invoice_positions = item['positions']
        if detailed_invoice_json is not None:
            if detailed_invoice_json['storeWayBill']['storeStatus'] == 'Published':
                invoice_draft_or_accepted = True
            if detailed_invoice_json['storeWayBill']['storeStatus'] == 'Draft':
                invoice_draft_or_accepted = False
            invoice_positions = detailed_invoice_json['storeWayBill']['products']
        supplier_obj = kontur_suppliers.objects.filter(supplier_id=item['supplierId']).first()
        kontur_invoice, status = kontur_invoices.objects.update_or_create(invoice_id=item['id'], defaults={
                                                     'invoice_number': item['number'],
                                                     'invoice_date': datetime.datetime.strptime(item['receiveDate'], "%Y-%m-%dT%H:%M:%SZ").date(),
                                                     'invoice_supplier' : supplier_obj,
                                                     'invoice_sum': invoice_sum,
                                                     'invoice_draft_or_accepted': invoice_draft_or_accepted,
                                                     'invoice_positions': invoice_positions
                                                 })

        if status == True:
            create_counter = create_counter + 1
        if status == False:
            update_counter = update_counter + 1
    print('created : ',create_counter)
    print('updated : ',update_counter)
    return
def generate_barcode_for_product(product_id):
    print('todo')
def create_xlsx_file_for_printer_kontur():
    try:
        shop_ids = kontur_market_get_shops()        
        products = kontur_market_get_products(shop_ids[0]['id'])
        list_of_products_for_xlsx_file = []
        for product in products:
            barcodes = product.get('barcodes')
            if barcodes is None or barcodes.__len__() == 0:
                continue
            for barcode in barcodes:
                if barcode.startswith('28999999'):
                    list_of_products_for_xlsx_file.append(product)
                    break
    except:
        print('Error')
    list_of_products_for_xlsx_file_xlsx = []
    counter = 1
    for product in list_of_products_for_xlsx_file:
        name = product['name']
        shelf_life = ''
        contents = ''
        kontur_product = kontur_products.objects.filter(product_id=product['id'])
        if kontur_product.__len__() != 0:
            kontur_product = kontur_product[0]
            if kontur_product.product_shelf_life is not None:
                shelf_life = kontur_product.product_shelf_life
            if kontur_product.product_contents is not None:
                contents = kontur_product.product_contents
        for barcode in product['barcodes']:
            if barcode.startswith('28999999'):
                code_to_add = barcode[8:12]
                break
        if product['sellPricePerUnit'] is None:
            print('Product', product['name'], 'has no valid sell price, skipping')
            continue
        list_of_products_for_xlsx_file_xlsx.append([counter,product['code'],product['name'],'0',product['sellPricePerUnit'],contents,shelf_life,code_to_add])
        list_of_products_for_xlsx_file_xlsx.append([10000 + counter,product['code'],product['name'],'1',product['sellPricePerUnit'],contents,shelf_life,'1' + code_to_add.zfill(4)])
        counter = counter + 1
    data = [['1','2','3','4','5','6','7','8']]
    for item in list_of_products_for_xlsx_file_xlsx:
        data.append(item)
    df = pd.DataFrame(data)
    df.to_excel('Файл_для_принтера.xlsx', index=False, header=False)
    
def product_check_code(input):
    try:
        if barcodenumber.check_code('ean13', str(input)) or barcodenumber.check_code('ean8', str(input)):
            return True
    except Exception as e:
        print(e)
        
def get_product_ids_from_dreamkas_receipts():
    if os.path.exists("./receipts_condensed/result.json"):
         with open(f"./receipts_condensed/result.json", "r", encoding="utf-8-sig") as f:
             return json.load(f)
    if not os.path.exists("./receipts/"):
        os.makedirs("./receipts/")
    receipt_list = os.listdir('./receipts')
    print('Begin Receipt collect')
    for i in range(365):
        if f"{str((date.today()-timedelta(days=365-i)).day).zfill(2)}-{str((date.today()-timedelta(days=365-i)).month).zfill(2)}-{(date.today()-timedelta(days=365-i)).year}.json" not in receipt_list:
            receipt = DREAM_KAS_API.get_receipts_for_a_day(date_from_day=(date.today()-timedelta(days=550-i)).day,
                                        date_from_month=(date.today()-timedelta(days=365-i)).month,
                                        date_from_year=(date.today()-timedelta(days=365-i)).year,
                                        date_to_day=(date.today()-timedelta(days=365-i)).day,
                                        date_to_month=(date.today()-timedelta(days=365-i)).month,
                                        date_to_year=(date.today()-timedelta(days=365-i)).year)
            data = receipt[0]['data']
            with open(f"./receipts/{str((date.today()-timedelta(days=365-i)).day).zfill(2)}-{str((date.today()-timedelta(days=365-i)).month).zfill(2)}-{(date.today()-timedelta(days=365-i)).year}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            time.sleep(1)
    print('End Receipt collect')
    if not os.path.exists("./receipts_condensed/"):
        os.makedirs("./receipts_condensed/")
    for receipt in os.listdir('./receipts'):
        with open(f"./receipts/{receipt}", "r", encoding="utf-8-sig") as f:
            try:
                data = json.load(f)
                condensed_data = []
                for sale in data:
                    for sale_position in sale['positions']:
                        sale_position = {'id': sale_position['id']}
                        if sale_position['id'] not in str(condensed_data):
                            condensed_data.append(sale_position['id'])
                with open(f"./receipts_condensed/{receipt}", "w", encoding="utf-8-sig") as f:
                    json.dump(condensed_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                pass
    sold_products = []
    print('Begin Product id Collect')
    counter = 0

    for receipt in os.listdir('./receipts_condensed'):
        with open(f"./receipts_condensed/{receipt}", "r", encoding="utf-8-sig") as f:
            try:
                data = json.load(f)
                for product_id in data:
                    if product_id not in str(sold_products):
                        sold_products.append(product_id)
                if counter % 100 == 0:
                    print('Product id Collect')
                counter = counter + 1
            except Exception as e:
                print(e)
                pass
    return sold_products
def get_product_ids_from_dreamkas_invoices():
    list_of_invoice_ids = []
    list_of_invoice_product_ids = []
    if not os.path.exists("./dreamkas_invoices/"):
        os.makedirs("./dreamkas_invoices/")
    i = 0
    while i <= 5000:
        dreamkas_documents = DREAM_KAS_API.get_documents(limit=1000,offset=i)
        for document in dreamkas_documents:
            list_of_invoice_ids.append(document['id'])
        i = i + 1000
    for invoice_id in list_of_invoice_ids:
        if os.path.exists(f'./dreamkas_invoices/{invoice_id}.json'):
            continue
        invoice = DREAM_KAS_API.get_document(invoice_id)
        with open(f'./dreamkas_invoices/{invoice_id}.json', 'w', encoding='utf-8') as f:
            json.dump(invoice, f, indent=2, ensure_ascii=False)
    counter = 0
    for invoice_File in os.listdir('./dreamkas_invoices/'):
        with open(f'./dreamkas_invoices/{invoice_File}', 'r', encoding='utf-8') as f:
            invoice = json.load(f)
            positions = invoice.get('positions')
            if positions is not None:
                for position in positions:
                    if position['productId'] == None:
                        continue
                    if position['productId'] not in str(list_of_invoice_product_ids):
                        list_of_invoice_product_ids.append(position['productId'])
        counter = counter + 1
        if counter % 100 == 0:
            print('Invoice id collect', counter)
    return list_of_invoice_product_ids

def transfer_all_goods_from_dreamkas_to_kontur():
    optimized_dreamkas_groups = {}
    dreamkas_groups = DREAM_KAS_API.get_groups()
    for dreamkas_group in dreamkas_groups['categories']:
        optimized_dreamkas_groups[str(dreamkas_group['id'])] = dreamkas_group['name']
    shops = kontur_market_get_shops()
    shop_id = shops[0]['id']
    market_products_optimized_for_search_by_barcode = {}
    market_products_optimized_for_search_by_name = {}
    market_products = kontur_market_get_products(shop_id)
    market_products_optimized_for_search_by_id = {}
    for market_product in market_products:
        market_products_optimized_for_search_by_id[str(market_product['id'])] = market_product
    market_groups = kontur_market_get_product_groups(shop_id)
    dreamkas_products = DREAM_KAS_API.get_products()
    dreamkas_products_optimized_for_search_by_productId = {}
    for dreamkas_product in dreamkas_products:
        dreamkas_products_optimized_for_search_by_productId[str(dreamkas_product['id_out'])] = dreamkas_product
        
    #dreamkas_groups = DREAM_KAS_API.get_groups()
    #dreamkas_products = DREAM_KAS_API.get_products()

    list_of_invoice_product_ids = get_product_ids_from_dreamkas_invoices()
    sold_products = get_product_ids_from_dreamkas_receipts()
    unique_elements = list(set(sold_products) | set(list_of_invoice_product_ids))
    products_to_create = []
    for item in unique_elements:
        try:
            item = dreamkas_products_optimized_for_search_by_productId[str(item)]
        except:
            continue
        ## Product Type and group id
        product_type = 'Product'
        group_id = None
        product_group_dreamkas = None
        if 'group_id' in str(item):
            product_group_dreamkas = optimized_dreamkas_groups[str(item['group_id'])]
        if product_group_dreamkas == 'Сигареты, Табачная продукция [Индивидуальная наценка]':
            product_type = 'Tobacco'
            group_id = 'c2ff2cff-662b-4f8b-bf52-bc12c2bedeff'
        if product_group_dreamkas == 'Сигареты':
            product_type = 'Tobacco'
            group_id = 'c2ff2cff-662b-4f8b-bf52-bc12c2bedeff'
        if product_group_dreamkas == 'Табак':
            product_type = 'Tobacco'
            group_id = 'c2ff2cff-662b-4f8b-bf52-bc12c2bedeff'
        if product_group_dreamkas == 'Вода, соки, нектары, напитки [30%,>5]':
            product_type = 'Water'
            group_id = 'c2ff2cff-662b-4f8b-bf52-bc12c2bedeff'
        if product_group_dreamkas == 'Весовой Товар Колбаса Вареная, Сосиски, сардельки [18%]':
            group_id = 'd1ed362a-673b-48e5-9779-b5de1e7a790c'
        if product_group_dreamkas == 'Весовой Товар Колбаса Копченая [20%]':
            group_id = 'd1ed362a-673b-48e5-9779-b5de1e7a790c'
        if product_group_dreamkas == 'Йогурт, Творог, Сыр, Сливки, молочные напитки[20%, >5]':
            product_type = 'MilkProducts'
            group_id = '193ccf08-b3a9-43f1-be78-b7ba7ab5082e'
        if product_group_dreamkas == 'Сметана [15%, >1]':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'Ряженка,Снежок,айран, тан[ 20%, >5 ]':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'Молочка':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'Молоко[15% , >5]':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'Молоко[15%, >1](Жирность 3.2%)':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'Кефир [ 15 % ]':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'Йогурт[20%, >5]':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'Масло Сливочное[15%, >5]':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'йогурт':
            product_type = 'MilkProducts'
        if product_group_dreamkas == 'йогур':
            product_type = 'MilkProducts'
        for mgroup in market_groups:
            if product_group_dreamkas == mgroup['name']:
                group_id = mgroup['id']
        ## id/type
        priceType = 'FixPrice'
        item_name = item['name']
        
        unit = 'Piece'
        if str(item['type']) == '166':
            unit = 'Kilogram'
        ## Barcodes
        Barcodes_to_create = []
        VendorCodes_to_create = ''
        if 'barcodes' in str(item):
            for barcode in item['barcodes']:
                if product_check_code(barcode) == True:
                    Barcodes_to_create.append(barcode)
                else:
                    if VendorCodes_to_create == '':
                        VendorCodes_to_create = VendorCodes_to_create + barcode 
                    else:
                        VendorCodes_to_create = VendorCodes_to_create + ',' + barcode
        vatRate = 'NoVat'
        sellPricePerUnit = 0
        for price in item['prices']:
            if price['deviceId'] == 177572:
                sellPricePerUnit = float(price['value'])/100
                break
        dividerInKopecks = 'Rouble'
        if Barcodes_to_create.__len__() == 0:
            Barcodes_to_create = ''
        products_to_create.append([shop_id,product_type,priceType,item_name,unit,group_id,Barcodes_to_create,VendorCodes_to_create,vatRate,sellPricePerUnit,dividerInKopecks])
    print('a')
    for item in products_to_create:
        product_to_create = {
                'shopId' : item[0],
                'productType' : item[1],
                'priceType' : item[2],
                'name' : item[3],
                'unit' : item[4],
                'groupId' : item[5],
                'barCodes' : item[6],
                'VendorCode' : item[7],
                'vatRate' : item[8],
                'sellPricePerUnit' : item[9],
                'DividerInKopecks' : item[10]
            }
        resp = kontur_market_create_product(product_to_create['shopId'], product_to_create)
        if 'error' in str(resp):
            if "already contains barcode" in resp['error']['message']:
                product_id_to_check = resp['error']['message'].split('"Product ')[1].split(" already contains")[0]
                market_product_to_check = market_products_optimized_for_search_by_id.get(product_id_to_check)
                market_product_vs_product_to_create_differences = []
                if 'sellPricePerUnit' in str(market_product_to_check):
                    if float(str(market_product_to_check['sellPricePerUnit']).replace(',','.')) != float(str(product_to_create['sellPricePerUnit']).replace(',','.')):
                        price = {'SellPrice' : str(product_to_create['sellPricePerUnit']).replace(',','.')}
                        kontur_market_patch_product(product_to_create['shopId'], market_product_to_check['id'], price)
                        market_product_vs_product_to_create_differences.append(f"sellPricePerUnit. Market = {market_product_to_check['sellPricePerUnit']}. Dreamkas = {product_to_create['sellPricePerUnit']}")
                if 'barcodes' in str(market_product_to_check):
                    barcode_diff = False
                    for barcode in market_product_to_check['barcodes']:
                        if barcode not in product_to_create['barCodes']:
                            barcode_diff = True
                    for barcode in product_to_create['barCodes']:
                        if barcode not in market_product_to_check['barcodes']:
                            barcode_diff = True
                if barcode_diff == True:
                    market_product_vs_product_to_create_differences.append(f"barCodes. Market = {market_product_to_check['barcodes']}. Dreamkas = {product_to_create['barCodes']}")
                for difference in market_product_vs_product_to_create_differences:
                    print(product_to_create['name'], difference)
    print('a')

        
def kontur_market_get_shops():
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.get('https://api.kontur.ru/market/v1/shops',headers=headers)
    return resp.json()['items']
def kontur_market_get_product(shop_id,product_id):
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.get(f'https://api.kontur.ru/market/v1/shops/{shop_id}/products/{product_id}',headers=headers)
    return resp.json()
def kontur_market_get_products(shop_id):
    
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.get(f'https://api.kontur.ru/market/v1/shops/{shop_id}/products',headers=headers)
    return resp.json()['items']
def kontur_market_get_product_groups(shop_id):
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.get(f'https://api.kontur.ru/market/v1/shops/{shop_id}/product-groups',headers=headers)
    return resp.json()['items']
def kontur_market_create_product(shop_id, product_data):
    """
    Template for product_data:
    'id' - non essential
    'shopId' - shop_id
    'productType' = One of these:
    LightAlcohol,HighAlcohol,AnotherExcise,Product,
    TechCard,Service,Prepayment,Tobacco,Shoes,Medicine,MarkedDress,
    Tires,Perfume,PhotoEquipment,MilkProducts,Water,Furs,Bio,Antiseptic,
    Softdrinks,MedicalDevices,Vetpharma,Seafood,Nabeer,Bicycle,PetFood,
    VegetableOil,Conserve,AutoFluids,Grocery,Chemistry
    'priceType' = 'FixPrice' - fixed price, 'WithoutPrice' - set it on cash register, 'PriceRule' - Sets it to % 
    'name' - product name, literally
    'unit' - 'Kilogram', 'Piece' preferred but others are available
    'groupId' - group id, get them from group ids func
    'barCodes' - [] list, separated by comma, 
    'VendorCode' - Article of good, text n stuff, optional.
    'vatRate' - 'NoVat' pref unless others wanted/needed, see api itsel.
    'sellPricePerUnit' - literally price of sale if 'FixPrice' is used.
    'Percent' - percentage of price if 'PriceRule' is used.
    'DividerInKopecks' - one of next: None,TenKopecks,HalfRouble,Rouble,FiveRouble,TenRouble
    """
    

    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.post(f'https://api.kontur.ru/market/v1/shops/{shop_id}/products',headers=headers, json=product_data)
    return resp.json()

def kontur_market_patch_product(shop_id, product_id, product_data):
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    resp = session.patch(f'https://api.kontur.ru/market/v1/shops/{shop_id}/products/{product_id}',headers=headers, json=product_data)
    return resp

def kontur_market_send_products(shop_id):
    headers = {
        'x-kontur-apikey': KONTUR_MARKET_API_KEY
    }
    json_data = []
    resp = session.post(f'https://api.kontur.ru/market/v1/shops/{shop_id}/products/syncCashboxes',headers=headers, json=json_data)
    return resp
    
def kontur_market_product_mass_action_107(product_ids,cardsAction,additional_data):
    """ 
    to be found more about this
    cardIds = [] of ids.
    cardsAction:ChangeUnitType
        
    """
    link = "https://market.kontur.ru/api/v107/b5e5e815-6c18-4168-8957-83887becb83a/{KONTUR_MARKET_RETAIL_OUTLET_ID}/KONTUR_MARKET_SHOP_ID/Cards/StartMassAction"
    json = {"cardIds":product_ids,"cardsAction":cardsAction,"value":additional_data}
    resp = session.post(link, json=json)
    return resp
    
def kontur_market_patch_product_107(product_id, product_data):
    link = "https://market.kontur.ru/api/v107/b5e5e815-6c18-4168-8957-83887becb83a/{KONTUR_MARKET_RETAIL_OUTLET_ID}/KONTUR_MARKET_SHOP_ID/Cards/SaveCard"
    resp = session.post(link, json=product_data)
    return resp.json()

def create_links_from_dreamkas_products(dreamkas_products):
    for dreamkas_product in dreamkas_products:
        print(dreamkas_product)
        
def create_document_from_excel_kontur(excel_attachment, msg_sender):
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
            
    return
# json_vatRate = None if vatRate == 'NoVat'
# product_data = {"card":
#     {"cateringIngredient":None,
#      "id":product_id,
#      "ownerDepartmentId":"{KONTUR_MARKET_RETAIL_OUTLET_ID}",
#      "naturalId":code,
#      "cateringIngredientId":None,
#      "name":"name","capacity":None,
#      "alcoholByVolumeRange":None,
#      "packed":true,
#      "canChangePack":False,
#      "category":"NonAlcoholic",
#      "alcoholCategory":None,
#      "barCodes":barcodes,
#      "egaisCodes":[],
#      "isDeleted":False,
#      "isArchived":False,
#      "archiveDate":None,
#      "needToProcess":False,
#      "needToShowSellPriceTrigger":False,
#      "lastShownTriggerInfo":None,
#      "currentTriggerInfos":[],
#      "packs":[],
#      "withoutBarcode":False,
#      "groupId":groupId,
#      "forceProcessed":False,
#      "vatRate":json_vatRate,
#      "prices":
#          {"sellPrice":190,
#           "percent":None,
#           "dividerInKopecks":None,
#           "buyPrice":None,
#           "buyPriceDate":None,
#           "priceType":"FixPrice",
#           "documentId":None,
#           "isDiscountDisabled":False,
#           "averageBuyPrice":None,
#           "isBonusDisabled":False},
#      "taxSystem":"Patent",
#      "unitType":"Piece",
#      "vendorCode":None,
#      "description":None,
#      "ingredients":None,
#      "consumables":None,
#      "alternativeUnitQuantity":1000,
#      "alternativeUnitType":"Gram",
#      "versionId":None,
#      "ingredientIn":[],
#      "consumableIn":[],
#      "kitchenId":None,
#      "modifiersKitIds":None,
#      "productType":"CommonCard",
#      "modificationDataInfo":{
#          "metaCardId":None,
#          "modificationCardIds":[],
#          "cardModifications":[]},
#      "additionalInfoData":{
#          "country":"","producer":"",
#          "structure":""},
#      "serviceDuration":None,
#      "minimumBalance":None,
#      "keepingPeriod":None,
#      "technoTechCard":None,
#      "timestamp":639019459445532300,
#      "isTechCardExcise":False,
#      "numberOfServings":None,
#      "withBalance":False,
#      "orderQuantum":None,
#      "cateringTechCardId":None,
#      "techCardUnitType":None,
#      "ingredientsUnitType":None,
#      "beverageCodes":[],
#      "producers":[],
#      "products":[],
#      "quantity":0,
#      "shopQuantity":0,
#      "fullQuantity":0,
#      "storeQuantity":0,
#      "lastInventoryDate":None},
#     "cardSavingSource":"ProductCard"}
# ownerDepartmentId - organization id
# naturalId  - the natural id counting from 0 when products were created and going up, assigned auto by market
# 