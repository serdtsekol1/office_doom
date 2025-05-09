import os
from datetime import datetime
from slugify import slugify

import barcodenumber
import xmltodict
from django.core.files.uploadedfile import UploadedFile

from dremkas.settings import DIADOC_API, DREAM_KAS_API
from mainapp.models import DiadocInvoice, Supplier, DiadocPreset
from django.core.files.storage import default_storage

def update_diadoc_invoices_v2(diadoc_id, store_id):
    invoices = DIADOC_API.get_documents_v2(diadoc_id)
    for item in invoices:
        try:
            store_destination_id = store_id
            diadoc_invoice, diadoc_invoice_status = DiadocInvoice.objects.update_or_create(diadoc_id=item['id'], defaults={
                'kontragent': item['kontragent'],
                'sum': item['sum'],
                'number': item['num'],
                'issue_date': datetime.strptime(item['date'], "%d.%m.%Y").strftime("%Y-%m-%d"),
                'invoice_status': item['status'],
                'downloadlink': item['link_document_attachment'],
                'store_id': store_destination_id,
            })
            print(diadoc_invoice_status)
            print(diadoc_invoice.kontragent)
            print(diadoc_invoice.number)
            print(diadoc_invoice.issue_date)
            try:
                download_invoice_from_diadoc(item['id'])
                with open(f'media/diadoc_files/{item["id"]}.xml', "r", encoding='windows-1251', errors='ignore') as xmlfileObj:
                    data_dict = xmltodict.parse(xmlfileObj.read())
                valid_presets = get_diadoc_presets_for_file(data_dict)
            except Exception as ex:
                print(ex)
                continue
            if valid_presets is not False and valid_presets.__len__() is not 0:
                print(valid_presets)
                store_destination_id = valid_presets[0].store_destination_fk.store_id
                diadoc_invoice, diadoc_invoice_status = DiadocInvoice.objects.update_or_create(diadoc_id=item['id'], defaults={
                    'store_id': store_destination_id,
                })
        except:
            print('f')

def get_diadoc_presets_for_file(file):
    print('1111')
    inn = None
    try:
        inn = file["Файл"]["Документ"]["СвСчФакт"]["СвПрод"]["ИдСв"]["СвЮЛУч"]["@ИННЮЛ"]
    except:
        pass
    try:
        inn = file["Файл"]["Документ"]["СвСчФакт"]["СвПрод"]["ИдСв"]["СвИП"]["@ИННФЛ"]
    except:
        pass
    try:
        print(file["Файл"]["Документ"]["СвСчФакт"]["СвПрод"]["ИдСв"])
    except Exception as ex:
        print(file)
    if inn is None:
        print('Невозможно найти ИНН')
        return False
    valid_presets_inn = DiadocPreset.objects.filter(supplier_inn=inn)
    valid_presets_store_destination = []
    for preset in valid_presets_inn:
        try:
            if str(xmltodict.parse(preset.store_destination_information)) == str(file['Файл']['Документ']['СвСчФакт']['ГрузПолуч']['Адрес']):
                valid_presets_store_destination.append(preset)
                continue
        except:
            pass
        try:
            if str(xmltodict.parse(preset.store_destination_information)) == str(file['Файл']['Документ']['СвСчФакт']['СвПрод']['Адрес']):
                valid_presets_store_destination.append(preset)
                continue
        except:
            pass
        try:
            if str(xmltodict.parse(preset.store_destination_information)) == str(file['Файл']['Документ']['СвСчФакт']['ГрузПолуч']['Адрес']).replace('  ',' '):
                valid_presets_store_destination.append(preset)
                continue
        except:
            pass
        try:
            if ('||') in preset.store_destination_information:
                num = preset.store_destination_information.split('||').__len__()
                num_met = 0
                for str_val in preset.store_destination_information.split('||'):
                    if str_val in str(file['Файл']['Документ']['СвСчФакт']['ГрузПолуч']['Адрес']):
                        num_met = num_met + 1
                if num_met == num:
                    valid_presets_store_destination.append(preset)
                    continue
        except:
            pass
        try:
            if str(xmltodict.parse(preset.store_destination_information)) == str(file['Файл']['Документ']['СвСчФакт']['ГрузПолуч']['ИдСв']):
                valid_presets_store_destination.append(preset)
                continue
        except:
            pass
    return valid_presets_store_destination



