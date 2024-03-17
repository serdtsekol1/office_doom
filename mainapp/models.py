import datetime
import json
import os
import pickle
from decimal import Decimal

from django.db import models

from datetime import datetime as datetime2
from django.utils import timezone

from datetime import timedelta, date

from dremkas.settings import DREAM_KAS_API, DIADOC_API, current_store_id
# from mainapp.gmail_invoices import get_gmail_messages


class Store(models.Model):
    store_name = models.CharField('store_name', blank=True, null=True, max_length=255, default=None)
    store_id = models.IntegerField('store_id', blank=True, null=True)
    diadoc_id = models.TextField('diadoc_id', blank=True, null=True, default=None)
    gmail_client_secret = models.CharField('gmail_client_secret', blank=True, null=True, max_length=255, default=None)

    @property
    def store_devices(self):
        devices = Device.objects.filter(store_id=current_store_id)
        store_devices = []
        for device in devices:
            store_devices.append(device.device_id)
        return store_devices

    @staticmethod
    def update_stores_and_devices():
        for store in DREAM_KAS_API.get_stores():
            Store.objects.update_or_create(store_id=store['id'], store_name=store['name'])
        for device in DREAM_KAS_API.get_devices():
            Device.objects.update_or_create(device_id=device['id'], store_id=device['groupId'])


class Device(models.Model):
    device_id = models.IntegerField('device_id')
    store_id = models.IntegerField('owner_store_id')


class Product(models.Model):
    id_out = models.CharField('id_out', max_length=255, blank=True, default=None, null=True)
    name = models.CharField('name', max_length=255, blank=True, default=None, null=True)
    type = models.IntegerField('type', default=796, null=True, blank=True)
    # unit 796 - штучный
    # unit 166 - Весовой.
    marked_good = models.BooleanField('marked', default=False, null=True)
    nds = models.IntegerField('NDS', default=None, null=True, blank=True)
    # None - без ндс
    # 0 - 0%
    # 10 - 10%
    # 20 - 20%
    # 110 - 10/110%
    # 120 - 20/120%
    group_id = models.CharField('Group_ID', max_length=255, default=None, null=True, blank=True)
    updatedAt = models.CharField('date_of_last_update', max_length=255, default=None, null=True, blank=True)
    short_name = models.TextField('short_name', blank=True, default=None, null=True)

    @property
    def price_for_shop(self):
        current_shop = os.environ.get('CURRENT_SHOP')
        shop = json.loads(os.environ.get('SHOP_IDS'))[int(current_shop) - 1]
        return self.prices_set.filter(device_id__in=shop).first()

    # alias_codes = models.ManyToManyField(Alias_codes)

    ## to find object with ['BARCODE'] : Product.objects.filter(barcodes__0__in=['1231231231231'])

    @staticmethod
    def update_products():
        products_list = DREAM_KAS_API.get_products()
        existing_products = Product.objects.filter(id_out__in=[item['id_out'] for item in products_list])
        existing_product_map = {product.id_out: product for product in existing_products}
        to_create = []
        to_update = []
        products_list_created = []
        products_list_changed = []
        i = 0
        for item in products_list:
            if i % 1000 == 0:
                print('Подготовка листов для создания и обновления товаров. Прогресс - ', i)
            i = i + 1
            product_data = {
                'name': item['name'],
                'type': item['type'],
                'marked_good': item['marked_good'],
                'nds': item['nds'],
                'group_id': item['group_id'] if 'group_id' in item else None,
                'updatedAt': item['updatedAt'] if 'updatedAt' in item else None
            }
            if item['id_out'] in existing_product_map:
                ## Продукт найден - его нужно просто апдейтнуть.
                product = existing_product_map[item['id_out']]
                if product.updatedAt == item['updatedAt']:
                    continue
                for key, value in product_data.items():
                    setattr(product, key, value)
                to_update.append(product)
                products_list_changed.append(item)
            else:
                # Не найден - создать.
                to_create.append(Product(id_out=item['id_out'], **product_data))
                products_list_created.append(item)
        print('Создание новых товаров.')
        Product.objects.bulk_create(to_create)
        print('Обновление существующих товаров.')
        Product.objects.bulk_update(to_update, ['name', 'type', 'marked_good', 'nds', 'group_id'])

        prices_to_create = []
        prices_to_update = []
        barcodes_to_create = []
        barcodes_to_update = []
        existing_prices = Prices.objects.filter(product_fk__id_out__in=[item['id_out'] for item in products_list_changed])
        existing_barcodes = Barcodes.objects.filter(product_fk__id_out__in=[item['id_out'] for item in products_list_changed])
        price_map = {(price.product_fk.id_out, price.device_id): price for price in existing_prices}
        barcode_map = {barcode.product_fk.id_out: barcode for barcode in existing_barcodes}

        i = 0
        barcode_duplicates = []
        barcodes_in_dreamkas = []
        products_in_dreamkas = []
        ##### Удалить обьекты штрихкодов \ артикулов, которые не существуют в дримкасе.
        for item in products_list:
            products_in_dreamkas.append(item['id_out'])
            barcodes_in_dreamkas.extend([f for f in item['barcodes']])
        Barcodes.objects.all().exclude(barcode__in=barcodes_in_dreamkas).delete()
        Product.objects.all().exclude(id_out__in=products_in_dreamkas).delete()

        ##### Удалить обьекты штрихкодов \ артикулов, которые не существуют в дримкасе.
        for item in products_list:
            barcodes_in_dreamkas.extend([f for f in item['barcodes']])
        Barcodes.objects.all().exclude(barcode__in=[products_list]).delete()

        for item in products_list_changed:
            if i % 1000 == 0:
                print('Подготовка листов для цен и штриходов в товарах. Прогресс - ', i)
            i = i + 1
            product = Product.objects.get(id_out=item['id_out'])
            if 'prices' in item:
                for price_data in item['prices']:
                    key = (product.id_out, price_data['deviceId'])
                    if key in price_map:
                        # Update existing price
                        price_obj = price_map[key]
                        price_obj.value = price_data['value']
                        prices_to_update.append(price_obj)
                    else:
                        # Create new price
                        prices_to_create.append(Prices(product_fk=product, device_id=price_data['deviceId'], value=price_data['value']))
                for barcode_data in item['barcodes']:

                    if product.id_out not in barcode_map or not Barcodes.objects.filter(barcode=barcode_data).exists():
                        barcodes_to_create.append(Barcodes(product_fk=product, barcode=barcode_data))  # Штрихкол\артикул не существует. Его нужно создать.
                        # Соответственно он никому не призначен и ничего более.
                    else:
                        # Такой код уже есть. Нужно проверить есть ли дубликаты.
                        if Product.objects.filter(barcodes__barcode=barcode_data).count() > 1:
                            # Добавить вещи с дубликатами кодов\артикулов в список
                            for product_obj in Product.objects.filter(barcodes__barcode=barcode_data):
                                # Для предотвращения дубликатов дубликатов (хе-хе)
                                if product_obj not in barcode_duplicates:
                                    barcode_duplicates.append(product_obj)
                            continue
                        else:
                            barcode_product_obj = Product.objects.filter(barcodes__barcode=barcode_data).first()
                            if barcode_product_obj and barcode_product_obj.id_out == item['id_out']:
                                continue
                            if barcode_product_obj and barcode_product_obj.id_out != item['id_out'] or not barcode_product_obj:
                                temp_obj = Barcodes.objects.filter(barcode=barcode_data).first()
                                temp_obj.product_fk = Product.objects.filter(id_out=item['id_out']).first()
                                temp_obj.save()
        print('Создание цен для товаров.')
        Prices.objects.bulk_create(prices_to_create)
        print('Обновление цен для товаров.')
        Prices.objects.bulk_update(prices_to_update, ['value'])
        print('Создание штрихкодов для товаров.')
        Barcodes.objects.bulk_create(barcodes_to_create)
        if barcode_duplicates.__len__() > 0:
            for dupe in barcode_duplicates:
                print(dupe.name, 'Создержит дубликат по артикулу \ штриходу. Проверьте, исправьте.')
        # for item in products_list:
        #     i = i + 1
        #     if i % 1000 == 0:  # Check if it's a 1000th iteration
        #         print(f"This is the {i}th iteration.")
        #     product = Product.objects.get(id_out=item['id_out'])
        #     if 'prices' in item:
        #         for price in item['prices']:
        #             # Here we assume that a product can have multiple prices for different devices,
        #             # but only one price per device.
        #             price_obj, created = product.prices_set.get_or_create(device_id=price['deviceId'], defaults={'value': price['value']})
        #             if not created:
        #                 price_obj.value = price['value']
        #                 price_obj.save()
        #     if 'barcodes' in item:
        #         for barcode in item['barcodes']:
        #             product.barcodes_set.update_or_create(barcode=barcode)


