from datetime import datetime,timedelta,date
from decimal import ROUND_UP, Decimal
from django.utils import timezone
from dremkas.settings import DREAM_KAS_API
from mainapp import global_var
from mainapp.Dreamkas_documents.draft_cleanup import draft_cleanup
from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object, fetch_documents_positions
from mainapp.Dreamkas_documents.suppliers import fetch_or_create_supplier
from mainapp.Dreamkas_documents.stores import fetch_or_create_store
from mainapp.Dreamkas_documents.funcs import find_latest_document_iteration, get_map, parse_number, status_to_flag
from mainapp.logging_utils import log_item
from mainapp.models import Invoice_v3, Position_invoice_v3, Product


def define_if_invalid_document_was_fixed(initial_document):
    initial_document = fetch_document_object(initial_document)
    latest_document = fetch_document_object(initial_document.latest_iteration_id)
    if initial_document.flag_invalid is True:
        if initial_document.latest_iteration_id != initial_document.dreamkas_id:
            latest_document = fetch_document_object(initial_document.latest_iteration_id)
            if latest_document.flag_invalid is False:
                initial_document.flag_invalid_fixed = True
                initial_document.save()
                return True
        if initial_document.flag_invalid_reason =='Накладная не была расценена автоматически. Расцените вручную.':
            if initial_document.latest_iteration_id != initial_document.dreamkas_id:
                latest_document = fetch_document_object(initial_document.latest_iteration_id)
                if latest_document.latest_iteration_id != None:
                    initial_document.flag_invalid_fixed = True
                    initial_document.save()
                    if latest_document.flag_invalid is True:
                        latest_document.flag_invalid_fixed = True
                        latest_document.save()
                        return True
        if (("Что-то не так с количеством в накладной" in initial_document.flag_invalid_reason) or 
        ("Что-то не так с ценой в накладной" in initial_document.flag_invalid_reason) or 
        ("Что-то не так с суммой в накладной" in initial_document.flag_invalid_reason) or 
        ("Что-то не так с ПОЗИЦИЯМИ документа" in initial_document.flag_invalid_reason)):
            define_if_document_is_invalid(initial_document)
    return False
def define_if_document_is_invalid(document):
    if type(document) == int:
        document = fetch_document_object(document)
    if document.__class__.__name__ == 'Invoice_v3' or document.__class__.__name__ == 'Correction_v3':
        if document.flag_status != '1':
            return
        if document.flag_invalid_fixed is True:
            return
        if (
            (document.number == None)
            or (document.acceptedAt == None)
            or (document.supplier == None)
            or (document.totalSum == None)
            ):
            document.flag_invalid = True
            document.flag_invalid_reason = 'Что-то не так с Номером, Датой принятия, Поставщиком или Суммой'
            document.save()
        document_positions = fetch_documents_positions(document_id=document.dreamkas_id)
        if (("Что-то не так с количеством в накладной" in document.flag_invalid_reason) or 
        ("Что-то не так с ценой в накладной" in document.flag_invalid_reason) or 
        ("Что-то не так с суммой в накладной" in document.flag_invalid_reason) or
        ("Что-то не так с ПОЗИЦИЯМИ документа" in document.flag_invalid_reason)):
            flag_invalid = False
            for position in document_positions:
                if ((position.position_name == None) or
                (position.position_amount == None) or (position.position_amount == 0) or 
                (position.position_price == None) or (position.position_price == 0) or 
                (position.position_sum == None) or (position.position_sum == 0) or
                (position.position_id == None) or (position.position_id == '')):
                    document.flag_invalid = True
                    document.flag_invalid_reason = f'Что-то не так с ПОЗИЦИЯМИ документа. Позиция №,{position.position_num}'
                    document.save()
                    flag_invalid = True
            if flag_invalid is False:
                log_item(f"Документ {document.number} от {document.supplier} на сумму {document.totalSum} - Снят флаг ошибки")
                print(f"Документ {document.number} от {document.supplier} на сумму {document.totalSum} - Снят флаг ошибки")
                document.flag_invalid = False
                document.flag_invalid_reason = None
                document.save()
        if "Нету последней итерации" in document.flag_invalid_reason:
            if document.latest_iteration_id is not None:
                log_item(f"Документ {document.number} от {document.supplier} на сумму {document.totalSum} - Снят флаг ошибки")
                print(f"Документ {document.number} от {document.supplier} на сумму {document.totalSum} - Снят флаг ошибки")
                document.flag_invalid = False
                document.flag_invalid_reason = None
                document.save()
            else:
                from mainapp.Dreamkas_documents.update_documents import update_document
                update_document(document.dreamkas_id)
                document.flag_invalid = True
                document.flag_invalid_reason = "Нету последней итерации"
                document.save()

        
        
        
 
