from dremkas.settings import DREAM_KAS_API
from mainapp.models import Invoice, Supplier, Supplier_name, Supplier_id_dreamkas, Store
from decimal import Decimal
from datetime import datetime as datetime2
from django.utils import timezone
from datetime import timedelta, date


def delete_all_suppliers():
    Supplier.objects.all().delete()

def dreamkas_update_suppliers():
    supplier_list = DREAM_KAS_API.get_suppliers()
    for supplier in supplier_list:
        # Если у поставщика есть имя (т.е не пустой поставщик)
        if 'name' in supplier:

            # И инн
            if 'inn' in supplier:
                # Найти в базе поставщика с таким инн. Если нету - создать.
                supplier_obj = Supplier.objects.filter(inn=supplier['inn']).first()

                # Найти в базе поставщика с таким инн. Если нету - создать.
                if supplier_obj is None:
                    supplier_obj = Supplier.objects.create(inn=supplier['inn'])
                    Supplier_name.objects.create(name=supplier['name'],supplier_fk=supplier_obj)
                    Supplier_id_dreamkas.objects.create(dreamkas_id=supplier['id'], supplier_fk=supplier_obj)

                # Если есть - просмотреть есть ли имя м ид дримкаса для поставщика в списке имен и ид поставщика в нашей базе
                else:

                    # есть ли имя
                    if supplier_obj.supplier_name_set.filter(name=supplier['name']).first() is None:
                        #Нету
                        Supplier_name.objects.create(name=supplier['name'], supplier_fk=supplier_obj)
                        Supplier_id_dreamkas.objects.create(dreamkas_id=supplier['id'], supplier_fk=supplier_obj)

                    # есть ли ид
                    if supplier_obj.supplier_id_dreamkas_set.filter(dreamkas_id=supplier['id']).first() is None:
                        #Нету
                        Supplier_id_dreamkas.objects.create(dreamkas_id=supplier['id'], supplier_fk=supplier_obj)

            #Нету инн но есть имя. Найти если есть имя и ид дримкаса для поставщика в списке ммен и итд поставщиков.
            else:
                supplier_name_obj = Supplier_name.objects.filter(name=supplier['name']).first()
                if supplier_name_obj is None:
                    supplier_obj = Supplier.objects.create()
                    Supplier_name.objects.create(name=supplier['name'], supplier_fk=supplier_obj)
                    Supplier_id_dreamkas.objects.create(dreamkas_id=supplier['id'], supplier_fk=supplier_obj)
                supplier_id_obj = Supplier_id_dreamkas.objects.filter(dreamkas_id=supplier['id']).first()
                if supplier_id_obj is None:
                    Supplier_id_dreamkas.objects.create(dreamkas_id=supplier['id'], supplier_fk=supplier_obj)









    return