def generate_document_from_preset(document,diadocpreset):
    prefix = diadocpreset
    return
def download_invoice_from_diadoc(diadoc_document_id):
    print('1113')
    file_name = f'media/diadoc_files/{diadoc_document_id}.xml'
    print('1114')
    download_link = DiadocInvoice.objects.get(diadoc_id=diadoc_document_id).downloadlink
    print('11')
    print(download_link)
    print('asd')
    DIADOC_API.download(url=download_link, file_name=file_name)
    print('asd2')

def create_invoice_from_diadoc_document_v2(diadoc_user_id, diadoc_document_id):
    download_invoice_from_diadoc(diadoc_document_id)
    print('test_1')
    file_name = f'media/diadoc_files/{diadoc_document_id}.xml'
    with open(file_name, "r", encoding='windows-1251', errors='ignore') as xmlfileObj:
        data_dict = xmltodict.parse(xmlfileObj.read())
    valid_presets = get_diadoc_presets_for_file(data_dict)
    if valid_presets.__len__() == 0:
        print('Количество подходящих шаблонов - 0. Настройте шаблоны')
        return
    print('test_2')
    if valid_presets.__len__() > 1:
        print('КОличество подходящик шаблонов - более одного. Настройте шаблоны.')
        for valid_preset in valid_presets:
            print(valid_preset.id)
            print(valid_preset.preset_name)
            print(valid_preset.supplier_fk)

        return
    data = {}
    preset = valid_presets[0]
    print('test_3')
    date_flag = False
    try:
        data.update({"date": datetime.strptime(data_dict["Файл"]["Документ"]["СвСчФакт"]["@ДатаСчФ"], "%d.%m.%Y").strftime("%Y-%m-%d")})
        date_flag = True
    except Exception as Ex:
        pass
    if date_flag is not True:
        try:
            data.update({"date": datetime.strptime(data_dict["Файл"]["Документ"]["СвСчФакт"]["@ДатаДок"], "%d.%m.%Y").strftime("%Y-%m-%d")})
            date_flag = True
        except Exception as Ex:
            pass
    if date_flag == False:
        raise Exception
    data.update({"inn": preset.supplier_inn})
    number_flag = False
    try:
        data.update({"doc_id": data_dict["Файл"]["Документ"]["СвСчФакт"]["@НомерСчФ"]})
        number_flag = True
    except Exception as Ex:
        pass
    if number_flag is not True:
        try:
            data.update({"doc_id": data_dict["Файл"]["Документ"]["СвСчФакт"]["@НомерДок"]})
            number_flag = True
        except Exception as Ex:
            pass
    goods = []
    for item in data_dict['Файл']['Документ']['ТаблСчФакт']['СведТов']:
        if item == "@НомСтр" or item == "@КолТов":
            new_position = search_goods_xml_diadoc(preset.supplier_prefix, data_dict['Файл']['Документ']['ТаблСчФакт']['СведТов'])
            print(new_position)
            goods.append(new_position)
            break
        new_position = search_goods_xml_diadoc(preset.supplier_prefix, item)
        print(new_position)
        goods.append(new_position)
    data.update({"positions": goods})
    partnerid = DREAM_KAS_API.search_partner_id_by_inn(data["inn"])
    print('creating_document')
    print('test_1')
    print(data["date"])
    print('test_2')
    print(partnerid)
    print('test_3')
    print(str(data["doc_id"]))
    print('test_3.5')
    try:
        result = DREAM_KAS_API.createdocument(data["date"], "Документ Создан Автоматически. Источник - Диадок", partnerid, str(data["doc_id"]), positions=data["positions"],target_store_id=preset.store_destination_fk.store_id)
    except Exception as Ex:
        print(Ex)
    print('result')
    print(result)
    print('endresult')
    print('test_4')
    return 'https://kabinet.dreamkas.ru/app/#!/documents/card~2F' + result['id']