def update_invoice(dreamkas_id,document_external=None):
    if document_external is not None:
        document = document_external
    else:
        if type(dreamkas_id) == int or type(dreamkas_id) == str:
            document = DREAM_KAS_API.get_document(id_document=dreamkas_id)
        else:
            document = dreamkas_id
    if document is False:
        document_internal = fetch_document_object(dreamkas_id)
        document_internal.status = 2
        document_internal.save()
        return False
    invoice_object = Invoice_v3.objects.filter(dreamkas_id=dreamkas_id)
    create = False
    if invoice_object.__len__() == 0:
        create = True
        invoice_object = Invoice_v3.objects.create(dreamkas_id=dreamkas_id)
    else:
        invoice_object = invoice_object.first()
        
    supplier = None
    store = None
    if 'sourceLegalEntity' in document:
        supplier = fetch_or_create_supplier(document['sourceLegalEntity']['name'])
    if "targetStoreId" in document:
        store = fetch_or_create_store(document['targetStoreId'])
        
    flag_payment_overdue = False
    if supplier is not None:
        if supplier.paymenttime:
            django_date = timezone.make_aware(datetime.strptime(document['issueDate'], '%Y-%m-%d')).date()
            if date.today() > django_date + timedelta(days=supplier.paymenttime):
                flag_payment_overdue = True
                
    if document["status"] == 'ACCEPTED':
        acceptedAt = document["acceptedAt"]
    else:
        acceptedAt = None
        
    totalSum = Decimal(int(document['totalSum']) / 100).quantize(Decimal('0.00'), rounding=ROUND_UP)
    if str(totalSum).split('.')[0].__len__() > 10:
        print("Sum is too long!")
        print("unable to update invoice", dreamkas_id, document['num'])
        return False, None
    
    invoice_object.totalSum = totalSum
    invoice_object.supplier = document['sourceLegalEntity']['name'] if 'sourceLegalEntity' in document else None
    invoice_object.supplier_fk = supplier
    invoice_object.flag_payment_overdue = flag_payment_overdue
    invoice_object.flag_payment_type = True if "[НАЛ]" in document['num'] else False
    invoice_object.number = document['num']
    invoice_object.issue_date = document['issueDate']
    invoice_object.destination = store
    invoice_object.acceptedAt = acceptedAt
    invoice_object.flag_status = status_to_flag(document['status'])

    if create:
        invoice_object.flag_paid = False

    invoice_object.save()
    
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    to_create, to_update, to_delete = define_and_prep_document_positions_internal(document['id'], document_external=document)
    if to_create is False:
        return False
    positions_to_create.extend(to_create)
    positions_to_update.extend(to_update)
    positions_to_delete.extend(to_delete)
    
    Position_invoice_v3.objects.bulk_create(positions_to_create)
    Position_invoice_v3.objects.bulk_update(positions_to_update, ['flag_found','position_amount','position_price','position_sum','position_name','position_id'])
    
    for position in positions_to_delete:
        position.delete()
    find_latest_document_iteration(dreamkas_id)

    return True

