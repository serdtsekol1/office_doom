import os
import threading
import time
import json
import barcodenumber
import pandas as pd
from datetime import date, timedelta
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

import datetime

from dremkas.settings import DREAM_KAS_API
from mainapp import global_var

def periodicTask():
    
    if global_var.init is True:
        return
    global_var.init = True
    from mainapp.kontur_market_api import kontur_market_send_products,kontur_market_get_shops,kontur_get_invoices,kontur_get_suppliers,kontur_update_products
    shop_id = kontur_market_get_shops()[0]['id']
    counter = 0
    while True:
        try:
            kontur_update_products()
            if counter % 60 == 0:
                kontur_get_suppliers()
                kontur_get_invoices()
            else:
                kontur_get_invoices(scan=True)
            kontur_market_send_products(shop_id)
            counter = counter + 1
            time.sleep(60)
        except:
            pass


class MainappConfig(AppConfig):
    name = 'mainapp'
    verbose_name = _('admin__mainapp')
    def ready(self):
        from mainapp.logging_utils import create_log_file
        global_var.log_filename = create_log_file()
        from mainapp.logging_utils import get_logger
        logger = get_logger(__name__)
        logger.info('Django up')
        
        if os.environ.get('RUN_MAIN', None) == 'true':
            thread = threading.Thread(target=periodicTask)
            thread.daemon = True
            thread.start()
            
            
        
        
        
        # if 'type' not in str(dproduct):
        #     continue
        # if dproduct['type'] == '796':
        #     m_unit = 'Piece'
        # if dproduct['type'] == '166':
        #     m_unit = 'Kilogram'
        # for barcode in dproduct['barcodes']:
        #     try:
        #         if market_products_optimized_for_search_by_barcode[barcode]['unit'] != m_unit:
        #             print(f"Unit of {market_products_optimized_for_search_by_barcode[barcode]['name']} Changed. {market_products_optimized_for_search_by_barcode[barcode]['unit']} > {m_unit}")
        #             ##resp = kontur_market_patch_product(shop_id, market_products_optimized_for_search_by_barcode[barcode]['id'], {'unit' : m_unit})
        #             if m_unit == 'Kilogram':
        #                 kilogram_ids.append(market_products_optimized_for_search_by_barcode[barcode]['id'])
        #                 counter_i = counter_i + 1
        #             if m_unit == 'Piece':
        #                 piece_ids.append(market_products_optimized_for_search_by_barcode[barcode]['id'])
        #                 counter_i = counter_i + 1
        #             if counter_i % 50 == 0 and counter_i > 1:
        #                 if piece_ids.__len__() > 0:
        #                     unq = list(set(piece_ids))
        #                     resp = kontur_market_product_mass_action_107(piece_ids, 'ChangeUnitType', 'Piece')
        #                     time.sleep(5)
        #                 if kilogram_ids.__len__() > 0:
        #                     unq = list(set(kilogram_ids))
        #                     resp = kontur_market_product_mass_action_107(kilogram_ids, 'ChangeUnitType', 'Kilogram')
        #                     time.sleep(5)
        #                 piece_ids = []
        #                 kilogram_ids = []

                    ##print(resp)
            # except:
            #     pass

    
    

    ## Mass change of dreemproduct names/dpts begin
    # df = pd.read_excel("Z:\\all_products_for_excel_2 edited.xlsx")
    # df2 = df.values
    # list_of_departments = DREAM_KAS_API.get_departments()
    # i = 0
    # for line in df2:
    #     i = i + 1
    #     flag_dpt = False
    #     product = DREAM_KAS_API.get_product(line[0])
    #     if product['name'] != line[1]:
    #         DREAM_KAS_API.change_product_v2(line[0], 'name', line[1])
    #         print(f"Product name changed from {product['name']} to {line[1]}")
    #     if "'department'" not in str(product) and str(line[2]) != 'nan':
    #         flag_dpt = True
    #     if "'department'" in str(product):
    #         if flag_dpt != True:
    #             if product['department']['name'] != line[2]:
    #                 flag_dpt = True
    #     if flag_dpt:
    #         department_to_change_to = 'nan'
    #         for department in list_of_departments:
    #             if department['name'] == line[2]:
    #                 department_to_change_to = department['id']
    #                 break
    #         if str(department_to_change_to) != 'nan':
    #             DREAM_KAS_API.update_good(line[0], group_id=department_to_change_to)
    #             print(f"Product {line[1]} department changed from ",('None' if 'department' not in product else product['department']['name']),f" to {line[2]}")
    #     if product['isMarked'] != line[3]:
    #         DREAM_KAS_API.change_product_v2(line[0], 'isMarked', line[3])
    #     if i % 250 == 0:
    #         print(f"Processed {i} products")
    ## Mass change of dreemproduct names/dpts end
    # import barcodenumber


    # if not os.path.exists("./receipts/"):
    #     os.makedirs("./receipts/")
    # receipt_list = os.listdir('./receipts')
    # print('Begin Receipt collect')
    # for i in range(10):
    #     if f"{str((date.today()-timedelta(days=550-i)).day).zfill(2)}-{str((date.today()-timedelta(days=550-i)).month).zfill(2)}-{(date.today()-timedelta(days=550-i)).year}.json" not in receipt_list:
    #         receipt = DREAM_KAS_API.get_receipts_for_a_day(date_from_day=(date.today()-timedelta(days=550-i)).day,
    #                                     date_from_month=(date.today()-timedelta(days=550-i)).month,
    #                                     date_from_year=(date.today()-timedelta(days=550-i)).year,
    #                                     date_to_day=(date.today()-timedelta(days=550-i)).day,
    #                                     date_to_month=(date.today()-timedelta(days=550-i)).month,
    #                                     date_to_year=(date.today()-timedelta(days=550-i)).year)
    #         data = receipt[0]['data']
    #         print('Receipt collect')
    #         with open(f"./receipts/{str((date.today()-timedelta(days=550-i)).day).zfill(2)}-{str((date.today()-timedelta(days=550-i)).month).zfill(2)}-{(date.today()-timedelta(days=550-i)).year}.json", "w", encoding="utf-8") as f:
    #             json.dump(data, f, indent=2, ensure_ascii=False)
    #         time.sleep(1)
    # print('End Receipt collect')
    # sold_products = []
    # sold_products_2 = {}
    # print('Begin Product id Collect')
    # counter = 0
    # for receipt in os.listdir('./receipts'):
    #     with open(f"./receipts/{receipt}", "r", encoding="utf-8") as f:
    #         try:
    #             data = json.load(f)
    #             for sale in data:
    #                 for sale_position in sale['positions']:
    #                     if sale_position['id'] not in sold_products:
    #                         sold_products.append(sale_position['id'])
    #                         sold_products_2[sale_position['id']] = 1
    #                     else:
    #                         sold_products_2[sale_position['id']] = sold_products_2[sale_position['id']] + 1
    #             if counter % 100 == 0:
    #                 print('Product id Collect')
    #             counter = counter + 1
    #         except:
    #             pass
    # print('End Product id Collect')
    # if not os.path.exists("./products/"):
    #     os.makedirs("./products/")
    # print('Begin Product Collect')
    # ## Uncomment when done
    # ## for sold_product in sold_products:
    # ##     if not os.path.exists(f"./products/{sold_product}.json"):
    # ##         product = DREAM_KAS_API.get_product(sold_product)
    # ##         with open(f"./products/{sold_product}.json", "w", encoding="utf-8") as f:
    # ##             json.dump(product, f, indent=2, ensure_ascii=False)
    # ##     print('Product Collect')
    # ## print('End Product Collect')
    # all_products_for_excel = []
    # for product in os.listdir("./products/"):
    #     with open(f"./products/{product}", "r", encoding="utf-8") as f:
    #         product_data = json.load(f)
    #         if 'E_NOT_FOUND' in str(product_data):
    #             continue
    #         barcode_for_excel = ''
    #         codes_for_excel = ''
    #         if 'E_INTERNAL' in str(product_data):
    #             continue
    #             #product = DREAM_KAS_API.get_product(product.strip('.json'))
    #             #if 'E_INTERNAL' in str(product):
    #                 #continue
    #         if 'barcodes' in str(product_data):
    #             for barcode in product_data['barcodes']:
    #                 if product_check_code(input=barcode):
    #                     barcode_for_excel = barcode_for_excel + barcode + ','
    #                 else:
    #                     codes_for_excel = codes_for_excel + barcode + ','
    #         if product_data['unit'] == 796:
    #             product_countable_for_excel = 'шт'
    #         else:
    #             product_countable_for_excel = 'кг'
    #         type_of_product_for_excel = 'Простой товар'
    #         if product_data['type'] == 'TOBACCO':
    #             type_of_product_for_excel = 'Табак'
    #         department_name = ''
    #         try:
    #             department_name = product_data['department']['name']
    #         except:
    #             pass
    #         price = 0
    #         try:
    #             price = product_data['prices'][0]['value']/100
    #         except:
    #             pass
            
    #         product_for_excel = [product_data['name'],barcode_for_excel,price,product_countable_for_excel,codes_for_excel,'0%',type_of_product_for_excel,0,0,department_name]
    #         all_products_for_excel.append(product_for_excel)
    # for excel_product in all_products_for_excel:
    #     if excel_product[0] in str(market_products):
    #         continue
    #     if excel_product[1].strip(',').split(',')[0] in str(market_products) and excel_product[1].strip(',').split(',')[0] is not '':                        
    #         for market_product in market_products:
    #             if excel_product[1].strip(',').split(',')[0] in str(market_product):
    #                 if market_product['name'] != excel_product[0].strip():
    #                     print('fail')
    #         continue
    #     product_type = 'Product'
    #     if excel_product[6] == 'Табак' or excel_product[9] == 'Сигареты, Табачная продукция [Индивидуальная наценка]' or 'Сигареты' in excel_product[9]:
    #         product_type = 'Tobacco'
    #     milk_product_list = ['Творог[20%,>5]','Йогурт[20%, >5]','Молоко[15%, >1](Жирность 3.2%)','Молоко Длительного Хранения[20%, >5]','Сырок Творожный[ 20%, =1]','Ряженка,Снежок,айран, тан[ 20%, >5 ]','Молоко[15% , >5]','Молочная продукция[20%, >5]','Кефир [ 15 % ]','Молочка','Йогурт, Творог, Сыр, Сливки, молочные напитки[20%, >5]','Мороженое [30%, >5]','Сметана [15%, >1]','Масло Сливочное[15%, >5]',]
    #     for milk_product in milk_product_list:
    #         if excel_product[9] == milk_product:
    #             product_type = 'MilkProducts'
    #             break
    #     if excel_product[9] == 'Вода, соки, нектары, напитки [30%,>5]':
    #         product_type = 'Water'
    #     if excel_product[9] == 'Весовой Товар Колбаса Вареная, Сосиски, сардельки [18%]' or 'Весовой Товар Колбаса Копченая [20%]':
    #         group_id = 'd1ed362a-673b-48e5-9779-b5de1e7a790c' ## 'Колбаса, Сосиски, сардельки [25%]'
    #     if excel_product[9] == 'Йогурт, Творог, Сыр, Сливки, молочные напитки[20%, >5]':
    #         group_id = '193ccf08-b3a9-43f1-be78-b7ba7ab5082e' ## 'Йогурт, Творог, Сыр, Сливки[22%, >5]'
    #     for product_group in product_groups:
    #         if excel_product[9] == product_group['name']:
    #             group_id = product_group['id']
    #             break
    #     unit = 'Piece'
    #     if excel_product == 'кг':
    #         unit = 'Kilogram'
    #     print(excel_product)
    #     barCodes = excel_product[1].strip(',').split(',')
    #     if barCodes == ['']:
    #         barCodes = None
    #     product_to_create = {
    #         'shopId' : shop_id,            
    #         'productType' : product_type,
    #         'priceType' : 'FixPrice',
    #         'name' : excel_product[0],
    #         'unit' : unit,
    #         'groupId' : group_id,
    #         'barCodes' :  barCodes,
    #         'VendorCode' : excel_product[4],
    #         'vatRate' : 'NoVat',
    #         'sellPricePerUnit' : excel_product[2],
    #         'DividerInKopecks' : 'Rouble'
    #     }
    #     resp_create = kontur_market_create_product(shops[0]['id'],product_to_create)
    #     print(f'product {excel_product[0]} created')
    #     if 'name' not in str(resp_create) or 'id' not in str(resp_create) or 'productType' not in str(resp_create):
    #         print(resp_create)
    
    # print("Автоматическое обновление накладных")
    # from mainapp.Dreamkas_documents.update_documents import update_documents
    # from mainapp.Reports.invoice_report import create_invoice_report
    # from mainapp.Reports.invoice_report import invoice_report_range_of_dates
    # from mainapp.models import Correction_invoice_v3,Invoice_v3,Pricing_order_v3,Position_pricing_order_v3,Position_invoice_v3,Position_correction_invoice_v3
    # from mainapp.Dreamkas_documents.funcs import find_latest_document_iteration
    # from mainapp.dreamkas_documents import global_draft_cleanup
    # # Initial update    
    # # update_documents(invoices=False,pricing_orders=False,correction_invoices=False,blanks=False,to_check_for_fixed_documents=False,find_latest_iterations=False)
    # i = 0
    # while True:            
    #     if i > 60:
    #         global_var.invoices_num = 50  
    #         global_var.pricing_num = 100
    #         global_var.correction_invoices_num = 10
    #         i = 0
    #         time.sleep(60)
    #     else:
    #         global_var.invoices_num = 10
    #         global_var.pricing_num = 20
    #         global_var.correction_invoices_num = 5
    #         i = i + 1
    #         time.sleep(60)
    #     global_var.invoices_being_updated = True
    #     if global_var.new_invoices_num is not None:
    #         global_var.invoices_num = global_var.new_invoices_num
    #         global_var.new_invoices_num = None
    #     if global_var.new_pricing_num is not None:
    #         global_var.pricing_num = global_var.new_pricing_num
    #         global_var.new_pricing_num = None
    #     if global_var.new_correction_invoices_num is not None:
    #         global_var.correction_invoices_num = global_var.new_correction_invoices_num
    #         global_var.new_correction_invoices_num = None
            
    #     try:
    #         update_documents(invoices=True,pricing_orders=True,invoice_limit=global_var.invoices_num,pricing_order_limit=global_var.pricing_num,correction_invoices=True,correction_invoice_limit=global_var.correction_invoices_num,to_fetch_unpriced_invoices=False,blanks=False)
    #         global_draft_cleanup()
    #     except:
    #         pass
    #     global_var.invoices_being_updated = False
    #     global_var.invoices_last_update_at = datetime.datetime.now()
    #     global_var.invoices_next_update_at = datetime.datetime.now() + datetime.timedelta(seconds=60)
    #     global_var.save_persistent_vars()












            
