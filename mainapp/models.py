import datetime
import json
import os
from decimal import Decimal

from django.db import models

from datetime import datetime as datetime2
from django.utils import timezone

from datetime import timedelta, date

from dremkas.settings import DREAM_KAS_API, DIADOC_API
from mainapp.gmail_invoices import get_gmail_messages


class Product(models.Model):
    id_out = models.CharField('id_out', max_length=255, blank=True, default=None)
    name = models.CharField('name', max_length=255, blank=True, default=None)
    type = models.CharField('type', max_length=255, blank=True, default=None)
    price = models.DecimalField('price', null=True, blank=True, decimal_places=2, max_digits=9, default=None)
    marked_good = models.BooleanField('marked', default=False)
    nds = models.IntegerField('NDS', default=None, null=True, blank=True)

    # None - без ндс
    # 0 - 0%
    # 10 - 10%
    # 20 - 20%
    # 30 - 30%

    # barcodes =
    # product_codes =
    # def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
    #     print(force_insert, force_update, update_fields)
    #     # session = HTMLSession()
    #     # array_result = []
    #     # offset = 0
    #     # result = session.get(f'https://kabinet.dreamkas.ru/api/products/{self.id}', auth=HTTPBasicAuth(login, password)).json()
    #     super(Product, self).save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def codes(self):
        code = ""
        for c in self.barcodes_set.all():
            code += f"{c.code}, "
        return code[:-2]


class Prices(models.Model):
    deviceid = models.CharField('deviceid', max_length=255, blank=True, default=None, null=True)
    value = models.DecimalField('value', null=True, blank=True, decimal_places=2, max_digits=9, default=None)
    product_fk = models.ForeignKey(Product, verbose_name="Product", on_delete=models.CASCADE)


class Product_codes(models.Model):
    product_code = models.CharField('Артикул', max_length=255, blank=True, default=None, null=True)
    product_fk = models.ForeignKey(Product, verbose_name="Product", on_delete=models.CASCADE)


class Barcodes(models.Model):
    code = models.CharField('type', max_length=255, blank=True, default=None, null=True)
    product_fk = models.ForeignKey(Product, verbose_name="Product", on_delete=models.CASCADE)


