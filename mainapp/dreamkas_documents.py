import threading
import time

from dremkas.settings import DREAM_KAS_API
from mainapp import global_var
from mainapp.models import Invoice, Invoice_v3, Position_invoice_v3, Product, Supplier, Supplier_name, Supplier_id_dreamkas, Store
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, date, datetime

def delete_long_not_accepted_documents():
    return
def delete_all_suppliers():
    Supplier.objects.all().delete()
def delete_broken_suppliers():
    supplier_map = []
    supplier_dupes = []
    for supplier_obj in Supplier.objects.all():
        if supplier_obj.supplier_name_set.all().__len__() == 0 and supplier_obj.inn == None:
            supplier_obj.delete()
        if supplier_obj.inn is not None:
            if supplier_obj.inn not in supplier_map:
                supplier_map.append(supplier_obj.inn)
                continue
            supplier_dupes.append(supplier_obj.inn)
    print(supplier_dupes)


def calculate_income(document_id, pricing_id):
    invoice = DREAM_KAS_API.get_document(document_id)
    pricint = DREAM_KAS_API.get_document(pricing_id)
    print('a')
    return

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





def failsafe_invoices_being_updated():
    if global_var.Failsafe_flag is True:
        return
    global_var.Failsafe_flag = True
    time.sleep(1200)
    if global_var.invoices_being_updated is True:
        global_var.invoices_being_updated = False
    global_var.Failsafe_flag = False
def update_pricing_orders_v2(offset=None,limit=1000):
    documents_external = DREAM_KAS_API.get_documents(limit=limit, offset=offset, document_type=11)
    
def draft_cleanup(documents_external):
    deletions = 0
    for document_external in documents_external:
        if datetime.now() > datetime.strptime(document_external['createdAt'], '%Y-%m-%d') + timedelta(days=4) and document_external['status'] == 'DRAFT':
            DREAM_KAS_API.delete_document(document_external['id'])
            document_internal = Invoice_v3.objects.filter(dreamkas_id=document_external['id'])
            if document_internal.__len__() > 1:
                doc_internal = document_internal.first()
                doc_internal.flag_status = 2
                doc_internal.save()
            deletions = deletions + 1
    return deletions
                