class Barcodes(models.Model):
    product_fk = models.ForeignKey(Product, max_length=255, blank=True, default=None, null=True, on_delete=models.CASCADE)
    barcode = models.CharField('Barcode, EAN13/8, alias_codes', max_length=255, blank=True, default=None, null=True)
    multiplier = models.IntegerField('multiplier', blank=True, default=1, null=True)
    # Если товар приходит в накладной как 1, но его на деле, к примеру, 5 шт., или 50 кг - ставиться цифра мультипликатора.
    # В результате должно быть следующее:
    # ЕСЛИ штрих код находиться в нашей базе то кол-во = кол-во * мультикликатор. Прим.
    # Пришло Сахар. 3 шт. В Каждом "Сахар" товаре - 50 кг. Мультипликатор - 50. Пришло в итоге - 150 шт.

    # To add an object:
    # product_obj = Product object that I need to add barcode to
    # product_obj.barcodes_set.update_or_create(barcode=[Barcode that I need to add to product])
    # To find an object by barcode
    # Product.objects.filter(barcodes__barcode=1231231231234)


class Prices_shop(models.Model):
    product_fk = models.ForeignKey(Product, max_length=255, blank=True, default=None, null=True, on_delete=models.CASCADE)
    shop_id = models.CharField('shop_id', max_length=255, blank=True, default=None, null=True)
    value = models.IntegerField('price', null=True, blank=True, default=None)


class Prices(models.Model):
    product_fk = models.ForeignKey(Product, max_length=255, blank=True, default=None, null=True, on_delete=models.CASCADE)
    device_id = models.CharField('device_id', max_length=255, blank=True, default=None, null=True)
    value = models.IntegerField('price', null=True, blank=True, default=None)