class Supplier(models.Model):
    inn = models.IntegerField('inn', blank=True, default=None, null=True)
    name = models.CharField('name', max_length=255, blank=True, default=None, null=True)
    paymenttime = models.IntegerField('paymenttime', blank=True, default=None, null=True)
    balance = models.DecimalField('balance', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    comment = models.CharField('comment', max_length=2555, blank=True, default=None, null=True)
    invoices_non_program = models.CharField('invoices_non_program', max_length=5000, blank=True, default='', null=True)
    invoice_program = models.CharField('invoices_program', max_length=5000, blank=True, default='', null=True)


class Position(models.Model):
    position_id = models.CharField("Position_id", blank=True, null=True, max_length=255, default=None)
    position_amount = models.DecimalField("position_amount", blank=True, null=True, default=None, max_digits=11, decimal_places=2)
    position_sum = models.DecimalField("position_sum", blank=True, null=True, default=None, max_digits=11, decimal_places=2)


class Invoice(models.Model):
    id_dreem = models.IntegerField('id_dreem', blank=True, default=None, null=True)
    supplier = models.CharField('Поставщик', max_length=255, blank=True, default=None, null=True)
    supplier_fk = models.ForeignKey(Supplier, max_length=255, blank=True, default=None, null=True, on_delete=models.SET_NULL)
    number = models.CharField('Номер', max_length=255, blank=True, default=None, null=True)
    sum = models.DecimalField('Сумма', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    issue_date = models.DateField('Дата', blank=True, default=None, null=True)
    paidmoney = models.DecimalField('Сумма оплаты', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    profit = models.DecimalField('Прибыль', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    paid = models.BooleanField('Оплата', default=False)
    invoicetype = models.BooleanField('Тип накладной', default=False)
    overdue = models.BooleanField('Просрочена ли накладная?', default=False)
    invoice_status = models.BooleanField('DRAFT OR ACCEPTED', null=True, blank=True, default=False)
    hide = models.BooleanField('Спрятать накладную от показа?', null=True, blank=True, default=False)
    hide_comment = models.CharField('Комментарий \ Причина того что накладная не видна', max_length=255, blank=True, default=None, null=True)
    ignore_problem = models.BooleanField('Игнорировать ли возможную проблему с накладной?', null=True, blank=True, default=False)
    printed = models.BooleanField('Was it printed?', null=True, blank=True, default=False)
    created_via_program = models.BooleanField('Created via program?', null=True, blank=True, default=False)
    positions = models.ManyToManyField(Position)

    # linked_documents = models.ManyToManyField("self", blank=True)

    @property
    def date_to_pay(self):
        if self.supplier_fk:
            if self.supplier_fk.paymenttime:
                return (self.issue_date
                        + timedelta(days=self.supplier_fk.paymenttime))
        return None

    @staticmethod
    def update_invoices():
        documents = DREAM_KAS_API.get_documents(limit=1000)
        count = 0
        for document in documents:
            count += 1
            # print(count, document)
            if len(document['children']) > 1:
                pricing_invoice = DREAM_KAS_API.get_document(document['children'])
                # print(pricing_invoice)

            document_source = None
            try:
                document_source = document['sourceName']
            except:
                print(document)
                continue
            if document_source != None:

                supplier, supplier_create = Supplier.objects.update_or_create(name=document['sourceName'], defaults={

                 })
            # True if date.today() > document['issueDate'] + timedelta(days=supplier.paymenttime) else False,
            overdue = False

            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime2.strptime(document['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    overdue = True
            if Invoice.objects.filter(id_dreem = document['id']) == [] : # If it doesnt exist - create one, with the flags set as default(like - printed)
                                                                            # else - just update it without setting flags such as printed True
                invoice, invoice_create = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
                    'number': document['num'],
                    'supplier': document['sourceName'],
                    'supplier_fk': supplier,
                    'sum': Decimal(int(document['totalSum']) / 100),
                    'issue_date': document['issueDate'],
                    'invoicetype': True if "НАЛ" in document['num'] else False,
                    'overdue': overdue,
                    'printed': False,
                    'invoice_status': True if "ACCEPTED" in document["status"] else False
                })
            else:
                if Invoice.objects.filter(id_dreem = document['id']).__len__() == 1:
                    invoice, invoice_create = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
                        'number': document['num'],
                        'supplier': document['sourceName'],
                        'supplier_fk': supplier,
                        'sum': Decimal(int(document['totalSum']) / 100),
                        'issue_date': document['issueDate'],
                        'invoicetype': True if "НАЛ" in document['num'] else False,
                        'overdue': overdue,
                        'invoice_status': True if "ACCEPTED" in document["status"] else False
                    })

            count = Invoice.objects.all().count()
            # Invoice.objects.filter(id_dreem__in=[1234,12345]).update()
            documents_to_delete = []
        for i, invoice in enumerate(Invoice.objects.all()):
            if invoice.invoice_status is not True:
                print(i, count)
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


class DailyInvoiceReport(models.Model):
    date = models.DateField('Date Of Report', blank=True, default=None, null=True)
    invoice_list = models.ManyToManyField(Invoice)
    spendings = models.DecimalField('Spendings', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    estimated_profit = models.DecimalField('Estimated Profit', null=True, blank=True, decimal_places=2, max_digits=11, default=None)

    @staticmethod
    def generate_invoice_report(date=None):
        if date == None:
            date = datetime.datetime.today().date()
        if DailyInvoiceReport.objects.filter(date=date) == []:
            pass
        else:
            return
        Invoice.update_invoices()
        non_printed_invoices = Invoice.objects.filter(printed=False, hide=False)
        print(non_printed_invoices.__len__())
        ##TODO: Change Printed to id of report.

        for invoice in non_printed_invoices:
            if invoice.invoice_status == False:
                continue
            if invoice.profit == None:
                id_checker = None
                invoice.profit = 0  # Profit not counted. Need to count it
            #    print("Debug: invoice profit = 0 , counting profit.")
                http_invoice = DREAM_KAS_API.get_document(invoice.id_dreem)  # get that document with no profit
                if http_invoice['children'] == []:  # Document has no pricing order. profit = 0 , continue with next document
             #       print("0 children documents, profit = 0")
                    continue

                for children_document in http_invoice['children']:  # Document has children. Check if any of them are pricing order.
                    invoice_profit = 0
                    children_document_id = children_document['id']
                    if children_document['type'] == 'PRICING_ORDER': # Pricing ordder. Operation begins.
                        pricing_order_document = DREAM_KAS_API.get_document(children_document_id)  # Document is pricing order, get it by id.
              #          print("Got Document " + children_document_id)
                        if pricing_order_document['status'] == 'DRAFT':  # Pricing order not valid, skipping
                            continue
               #             print("Pricing order = Draft, skipping")
                        else:
                            goods_that_need_to_be_priced_amount = http_invoice['positions'].__len__() #Pricing is valid. Getting amount of goods in invoice
                            total_priced_goods = 0 #setting amount of goods that correctly priced to 0. Increase it with each correct pricing.
                            for good in http_invoice['positions']:
                                for priced_good in pricing_order_document['positions']:
                                    if good['productId'] == priced_good['productId']: # IF goods match - calculate profit from good.
                                        total_priced_goods = total_priced_goods + 1
                                        invoice_profit = invoice_profit + float(good['amount'])/1000*float(priced_good['price'])/1000
                   #                     print(good['name'])
                  #                      print(float(good['amount'])/1000)
                 #                       print(float(priced_good['price'])/1000)
                #                        print('Income_for_this_good:' + str( float(good['amount'])/1000 * float(priced_good['price'])/1000))

                            if total_priced_goods != goods_that_need_to_be_priced_amount:
                                invoice_profit = -505
                    if invoice.profit is not 0 and invoice_profit >= 0:
                        print(0)
                        if children_document_id > id_checker:
                            invoice.profit = invoice_profit
                        else:
                            pass
                    if invoice.profit == 0 and invoice_profit >= 0:
                        invoice.profit = invoice_profit
                        id_checker = children_document_id
                    if invoice_profit <0:
                        invoice.profit = invoice_profit
                        print("ERROR INVOICE. INVOICE PRICING STATUS" , invoice_profit)
                        print('Invoice info:')
                        print('Invoice number: ' , invoice.number)
                        print('Invoice id_dreem:' , invoice.id_dreem)
                        print('Invoice supplier:' , invoice.supplier)
                        print('Invoice sum:' , invoice.sum)
                        print("Please Look into that invoice and create a proper pricing invoice.")


                invoice.save()
        total_estimated_profit = 0
        total_spendings = 0
        for invoice in non_printed_invoices:
            if invoice.profit > 0:
                total_profit = total_estimated_profit + invoice.profit
            total_spendings = total_spendings + invoice.sum

        new_daily_report = DailyInvoiceReport.objects.update_or_create(date=datetime.date.today(), defaults={
            'date': date,
            'spendings' : total_spendings,
            'estimated_profit' : total_estimated_profit
        })
        new_daily_report[0].save()
        new_daily_report[0].invoice_list.set(non_printed_invoices)

class LinkedDocuments(models.Model):
    class DocumentTypesList(models.TextChoices):
        PRICING = "PRICING"
        EDIT = "EDIT"

    invoice_fk = models.ForeignKey(Invoice, on_delete=models.CASCADE)  # Документи, які є в самому інвойсі.
    document_id = models.IntegerField("Linked Document ID", null=True, blank=True, default=None)
    document_type = models.CharField(choices=DocumentTypesList.choices, default=None, null=True, blank=True, max_length=255)
    document_status = models.BooleanField('Document_status', null=True, blank=True, default=False)


class DiadocInvoice(models.Model):
    diadoc_id = models.CharField('diadoc_id', max_length=255, blank=True, default=None, null=True)
    kontragent = models.CharField('Поставщик', max_length=255, blank=True, default=None, null=True)
    number = models.CharField('Номер', max_length=255, blank=True, default=None, null=True)
    sum = models.CharField('Сумма', max_length=255, blank=True, default=None, null=True)
    # sum = models.DecimalField('Сумма', null=True, blank=True, decimal_places=2, max_digits=11, default=None)
    issue_date = models.DateField('Дата', blank=True, default=None, null=True)
    status = models.CharField('Статус', max_length=255, blank=True, default=None, null=True)
    downloadlink = models.CharField('Статус', max_length=1000, blank=True, default=None, null=True)
    invoices = models.ManyToManyField(Invoice)

    @staticmethod
    def update_diadoc_invoices():
        invoices = DIADOC_API.get_documents()
        for item in invoices:
            DiadocInvoice.objects.update_or_create(diadoc_id=item['id'], defaults={
                'kontragent': item['kontragent'],
                'sum': item['sum'],
                'number': item['num'],
                'issue_date': datetime2.strptime(item['date'], "%d.%m.%Y").strftime("%Y-%m-%d"),
                # ({"date": datetime.datetime.strptime(data_dict["Файл"]["Документ"]["СвСчФакт"]["@ДатаСчФ"], "%d.%m.%Y").strftime("%Y-%m-%d")})
                'invoice_status': item['status'],
                'downloadlink': item['link_document_attachment'],
            })
        return


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
    message_id = models.CharField("message id", max_length=255, blank=True, default=None, null=True)
    message_name = models.CharField("Название сообщения", max_length=255, blank=True, default=None, null=True)
    invoices = models.ManyToManyField(Invoice)
    attachments = models.ManyToManyField(GmailMessageAttachment)

    @staticmethod
    def update_gmail_messages():
        companies_list = []
        for file in os.listdir("media/gmail_suppliers"):
            try:
                company = json.loads(open(r"media/gmail_suppliers/" + file).read())
                companies_list.append([company["company_mail"], company["company_time_format"]])
            except:
                print(r"media/gmail_suppliers/" + file)
                print("error opening file as json")
                pass

        messages = get_gmail_messages()
        for message in messages:
            message_id = None
            message_date = None
            message_subject = None
            message_sender = None

            if message.sender[message.sender.find("<"):].replace("<", "").replace(">", "") != "no-reply@accounts.google.com":
                try:
                    message_id = message.headers["Message-Id"].replace("<", "").replace(">", "")
                except:
                    pass
                try:
                    message_id = message.headers["Message-ID"].replace("<", "").replace(">", "")
                except:
                    pass
                if message_id == None:
                    print("sender:" + message.sender[message.sender.find("<"):].replace("<", "").replace(">", ""))
                    print("name:" + message.subject)
                    print("Error. Couldn't find message_id")
                    continue
                try:
                    for ruleset in companies_list:
                        if message.sender[message.sender.find("<"):].replace("<", "").replace(">", "") == ruleset[0]:
                            message_date = datetime.datetime.strptime(message.date, ruleset[1])
                except:
                    pass
                if message_date == None:
                    print("sender:" + message.sender[message.sender.find("<"):].replace("<", "").replace(">", ""))
                    print("name:" + message.subject)
                    print("Не найдена дата либо ошибка даты или ее формата либо данный отправитель не числится в списке отправителей")
                    continue
                message_sender = message.sender[message.sender.find("<"):].replace("<", "").replace(">", "")
                attachments_gmail = [f.filename for f in message.attachments]
                gmail_message = Gmail_Messages.objects.filter(
                    message_sender=message_sender,
                    message_date=message_date.date(),
                    message_name=message.subject,
                    attachments__name__in=attachments_gmail
                ).distinct().first()

                if gmail_message:
                    gmail_message.message_sender = message_sender
                    gmail_message.message_date = message_date
                    gmail_message.message_name = message.subject
                    gmail_message.save()
                else:
                    gmail_message = Gmail_Messages(
                        message_id=message_id,
                        message_sender=message_sender,
                        message_date=message_date,
                        message_name=message.subject
                    )
                    gmail_message.save()

                gmail_message_attachments = []
                for attachment in message.attachments:
                    gmail_message_attachment, gmail_message_attachment_bool = GmailMessageAttachment.objects.update_or_create(name=attachment.filename)
                    gmail_message_attachments.append(gmail_message_attachment)
                gmail_message.attachments.set(gmail_message_attachments)
                # gmail_message, gmail_message_bool = Gmail_Messages.objects.update_or_create(message_id=message_id, defaults={
                #     'message_sender': message.sender[message.sender.find("<"):].replace("<", "").replace(">", ""),
                #     'message_date': message_date,
                #     'message_name': message.subject,
                # })
                # gmail_message.gmailmessageattachment_set.update_or_create(
                #     name=message.attachments,
                # )
        return