def generate_file_to_delete_from_rests_and_egais_rests(filename_rests=None,  filename_rests_egais=None):
    #Filename_rests in ways of next form:
    #TXT BEGIN:
    #BARCODE
    #Amount
    #BARCODE
    #Amount
    #BARCODE
    #Amount
    #e.g.:
    #4444444444444
    #15
    #5555555555550
    #25
    #2657391263101
    #144
    import openpyxl, os
    if filename_rests is None:
        filename="Z:\dreamkas_new\ОСТАТКИ.txt"
    else:
        filename=filename_rests
    
    condensed_list = []
    with open(filename, 'r') as file:
        lines = file.readlines()
    line_count = len(lines)
    i = 0
    for i in range(line_count-1):
        if lines[i].strip().__len__() == 13:
            found = False
            for condensed_line in condensed_list:
                if condensed_line[0] == lines[i].strip():
                    found = True
                    condensed_line[1] = condensed_line[1] + int(lines[i+1].strip())
            if found is False:
                condensed_list.append([lines[i].strip(),int(lines[i+1].strip())])
    print(condensed_list)
    if filename_rests_egais is None:
        filename_rests_egais_inner="Z:\dreamkas_new\\rests-20250402_0508.xlsx"
    else:
        filename_rests_egais_inner=filename_rests_egais
    try:
        wb = openpyxl.load_workbook(filename_rests_egais_inner)
    except Exception as ex:
        print(filename_rests_egais_inner)
        print("file missing!")
    
    sheet = wb.active
    res_table = [list(row) for row in sheet.iter_rows(min_row=2, values_only=True)]
    found_products = []
    what_we_have = condensed_list
    what_is_listed = res_table
    what_is_listed_condensed = []
    for product in what_is_listed:
        found = False
        for product_condensed in what_is_listed_condensed:
            if product_condensed[0] == product[0]:
                product_condensed[3] = int(product_condensed[3]) + int(product[3])
                found = True
        if found == False:
            what_is_listed_condensed.append(product)
    for product in what_is_listed_condensed:
        found_product = DREAM_KAS_API.search_goods(product[0],q_is_vendor_code=False)
        found_products.append(found_product)
    what_we_have_dict = []
    for product in what_we_have:
        result = {
            "Barcode": str(product[0]),
            "Amount": str(product[1])
        }
        what_we_have_dict.append(result)
    what_is_listed_condensed_dict = []
    for product in what_is_listed_condensed:
        result = {
            "AlcoCode": str(product[0]),
            "FACode": str(product[1]),
            "FBCode": str(product[2]),
            "Amount": str(product[3]),
            "Name": str(product[6]),
            "AlcPercent": str(product[8]),
            "Liters": str(product[9]),
        }
        what_is_listed_condensed_dict.append(result)
    for product in what_we_have_dict:
        for found_product in found_products:
            if found_product.__len__() > 0: 
                if str(product['Barcode']) in str(found_product[0]):
                    product['AlcoCode'] = found_product[0]['meta']['codes']
    for product in what_we_have_dict:
        if 'AlcoCode' in product:
            for product_listed in what_is_listed_condensed_dict:
                for alco_code in product['AlcoCode']:
                    if alco_code == product_listed['AlcoCode']:
                        product['listed_amount'] = product_listed['Amount']
    to_delete = []
    for item in what_we_have_dict:
        if 'listed_amount' in str(item):
            item['amount_to_remove'] = int(float(item['listed_amount'])) - int(item['Amount'])
            to_delete.append(item)
    to_delete_egais = []
    for item in to_delete:
        if item['amount_to_remove'] > 0:
            for item_2 in what_is_listed:
                if item_2[0] in str(item):
                    if item['amount_to_remove'] > item_2[3]:
                        to_delete_egais.append(item_2)
                        item['amount_to_remove'] = item['amount_to_remove'] - item_2[3]
                    else:
                        item_2[3] = item_2[3] - item['amount_to_remove']
                        to_delete_egais.append(item_2)
                        item['amount_to_remove'] = 0

    print('a')
    
