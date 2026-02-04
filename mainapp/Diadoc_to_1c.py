import time, datetime
from pywinauto import keyboard
import os
import psutil
import pyautogui


import xmltodict
from mainapp.diadoc_to_dreamkas import check_code
from mainapp.kontur_market_api import kontur_market_get_products, kontur_market_get_shops
from mainapp.models import DiadocInvoice, Invoice
from dremkas.settings import DIADOC_API
def update_diadoc_invoices(diadoc_account_id):
    try:
        invoices = DIADOC_API.get_documents_v2(diadoc_account_id)
        for item in invoices:
            try:
                diadoc_invoice, diadoc_invoice_status = DiadocInvoice.objects.update_or_create(
                    diadoc_id=item['id'], 
                    defaults={
                        'kontragent': item['kontragent'],
                        'sum': item['sum'],
                        'number': item['num'],
                        'issue_date': datetime.datetime.strptime(item['date'], "%d.%m.%Y").strftime("%Y-%m-%d"),
                        'invoice_status': item['status'],
                        'downloadlink': item['link_document_attachment'],
                        'diadoc_account_id': diadoc_account_id,
                    }
                )                
            except Exception as e:
                continue
    except Exception as e:
        return
    
def extract_positions_for_invoice(diadoc_document_id):
    resulting_positions = []
    try:
        shop_ids = kontur_market_get_shops()        
        products = kontur_market_get_products(shop_ids[0]['id'])
    except:
        return False
    positions, document_info = extract_positions_from_invoice(diadoc_document_id)
    if not positions:
        return False
    barcode_to_product = {}
    for product in products:
        for barcode in (product.get('barcodes') or []):
            barcode_to_product[barcode] = product
    for position in positions:
        matched_product = barcode_to_product.get(position['barcode'])
        resulting_positions.append({"position": position, "product": matched_product})
    return resulting_positions, document_info
def extract_positions_from_invoice(diadoc_document_id):
    all_positions = []
    file_name = f'media/diadoc_files/{diadoc_document_id}.xml'
    download_link = DiadocInvoice.objects.get(diadoc_id=diadoc_document_id).downloadlink
    DIADOC_API.download(url=download_link, file_name=file_name)
    try:
        with open(file_name, "r", encoding='windows-1251', errors='ignore') as xmlfileObj:
            data_dict = xmltodict.parse(xmlfileObj.read())
    except Exception as e:
        return False
    for position in data_dict['Файл']['Документ']['ТаблСчФакт']['СведТов']:
        productcode = None
        try:
             if check_code(position['ДопСведТов']['@КодТов'][1:14]):
                 productcode = position['ДопСведТов']['@КодТов'][1:14]
        except:
            continue
        if productcode is None:
            try:
                temp_productcode = position['ДопСведТов']['НомСредИдентТов']['НомУпак']
                if isinstance(temp_productcode, list):
                    temp_productcode = str(temp_productcode[0][3:16])
                else:
                    temp_productcode = str(temp_productcode[3:16])
                if check_code(temp_productcode):
                    productcode = temp_productcode
            except:
                continue
        if productcode is not None:
            new_position = {
                "barcode": productcode,
                "name" : position["@НаимТов"],
                "amount": round(float(position["@КолТов"])),
                "costWithTax": round(float(position["@ЦенаТов"])),
                "sumCost": round(float(position["@СтТовУчНал"]))
            }
        all_positions.append(new_position)
    document_sender = data_dict['Файл']['Документ']['СвСчФакт']['ГрузОт']['ГрузОтпр']['ИдСв']['СвЮЛУч']
    document_info = {
        "document_number": data_dict['Файл']['Документ']['СвСчФакт']['@НомерДок'],
        "document_date": data_dict['Файл']['Документ']['СвСчФакт']['@ДатаДок'],
        "document_sender_name": document_sender['@НаимОрг'],
        "document_sender_inn": document_sender['@ИННЮЛ'],
    }
    return all_positions, document_info
                                    
            
def add_product_to_invoice(barcode):
    keyboard.send_keys(f"{barcode}{{ENTER}}")


        

def process_for_partner(diadoc_document_id):
    import time, datetime
    from mainapp.Diadoc_to_1c import extract_positions_for_invoice
    positions,document_info = extract_positions_for_invoice(diadoc_document_id)
    from pywinauto import keyboard
    def wait_if_there_is_a_picture(picture_path):
        counter = 0
        while True:
            counter += 1
            if counter > 4:
                return False
            box = pyautogui.locateOnScreen(picture_path, confidence=0.8)
            if box is not None:
                return True
            else:
                time.sleep(1)
    def wait_until_picture_appears(picture_path):
        counter = 0
        while True:
            counter += 1
            if counter > 15:
                return None
            box = pyautogui.locateOnScreen(picture_path, confidence=0.8)
            if box is not None:
                return box
            else:
                time.sleep(1)
    import psutil
    process_list = ['1cv8s.exe','1cv8.exe',]
    for process in psutil.process_iter():
        for process_name in process_list:
            if process.name() == process_name:
                process.kill()
    import os
    os.startfile("C:\\Program Files (x86)\\1cv8\\common\\1cestart.exe")
    box = wait_until_picture_appears("1c_prepr_1.png")
    if box is None:
        pyautogui.alert(text='Не найдена кнопка для запуска 1С',button='OK',title='')
    x,y = pyautogui.center(box)
    time.sleep(1)
    pyautogui.click(x,y)
    time.sleep(1)
    box = wait_until_picture_appears("enter.png")
    if box is None:
        pyautogui.alert(text='Не найдена кнопка для запуска 1С (2)',button='OK',title='')
    x,y = pyautogui.center(box)
    time.sleep(1)
    pyautogui.click(x,y)
    time.sleep(1)
    box = wait_until_picture_appears("prihodnaya_nakladnaya.png")
    if box is None:
        pyautogui.alert(text='Не найдена кнопка Приходная накладная',button='OK',title='')
    x,y = pyautogui.center(box)
    time.sleep(1)
    pyautogui.click(x,y)
    time.sleep(1)
    box = wait_until_picture_appears("add_button.png")
    if box is None:
        pyautogui.alert(text='Не найдена кнопка Добавить накладную',button='OK',title='')
    x,y = pyautogui.center(box)
    time.sleep(2)
    pyautogui.click(x,y)
    time.sleep(1)
    box = wait_until_picture_appears("kontragent.png")
    if box is None:
        pyautogui.alert(text='Не найдена строка Контрагент',button='OK',title='')
    x,y = pyautogui.center(box)
    time.sleep(2)
    pyautogui.click(x,y)
    time.sleep(1)
    box = wait_until_picture_appears("add_position.png")
    if box is None:
        pyautogui.alert(text='Не найдена кнопка Добавить позицию',button='OK',title='')
    x,y = pyautogui.center(box)
    time.sleep(2)
    pyautogui.click(x,y)
    time.sleep(1)
    
    # for position in positions:
    #     barcode = position['position']['barcode']
    #     keyboard.send_keys(f"{barcode}{{ENTER}}")
    #     box = wait_if_there_is_a_picture("product_not_found.png")
    #     if box is True:
    #         box = wait_until_picture_appears("add_position.png")