class Supplier(models.Model):
    inn = models.BigIntegerField('inn', blank=True, default=None, null=True)
    name = models.CharField('name', max_length=255, blank=True, default=None, null=True)
    paymenttime = models.IntegerField('paymenttime', blank=True, default=None, null=True)
    balance = models.DecimalField('balance', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    comment = models.CharField('comment', max_length=2555, blank=True, default=None, null=True)
    invoices_non_program = models.CharField('invoices_non_program', max_length=5000, blank=True, default='', null=True)
    invoice_program = models.CharField('invoices_program', max_length=5000, blank=True, default='', null=True)
    supplier_prefix = models.CharField('comment', max_length=255, blank=True, default=None, null=True)



class Supplier_name(models.Model):
    name = models.CharField('name', blank=True, default=None, null=True, max_length=255)
    supplier_fk = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    priority = models.BooleanField('if this name should be used as first', blank=True, default=False, null=True)



class Supplier_id_dreamkas(models.Model):
    dreamkas_id = models.BigIntegerField('id', blank=True, default=None, null=True)
    supplier_fk = models.ForeignKey(Supplier, on_delete=models.CASCADE)


class Position(models.Model):
    position_id = models.CharField("Position_id", blank=True, null=True, max_length=255, default=None)
    position_amount = models.DecimalField("position_amount", blank=True, null=True, default=None, max_digits=11, decimal_places=2)
    position_sum = models.DecimalField("position_sum", blank=True, null=True, default=None, max_digits=11, decimal_places=2)


class Document(models.Model):
    id_dreem = models.BigIntegerField('id_dreem', blank=True, default=None, null=True)
    document_type = models.Choices


class Invoice(models.Model):
    id_dreem = models.BigIntegerField('id_dreem', blank=True, default=None, null=True)
    latest_edit_id_dreem = models.IntegerField('id_dreem', blank=True, default=None, null=True)
    supplier = models.CharField('Поставщик', max_length=255, blank=True, default=None, null=True)
    supplier_fk = models.ForeignKey(Supplier, max_length=255, blank=True, default=None, null=True, on_delete=models.SET_NULL)
    number = models.CharField('Номер', max_length=255, blank=True, default=None, null=True)
    sum = models.DecimalField('Сумма', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    income = models.DecimalField('Доход', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    issue_date = models.DateField('Дата', blank=True, default=None, null=True)
    paidmoney = models.DecimalField('Сумма оплаты', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    profit = models.DecimalField('Прибыль', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    paid = models.BooleanField('Оплата', default=False, blank=True, null=True, )
    invoicetype = models.BooleanField('Тип накладной - НАЛ \ БЕЗНАЛ', default=False)
    overdue = models.BooleanField('Просрочена ли накладная?', default=False)
    invoice_status = models.BooleanField('DRAFT OR ACCEPTED', null=True, blank=True, default=False)
    hide = models.BooleanField('Спрятать накладную от показа?', null=True, blank=True, default=False)
    hide_comment = models.CharField('Комментарий \ Причина того что накладная не видна', max_length=255, blank=True, default=None, null=True)
    ignore_problem = models.BooleanField('Игнорировать ли возможную проблему с накладной?', null=True, blank=True, default=False)
    printed = models.BooleanField('Was it printed?', null=True, blank=True, default=False)
    created_via_program = models.BooleanField('Created via program?', null=True, blank=True, default=False)
    previous_snapshot = models.TextField('Snapshot', null=True, blank=True, default=None)
    positions = models.ManyToManyField(Position)
    # store_id = models.IntegerField('receiver_id', null=True,blank=True,default=None)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True)

    # linked_documents = models.ManyToManyField("self", blank=True)

    @property
    def date_to_pay(self):
        if self.supplier_fk:
            if self.supplier_fk.paymenttime:
                return (self.issue_date
                        + timedelta(days=self.supplier_fk.paymenttime))
        return None

    @property
    def profit(self):
        if self.sum:
            if self.income:
                return (self.income - self.sum)

    @staticmethod
    def calculate_income(invoice, pricing_document):
        income = 0
        invoice_products_amount = invoice['positions'].__len__()
        calculated_products_counter = 0

        for product_invoice in invoice['positions']:
            for product_pricing in pricing_document['positions']:
                if product_invoice['productId'] == product_pricing['productId']:
                    calculated_products_counter = + 1
                    income = income + float(product_invoice['amount']) / 1000 * float(product_pricing['price']) / 100
        if invoice_products_amount != calculated_products_counter:
            return -5
        else:
            return income

        # http_invoice = DREAM_KAS_API.get_document(invoice_object.id_dreem)
        # products_count = http_invoice['positions'].__len__()
        #
        # if http_invoice['children'] == []:
        #     return calculated_invoice_income
        # for child_document in http_invoice['children']:
        #     if child_document['type'] == 'PRICING_ORDER':
        #         pricing_order_doc = DREAM_KAS_API.get_document(child_document['id'])
        #
        #         if pricing_order_doc['status'] != 'DRAFT' and pricing_order_doc['id'] > id_checker:
        #             priced_products_count = 0
        #             for product_invoice in http_invoice['positions']:
        #                 for product_pricing_order in pricing_order_doc['positions']:
        #                     if product_invoice['productId'] == product_pricing_order['productId']:
        #                         priced_products_count =+1
        #                         invoice_income = invoice_income + float(product_invoice['amount']) / 1000 * float(product_pricing_order['price']) / 100
        #             if priced_products_count == products_count:
        #                 calculated_invoice_income = invoice_income
        #             else:
        #                 print('Товары накладной и расценки не совпадают.')
        #                 print()

        # return calculated_invoice_income

        # try:
        #     debug_code = "get http invoice"
        #     http_invoice = DREAM_KAS_API.get_document(invoice_object.id_dreem)
        #     debug_code = "get invoice children"
        #     if http_invoice['children'] == []:
        #         return 0
        #
        #     for children_document in http_invoice['children']:
        #         invoice_income = 0
        #         if children_document['type'] == 'PRICING_ORDER':
        #             pricing_order_document = DREAM_KAS_API.get_document(children_document['id'])
        #             if pricing_order_document['status'] == 'DRAFT':
        #                 continue
        #         else:
        #             continue
        #         debug_code = "count profit"
        #         goods_that_need_to_be_priced_amount = http_invoice['positions'].__len__()
        #         total_priced_goods = 0
        #         for good in http_invoice['positions']:
        #             for priced_good in pricing_order_document['positions']:
        #                 if good['productId'] == priced_good['productId']:
        #                     total_priced_goods = total_priced_goods + 1
        #                     invoice_income = invoice_income + float(good['amount']) / 1000 * float(priced_good['price']) / 100
        #
        #         if total_priced_goods != goods_that_need_to_be_priced_amount:
        #             invoice_income = -505
        #
        #         if calculated_invoice_income != 0 and invoice_income > 0:  # IF calc WAS done and this iteration is success - Check
        #             if children_document['id'] > id_checker:  # if this is latest pricing document.
        #                 calculated_invoice_income = invoice_income  # if yes - set calc to this iteration profit
        #                 id_checker = children_document['id']
        #
        #                 #if goods_that_need_to_be_priced_amount :
        #                 #    print('Некорректное кол-во товаров в расценке и в накладной. ID Накладной - ', invoice_object.id_dreem)
        #         if calculated_invoice_income == 0 and invoice_income > 0:  # IF calc wasn't done and this iteration calc is success
        #             calculated_invoice_income = invoice_income
        #             id_checker = children_document['id']
        #         if calculated_invoice_income < 0:
        #             calculated_invoice_income = invoice_income
        #             print("ERROR INVOICE. INVOICE PRICING STATUS", invoice_income)
        #             print('Invoice info:')
        #             print('Invoice number: ', invoice_object.number)
        #             print('Invoice id_dreem:', invoice_object.id_dreem)
        #             print('Invoice supplier:', invoice_object.supplier)
        #             print('Invoice sum:', invoice_object.sum)
        #             print("Please Look into that invoice and create a proper pricing invoice.")
        #     return calculated_invoice_income
        #
        # except Exception as Ex:
        #     print("ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR")
        #     print("error after this action:")
        #     print(debug_code)
        #     print("Exception:")
        #     print(Ex)
        #     print("ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR")
        #     return -505

    @staticmethod
    def find_latest_iteration(list_of_dicts):
        linked_documents = []
        for dict_doc in list_of_dicts:
            linked_documents = []
            for dict_doc_2 in list_of_dicts:
                if dict_doc_2['origin'] == dict_doc['id']:
                    linked_documents.append(dict_doc_2)
            dict_doc.update({'linked_documents': linked_documents})

    @staticmethod
    def find_difference__in_positions_between_documents(inv_obj_1, inv_obj_2):
        inv_obj_1_positions = None
        inv_obj_2_positions = None
        try:
            inv_obj_1_positions = inv_obj_1['positions']
        except:
            pass
        try:
            inv_obj_2_positions = inv_obj_2['positions']
        except:
            pass
        if inv_obj_1_positions == None or inv_obj_2_positions == None:
            return -1

    @staticmethod
    def group_products_in_document(inv_obj, mode=0):
        # If invoice has
        # product 1, x 25 for 50
        # product 2, x 5 for 50
        # product 2, x 100 for 5
        # return
        # product 1, x 125 for 50
        # product 2, x 5 for 50
        # msg (Product 1 prices mismatch!! 25 for 50 and 100 for 5!!, investigate!!)
        # If invoice has
        # product 1, x 25 for 50
        # product 2, x 5 for 50
        # product 2, x 100 for 50
        # return
        # product 1, x 125 for 50
        # product 2, x 5 for 50
        inv_obj_positions = None
        try:
            inv_obj_positions = inv_obj['positions']
        except:
            pass
        if inv_obj_positions == None:
            return -1
        result_positions = []
        for pos in inv_obj_positions:
            if not any(d['productId'] == pos['productId'] for d in result_positions):
                result_positions.append(pos)
            else:
                for pos_2 in result_positions:
                    if pos_2['productId'] == pos['productId']:
                        pos_2['amount'] = str(int(pos_2['amount']) + int(pos['amount']))
                        if mode == 0:
                            if pos_2['costWithTax'] < pos['costWithTax']:
                                pos_2['costWithTax'] = pos['costWithTax']
                        if mode == 1:
                            if pos_2['costWithTax'] != pos['costWithTax']:
                                pos_2['costWithTax'] = str(
                                    (float(pos_2['amount']) * float(pos_2['costWithTax']) + float(pos['amount']) * float(pos['costWithTax'])) / (float(pos['amount']) + float(pos['amount'])))
                                ## Calculate average price of 2 goods, depending from their amount
        return result_positions
        # for pos in inv_obj_positions:
        #    if pos not in result_positions:

    def map_document(invoice, document):
        list_of_linked_corrections = []
        list_of_linked_corrections_to_process = []
        if document['children'].__len__() > 0:
            for linked_document in document['children']:
                if linked_document['type'] != 'INCOME_INVOICE_CORRECTION':
                    continue
                list_of_linked_corrections_to_process.append({'id': linked_document['id']})
        if list_of_linked_corrections_to_process.__len__() > 0:
            list_of_linked_corrections.append({'origin': "origin", 'id': document['id'], 'positions': document['positions']})

        while list_of_linked_corrections_to_process.__len__() > 0:
            work_list = list_of_linked_corrections_to_process.copy()
            list_of_linked_corrections_to_process = []
            for linked_correction in work_list:
                linked_document_http = DREAM_KAS_API.get_document(linked_correction['id'])
                if linked_document_http['status'] != 'ACCEPTED':
                    continue
                list_of_linked_corrections.append({'origin': linked_document_http['parentId'], 'id': linked_document_http['id'], 'positions': linked_document_http['positions']})
                if linked_document_http['children'].__len__() == 0:
                    continue
                for linked_document in linked_document_http['children']:
                    if linked_document['type'] != 'INCOME_INVOICE_CORRECTION':
                        continue
                    list_of_linked_corrections_to_process.append({'id': linked_document_http['id']})

        return list_of_linked_corrections

        # if document['children'].__len__() > 1:
        #     for linked_document in document['children']:
        #         linked_document_http = DREAM_KAS_API.get_document(linked_document['id'])
        #         if linked_document_http['status'] == 'ACCEPTED':
        #             invoice.linkeddocuments_set.update_or_create(document_id=linked_document['id'], document_type=linked_document['type'], document_status=True)
        #             if linked_document_http['type'] == 'INCOME_INVOICE_CORRECTION':
        #                 list_of_linked_corrections.append({'origin': linked_document_http['parentId'], 'id': linked_document_http['id'], 'positions': linked_document_http['positions']})
        #                 list_of_linked_corrections_to_process.append({'origin': linked_document_http['parentId'], 'id': linked_document_http['id']})
        # print(list_of_linked_corrections)
        # while list_of_linked_corrections_to_process.__len__() != 0:
        #     print(list_of_linked_corrections)
        #     list_of_linked_corrections.append({'id': document['id'], 'positions': document['positions']})
        #     work_list = list_of_linked_corrections_to_process.copy()
        #     list_of_linked_corrections_to_process = []
        #     for id_dreem_2 in work_list:
        #         try:
        #             linked_document_http_2 = DREAM_KAS_API.get_document(id_dreem_2['id'])
        #         except:
        #             print('a')
        #         if linked_document_http['status'] == 'ACCEPTED':
        #             invoice.linkeddocuments_set.update_or_create(document_id=linked_document['id'], document_type=linked_document['type'], document_status=True)
        #             for linked_document_2 in linked_document_http_2['children']:
        #                 if linked_document_2['type'] == 'INCOME_INVOICE_CORRECTION':
        #                     list_of_linked_corrections.append(({'origin': linked_document_http['parentId'], 'id': linked_document_http['id'], 'positions': linked_document_http['positions']}))
        #                     list_of_linked_corrections_to_process.append({'origin': linked_document_http['parentId'], 'id': linked_document_http['id']})
        # return list_of_linked_corrections

    @staticmethod
    def update_invoices():

        documents = DREAM_KAS_API.get_documents(limit=500)
        counter = 0
        total_count = documents.__len__()
        for document in documents:
            counter += 1
            if counter % 50 == 0:
                print('Обновление накладных. Прогресс - ', counter, '/', total_count)
            document_source = None
            try:
                document_source = document['sourceName']
            except:
                print('Cannot find sourcename of document', document)
                continue
            if document_source != None:
                print(document['sourceName'])
                supplier, supplier_create = Supplier.objects.update_or_create(name=document['sourceName'], defaults={})
            # Update Overdue status

            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime2.strptime(document['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    overdue = True
                else:
                    overdue = False
            document = DREAM_KAS_API.get_document(document['id'])
            ############# If Document Exists - update what needs to be updated.
            ############# Else - create one with default flags.
            invoice = Invoice.objects.filter(id_dreem=document['id']).first()
            if invoice is None:
                invoice, invoice_create = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
                    # 'number': document['num'],
                    # 'supplier': document['sourceName'],
                    # 'supplier_fk': supplier,
                    # 'sum': Decimal(int(document['totalSum']) / 100),
                    # 'issue_date': document['issueDate'],
                    # 'invoicetype': True if "НАЛ" in document['num'] else False,
                    # 'overdue': overdue,
                    'printed': False,
                    'invoice_status': True if "ACCEPTED" in document["status"] else False,
                    'hide': False,
                })
                if "ACCEPTED" not in document["status"]:
                    print('asd')
                    invoice, invoice_create = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
                        'supplier': document_source,
                        'supplier_fk': supplier,
                        'sum': Decimal(int(document['totalSum']) / 100),
                        'issue_date': document['issueDate'],
                        'invoicetype': True if "НАЛ" in document['num'] else False,
                        'overdue': overdue if supplier.paymenttime is not None else False,
                    })
                    continue
            if "INCOME_INVOICE_CORRECTION" in str(document):
                Invoice.map_document(invoice, document)
            latest_edit_id_dreem = None
            current_document = document
            if invoice.previous_snapshot:
                previous_snapshot = invoice.previous_snapshot
            list_of_linked_corrections_to_process = []
            list_of_linked_corrections = []

            # if current_document['children'].__len__() > 1:
            #     list_of_linked_corrections = Invoice.map_all_corrections(invoice = invoice, document = current_document )
            #     for linked_document in current_document['children']:
            #         linked_document_http = DREAM_KAS_API.get_document(linked_document['id'])
            #         if linked_document_http['status'] == 'ACCEPTED':
            #             invoice.linkeddocuments_set.update_or_create(document_id=linked_document['id'], document_type=linked_document['type'], document_status=True)
            #             if linked_document_http['type'] == 'INCOME_INVOICE_CORRECTION':
            #                 list_of_linked_corrections.append({'origin' : linked_document_http['parentId'], 'id' : linked_document_http['id'],  'positions' : linked_document_http['positions']})
            #                 list_of_linked_corrections_to_process.append({'origin' : linked_document_http['parentId'], 'id' : linked_document_http['id']})

            # linked_documents = []
            # for dict_doc in all_docs:
            #     linked_documents = []
            #     for dict_doc_2 in all_docs:
            #         if dict_doc_2['origin'] == dict_doc['id']:
            #             linked_documents.append(dict_doc_2)
            #     dict_doc.update({'linked_documents': linked_documents})
            # for dict_doc in all_docs:
            #     if f"'id': {last_id}" in str(dict_doc):
            #         print(dict_doc)

            # while list_of_linked_corrections_to_process.__len__() != 0:
            #     list_of_linked_corrections.append({'id': current_document['id'], 'positions': current_document['positions']})
            #     work_list = list_of_linked_corrections_to_process.copy()
            #     list_of_linked_corrections_to_process = []
            #     for id_dreem_2 in work_list:
            #         try:
            #             linked_document_http_2 = DREAM_KAS_API.get_document(id_dreem_2['id'])
            #         except:
            #             print('a')
            #         if linked_document_http['status'] == 'ACCEPTED':
            #             invoice.linkeddocuments_set.update_or_create(document_id=linked_document['id'], document_type=linked_document['type'], document_status=True)
            #             for linked_document_2 in linked_document_http_2['children']:
            #                 if linked_document_2['type'] == 'INCOME_INVOICE_CORRECTION':
            #                     list_of_linked_corrections.append(({'origin' : linked_document_http['parentId'], 'id' : linked_document_http['id'],  'positions' : linked_document_http['positions']}))
            #                     list_of_linked_corrections_to_process.append({'origin': linked_document_http['parentId'], 'id': linked_document_http['id']})

            # if list_of_linked_corrections.__len__() != 0:
            #     print('a')

        if document['children'].__len__() > 1:
            for linked_document in document['children']:
                linked_document_http = DREAM_KAS_API.get_document(linked_document['id'])
                if linked_document_http['status'] == 'ACCEPTED':
                    invoice.linkeddocuments_set.update_or_create(document_id=linked_document['id'], document_type=linked_document['type'], document_status=True)
                    if linked_document_http['type'] == 'INCOME_INVOICE_CORRECTION':
                        invoicecorrections = +1
        print(document)
        invoice, invoice_create = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
            'number': document['num'],
            'supplier': document['sourceLegalEntity']['name'],
            'supplier_fk': supplier,
            'sum': Decimal(int(document['totalSum']) / 100),
            'issue_date': document['issueDate'],
            'invoicetype': True if "НАЛ" in document['num'] else False,
            'overdue': overdue,
            'invoice_status': True if "ACCEPTED" in document["status"] else False
        })
        if invoice['children'].__len__() > 1:
            for linked_document in invoice['children']:
                linked_document_http = DREAM_KAS_API.get_document(linked_document['id'])
                if linked_document_http['status'] == 'ACCEPTED':
                    invoice.linkeddocuments_set.update_or_create(document_id=linked_document['id'], document_type=linked_document['type'], document_status=True)
        for linked_document in invoice.linkeddocuments_set.all():
            print('a')
            ###TODO!!

        ############# For each invoice that is not draft - check it for children and check if snapshot exists.
        # If snapshot doesn't exist - create one, calculate income and write it, create snapshot.
        # If snapshot exists - check if snapshot matches response of children of invoice.
        # If it doesn't - calculate income and write it, rewrite snapshot
        # If it does - do nothing, cause nothing changed.
        ## TODO

        # if invoice.invoice_status == True:
        #     if invoice.previous_snapshot:
        #         if invoice.previous_snapshot != str(document['children']):
        #             calculated_income = Invoice.calculate_income(invoice)
        #             invoice.previous_snapshot = str(document['children'])
        #             if calculated_income > 0:
        #                 invoice.income = calculated_income
        #             else:
        #                 invoice.income = 0
        #             invoice.save()
        #     else:
        #         calculated_income = Invoice.calculate_income(invoice)
        #         invoice.previous_snapshot = str(document['children'])
        #         if calculated_income > 0:
        #             invoice.income = calculated_income
        #         else:
        #             invoice.income = 0
        #         invoice.save()

        counter = Invoice.objects.all().count()
        # Check All documents that are DRAFT for their resp. code.
        # IF Code is 404 - document is deleted, therefore - delete it from database.
        documents_to_delete = []
        for i, invoice in enumerate(Invoice.objects.all()):
            if invoice.invoice_status is not True:
                print(i, counter)
                document = DREAM_KAS_API.get_document(invoice.id_dreem)
                if document["status"] == 404:
                    documents_to_delete.append(invoice.id_dreem)
                    continue
                print(document)
                invoice2, invoice_create2 = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
                    'invoice_status': True if "ACCEPTED" in document["status"] else False})
        for item in documents_to_delete:
            Invoice.objects.filter(id_dreem=item).delete()

    def update_invoice(id_dreem):
        document = DREAM_KAS_API.get_document(id_dreem)
        invoice, invoice_create = Invoice.objects.update(id_dreem=document['id'], defaults={
            'invoice_status': True if "ACCEPTED" in document["status"] else False})


