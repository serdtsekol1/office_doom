import os
import threading
import time

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

import datetime

from mainapp import global_var



def periodicTask():
    from mainapp.Dreamkas_documents.pricing_orders import create_pricing_order
    from mainapp.models import GoodGroups
    if global_var.init is True:
        return
    global_var.init = True
    from mainapp.dreamkas_documents import update_invoices_v2, generate_file_to_delete_from_rests_and_egais_rests
    print("Автоматическое обновление накладных")
    from mainapp.Dreamkas_documents.update_documents import update_invoices,update_documents
    from mainapp.models import Invoice_v3, Position_invoice_v3 ,Pricing_order_v3, Position_pricing_order_v3
    from mainapp.Dreamkas_documents.funcs import build_tree_of_documents, find_latest_document_iteration, calculate_profit
    def get_doc_and_info(dreamkas_Id):
        from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object,fetch_documents_positions
        from mainapp.models import Invoice_v3
        document = fetch_document_object(dreamkas_Id)
        positions = fetch_documents_positions(document)

        if document.__class__ == Invoice_v3:
            print(document.number)
            print(document.issue_date)
            print(document.supplier)
            print(document.destination)
            for pos in positions:
                print(pos.position_num, '|',pos.position_name,'|', pos.position_amount, '|', pos.position_price, '|', pos.position_sum)
        elif document.__class__ == Pricing_order_v3:
            print(document.number)
            print(document.issue_date)
            print(document.destination)
            for pos in positions:
                print(pos.position_num, '|',pos.position_name,'|', pos.position_price_old, '->', pos.position_price_new)
    # get_doc_and_info(84953840)
    # get_doc_and_info(84953852)
    GoodGroups.update_good_groups()
    create_pricing_order(85615144)
    update_documents(invoices=True,pricing_orders=True,invoice_limit=100,pricing_order_limit=100,correction_invoices=True,correction_invoice_limit=35)
    i = 0
    while True:
        i = i + 1
        time.sleep(90)
        update_documents(invoices=True,pricing_orders=True,invoice_limit=15,pricing_order_limit=66,correction_invoices=True,correction_invoice_limit=5)
        if i > 60:
            time.sleep(45)
            update_documents(invoices=True,pricing_orders=True,invoice_limit=50,pricing_order_limit=20,correction_invoices=True,correction_invoice_limit=20)
            i = 0
class MainappConfig(AppConfig):
    name = 'mainapp'
    verbose_name = _('admin__mainapp')
    def ready(self):
        if os.environ.get('RUN_MAIN', None) == 'true':
            thread = threading.Thread(target=periodicTask)
            thread.daemon = True
            thread.start()