def define_invoices_to_update_or_create(internal_dreamkas_documents_map,external_documents):
    invoices_to_create =[]
    invoices_to_update =[]
    for external_document in external_documents:
        if int(external_document['id']) not in internal_dreamkas_documents_map:
            invoices_to_create.append(external_document)
            continue
        # if int(external_document['id']) in internal_dreamkas_documents_map:
        #     internal_document = Invoice_v3.objects.get(dreamkas_id=external_document['id'])
        #     if (
        #             internal_document.number != external_document['num'] or
        #             int(internal_document.sum * 100) != int(external_document['totalSum']) or
        #             internal_document.position_invoice_v3_set.all().__len__() != external_document['positionCount']
        #         ):
        invoices_to_update.append(external_document)
    return invoices_to_create,invoices_to_update

def prep_invoices_for_bulk_creation(invoices_to_create):
    to_create = []
    for invoice_to_create in invoices_to_create:
        supplier = None
        store = None
        if 'sourceName' in invoice_to_create:
            supplier = fetch_or_create_supplier(invoice_to_create['sourceName'])
        if "targetStoreId" in invoice_to_create:
            store = fetch_or_create_store(invoice_to_create['targetStoreId'])
        flag_overdue = False
        if supplier is not None:
            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime.strptime(invoice_to_create['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    flag_overdue = True
        totalSum = Decimal(int(invoice_to_create['totalSum']) / 100).quantize(Decimal('0.00'), rounding=ROUND_UP)
        if str(totalSum).split('.')[0].__len__() > 10:
            print("Sum is too long!")
            print("unable to create invoice", invoice_to_create['id'], invoice_to_create['num'])
            continue
        if invoice_to_create["status"] == 'ACCEPTED':
            acceptedAt = invoice_to_create["acceptedAt"]
        else:
            acceptedAt = None
        
        # Map status to flag_status using the utility function
        flag_status = status_to_flag(invoice_to_create["status"])
        invoice_new = Invoice_v3(
            dreamkas_id=invoice_to_create['id'],
            supplier=invoice_to_create['sourceName'] if 'sourceName' in invoice_to_create else None,
            supplier_fk=supplier,
            number=invoice_to_create['num'],
            issue_date=invoice_to_create['issueDate'],
            destination=store,
            totalSum=totalSum,
            acceptedAt=acceptedAt,
            flag_status=flag_status,
            flag_payment_type= True if "[НАЛ]" in invoice_to_create['num'] else False,
            flag_paid=False,
            flag_payment_overdue=flag_overdue,
        )
        to_create.append(invoice_new)
    return to_create

def prep_invoices_for_bulk_update(invoices_to_update):
    to_update = []
    for invoice_to_update in invoices_to_update:
        supplier = None
        store = None
        invoice_internal = Invoice_v3.objects.filter(dreamkas_id=invoice_to_update['id'])
        if invoice_internal.__len__() == 0:
            print("Error. Invoice that needs to be updated is not found")
            print(invoice_internal)
            print("Error End.")
            continue
        invoice_internal = invoice_internal.first()      
        if 'sourceName' in invoice_to_update:
            supplier = fetch_or_create_supplier(invoice_to_update['sourceName'])
        if "targetStoreId" in invoice_to_update:
            store = fetch_or_create_store(invoice_to_update['targetStoreId'])
        flag_payment_overdue = False
        if supplier is not None:
            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime.strptime(invoice_to_update['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    flag_payment_overdue = True
        if invoice_to_update["status"] == 'ACCEPTED':
            acceptedAt = invoice_to_update["acceptedAt"]
        else:
            acceptedAt = None
        
        # Map status to flag_status using the utility function
        flag_status = status_to_flag(invoice_to_update["status"])
        invoice_internal.supplier=invoice_to_update['sourceName'] if 'sourceName' in invoice_to_update else None
        invoice_internal.supplier_fk=supplier
        invoice_internal.number=invoice_to_update['num']
        invoice_internal.issue_date=invoice_to_update['issueDate']
        invoice_internal.destination=store
        invoice_internal.acceptedAt=acceptedAt
        invoice_internal.totalSum = Decimal(int(invoice_to_update['totalSum']) / 100).quantize(Decimal('0.00'), rounding=ROUND_UP)
        if str(invoice_internal.totalSum).split('.')[0].__len__() > 10:
            print("Sum is too long!")
            print("unable to update invoice", invoice_to_update['id'], invoice_to_update['num'])
            continue
        invoice_internal.flag_status = flag_status
        invoice_internal.flag_payment_type= True if "[НАЛ]" in invoice_to_update['num'] else False
        invoice_internal.flag_payment_overdue = flag_payment_overdue
        to_update.append(invoice_internal)
    return to_update

def define_and_prep_document_positions_internal(document_id,document_external=None):

    if document_external is None:
        external_doc = DREAM_KAS_API.get_document(id_document=document_id)
    else:
        external_doc = document_external
    internal_doc = Invoice_v3.objects.filter(dreamkas_id=document_id)

    if internal_doc.__len__() == 0:
        ##TODO: error handling.
        return False
    if external_doc == False:
        return False
    internal_doc = internal_doc.first()
    i = 0
    flag_invalid = False
    flag_invalid_reason = None
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    if Position_invoice_v3.objects.filter(invoice_v3_fk=internal_doc).all().__len__() > 0:
        i = 0
        for position_external in external_doc['positions']:
            position_internal = Position_invoice_v3.objects.filter(invoice_v3_fk=internal_doc,position_num=i).first()
            if position_internal is None:
                break
            product_fk = Product.objects.filter(id_out=position_external['productId'])
            if product_fk.__len__() == 0:
                flag_found = False 
            else:
                product_fk = product_fk.first()
                flag_found = True
            position_amount = parse_number(position_external.get('amount'))
            if position_amount is None:
                flag_invalid = True
                flag_invalid_reason = f'{position_external.get("name"),"Что-то не так с количеством в накладной."}'
            position_price = parse_number(position_external.get('costWithTax'))
            if position_price is None:
                flag_invalid = True
                flag_invalid_reason = f'{position_external.get("name"),"Что-то не так с ценой в накладной."}'
            position_sum = parse_number(position_external.get('sumCost'))
            if position_sum is None:
                flag_invalid = True
                flag_invalid_reason = f'{position_external.get("name"),"Что-то не так с суммой в накладной."}'
            if flag_invalid is True:
                internal_doc.flag_invalid = True
                internal_doc.flag_invalid_reason = flag_invalid_reason
                internal_doc.save()
                print(internal_doc.dreamkas_id, internal_doc.number, flag_invalid_reason)
                print(f"https://kabinet.dreamkas.ru/app/#!/documents/card~2F{internal_doc.dreamkas_id}")
                break
            position_internal.flag_found = flag_found
            position_internal.position_amount = position_amount  / 1000 if position_amount is not None else None
            position_internal.position_price = position_price / 100 if position_price is not None else None
            position_internal.position_sum = position_sum / 100 if position_sum is not None else None
            position_internal.position_name = position_external['name']
            position_internal.position_id = position_external['productId']
            positions_to_update.append(position_internal)
            # if global_var.debug is True:
            #     print(position_internal.position_num, '|',position_internal.position_name)
            i = i + 1
        if flag_invalid is True and internal_doc.flag_status == 1:
            return False,False,False
    j = 0
    for position_external in external_doc['positions']:
        if j > external_doc['positions'].__len__() - 1:
            break
        if j < i:
            j = j + 1
            continue
        product_fk = Product.objects.filter(id_out=position_external['productId'])
        if product_fk.__len__() == 0:
            flag_found = False 
        else:
            product_fk = product_fk.first()
            flag_found = True

       

        position_amount = parse_number(position_external.get('amount'))
        if position_amount is None:
            flag_invalid = True
            flag_invalid_reason = f'{position_external.get("name"),"Что-то не так с количеством в накладной."}' 
        position_price = parse_number(position_external.get('costWithTax'))
        if position_price is None:
            flag_invalid = True
            flag_invalid_reason = f'{position_external.get("name"),"Что-то не так с ценой в накладной."}'
        position_sum = parse_number(position_external.get('sumCost'))
        if position_sum is None:
            flag_invalid = True
            flag_invalid_reason = f'{position_external.get("name"),"Что-то не так с суммой позиции в накладной."}'
        position_to_create = Position_invoice_v3(
            invoice_v3_fk = internal_doc,
            flag_found = flag_found,
            product_fk = product_fk if flag_found is True else None,
            position_name = position_external['name'],
            position_num = j,
            position_id = position_external['productId'] if 'productId' in position_external else None,
            position_amount = position_amount / 1000 if position_amount is not None else None,
            position_price = position_price / 100 if position_price is not None else None,
            position_sum = position_sum / 100 if position_sum is not None else None
        )
        positions_to_create.append(position_to_create)
        j = j + 1
    if internal_doc.position_invoice_v3_set.all().__len__() > external_doc['positions'].__len__():
        i = 0
        while i < internal_doc.position_invoice_v3_set.all().__len__():
            if i <= external_doc['positions'].__len__() -1 :
                i = i + 1
                continue
            if i > external_doc['positions'].__len__() - 1:
                positions_to_delete.append(internal_doc.position_invoice_v3_set.all()[i])
            i = i + 1
    for position_internal in internal_doc.position_invoice_v3_set.filter(position_num__gt=external_doc['positions'].__len__() - 1):
        positions_to_delete.append(position_internal)
    return positions_to_create,positions_to_update,positions_to_delete

def update_invoices(limit=1000,offset=None,acceptedAtFrom=None,accetpedAtTo=None,query=None):
    documents_external = DREAM_KAS_API.get_documents(limit=limit, offset=offset,acceptedAtFrom=acceptedAtFrom,acceptedAtTo=accetpedAtTo,query=query)
    log_item('update_invoices: documents external fetched')
    print('Documents fetched')
    draft_cleanup(documents_external)
    log_item('update_invoices: draft cleanup done')
    print('Draft cleanup done')
    internal_dreamkas_documents_map = get_map(Invoice_v3,"dreamkas_id")
    invoices_to_create,invoices_to_update = define_invoices_to_update_or_create(internal_dreamkas_documents_map,documents_external)
    print('Invoices to create and update defined')
    log_item('update_invoices: invoices to create and update defined')
    to_create = prep_invoices_for_bulk_creation(invoices_to_create)
    to_update = prep_invoices_for_bulk_update(invoices_to_update)
    log_item('update_invoices: invoices to create and update prepared')
    print('Invoices to create and update prepared')
    Invoice_v3.objects.bulk_create(to_create)
    Invoice_v3.objects.bulk_update(to_update,['supplier','acceptedAt','supplier_fk','number','issue_date','destination','totalSum','flag_status','flag_payment_overdue','flag_payment_type'])
    print('Invoices created and updated')
    log_item('update_invoices: invoices created and updated')
    all_docs = invoices_to_create + invoices_to_update
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    j = 0
    log_item('update_invoices: getting positions')
    for document in all_docs:
        if all_docs.__len__() > 10:
            if j % int(all_docs.__len__()*0.1) == 0:
                print(f'Updating_invoices. Progress: {j} / {limit}')
                log_item(f'Updating_invoices. Progress: {j} / {limit}')
        else:
            print(f'Updating_invoices. Progress: {j} / {limit}')
            log_item(f'Updating_invoices. Progress: {j} / {limit}')
        j = j + 1
        to_create,to_update,to_delete = define_and_prep_document_positions_internal(document['id'])
        if to_create is False:
            continue
        positions_to_create.extend(to_create)
        positions_to_update.extend(to_update)
        positions_to_delete.extend(to_delete)
    log_item('update_invoices: positions to create and update defined')
    print('Positions to create and update defined')
    Position_invoice_v3.objects.bulk_create(positions_to_create)
    print("created", positions_to_create.__len__(), "positions")
    Position_invoice_v3.objects.bulk_update(positions_to_update,['flag_found','position_amount','position_price','position_sum','position_name','position_id'])
    i = 0
    for position in positions_to_delete:
        position.delete()
        i = i + 1
    print("deleted", i, "positions")
    print('Positions created and updated')
    all_doc_ids = []
    for doc in all_docs:
        all_doc_ids.append(doc['id'])
    return True, all_doc_ids