def update_invoices_v2(offset=None,limit=1000):
    documents_external = DREAM_KAS_API.get_documents(limit=limit, offset=offset)
    deletions = draft_cleanup(documents_external)
    while deletions != 0:
        documents_external = DREAM_KAS_API.get_documents(limit=limit, offset=offset)
        deletions = draft_cleanup(documents_external)
    invoices_to_create = []
    invoices_to_update = []
    internal_dreamkas_documents_map = []
    for internal_document in Invoice_v3.objects.all():
        internal_dreamkas_documents_map.append(internal_document.dreamkas_id)
    for external_document in documents_external:
        if int(external_document['id']) not in internal_dreamkas_documents_map:
            invoices_to_create.append(external_document)
        if int(external_document['id']) in internal_dreamkas_documents_map:
            if (
                    internal_document.number != external_document['num'] or
                    int(internal_document.sum * 100) != int(external_document['totalSum']) or
                    internal_document.position_invoice_v3_set.all().__len__() != external_document['positionCount']
                ):
                invoices_to_update.append(external_document)
            
    to_create = []
    for invoice_to_create in invoices_to_create:
        supplier = None
        if 'sourceName' in invoice_to_create:
            supplier_1 = Supplier_name.objects.filter(name=invoice_to_create['sourceName'])
            if supplier_1.__len__() == 0:
                ## add here: Create an supplier
                a = 0            
            else:
                supplier = supplier_1.first().supplier_fk
        store = None
        if "targetStoreId" in invoice_to_create:
            store_1 = Store.objects.filter(store_id=invoice_to_create["targetStoreId"])
            if store_1.__len__() == 0:
                ## add here: Create a Store
                a = 0
            else:
                store = store_1.first()
        flag_overdue = False
        if supplier is not None:
            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime.strptime(document['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    flag_overdue = True
        invoice_new = Invoice_v3(
            dreamkas_id=invoice_to_create['id'],
            supplier=invoice_to_create['sourceName'] if 'sourceName' in invoice_to_create else None,
            supplier_fk=supplier,
            number=invoice_to_create['num'],
            issue_date=invoice_to_create['issueDate'],
            destination=store,
            sum=Decimal(int(invoice_to_create['totalSum']) / 100),
            flag_status= True if "ACCEPTED" in invoice_to_create["status"] else False,
            flag_payment_type= True if "[НАЛ]" in invoice_to_create['num'] else False,
            flag_paid=False,
            flag_payment_overdue=flag_overdue,
        )
        to_create.append(invoice_new)
    print('test_3')
    to_update = []
    for invoice_to_update in invoices_to_update:
        invoice_internal = Invoice_v3.objects.filter(dreamkas_id=invoice_to_update['id'])
        if invoice_internal.__len__() == 0:
            print("Error. Invoice that needs to be updated is not found")
            print(invoice_internal)
            print("Error End.")
            continue
        invoice_internal = invoice_internal.first()
        
        supplier = None
        if 'sourceName' in invoice_to_update:
            supplier_1 = Supplier_name.objects.filter(name=invoice_to_update['sourceName'])
            if supplier_1.__len__() == 0:
                ## add here: Create an supplier
                a = 0            
            else:
                supplier = supplier_1.first().supplier_fk
                
        store = None
        if "targetStoreId" in invoice_to_update:
            store_1 = Store.objects.filter(store_id=invoice_to_update["targetStoreId"])
            if store_1.__len__() == 0:
                ## add here: Create a Store
                a = 0
            else:
                store = store_1.first()
                flag_payment_overdue = False
        if supplier is not None:
            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime.strptime(document['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    flag_payment_overdue = True
                    
        invoice_internal.supplier=invoice_to_update['sourceName'] if 'sourceName' in invoice_to_update else None
        invoice_internal.supplier_fk=supplier
        invoice_internal.number=invoice_to_update['num']
        invoice_internal.issue_date=invoice_to_update['issueDate']
        invoice_internal.destination=store
        invoice_internal.sum=Decimal(int(invoice_to_update['totalSum']) / 100)
        invoice_internal.flag_status= True if "ACCEPTED" in invoice_to_update["status"] else False
        invoice_internal.flag_payment_type= True if "[НАЛ]" in invoice_to_update['num'] else False
        invoice_internal.flag_payment_overdue = flag_payment_overdue
        to_update.append(invoice_internal)
    print('test_2')
    Invoice_v3.objects.bulk_create(to_create)
    Invoice_v3.objects.bulk_update(to_update,['supplier','supplier_fk','number','issue_date','destination','sum','flag_status','flag_payment_overdue','flag_payment_type'])
    print('test_1')
    all_docs = invoices_to_create + invoices_to_update
    j = 0
    for document in all_docs:
        print("Updating_invoices. Progress", j, "/", limit)
        j = j + 1
        external_doc = DREAM_KAS_API.get_document(id_document=document['id'])
        internal_doc = Invoice_v3.objects.filter(dreamkas_id=document['id'])
        if internal_doc.__len__() == 0:
            ##TODO: error handling.
            continue
        internal_doc = internal_doc.first()
        i = 0
        positions_to_create = []
        if Position_invoice_v3.objects.filter(invoice_v3_fk=internal_doc).all().__len__() > 0:
            Position_invoice_v3.objects.filter(invoice_v3_fk=internal_doc).all().delete()
        for position_external in external_doc['positions']:
            product_fk = Product.objects.filter(id_out=position_external['productId'])
            if product_fk.__len__() == 0:
                flag_found = False 
            else:
                product_fk = product_fk.first()
                flag_found = True
            try:
                position_amount = float(position_external['amount']/1000)
            except:
                position_amount = None
            try:
                position_price = float(position_external['costWithTax']/1000)
            except:
                position_price = None
            try:
                position_sum = float(position_external['sumCost']/1000)
            except:
                position_sum = None
            
            position_to_create = Position_invoice_v3(
                invoice_v3_fk = internal_doc,
                flag_found = flag_found,
                product_fk = product_fk if flag_found is True else None,
                position_name = position_external['name'],
                position_num = i,
                position_id = position_external['productId'] if 'productId' in position_external else None,
                position_amount = float(position_external['amount'])/1000 if (type(position_external['amount']) is float or type(position_external['amount']) is int) else None,
                position_price = float(position_external['costWithTax'])/100 if (type(position_external['costWithTax']) is float or type(position_external['costWithTax']) is int) else None,
                position_sum = float(position_external['sumCost'])/100 if (type(position_external['sumCost']) is float or type(position_external['sumCost']) is int) else None,
                                
            )
            positions_to_create.append(position_to_create)
            i = i + 1
        Position_invoice_v3.objects.bulk_create(positions_to_create)
        
        
         
    
        
def update_invoices(offset=None):
    #calculate_income()
    if global_var.Failsafe_flag is False:
        reset_thread = threading.Thread(target=failsafe_invoices_being_updated)
        reset_thread.start()
    if global_var.invoices_being_updated == True:
        print("Накладные уже обновляются. Подождите и попытайтесь снова.")
        return "Накладные уже обновляются. Подождите и попытайтесь снова."
    global_var.invoices_being_updated = True
    documents = DREAM_KAS_API.get_documents(limit=1000, offset=offset)
    if documents.__len__() == 0:
        global_var.invoices_being_updated = False
        return False
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
                django_date = timezone.make_aware(datetime.strptime(document['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    overdue = True



        try:
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
                invoice_internal.store = Store.objects.filter(store_id=document['targetStoreId']).first()
                if not invoice_internal.store:
                    print('error store not found')
                    print('id dreem' , document['id'])
                    print('storeid' ,document['targetStoreId'])
                invoice_internal.sum = Decimal(int(document['totalSum']) / 100)
                invoice_internal.invoice_status = True if "ACCEPTED" in document["status"] else False
                invoice_internal.overdue = overdue
                invoice_internal.invoicetype = True if "[НАЛ]" in document['num'] else False
                invoices_to_update.append(invoice_internal)
        except:
            print('Error creating or updating invoice')
            print(document)
            global_var.invoices_being_updated = False
    print('Создаются накладные. Кол-во - ', invoices_to_create.__len__())
    print('Обновляются накладные. Кол-во - ', invoices_to_update.__len__())
    Invoice.objects.bulk_create(invoices_to_create)
    Invoice.objects.bulk_update(invoices_to_update,['supplier','supplier_fk','number','issue_date','store','sum','invoice_status','overdue','invoicetype'])
    for invoice_internal in Invoice.objects.filter(invoice_status = False):
        if DREAM_KAS_API.get_document(invoice_internal.id_dreem)['status'] == 404:
            invoice_internal.delete()
    global_var.invoices_being_updated = False
    return True





        

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
    i = 0
    for invoice in Invoice.objects.all():
        i = i + 1
        if invoice.id_dreem not in invoice_map:
            invoice_map.append(invoice.id_dreem)
            continue
        print('dupe found')
        invoice_duplicate.append(invoice.id_dreem)
    for invoice_dupe in invoice_duplicate:
        #Invoice.objects.filter(id_dreem=invoice_dupe).order_by('id').first().delete()
        print('id_dreem:' ,invoice_dupe, ' - дупликат!')




def dreamkas_get_document():
    return


def dreamkas_get_children_of_document():
    return
def dreamkas_inventory_inventory_check_internal():

    return
def delete_duplicate_invoice_objects():
    from django.db.models import Count, Max
    from django.db.models import F

    # First, we group the objects by barcode and count the number of occurrences
    invoice_counts = Invoice.objects.values('id_dreem').annotate(count=Count('id_dreem'))

    # Next, we filter to get only the barcodes that have multiple occurrences
    duplicate_invoices = invoice_counts.filter(count__gt=1)

    # Now, for each duplicate barcode, we find the object with the biggest id and delete it
    for invoice_count in duplicate_invoices:
        max_id = Invoice.objects.filter(id_dreem=invoice_count['id_dreem']).aggregate(max_id=Max('id'))['max_id']
        Invoice.objects.filter(id=max_id).delete()