class LinkedDocuments(models.Model):
    invoice_fk = models.ForeignKey(Invoice, on_delete=models.CASCADE)  # Документи, які є в самому інвойсі.
    document_id = models.IntegerField("Linked Document ID", null=True, blank=True, default=None)
    document_type = models.CharField('Document type', default=None, null=True, blank=True, max_length=255)
    document_status = models.BooleanField('Document_status', null=True, blank=True, default=False)


class PresetGmail(models.Model):
    preset_name = models.TextField('preset_name', blank=True, default=None, null=True)
    supplier_fk = models.ForeignKey(Supplier, on_delete=models.DO_NOTHING, blank=True, default=None,null=True)
    supplier_mail = models.TextField('supplier_mail', blank=True, default=None, null=True)
    supplier_inn = models.BigIntegerField('supplier_inn', blank=True, default=None, null=True)
    supplier_name = models.TextField('supplier_name', blank=True, default=None, null=True)
    supplier_prefix = models.TextField('supplier_prefix', blank=True, default=None, null=True)
    supplier_time_format = models.TextField('supplier_time_format', blank=True, default=None, null=True)
    # Coordinates of stuff here
    # Date
    document_date_col = models.IntegerField('document_date_col', blank=True, default=None, null=True)
    document_date_row = models.IntegerField('document_date_row', blank=True, default=None, null=True)
    document_date_format = models.TextField('document_date_format', blank=True, default=None, null=True)
    document_non_regular_date = models.BooleanField('document_non_regular_date', blank=True, default=False, null=True)
    document_date_between_first = models.TextField('document_date_between_first', blank=True, default=False, null=True)
    document_date_between_second = models.TextField('document_date_between_second', blank=True, default=False, null=True)
    # Number
    document_number_col = models.IntegerField('document_number_col', blank=True, default=None, null=True)
    document_number_row = models.IntegerField('document_number_row', blank=True, default=None, null=True)
    document_non_regular_number = models.BooleanField('document_non_regular_number', blank=True, default=False, null=True)
    document_number_between_first = models.TextField('document_number_between_first', blank=True, default=False, null=True)
    document_number_between_second = models.TextField('document_number_between_second', blank=True, default=False, null=True)
    # Check for valid document
    supplier_unique_information = models.TextField('supplier_unique_information', blank=True, default=None, null=True)
    supplier_unique_information_col = models.IntegerField('supplier_unique_information_col', blank=True, default=None, null=True)
    supplier_unique_information_row = models.IntegerField('supplier_unique_infromation_row', blank=True, default=None, null=True)
    # Products
    product_start_row = models.IntegerField('product_start_row', blank=True, default=None, null=True)
    product_name_col = models.IntegerField('product_name_row', blank=True, default=None, null=True)
    product_code_col = models.IntegerField('product_code_row', blank=True, default=None, null=True)
    product_amount_col = models.IntegerField('product_amount_row', blank=True, default=None, null=True)
    product_amount_type_col = models.IntegerField('product_amount_type_row', blank=True, default=None, null=True)
    product_nds_col = models.IntegerField('product_nds_rwo', blank=True, default=None, null=True)
    product_sum_col = models.IntegerField('product_sum_row', blank=True, default=None, null=True)
    product_priority = models.IntegerField('product_priority',blank=True,default=None,null=True)
    # 0 - Code
    # 1 - Name, slugified.
    # Destination store
    document_store_destination = models.IntegerField('product_store_id', blank=True, default=None, null=True)
    document_store_information = models.TextField('product_store_information', blank=True, default=None, null=True)
    document_store_information_row = models.IntegerField('product_store_information_row', blank=True, default=None, null=True)
    document_store_information_col = models.IntegerField('product_store_information_col', blank=True, default=None, null=True)