def check_code(input):
        try:
            if barcodenumber.check_code('ean13', str(input)) or barcodenumber.check_code('ean8', str(input)):
                return True
        except Exception as e:
            print(e)
def search_goods_xml_diadoc(prefix,item):
    found_product = None
    productcode = None
    tempproductcode = ""
    if prefix is None:
        prefix = ''
    try:
        #Method 1
        if check_code(item['ДопСведТов']['@КодТов']):  # Case 1 : Barcode - correct, Found a good, product code is of a good. All good.
            productcode = item['ДопСведТов']['@КодТов']  # Case 2 : Barcode - correct, didn't find a good, product code is of a good. All good.
            found_product = DREAM_KAS_API.search_goods(productcode)  # Case 3 : Barcode - incorrect, nothing happens. All good.
            print('Method 1 Success')
    except:
        pass
    if found_product is None:
        try:
            #Method 1.5
            if check_code(item['ДопСведТов']['@КодТов'][1:14]):  # Case 1 : Barcode - correct, Found a good, product code is of a good. All good.
                productcode = item['ДопСведТов']['@КодТов'][1:14]  # Case 2 : Barcode - correct, didn't find a good, product code is of a good. All good.
                found_product = DREAM_KAS_API.search_goods(productcode)  # Case 3 : Barcode - incorrect, nothing happens. All good.
                print('Method 1.5 Success')
        except:
            pass
    if found_product is None:
        try:
            #Method 1.75
            if check_code(item['ДопСведТов']['@ГТИН'][1:14]):  # Case 1 : Barcode - correct, Found a good, product code is of a good. All good.
                productcode = item['ДопСведТов']['@ГТИН'][1:14]  # Case 2 : Barcode - correct, didn't find a good, product code is of a good. All good.
                found_product = DREAM_KAS_API.search_goods(productcode)  # Case 3 : Barcode - incorrect, nothing happens. All good.
                print('Method 1.75 Success')
        except:
            pass
    if found_product is None:
        #Method 2
        try:
            found_product = DREAM_KAS_API.search_goods((prefix + str(item['ДопСведТов']['@КодТов']).strip()))
            if productcode is None:
                productcode = prefix + str(item['ДопСведТов']['@КодТов'])  # If product code is not a barcode from prev. - apply prefix to code and set productcode as it.
            print('Method 2 Success')
            print("productcode :", productcode)
        ## Get good by applying Prefix to received code
        except:
            pass
    if found_product is None:
        #Method 3
        # if isinstance(productcode, list):
        #    productcode = productcode[0][3:16]
        # else:
        #    productcode = productcode[3:16]

        try:
            tempproductcode = item['ДопСведТов']['НомСредИдентТов']['НомУпак']
            if isinstance(tempproductcode, list):
                tempproductcode = str(tempproductcode[0][3:16])
            else:
                tempproductcode = str(tempproductcode[3:16])
            if check_code(tempproductcode):
                productcode = tempproductcode  # Barcode found in here, so this replaces any bs from before, including prefix and a code
                found_product = DREAM_KAS_API.search_goods(tempproductcode)

                ## Get good by stripping irrelevant numbers from list of codes, getting a good code
            print('Method 3 Success')
        except:
            pass
    if found_product is None:
        #Method 4
        try:
            goodtofind = []
            try:
                for good in (item['ИнфПолФХЖ2']):
                    if good['@Идентиф'] == "Для1С_Штрихкод":
                        goodtofind = str(good['@Значен']).split(',')
            except:
                pass
            if check_code(goodtofind[0]):
                productcode = goodtofind[0]
                print(goodtofind[0], "goodtofind[0] = EAN13/EAN8")
                found_product = DREAM_KAS_API.search_goods(goodtofind[0])
            if found_product is None:
                try:
                    if check_code(goodtofind[1]):
                        productcode = goodtofind[1]
                        print("goodtofind[0] result = None, Trying goodtofind[1]", found_product)
                        found_product = DREAM_KAS_API.search_goods(goodtofind[1])
                except:
                    pass
            else:
                pass
            if found_product is None:
                try:
                    if check_code(goodtofind[2]):
                        productcode = goodtofind[2]
                        print("goodtofind[0] result = None, Trying goodtofind[1]", found_product)
                        found_product = DREAM_KAS_API.search_goods(goodtofind[2])
                except:
                    pass
            else:
                pass
            print('Method 4 Success')
        except:
            pass
    if found_product is None:
        #Method 5
        try:
            tempproductcode = item['ДопСведТов']['НомСредИдентТов']['КИЗ']
            if isinstance(tempproductcode, list):
                tempproductcode = str(tempproductcode[0][1:14])
            else:
                tempproductcode = str(tempproductcode[1:14])
            if check_code(tempproductcode):
                productcode = tempproductcode  # Barcode found in here, so this replaces any bs from before, including prefix and a code
                found_product = DREAM_KAS_API.search_goods(tempproductcode)
            print('Method 5 Success')
        except:
            pass
        # if found_product is None:
    # if productcode is None:
    # productcode=item[] // ADD!!! ! ! ! ! ! !
    #   // IF NO CODE FOUND, IF NO PRODUCT FOUND - ADD NAME OF GOOD,LITERALLY NAME! INTO productcode!!!!!!!!!!!
    if found_product is None:
        #Method 6
        try:
            if tempproductcode == "":
                for word in slugify(item['@НаимТов']).split("-"):
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
            print('Method 6 Success')
            print("Productcode:", productcode)

        except:
            pass
    if found_product is None:
        #Method 7
        try:
            tempproductcode = item["ИнфПолФХЖ2"][1]["@Значен"]
            found_product = DREAM_KAS_API.search_goods(tempproductcode)
            print('Method 7 Success')
            print("found_product:", found_product )
            print("tempproductcode :", tempproductcode  )
        except:
            pass
    if found_product is None:
        #Method 8
        print('Method 8')
        try:
            if tempproductcode == "":
                for word in slugify(item['@НаимТов']).split('-'):
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
                productcode = prefix + tempproductcode
                print('Method 8 Success')
        except Exception as Ex:
            print(Ex)
            pass
    try:
        new_position = {
            "name": None if found_product else productcode,
            "barcodeControl": None,
            "amount": round(float(item["@КолТов"]) * 1000),
            "costWithTax": round(round(float(item["@СтТовУчНал"]) / float(item["@КолТов"]), 2) * 100),
            "sumCost": round(float(item["@СтТовУчНал"]) * 100),
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
    except Exception as Ex:
        print(Ex)
    return new_position
def debug_remove_deuplicate_diadoc_invoice_objects():
    from django.db.models import Count, Max
    invoice_counts = DiadocInvoice.objects.values('diadoc_id').annotate(count=Count('diadoc_id'))

    # Next, we filter to get only the barcodes that have multiple occurrences
    duplicate_invoices = invoice_counts.filter(count__gt=1)

    # Now, for each duplicate barcode, we find the object with the biggest id and delete it
    for invoice_count in duplicate_invoices:
        max_id = DiadocInvoice.objects.filter(diadoc_id=invoice_count['diadoc_id']).aggregate(max_id=Max('id'))['max_id']
        DiadocInvoice.objects.filter(id=max_id).delete()