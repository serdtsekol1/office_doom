import os
import threading
import time

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

import datetime

from mainapp import global_var






def periodicTask():
    if global_var.init is True:
        return
    global_var.init = True
    print("Автоматическое обновление накладных")
    from mainapp.Dreamkas_documents.update_documents import update_documents
    from mainapp.Reports.invoice_report import create_invoice_report
    from mainapp.Reports.invoice_report import invoice_report_range_of_dates
    from mainapp.models import Correction_invoice_v3,Invoice_v3,Pricing_order_v3,Position_pricing_order_v3,Position_invoice_v3,Position_correction_invoice_v3
    from mainapp.Dreamkas_documents.funcs import find_latest_document_iteration
    from mainapp.dreamkas_documents import global_draft_cleanup
    # Initial update    
    # update_documents(invoices=False,pricing_orders=False,correction_invoices=False,blanks=False,to_check_for_fixed_documents=False,find_latest_iterations=False)
    update_documents(invoices=True,pricing_orders=True,invoice_limit=25,pricing_order_limit=50,correction_invoices=True,correction_invoice_limit=5)
    global_var.invoices_last_update_at = datetime.datetime.now()
    global_var.save_persistent_vars()
    i = 0
    while True:
        i = i + 1
        time.sleep(60)
        # Regular update
        if (global_var.global_document_update_at is None or
            global_var.global_document_update_at.date() > datetime.datetime.now().date()
            ):
            update_documents(invoices=True,pricing_orders=True,invoice_limit=1000,pricing_order_limit=1000,correction_invoices=True,correction_invoice_limit=200)
            global_draft_cleanup()
            global_var.global_document_update_at = datetime.datetime.now().date()
            global_var.invoices_last_update_at = datetime.datetime.now()
            global_var.save_persistent_vars()
        else:
            update_documents(invoices=True,pricing_orders=True,invoice_limit=10,pricing_order_limit=10,correction_invoices=True,correction_invoice_limit=5)
            update_documents(invoices=False,pricing_orders=True,invoice_limit=10,pricing_order_limit=10,correction_invoices=False,acceptedAtFrom=str(datetime.datetime.now().date()))
            global_draft_cleanup()
            global_var.invoices_last_update_at = datetime.datetime.now()
            global_var.save_persistent_vars()

        if i > 60:
            time.sleep(45)
            update_documents(invoices=True,pricing_orders=True,invoice_limit=150,pricing_order_limit=300,correction_invoices=True,correction_invoice_limit=5)
            global_draft_cleanup()
            global_var.invoices_last_update_at = datetime.datetime.now()
            global_var.save_persistent_vars()
            i = 0


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