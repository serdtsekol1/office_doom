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
        diadoc_invoice, diadoc_invoice_status = DiadocInvoice.objects.update_or_create(diadoc_id=item['id'], defaults={
            'kontragent': item['kontragent'],
            'sum': item['sum'],
            'number': item['num'],
            'issue_date': datetime.strptime(item['date'], "%d.%m.%Y").strftime("%Y-%m-%d"),
            # ({"date": datetime.datetime.strptime(data_dict["Файл"]["Документ"]["СвСчФакт"]["@ДатаСчФ"], "%d.%m.%Y").strftime("%Y-%m-%d")})
            'invoice_status': item['status'],
            'downloadlink': item['link_document_attachment'],
            'store_id': store_id,
        })
        print(diadoc_invoice_status)
        print(diadoc_invoice.kontragent)
        print(diadoc_invoice.number)
        print(diadoc_invoice.issue_date)

def get_diadoc_presets_for_file(file):
    inn = None
    try:
        inn = file["Файл"]["Документ"]["СвСчФакт"]["СвПрод"]["ИдСв"]["СвЮЛУч"]["@ИННЮЛ"]
    except:
        pass
    try:
        inn = file["Файл"]["Документ"]["СвСчФакт"]["СвПрод"]["ИдСв"]["СвИП"]["@ИННФЛ"]
    except:
        pass
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


    return valid_presets_store_destination



def generate_document_from_preset(document,diadocpreset):
    prefix = diadocpreset
    return
def create_invoice_from_diadoc_document_v2(diadoc_user_id, diadoc_document_id):
    file_name = f'media/diadoc_files/{diadoc_document_id}.xml'
    download_link = DiadocInvoice.objects.get(diadoc_id=diadoc_document_id).downloadlink
    DIADOC_API.download(url=download_link, file_name=file_name)
    with open(file_name, "r", encoding='windows-1251', errors='ignore') as xmlfileObj:
        data_dict = xmltodict.parse(xmlfileObj.read())
    valid_presets = get_diadoc_presets_for_file(data_dict)
    if valid_presets.__len__() == 0:
        print('Количество подходящих шаблонов - 0. Настройте шаблоны')
        return
    if valid_presets.__len__() > 1:
        print('КОличество подходящик шаблонов - более одного. Настройте шаблоны.')
        for valid_preset in valid_presets:
            print(valid_preset.id)
            print(valid_preset.preset_name)
            print(valid_preset.supplier_fk)

        return
    data = {}
    preset = valid_presets[0]
    data.update({"date": datetime.strptime(data_dict["Файл"]["Документ"]["СвСчФакт"]["@ДатаСчФ"], "%d.%m.%Y").strftime("%Y-%m-%d")})
    data.update({"inn": preset.supplier_inn})
    data.update({"doc_id": data_dict["Файл"]["Документ"]["СвСчФакт"]["@НомерСчФ"]})
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
    print(data["date"])
    print(partnerid)
    print(str(data["doc_id"]))
    result = DREAM_KAS_API.createdocument(data["date"], "Документ Создан Автоматически. Источник - Диадок", partnerid, str(data["doc_id"]), positions=data["positions"],target_store_id=preset.store_destination_fk.store_id)
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
    try:
        if check_code(item['ДопСведТов']['@КодТов']):  # Case 1 : Barcode - correct, Found a good, product code is of a good. All good.
            productcode = item['ДопСведТов']['@КодТов']  # Case 2 : Barcode - correct, didn't find a good, product code is of a good. All good.
            found_product = DREAM_KAS_API.search_goods(productcode)  # Case 3 : Barcode - incorrect, nothing happens. All good.
    except:
        pass
    if found_product is None:
        try:
            found_product = DREAM_KAS_API.search_goods((prefix + str(item['ДопСведТов']['@КодТов']).strip()))
            if productcode is None:
                productcode = prefix + str(item['ДопСведТов']['@КодТов'])  # If product code is not a barcode from prev. - apply prefix to code and set productcode as it.

        ## Get good by applying Prefix to received code
        except:
            pass
    if found_product is None:
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
        except:
            pass
    if found_product is None:
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
        except:
            pass
    if found_product is None:
        try:
            tempproductcode = item['ДопСведТов']['НомСредИдентТов']['КИЗ']
            if isinstance(tempproductcode, list):
                tempproductcode = str(tempproductcode[0][1:14])
            else:
                tempproductcode = str(tempproductcode[1:14])
            if check_code(tempproductcode):
                productcode = tempproductcode  # Barcode found in here, so this replaces any bs from before, including prefix and a code
                found_product = DREAM_KAS_API.search_goods(tempproductcode)
        except:
            pass
        # if found_product is None:
    # if productcode is None:
    # productcode=item[] // ADD!!! ! ! ! ! ! !
    #   // IF NO CODE FOUND, IF NO PRODUCT FOUND - ADD NAME OF GOOD,LITERALLY NAME! INTO productcode!!!!!!!!!!!
    if found_product is None:
        try:
            tempproductcode = ""
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
        except:
            pass
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