# def make_new_products_from_dreamkas(dreamkas_groups,dproducts,mproducts,shop_id):
#     optimized_dreamkas_groups = {}
#     for dreamkas_group in dreamkas_groups['categories']:
#         optimized_dreamkas_groups[str(dreamkas_group['id'])] = dreamkas_group['name']
#     for dproduct in dproducts:
#         if 'updatedAt' in str(dproduct):
#             if (datetime.datetime.now() - datetime.datetime.strptime(dproduct['updatedAt'], '%Y-%m-%dT%H:%M:%S.%fZ')) > timedelta(days=10):
#                 pass
#         else:
#             continue
#         need_to_create = False
#         if dproduct['name'] not in str(mproducts):
#             if 'barcodes' in str(dproduct):
#                 found_barcode = False
#                 for barcode in dproduct['barcodes']:
#                     if barcode in str(mproducts):
#                         found_barcode = True
#                 if found_barcode == False:
#                     need_to_create = True
#             else:
#                 need_to_create = True
#         if need_to_create == True:    
#             barcodes_to_create = []
#             vendor_codes_to_create = []
#             for barcode in dproduct['barcodes']:
#                 if barcode not in str(mproducts):
#                     if product_check_code(barcode) == True:
#                         barcodes_to_create.append(barcode)
#                     barcodes_to_create.append(barcode)
#                 if barcode in str(mproducts):
#                     print('a')
#                     flag_yes = False
#                     if flag_yes == True:
#                         pass ## manual imput
#             product_type = 'Product'
#             if 'group_id' in str(dproduct):
#                 if 'Табак' in optimized_dreamkas_groups[str(dproduct['group_id'])] or 'Сигареты, Табачная продукция [Индивидуальная наценка]' in optimized_dreamkas_groups[str(dproduct['group_id'])] or 'Сигареты' in optimized_dreamkas_groups[str(dproduct['group_id'])]:
#                     product_type = 'Tobacco'
#                 milk_product_list = ['Творог[20%,>5]','Йогурт[20%, >5]','Молоко[15%, >1](Жирность 3.2%)','Молоко Длительного Хранения[20%, >5]','Сырок Творожный[ 20%, =1]','Ряженка,Снежок,айран, тан[ 20%, >5 ]','Молоко[15% , >5]','Молочная продукция[20%, >5]','Кефир [ 15 % ]','Молочка','Йогурт, Творог, Сыр, Сливки, молочные напитки[20%, >5]','Мороженое [30%, >5]','Сметана [15%, >1]','Масло Сливочное[15%, >5]',]
#                 for milk_product in milk_product_list:
#                     if milk_product in optimized_dreamkas_groups[str(dproduct['group_id'])]:
#                         product_type = 'MilkProducts'
#                         break
#                 if 'Вода, соки, нектары, напитки [30%,>5]' in optimized_dreamkas_groups[str(dproduct['group_id'])]:
#                     product_type = 'Water'
                
