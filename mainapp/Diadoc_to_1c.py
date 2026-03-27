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
            pass
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
                pass
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
    keyboard.send_keys(str(barcode))
    pyautogui.press("enter")


        

def process_for_partner(diadoc_document_id):
    import pyperclip
    import time, datetime
    from mainapp.Diadoc_to_1c import extract_positions_for_invoice
    positions,document_info = extract_positions_for_invoice(diadoc_document_id)
    def find_pic(picture_path):
        try:
            box = pyautogui.locateOnScreen(picture_path, confidence=0.8)
            return True
        except:
            return False
    def wait_for_change_on_screen(times=25):
        im1 = pyautogui.screenshot()
        counter = 0
        while True:
            im2 = pyautogui.screenshot()
            if im1 != im2:
                return True
            time.sleep(0.1)
            counter = counter + 1
            if counter > times:
                return False
    def wait_if_there_is_a_picture(picture_path):
        counter = 0
        while True:
            if counter > 5:
                return False
            box = None
            try:
                box = pyautogui.locateOnScreen(picture_path, confidence=0.8)
            except:
                pass
            if box is not None:
                return True
            else:
                time.sleep(1)
            counter += 1
    def wait_until_picture_appears_and_click(picture_path):
        counter = 0
        while True:
            try:
                box = pyautogui.locateOnScreen(picture_path, confidence=0.8)
                if box is not None:
                    x,y = pyautogui.center(box)
                    pyautogui.click(x,y)
                    time.sleep(5)
                    return True
            except Exception as e:
                pass
                time.sleep(0.2)
                counter = counter + 1
                if counter > 25:
                    return False
    def wait_until_picture_appears(picture_path):
        counter = 0
        while True:
            counter += 1
            if counter > 50:
                return None
            box = pyautogui.locateOnScreen(picture_path, confidence=0.8)
            if box is not None:
                return box
            else:
                time.sleep(0.1)
    import psutil
    process_list = ['1cv8s.exe','1cv8.exe',]
    for process in psutil.process_iter():
        for process_name in process_list:
            if process.name() == process_name:
                process.kill()
    import os
    
    os.startfile("C:\\Program Files (x86)\\1cv8\\common\\1cestart.exe")
    time.sleep(3)
    step = "Включение 1С"
    if not wait_until_picture_appears_and_click("mainapp\\1c\\1c_predpr_1.png"):
        print(f'fail at {step}')
        return False
    step = "Включение 1С 2"
    if not wait_until_picture_appears_and_click("mainapp\\1c\\enter.png"):
        print(f'fail at {step}')
        return False
    step = "Открыть номенклатуру"
    if not wait_until_picture_appears_and_click('mainapp\\1c\\nomencl_btn.png'):
        print(f'fail at {step}')
        return False
    keyboard.send_keys("*+Y")
    if not wait_until_picture_appears('mainapp\\1c\\nomencl.png'):
        print(f'fail at {step}')
        return False
    step = "Товары"
    pyautogui.click(850,450)
    time.sleep(0.5)
    for position in positions:
        product_name = position['product']['name'] if position['product'] else position['position']['name']
        if position.get('product') is not None:
            product_barcodes = [barcode for barcode in position['product']['barcodes']]
        else:
            product_barcodes = [position['position']['barcode']]
        keyboard.send_keys("{F7}")
        pyautogui.click(850,450)
        time.sleep(0.5)
        print("entering barcode: ", product_barcodes[0])
        pyperclip.copy(str(product_barcodes[0]))
        keyboard.send_keys("^v")
        time.sleep(0.2)
        keyboard.send_keys("{ENTER}")
        time.sleep(1)
        try:
            if find_pic("mainapp\\1c\\product_not_found.png"):
                keyboard.send_keys("{ENTER}")
                time.sleep(0.5)
                keyboard.send_keys("{INSERT}")
                time.sleep(0.5)
                pyperclip.copy(str(product_name))
                keyboard.send_keys("^v")
                time.sleep(0.5)
                keyboard.send_keys("{^ENTER}")
                time.sleep(2)
                pyautogui.click(1343, 190)
                time.sleep(0.1)
                pyautogui.click(1323, 315)
                time.sleep(0.1)
                pyautogui.click(1273, 650)
                time.sleep(0.5)
                pyautogui.click(342, 334)
                time.sleep(0.5)
                for barcode in product_barcodes:
                    pyperclip.copy(str(barcode))
                    keyboard.send_keys("{INSERT}")
                    time.sleep(0.3)
                    pyautogui.click(619, 396)
                    keyboard.send_keys("^v")
                    keyboard.send_keys("^{ENTER}")
                    time.sleep(0.5)
                break
        except Exception as e:
            print(e)
            break
        
            
        
        
        
    
    
    # for position in positions:
    #     barcode = position['position']['barcode']
    #     keyboard.send_keys(f"{barcode}{{ENTER}}")
    #     box = wait_if_there_is_a_picture("product_not_found.png")
    #     if box is True:
    #         box = wait_until_picture_appears("add_position.png")