import datetime
import operator
import pickle
import re
from enum import Enum
from itertools import groupby
import time

from slugify import slugify
import barcodenumber
from requests.auth import HTTPBasicAuth
from requests_html import HTMLSession

# from dremkas.settings import MEDIA_ROOT
from mainapp.helper import open_file_type, save_to_json


class DocType(Enum):
    PEREMESHENIE = 2
    OPRIHODOVANIE = 3
    SPISANIE = 4
    PRIHODNAYA_NAKLADNAYA = "5,13"
    KORREKTIROVKA = 7
    AKT_REALIZACII = 10
    PEREOCENKA = 11
    KASSOVAYA_SMENA = 12


# 0: {label: "Перемещение", value: 2}
# 1: {label: "Оприходование", value: 3}
# 2: {label: "Списание", value: 4}
# 3: {label: "Приходная накладная", value: "5,13"}
# 4: {label: "Корректировка приходной накладной", value: 7}
# 5: {label: "Акт реализации", value: 10}
# 6: {label: "Переоценка", value: 11}
# 7: {label: "Кассовая смена", value: 12}


class DreamKasApi:
    URL_HOST = "https://kabinet.dreamkas.ru"
    URL_LOGIN_API = f"{URL_HOST}/app/login"
    URL_DOCUMENTS_API = f"{URL_HOST}/api/documents"
    URL_DOCUMENTS_v1_API = f"{URL_HOST}/api/v1/documents"
    URL_PRODUCTS_API = f"{URL_HOST}/api/products"
    URL_PRODUCTS_API_V2 = f"{URL_HOST}/api/products"
    URL_PRODUCTS_SEARCH_API = f"{URL_HOST}/api/v2/products/search"
    URL_CONTACTS_PARTNERS_API = f"{URL_HOST}/api/v1/edx/paper/contacts"
    URL_STORE_VIEW = f"{URL_HOST}/api/v1/ui/products/store_view"
    LOGIN = None
    PASSWORD = None
    session = None
    MONTHS = {"январь": "01", "января": "01",
              "февраль": "02", "февраля": "02",
              "март": "03", "марта": "03",
              "апрель": "04", "апреля": "04",
              "май": "05", "мая": "05",
              "июнь": "06", "июня": "06",
              "июль": "07", "июля": "07",
              "август": "08", "августа": "08",
              "сентябрь": "09", "сентября": "09",
              "октябрь": "10", "октября": "10",
              "ноябрь": "11", "ноября": "11",
              "декабрь": "12", "декабря": "12"}

    def check_code(self, input):
        try:
            if barcodenumber.check_code('ean13', str(input)) or barcodenumber.check_code('ean8', str(input)):
                return True
        except Exception as e:
            print(e)

    def __init__(self, login, password, token=None):
        self.session = HTMLSession()
        if token:
            self.TOKEN = token
            self.session.headers = {"Authorization": f"Bearer {self.TOKEN}"}
        else:
            self.session.auth = HTTPBasicAuth(self.LOGIN, self.PASSWORD)
        self.LOGIN = login
        self.PASSWORD = password
        self.login_http()
    def login_http(self):
        """
        Можливо колись понадобиться стандартний логін через https
        :return:
        """
        response = self.session.post(f'https://kabinet.dreamkas.ru/app/login', verify=True, json={
            "login": self.LOGIN,
            "password": self.PASSWORD
        })
        self.session.cookies = response.cookies
        if response.status_code == 200:
            return response.json()
        else:
            print("Login failed")
            print(response.json())
            return "Login Failed"

    def get_product_history(self,id_out):
        link = 'https://kabinet.dreamkas.ru/api/stock/history/' + str(id_out)
        http_resp = self.session.get(link)
        return http_resp

    def get_inventory_checks(self):
        inventory_checks = self.session.get(
            f"https://kabinet.dreamkas.ru/api/v1/documents?limit=1000&offset=0&filter[type]=1&filter[preset]=DOCUMENTS")  # треба буде зберігати потім в виді моделі як і накладні.
        inventory_checks = inventory_checks.json()
        for inventory_check in inventory_checks:
            inventory_check["createdAt"] = datetime.datetime.strptime(inventory_check["createdAt"], "%Y-%m-%d").strftime("%d.%m.%Y")
        return inventory_checks

    def inventory_check(self, inventory_check_id):
        inventory_check = self.session.get(f"https://kabinet.dreamkas.ru/api/v1/documents/{inventory_check_id}").json()
        return inventory_check

    def merge_inventory_check_items(self, inventory_check_id):
        inventory_check = self.session.get(f"https://kabinet.dreamkas.ru/api/v1/documents/{inventory_check_id}").json()
        inventory_check_items = inventory_check["positions"]
        inventory_check_items.sort(key=operator.itemgetter('productId'))
        grouped_products = []
        for productId, group in groupby(inventory_check_items, key=operator.itemgetter('productId')):
            group = list(group)
            for item in group:
                if item["amount"] == None or item["amount"] == "null":
                    item["amount"] = 0
            total_amount = sum(int(item['amount']) for item in group)
            group[0]['amount'] = total_amount
            grouped_products.append(group[0])
        inventory_check["positions"] = grouped_products
        responce = self.session.patch(f"https://kabinet.dreamkas.ru/api/v1/documents/{inventory_check_id}/", json=inventory_check)

    def update_inventory_check(self, inventory_check_id, new_item):
        inventory_check = self.session.get(f"https://kabinet.dreamkas.ru/api/v1/documents/{inventory_check_id}").json()
        edited_inventory_check = inventory_check


        for item in new_item:
            new_position = {
                "documentId": inventory_check_id,
                "barcodeControl": None,
                "amount": round(float(item["value"]) * 1000),
                "product": None,
                "barcode": None,
                "productId": DreamKasApi.search_goods(self, item["data-id"])["id"],
                "marks": None,
                "marksChecked": None,
                "egaisAlc": None,
                "egaisCode": None,
                "egaisVolume": None,
                "egaisTypeCode": None,
                "egaisIsPacked": None
            }
            edited_inventory_check["positions"].append(new_position)

        responce = self.session.patch(f"https://kabinet.dreamkas.ru/api/v1/documents/{inventory_check_id}/", json=edited_inventory_check)
        print("a")
    def update_product(self, id_out, json):
        #resp = self.session.get(f"https://kabinet.dreamkas.ru/api/v2/products/{id_out}/").json()
        resp = self.session.patch(f"https://kabinet.dreamkas.ru/api/v2/products/{id_out}/", json=json)
        print(resp)
        return resp



    def update_good(self, good_id, group_id=None):
        response = self.session.get(f"https://kabinet.dreamkas.ru/api/v2/products/{good_id}/").json()
        response["departmentId"] = str(group_id)
        asd = self.session.patch(f"https://kabinet.dreamkas.ru/api/v2/products/{good_id}/", json=response)
        print(asd)

        ## Get : https://kabinet.dreamkas.ru/api/v2/products/[id]9f60977e-5e8e-4724-aaa3-3447a3ef0af4
    # Цей метод - старий і використвоується тільки для групп. Його збережено шоб не їбатись з переробкою.
    # Але потім - треба змінити на апдейт продукт, де буде прийматись змінений товар і просто ід.

    def search_partner_id_by_inn(self, inn, full_info=False):
        """
        Пошук поставщика по ІНН
        :param inn: ІНН
        :param full_info: Повна інформація поставщика/тільки id
        :return:
        """
        # TODO Якщо нема поставщика то треба звернутись до сервісу Dadata і по ньому створити новго поставщика в dreamkas
        # 991a11385053e95d9e289b4d65c87e7cecf50e7d - Token Який використовує dreamkas
        # 79cabf4b3ad875671861db3bb8a05f66829a0f46 - Token Який я зарегав на сайті https://dadata.ru/
        response = self.session.get(self.URL_CONTACTS_PARTNERS_API).json()
        search_res = [f for f in response if f.get("inn", None) == inn]
        if full_info:
            return search_res[0] if search_res else None
        if search_res == []:
            search_res = [f for f in response if f.get("inn", None) == str(inn)] # ЦЯ ХУЙНЯ ІСНУЄ БО ДРУМКАС ЯКОГОСЬ ХУЯ ПРИСОБАЧІЛИ ЗАМІСТЬ ІНТУ... ОДНОМУ
            ## СУКА!
            ## ОДНОМУ ПОСТАВЩИКУ ЗІ ВСЬОГО СПИСКУ ІНН В ВИДІ СТРІНГУ А НЕ ІНТУ. СУКААААААА НАХУУУУУУУУУЙ Я ЄБУ БЛЕАТЬ РОЗБИРАТИСЬ В ЇХ ФАКАПАХ. ЦЕ ДИБІЛІСТИКА НАХУЙ БЛЕАТЬ. ЯКОГО ХУЯ ВОНИ ЦЕ РОБЛЯТЬ?
            ## ЦЕ Ж ЗРОБЛЕНО ПО ДОЛБОЙОБСЬКІ
            if full_info:
                return search_res[0] if search_res else None
        return search_res[0]['id'] if search_res else None
        # ddata = Dadata("991a11385053e95d9e289b4d65c87e7cecf50e7d")
        # try:
        #     return ddata.find_by_id('party', q)[0]
        # except Exception as ex:
        #     print(ex)
        #     return None


    def search_goods(self, q, q_is_vendor_code=True, limit=10, use_stock=True, use_mrp_price=True):
        """
        Пошук товарів/товару
        :param q: Строка пошуку товару Example: "Курточка синя"
        :param q_is_vendor_code: True = Шукається тільки по вендор коду та штрихкоду, False = По всіх полях
        :param limit: Кількість товарів в результаті. Default 1
        :param use_stock:
        :param use_mrp_price:
        :return:
        """
        products = self.session.get(f'https://kabinet.dreamkas.ru/api/v2/products/search', params={
            "q": q,
            "limit": limit,
            "use_stock": use_stock,
            "use_mrp_price": use_mrp_price
        }).json()
        if q_is_vendor_code:
            for product in products:
                try:
                    if str(q) in product["vendorCodes"]:
                        return product
                except:
                    pass
                try:
                    if str(q) in product["barcodes"]:
                        return product
                except:
                    pass
        else:
            return products
        return None
    def get_stores(self):
        return self.session.get("https://kabinet.dreamkas.ru/api/v1/shops?").json()
    def get_devices(self):
        return self.session.get("https://kabinet.dreamkas.ru/api/devices").json()

    # def goods_analyzer(self, date_from, date_to):
    #     departments = self.get_departments()
    #     valid_Departments = []
    #     for department in departments:
    #         if "[" in department['name'] and "]" in department['name']:
    #             valid_Departments.append(department['id'])
    #     devices = self.get_devices()
    #     problematic_goods_invalid_department = []
    #     for device in devices:
    #         result = self.get_receipts(date_from, date_to, device['id'])
    #         for receipt in result['data']:
    #             for position in receipt['positions']:
    #                 if position['departmentId'] not in valid_Departments:
    #                     problematic_good = position['id']
    #                     if problematic_good not in problematic_goods_invalid_department:
    #                         problematic_goods_invalid_department.append(problematic_good)
    #     resulting_list_problematic_goods_invalid_department = []
    #     for good in problematic_goods_invalid_department:
    #         responce = self.session.get(f"https://kabinet.dreamkas.ru/api/v2/products/{good}").json()
    #         new_good = {'good_id' : responce['id'],  "good_name": responce['name'], "department_id": responce['departmentId']}
    #
    #         resulting_list_problematic_goods_invalid_department.append(new_good)
    #     date = datetime.datetime.strftime(datetime.datetime.today(), "%d-%m-%Y")
    #     save_to_json(f"media/report_technical_files/report_goods_invalid_department_{date}.json",resulting_list_problematic_goods_invalid_department)
    #     return None

    def get_departments(self):
        return self.session.get("https://kabinet.dreamkas.ru/api/departments").json()

    def get_receipts(self, date_from_year = None, date_from_month = None, date_from_day = None,  date_to_year = None, date_to_month = None, date_to_day = None, devices = None, store = None):
        if devices == None:
            if store == None:
                print('No device is or store selected')
                return
            from mainapp.models import Store
            devices = Store.objects.get(store_id=185449).store_devices
        else:
            if type(devices) is not list:
                print('devices accepts only list items. If there is only one device - put it into list of one')
                return
        date_from = datetime.datetime(date_from_year,date_from_month,date_from_day)
        date_to = datetime.datetime(date_to_year,date_to_month,date_to_day)
        current_date = date_from
        list_of_days = []
        while current_date <= date_to:
            list_of_days.append(current_date)
            current_date += datetime.timedelta(days=1)
        receipts = []
        for device in devices:
            for one_day in list_of_days:
                receipt = (self.get_receipts_for_a_day(date_from_year = one_day.year, date_from_month = one_day.month, date_from_day = one_day.day, date_to_year = one_day.year, date_to_month = one_day.month, date_to_day = one_day.day, device = device ))
                receipts.append(receipt)
        return receipts
    def get_receipts_for_a_day(self,date_from_year = None, date_from_month = None, date_from_day = None,  date_to_year = None, date_to_month = None, date_to_day = None, device = None):
        print('getting a receipt for a day', date_from_year, date_from_month, date_from_day)
        date_from = None
        date_to = None
        if date_from_year is None:
            if date_from_year == None and date_from_month == None and date_from_day == None:
                date_from = ''
            else:
                date_from = ''
                print('You need to enter year, month and day for "FROM" date. Applying no date instead')
        else:
            date_from = '&from=' + str(date_from_year) + '-' + str(date_from_month).zfill(2) + '-' + str(date_from_day).zfill(2) + "T00:00:00Z"

        if date_to_year is None:
            if date_to_year == None and date_to_month == None and date_to_day == None:
                date_to = ''
            else:
                date_to = ''
                print('You need to enter year, month and day for "FROM" date. Applying no date instead')
        else:
            date_to = '&to=' + str(date_to_year) + '-' + str(date_to_month).zfill(2) + '-' + str(date_to_day).zfill(2) + "T23:59:59Z"
        if device == None:
            device = ''
        else:
            device = '&devices=' + str(device)
        receipts = []
        receipt = self.session.get("https://kabinet.dreamkas.ru/api/receipts?" + date_from + date_to + device + "&limit=1000").json()
        receipts.append(receipt)
        if 'status' in str(receipt):
            print("https://kabinet.dreamkas.ru/api/receipts?" + date_from + date_to + device + "&limit=1000")
            print('status 400')
        offset = 0
        while receipt['data'].__len__() >= 1000:
            print(offset)
            offset = offset + 1000
            receipt = self.session.get("https://kabinet.dreamkas.ru/api/receipts?" + date_from + date_to + device + "&limit=1000&offset=" + str(offset)).json()
            if receipt['data'].__len__() != 0:
                receipts.append(receipt)
            else:
                break
        return receipts


    def createdocument(self, dataofdocument, comment, partner_id, doc_id, target_store_id=185449, positions=None):
        print('trying to get data')
        print(positions)
        if not positions:
            positions = []
        print('trying to get data')
        data = {
                "num": doc_id,
                "type": "INCOME_INVOICE",
                "comment": comment,
                "issueDate": dataofdocument,
                "partnerId": partner_id,
                "targetStoreId": target_store_id,
                "positions": positions,
                "status": "DRAFT"
                }
        print('data got')
        response = self.session.post(self.URL_DOCUMENTS_v1_API, json=data)
        return response.json()


    def price_invoice(self, positions):
        from mainapp.models import GoodGroups
        for item in positions:
            try:
                product = item['product']
                group = GoodGroups.objects.filter(group_id=product['categoryId']).first()
                if group:
                    if group.pricingpercent == 0:
                        item['price'] = "0"
                    else:
                        if group.roundnumber == 0:
                            round_number = 1
                        else:
                            round_number = group.roundnumber
                        price = int(item['costWithTax']) / 100
                        pricing_percent = group.pricingpercent
                        # method = item['method']
                        round_bigger_at = group.rule
                        price = round(price * (1 + pricing_percent / 100), 2)
                        if (price / round_number - int(price / round_number)) * round_number > round_number * round_bigger_at / 100:
                            price = int(int(price) / round_number) * round_number + round_number
                        else:
                            price = int(int(price) / round_number) * round_number

                    print(item)
                    print(price)
                    item['price'] = str(int(price * 100))
                    ## a = round(a*(1+b/100)),2)
                    ## a = result
                    ## b = percent to multiply. e.g. : 15% = 15, so in end it becomes 0.15, and multiply value is 1.15

                    ## if method = biggest
                    ## a = number
                    ## b = result
                    ## b =
                    # int(round(multiplied_sum/
                else:
                    item['price'] = "0"
            except Exception as ex:
                print(ex, item)
        return (positions)


    ## DREAM_KAS_API.create_pricing_order(type="PRICING_ORDER",parentId="39130105",comment="TESTTESTTESTTEST")
    ##responce2 = DREAM_KAS_API.create_pricing_order(39305438, type="PRICING_ORDER", parentId="39305438", comment="TESTTESTTESTTEST")
    ## Вот як отослати шо угодно через дримкас апи.
    def create_pricing_order(self, **keyword):
        # from mainapp.models import GoodGroups
        parentId = keyword.get("parentId")
        parent_document = self.get_document(parentId)
        target_store_id = parent_document['targetStoreId']
        positions = self.price_invoice(parent_document["positions"])

        # for item in positions:
        #     try:
        #         product = item['product']
        #         group = GoodGroups.objects.filter(group_id=product['categoryId']).first()
        #         if group:
        #             if group.pricingpercent == 0:
        #                 item['price'] = "0"
        #             else:
        #                 if group.roundnumber == 0:
        #                     round_number = 1
        #                 else:
        #                     round_number = group.roundnumber
        #                 price = int(item['costWithTax']) / 100
        #                 pricing_percent = group.pricingpercent
        #                 # method = item['method']
        #                 round_bigger_at = group.rule
        #                 price = round(price * (1 + pricing_percent / 100), 2)
        #                 if (price / round_number - int(price / round_number)) * round_number > round_number * round_bigger_at / 100:
        #                     price = int(price) + round_number
        #                 else:
        #                     price = int(price)
        #
        #             print(item)
        #             print(price)
        #             item['price'] = str(int(price * 100))
        #             ## a = round(a*(1+b/100)),2)
        #             ## a = result
        #             ## b = percent to multiply. e.g. : 15% = 15, so in end it becomes 0.15, and multiply value is 1.15
        #
        #             ## if method = biggest
        #             ## a = number
        #             ## b = result
        #             ## b =
        #             # int(round(multiplied_sum/
        #         else:
        #             item['price'] = "0"
        #     except Exception as ex:
        #         print(ex, item)

        data = {"type": "PRICING_ORDER",
                "targetStoreId": target_store_id, "positions": positions,
                "status": "DRAFT"}
        data.update(keyword)
        response = self.session.post(self.URL_DOCUMENTS_v1_API, json=data)
        return response.json()


    def delete_document(self, document_id):
        return

    def get_problematic_products(self,devices=[34796,31391,163617]):
    #     from datetime import timedelta, date
    #     today = date.today()
    #     last_day = date.today() - timedelta(days=1)
    #     for device in devices:
    #         responce = self.session.get(f"https://kabinet.dreamkas.ru/api/receipts?from={last_day}&to={today}&limit=1000&devices={device}")
    #         for item in responce.json()['data']['positions:']:
    #         self.session.get
        return "Work in progress"

    def get_products(self):
        offset = 0
        products_list = []
        existing_ids = set()  # Множина для зберігання існуючих id_out

        while True:
            for attempt in range(20):
                try:
                    response = self.session.get(f"https://kabinet.dreamkas.ru/api/products?limit=1000&offset={offset}")
                except:
                    print(f"Не удалось скачать продукты. Следующая попытка через ", attempt*(attempt/2), " секунд")
                    #time.sleep(attempt * (attempt / 1000))
                    continue
                if response.status_code == 200:
                    break
            products_data = response.json()

            if not products_data:
                break

            print(f'Скачиваются продукты. Прогресс - {offset}')
            offset += 1000

            for item in products_data:
                if item['id'] in existing_ids:  # Перевірка на існуючий id_out
                    continue
                product = {
                    'id_out': item['id'],
                    'name': item['name'],
                    'type': item['unit'],
                    'prices': item['prices'],
                    'marked_good': item['isMarked'] is True,
                    'nds': item['tax'],
                    'updatedAt' : item['updatedAt']
                }

                if 'department' in item:
                    product['group_id'] = item['department']['id']
                if 'barcodes' in item:
                    product['barcodes'] = item['barcodes']

                products_list.append(product)
                existing_ids.add(item['id'])  # Додавання id_out до множини існуючих

        return products_list

    def get_suppliers(self):
        return self.session.get("https://kabinet.dreamkas.ru/api/v1/edx/paper/contacts").json()
    def get_documents(self,offset, limit=100, document_type="5,13", ):
        # 0: {label: "Перемещение", value: 2}
        # 1: {label: "Оприходование", value: 3}
        # 2: {label: "Списание", value: 4}
        # 3: {label: "Приходная накладная", value: "5,13"}
        # 4: {label: "Корректировка приходной накладной", value: 7}
        # 5: {label: "Акт реализации", value: 10}
        # 6: {label: "Переоценка", value: 11}
        # 7: {label: "Кассовая смена", value: 12}

        # https://kabinet.dreamkas.ru/api/v1/documents?limit=1000&filter[type]=5&filter[source]=PAPER,KABINET
        # Request URL: https://kabinet.dreamkas.ru/api/v1/documents?limit=30&offset=0&filter[type]=5,13&filter[preset]=DOCUMENTS
        print("Послан запрос на получение документов.")
        if offset == 0:
            link = f"{self.URL_DOCUMENTS_v1_API}?limit={limit}&filter[type]={document_type}&filter[preset]=PAPER,DOCUMENTS"
        else:
            link = f"{self.URL_DOCUMENTS_v1_API}?limit={limit}&offset={offset}&filter[type]={document_type}&filter[preset]=PAPER,DOCUMENTS"
        response = self.session.get(link)
        if response.status_code == 200:
            print("Документы получены")
            return response.json()
        else:
            print("Login failed")
            return "Login Failed"

    def get_document(self, id_document):
        response = self.session.get(f"{self.URL_DOCUMENTS_v1_API}/{id_document}")
        return response.json()


    def get_groups(self):
        response = self.session.get(f"{self.URL_STORE_VIEW}/")
        return response.json()


    def get_product(self, id_product):
        response = self.session.get(f"{self.URL_PRODUCTS_API}/{id_product}")
        return response.json()
    def get_product_v2(self, id_product):
        response = self.session.get(f"https://kabinet.dreamkas.ru/api/v2/products/{id_product}")
        return response.json()


    # def price_invoice(self):
    #     filepath = "Z:/Invoices.json"
    #     return filepath

    def patch_document(self, id_document, positions, comment=""):
        data = {"reason": None,
                "comment": comment,
                "positions": positions}
        response = self.session.patch(f"{self.URL_DOCUMENTS_v1_API}/{id_document}", json=data)
        return response.json()


    # def generate_document_ipbaykov(self, file_content=None, file_path=None):
    #     data = {}
    #     if file_content:
    #         data_dict = xmltodict.parse(file_content)
    #     else:
    #         with open(file_path, "r") as xmlfileObj:
    #             data_dict = xmltodict.parse(xmlfileObj.read())
    #
    #     return data
    # def price_document(self, document):
    def document_status(self):
        documents = self.get_documents(250)

    def search_goods_gmail(self,prefix,product_name,product_code,product_amount,product_sum,priority=0):
        #0 - default
        #1 - Name
        found_product = None
        productcode = None
        try:
            if self.check_code(product_code):

                print("Product is EAC8/13")
                found_product = self.search_goods(str(product_code).strip())
        except:
            print("EAC8/13 check, product not found or error")
            pass
        if found_product is None and product_code is not None:
            try:
                found_product = self.search_goods(prefix + str(product_code))
                if productcode is None:
                    productcode = prefix + str(product_code)
                    print()
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
                found_product = self.search_goods(prefix + tempproductcode)
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


    def search_goods_xml_diadoc(self, prefix, item):
        goods = []
        found_product = None

        found_product = None
        productcode = None
        try:
            if self.check_code(item['ДопСведТов']['@КодТов']):  # Case 1 : Barcode - correct, Found a good, product code is of a good. All good.
                productcode = item['ДопСведТов']['@КодТов']  # Case 2 : Barcode - correct, didn't find a good, product code is of a good. All good.
                found_product = self.search_goods(productcode)  # Case 3 : Barcode - incorrect, nothing happens. All good.
        except:
            pass
        if found_product is None:
            try:
                found_product = self.search_goods((prefix + str(item['ДопСведТов']['@КодТов']).strip()))
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
                if self.check_code(tempproductcode):
                    productcode = tempproductcode  # Barcode found in here, so this replaces any bs from before, including prefix and a code
                    found_product = self.search_goods(tempproductcode)

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
                if self.check_code(goodtofind[0]):
                    productcode = goodtofind[0]
                    print(goodtofind[0], "goodtofind[0] = EAN13/EAN8")
                    found_product = self.search_goods(goodtofind[0])
                if found_product is None:
                    try:
                        if self.check_code(goodtofind[1]):
                            productcode = goodtofind[1]
                            print("goodtofind[0] result = None, Trying goodtofind[1]", found_product)
                            found_product = self.search_goods(goodtofind[1])
                    except:
                        pass
                else:
                    pass
                if found_product is None:
                    try:
                        if self.check_code(goodtofind[2]):
                            productcode = goodtofind[2]
                            print("goodtofind[0] result = None, Trying goodtofind[1]", found_product)
                            found_product = self.search_goods(goodtofind[2])
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
                if self.check_code(tempproductcode):
                    productcode = tempproductcode  # Barcode found in here, so this replaces any bs from before, including prefix and a code
                    found_product = self.search_goods(tempproductcode)
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
                found_product = self.search_goods(prefix + tempproductcode)
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
    def change_product_v2(self, good_id, what_to_change, new_value):
        response = self.session.get(f"https://kabinet.dreamkas.ru/api/v2/products/{good_id}/").json()
        response[what_to_change] = str(new_value)
        resp_patch = self.session.patch(f"https://kabinet.dreamkas.ru/api/v2/products/{good_id}/", json=response)
        return(resp_patch)