#                 if 'Весовой Товар Колбаса Вареная, Сосиски, сардельки [18%]' in optimized_dreamkas_groups[str(dproduct['group_id'])]:
#                     group_id = 'd1ed362a-673b-48e5-9779-b5de1e7a790c'
#                 if 'Весовой Товар Колбаса Копченая [20%]' in optimized_dreamkas_groups[str(dproduct['group_id'])]:
#                     group_id = 'd1ed362a-673b-48e5-9779-b5de1e7a790c'
#                 unit = 'Piece'
#                 if str(dproduct['type']) == '166':
#                     unit = 'Kilogram'
                
                    
            # if excel_product[6] == 'Табак' or excel_product[9] == 'Сигареты, Табачная продукция [Индивидуальная наценка]' or 'Сигареты' in excel_product[9]:
            #                 product_type = 'Tobacco'
            #             milk_product_list = ['Творог[20%,>5]','Йогурт[20%, >5]','Молоко[15%, >1](Жирность 3.2%)','Молоко Длительного Хранения[20%, >5]','Сырок Творожный[ 20%, =1]','Ряженка,Снежок,айран, тан[ 20%, >5 ]','Молоко[15% , >5]','Молочная продукция[20%, >5]','Кефир [ 15 % ]','Молочка','Йогурт, Творог, Сыр, Сливки, молочные напитки[20%, >5]','Мороженое [30%, >5]','Сметана [15%, >1]','Масло Сливочное[15%, >5]',]
            #             for milk_product in milk_product_list:
            #                 if excel_product[9] == milk_product:
            #                     product_type = 'MilkProducts'
            #                     break
            #             if excel_product[9] == 'Вода, соки, нектары, напитки [30%,>5]':
            #                 product_type = 'Water'
            #             if excel_product[9] == 'Весовой Товар Колбаса Вареная, Сосиски, сардельки [18%]' or 'Весовой Товар Колбаса Копченая [20%]':
            #                 group_id = 'd1ed362a-673b-48e5-9779-b5de1e7a790c' ## 'Колбаса, Сосиски, сардельки [25%]'
            #             if excel_product[9] == 'Йогурт, Творог, Сыр, Сливки, молочные напитки[20%, >5]':
            #                 group_id = '193ccf08-b3a9-43f1-be78-b7ba7ab5082e' ## 'Йогурт, Творог, Сыр, Сливки[22%, >5]'
            #             for product_group in product_groups:
            #                 if excel_product[9] == product_group['name']:
            #                     group_id = product_group['id']
            #                     break
            #             unit = 'Piece'
            #             if str(dproduct['type']) == '166':
            #                 unit = 'Kilogram'
            #             print(excel_product)
            #             barCodes = dproduct['barcodes']
            #             if barCodes == ['']:
            #                 barCodes = None
            # product_to_create = {
            #     'shopId' : shop_id,            
            #     'productType' : product_type,
            #     'priceType' : 'FixPrice',
            #     'name' : dproduct['name'],
            #     'unit' : unit,
            #     'groupId' : group_id,
            #     'barCodes' :  barcodes_to_create,
            #     'VendorCode' : excel_product[4],
            #     'vatRate' : 'NoVat',
            #     'sellPricePerUnit' : excel_product[2],
            #     'DividerInKopecks' : 'Rouble'
            # }
            # kontur_market_create_product(shop_id, product_to_create)