class DailyInvoiceReport(models.Model):
    date = models.DateField('Date Of Report', blank=True, default=None, null=True)
    invoice_list = models.ManyToManyField(Invoice)
    spendings = models.DecimalField('Spendings', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    estimated_profit = models.DecimalField('Estimated Profit', null=True, blank=True, decimal_places=2, max_digits=11, default=None)

    @staticmethod
    def generate_invoice_report(date=None):
        if date == None:
            date = datetime.datetime.today().date()
        # if DailyInvoiceReport.objects.filter(date=date).__len__() == 0:
        #     pass
        # else:
        #     return
        Invoice.update_invoices()
        non_printed_invoices = Invoice.objects.filter(printed=False, hide=False)
        print(non_printed_invoices.__len__())
        ##TODO: Change Printed to id of report.

        for invoice in non_printed_invoices:
            if invoice.invoice_status == False:
                continue
            invoice.income = Invoice.calculate_income(invoice)
            invoice.save()
        total_estimated_profit = 0
        total_spendings = 0
        for invoice in non_printed_invoices:
            if invoice.income:
                if invoice.income > 0:
                    total_profit = total_estimated_profit + invoice.income
                total_spendings = total_spendings + invoice.sum
            invoice.printed = True

        new_daily_report = DailyInvoiceReport.objects.update_or_create(date=datetime.date.today(), defaults={
            'date': date,
            'spendings': total_spendings,
            'estimated_profit': total_estimated_profit
        })
        new_daily_report[0].save()
        new_daily_report[0].invoice_list.set(non_printed_invoices)


class DiadocInvoice(models.Model):
    diadoc_id = models.CharField('diadoc_id', max_length=255, blank=True, default=None, null=True)
    kontragent = models.CharField('Поставщик', max_length=255, blank=True, default=None, null=True)
    number = models.CharField('Номер', max_length=255, blank=True, default=None, null=True)
    sum = models.CharField('Сумма', max_length=255, blank=True, default=None, null=True)
    # sum = models.DecimalField('Сумма', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    issue_date = models.DateField('Дата', blank=True, default=None, null=True)
    invoice_status = models.CharField('Статус', max_length=255, blank=True, default=None, null=True)
    downloadlink = models.CharField('Статус', max_length=1000, blank=True, default=None, null=True)
    invoices = models.ManyToManyField(Invoice)
    store_id = models.CharField('store_id', max_length=255, blank=True, default=None, null=True)

    @staticmethod
    def update_diadoc_invoices():
        invoices = DIADOC_API.get_documents()
        print('test_123')
        for item in invoices:
            diadoc_invoice, diadoc_invoice_status = DiadocInvoice.objects.update_or_create(diadoc_id=item['id'], defaults={
                'kontragent': item['kontragent'],
                'sum': item['sum'],
                'number': item['num'],
                'issue_date': datetime2.strptime(item['date'], "%d.%m.%Y").strftime("%Y-%m-%d"),
                # ({"date": datetime.datetime.strptime(data_dict["Файл"]["Документ"]["СвСчФакт"]["@ДатаСчФ"], "%d.%m.%Y").strftime("%Y-%m-%d")})
                'invoice_status': item['status'],
                'downloadlink': item['link_document_attachment'],
            })
            print(diadoc_invoice_status)
            print(diadoc_invoice.kontragent)
            print(diadoc_invoice.number)
            print(diadoc_invoice.issue_date)

        return


class DiadocPreset(models.Model):
    preset_name = models.CharField('preset_name', max_length=255, blank=True, default=None, null=True)
    supplier_fk = models.ForeignKey(Supplier, on_delete=models.DO_NOTHING, blank=True, default=None, null=True)
    supplier_name = models.TextField('supplier_name', blank=True, default=None, null=True)
    supplier_inn = models.BigIntegerField('group_id', blank=True, default=None, null=True)
    supplier_prefix = models.TextField('supplier_prefix', blank=True, default=None, null=True)
    store_destination_fk = models.ForeignKey(Store, on_delete=models.DO_NOTHING, blank=True, default=None, null=True)
    store_destination_information = models.CharField('supplier_name', max_length=2555, blank=True, default=None, null=True)


class GoodGroups(models.Model):
    group_id = models.IntegerField('group_id', blank=True, default=None, null=True)
    name = models.CharField('Name', max_length=255, blank=True, default=None, null=True)
    pricingpercent = models.IntegerField('pricingpercent', null=True, blank=True, default=0)
    roundnumber = models.IntegerField('roundnumber', blank=True, default=0, null=True)
    rule = models.IntegerField('rule', null=True, blank=True, default=0)

    @staticmethod
    def update_good_groups():
        categories = DREAM_KAS_API.get_groups()['categories']
        for item in categories:
            GoodGroups.objects.update_or_create(group_id=item['id'], defaults={'name': item['name']})


class GmailMessageAttachment(models.Model):
    name = models.TextField("message id", blank=True, default=None, null=True)


class Gmail_Messages(models.Model):
    message_sender = models.CharField("Отправитель", max_length=255, blank=True, default=None, null=True)
    message_sender_display = models.CharField('Отправитель , но для отображения', max_length=255, blank=True, default=None, null=True)
    message_date = models.DateField('Дата', blank=True, default=None, null=True)
    message_date_str = models.CharField("Дата, в случаях если нету шаблона", max_length=255, blank=True, default=None, null=True)
    message_id = models.CharField("message id", max_length=255, blank=True, default=None, null=True)
    message_name = models.CharField("Название сообщения", max_length=255, blank=True, default=None, null=True)
    message_store_id = models.CharField('store_id', max_length=255, blank=True, default=None, null=True)
    invoices = models.ManyToManyField(Invoice)
    attachments = models.ManyToManyField(GmailMessageAttachment)

    # @staticmethod
    # def update_gmail_messages(client_secret_json):
    #     companies_list = []
    #     for file in os.listdir("media/gmail_suppliers"):
    #         try:
    #             company = json.loads(open(r"media/gmail_suppliers/" + file).read())
    #             companies_list.append([company["company_mail"], company["company_time_format"]])
    #         except:
    #             print(r"media/gmail_suppliers/" + file)
    #             print("error opening file as json")
    #             pass
    #
    #     messages = get_gmail_messages(client_secret_json)
    #     for message in messages:
    #         message_id = None
    #         message_date = None
    #         message_subject = None
    #         message_sender = None
    #
    #         if message.sender[message.sender.find("<"):].replace("<", "").replace(">", "") != "no-reply@accounts.google.com":
    #             try:
    #                 message_id = message.headers["Message-Id"].replace("<", "").replace(">", "")
    #             except:
    #                 pass
    #             try:
    #                 message_id = message.headers["Message-ID"].replace("<", "").replace(">", "")
    #             except:
    #                 pass
    #             if message_id == None:
    #                 print("sender:" + message.sender[message.sender.find("<"):].replace("<", "").replace(">", ""))
    #                 print("name:" + message.subject)
    #                 print("Error. Couldn't find message_id")
    #                 continue
    #             try:
    #                 for ruleset in companies_list:
    #                     if message.sender[message.sender.find("<"):].replace("<", "").replace(">", "") == ruleset[0]:
    #                         message_date = datetime.datetime.strptime(message.date, ruleset[1])
    #                         message_sender = message.sender[message.sender.find("<"):].replace("<", "").replace(">", "")
    #                     if message.sender == ruleset[0]:
    #                         message_date = datetime.datetime.strptime(message.date, ruleset[1])
    #                         message_sender = message.sender
    #             except:
    #                 message_sender = message.sender
    #                 pass
    #             if message_date == None:
    #                 print("sender:", message_sender)
    #                 print("name:" + message.subject)
    #                 print("Не найдена дата либо ошибка даты или ее формата либо данный отправитель не числится в списке отправителей")
    #                 continue
    #             attachments_gmail = [f.filename for f in message.attachments]
    #             gmail_message = Gmail_Messages.objects.filter(
    #                 message_sender=message_sender,
    #                 message_date=message_date.date(),
    #                 message_name=message.subject,
    #                 attachments__name__in=attachments_gmail
    #             ).distinct().first()
    #
    #             if gmail_message:
    #                 gmail_message.message_sender = message_sender
    #                 gmail_message.message_date = message_date
    #                 gmail_message.message_name = message.subject
    #                 gmail_message.save()
    #             else:
    #                 gmail_message = Gmail_Messages(
    #                     message_id=message_id,
    #                     message_sender=message_sender,
    #                     message_date=message_date,
    #                     message_name=message.subject
    #                 )
    #                 gmail_message.save()
    #
    #             gmail_message_attachments = []
    #             for attachment in message.attachments:
    #                 gmail_message_attachment, gmail_message_attachment_bool = GmailMessageAttachment.objects.update_or_create(name=attachment.filename)
    #                 gmail_message_attachments.append(gmail_message_attachment)
    #             gmail_message.attachments.set(gmail_message_attachments)
    #             # gmail_message, gmail_message_bool = Gmail_Messages.objects.update_or_create(message_id=message_id, defaults={
    #             #     'message_sender': message.sender[message.sender.find("<"):].replace("<", "").replace(">", ""),
    #             #     'message_date': message_date,
    #             #     'message_name': message.subject,
    #             # })
    #             # gmail_message.gmailmessageattachment_set.update_or_create(
    #             #     name=message.attachments,
    #             # )
    #     return