def update_invoices():
    documents = DREAM_KAS_API.get_documents(limit=1000)
    source_map_external = []
    external_dreamkas_documents_map = []
    internal_dreamkas_documents_map = []
    for invoice_internal in Invoice.objects.all():
        internal_dreamkas_documents_map.append(invoice_internal.id_dreem)
    for document in documents:
        external_dreamkas_documents_map.append(document['id'])
        if 'sourceName' in document:
            if document['sourceName'] not in source_map_external:
                source_map_external.append(document['sourceName'])
                if Supplier_name.objects.filter(name=document['sourceName']).first() is None:
                    supplier_obj,supplier_status = Supplier.objects.update_or_create(name=document['sourceName'], defaults={})
                    Supplier_name.objects.update_or_create(name=document['sourceName'],supplier_fk= supplier_obj )
    invoices_to_create = []
    invoices_to_update = []
    for document in documents:
        supplier = None
        overdue = False
        if 'sourceName' in document:
            supplier = Supplier_name.objects.filter(name=document['sourceName']).first().supplier_fk
            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime2.strptime(document['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    overdue = True
        if int(document['id']) not in internal_dreamkas_documents_map:
            invoice_new = Invoice(
                id_dreem=document['id'],
                supplier=document['sourceName'] if 'sourceName' in document else None,
                supplier_fk=supplier if supplier else None,
                number=document['num'],
                issue_date=document['issueDate'],
                store=Store.objects.get(store_id=document['targetStoreId']),
                sum=Decimal(int(document['totalSum']) / 100),
                invoice_status= True if "ACCEPTED" in document["status"] else False,
                overdue=overdue,
                invoicetype= True if "[НАЛ]" in document['num'] else False,
                paid=False,
            )
            invoices_to_create.append(invoice_new)
            continue
        else:
            invoice_internal = Invoice.objects.filter(id_dreem=document['id']).first()
            invoice_internal.supplier = document['sourceName'] if 'sourceName' in document else None
            invoice_internal.supplier_fk = supplier if supplier else None
            invoice_internal.number = document['num']
            invoice_internal.issue_date = document['issueDate']
            invoice_internal.store = Store.objects.get(store_id=document['targetStoreId'])
            invoice_internal.sum = Decimal(int(document['totalSum']) / 100)
            invoice_internal.invoice_status = True if "ACCEPTED" in document["status"] else False
            invoice_internal.overdue = overdue
            invoice_internal.invoicetype = True if "[НАЛ]" in document['num'] else False
            invoices_to_update.append(invoice_internal)
    print('Создаются накладные. Кол-во - ', invoices_to_create.__len__())
    print('Обновляются накладные. Кол-во - ', invoices_to_update.__len__())
    Invoice.objects.bulk_create(invoices_to_create)
    Invoice.objects.bulk_update(invoices_to_update,['supplier','supplier_fk','number','issue_date','store','sum','invoice_status','overdue','invoicetype'])
    for invoice_internal in Invoice.objects.filter(invoice_status = False):
        if DREAM_KAS_API.get_document(invoice_internal.id_dreem)['status'] == 404:
            invoice_internal.delete()




        

        # invoice, invoice_create = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
        #     'number': document['num'],
        #     'supplier': document['sourceLegalEntity']['name'],
        #     'supplier_fk': supplier,
        #     'sum': Decimal(int(document['totalSum']) / 100),
        #     'issue_date': document['issueDate'],
        #     'invoicetype': True if "НАЛ" in document['num'] else False,
        #     'overdue': overdue,
        #     'invoice_status': True if "ACCEPTED" in document["status"] else False
        # })

        # if invoice_internal is None:
        #      invoice_new = Invoice(
        #         id=document['id'],
        #         name=product_external['name'],
        #         type=product_external['type'],  # Type here because unit is loaded into type when doing lists of products
        #         marked_good=product_external['marked_good'],
        #         nds=product_external['nds'],
        #         group_id=product_external['group_id'] if 'group_id' in product_external else None,
        #         updatedAt=product_external['updatedAt'] if 'updatedAt' in product_external else None
        #     )
        # if "ACCEPTED" not in document["status"]:
        #     print('asd')
        #     invoice, invoice_create = Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
        #         'supplier': document_source,
        #         'supplier_fk': supplier,
        #         'sum': Decimal(int(document['totalSum']) / 100),
        #         'issue_date': document['issueDate'],
        #         'invoicetype': True if "НАЛ" in document['num'] else False,
        #         'overdue': overdue if supplier.paymenttime is not None else False,
        #     })
def find_duplicate_invoices():
    invoice_map = []
    invoice_duplicate = []
    for invoice in Invoice.objects.all():
        if invoice.id_dreem not in invoice_map:
            invoice_map.append(invoice.id_dreem)
            continue
        invoice_duplicate.append(invoice.id_dreem)
    for invoice_dupe in invoice_duplicate:
        #Invoice.objects.filter(id_dreem=invoice_dupe).order_by('id').first().delete()
        print('id_dreem:' ,invoice_dupe, ' - дупликат!')




def dreamkas_get_document():
    return


def dreamkas_get_children_of_document():
    return
