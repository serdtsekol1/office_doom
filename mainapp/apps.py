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
    from mainapp.dreamkas_documents import update_invoices
    print("Следующее автоматическое обновление накладных через час")
    while True:
        time.sleep(3600)
        update_invoices()
class MainappConfig(AppConfig):
    name = 'mainapp'
    verbose_name = _('admin__mainapp')
    def ready(self):
        thread = threading.Thread(target=periodicTask)
        thread.daemon = True
        thread.start()