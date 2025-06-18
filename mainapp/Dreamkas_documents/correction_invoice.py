from datetime import datetime,timedelta,date
from decimal import ROUND_UP, Decimal
from django.utils import timezone
from dremkas.settings import DREAM_KAS_API
from mainapp import global_var
from mainapp.Dreamkas_documents.draft_cleanup import draft_cleanup
from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object
from mainapp.Dreamkas_documents.suppliers import fetch_or_create_supplier
from mainapp.Dreamkas_documents.stores import fetch_or_create_store
from mainapp.Dreamkas_documents.funcs import get_map, parse_number, status_to_flag, find_latest_document_iteration

from mainapp.models import Correction_invoice_v3, Position_correction_invoice_v3, Product



def define_correction_invoices_to_update_or_create(internal_dreamkas_documents_map,external_documents):
    correction_invoices_to_create =[]
    correction_invoices_to_update =[]
    for external_document in external_documents:
        if int(external_document['id']) not in internal_dreamkas_documents_map:
            correction_invoices_to_create.append(external_document)
            continue
        correction_invoices_to_update.append(external_document)
    return correction_invoices_to_create,correction_invoices_to_update

def prep_correction_invoices_for_bulk_creation(correction_invoices_to_create):
    to_create = []
    for correction_invoice_to_create in correction_invoices_to_create:
        supplier = None
        store = None
        if 'sourceName' in correction_invoice_to_create:
            supplier = fetch_or_create_supplier(correction_invoice_to_create['sourceName'])
        if "targetStoreId" in correction_invoice_to_create:
            store = fetch_or_create_store(correction_invoice_to_create['targetStoreId'])
        flag_overdue = False
        if supplier is not None:
            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime.strptime(correction_invoice_to_create['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    flag_overdue = True
        if 'totalSum' in str(correction_invoice_to_create):
            totalSum = Decimal(int(correction_invoice_to_create['totalSum']) / 100).quantize(Decimal('0.00'), rounding=ROUND_UP)
        else:
            totalSum = Decimal('0.00')
        if str(totalSum).split('.')[0].__len__() > 10:
            print("Sum is too long!")
            print("unable to create correction invoice", correction_invoice_to_create['id'], correction_invoice_to_create['num'])
            continue
        if correction_invoice_to_create["status"] == 'ACCEPTED':
            acceptedAt = correction_invoice_to_create["acceptedAt"]
        else:
            acceptedAt = None
        if correction_invoice_to_create["status"] == 'ACCEPTED':
            flag_status = '1'
        else:
            flag_status = '0'
        correction_invoice_new = Correction_invoice_v3(
            dreamkas_id=correction_invoice_to_create['id'],
            supplier=correction_invoice_to_create['sourceName'] if 'sourceName' in correction_invoice_to_create else None,
            supplier_fk=supplier,
            number=correction_invoice_to_create['num'],
            issue_date=correction_invoice_to_create['issueDate'],
            destination=store,
            acceptedAt=acceptedAt,
            totalSum=totalSum,
            flag_status=flag_status,
            flag_payment_type= True if "[НАЛ]" in correction_invoice_to_create['num'] else False,
            flag_paid=False,
            flag_payment_overdue=flag_overdue,
        )
        to_create.append(correction_invoice_new)
    return to_create

def prep_correction_invoices_for_bulk_update(correction_invoices_to_update):
    to_update = []
    for correction_invoice_to_update in correction_invoices_to_update:
        supplier = None
        store = None
        correction_invoice_internal = Correction_invoice_v3.objects.filter(dreamkas_id=correction_invoice_to_update['id'])
        if correction_invoice_internal.__len__() == 0:
            print("Error. Correction invoice that needs to be updated is not found")
            print(correction_invoice_internal)
            print("Error End.")
            continue
        correction_invoice_internal = correction_invoice_internal.first()      
        if 'sourceName' in correction_invoice_to_update:
            supplier = fetch_or_create_supplier(correction_invoice_to_update['sourceName'])
        if "targetStoreId" in correction_invoice_to_update:
            store = fetch_or_create_store(correction_invoice_to_update['targetStoreId'])
        flag_payment_overdue = False
        if supplier is not None:
            if supplier.paymenttime:
                django_date = timezone.make_aware(datetime.strptime(correction_invoice_to_update['issueDate'], '%Y-%m-%d')).date()
                if date.today() > django_date + timedelta(days=supplier.paymenttime):
                    flag_payment_overdue = True
        if correction_invoice_to_update["status"] == 'ACCEPTED':
            acceptedAt = correction_invoice_to_update["acceptedAt"]
        else:
            acceptedAt = None
        if correction_invoice_to_update["status"] == 'ACCEPTED':
            flag_status = '1'
        else:
            flag_status = '0'
        
        correction_invoice_internal.supplier=correction_invoice_to_update['sourceName'] if 'sourceName' in correction_invoice_to_update else None
        correction_invoice_internal.supplier_fk=supplier
        correction_invoice_internal.number=correction_invoice_to_update['num']
        correction_invoice_internal.issue_date=correction_invoice_to_update['issueDate']
        correction_invoice_internal.destination=store
        correction_invoice_internal.acceptedAt=acceptedAt
        correction_invoice_internal.totalSum = Decimal(int(correction_invoice_to_update['totalSum']) / 100).quantize(Decimal('0.00'), rounding=ROUND_UP)
        if str(correction_invoice_internal.totalSum).split('.')[0].__len__() > 10:
            print("Sum is too long!")
            print("unable to update correction invoice", correction_invoice_to_update['id'], correction_invoice_to_update['num'])
            continue
        correction_invoice_internal.flag_status=flag_status
        correction_invoice_internal.flag_payment_type= True if "[НАЛ]" in correction_invoice_to_update['num'] else False
        correction_invoice_internal.flag_payment_overdue = flag_payment_overdue
        to_update.append(correction_invoice_internal)
    return to_update

def define_and_prep_document_positions_internal(document_id):
    external_doc = DREAM_KAS_API.get_document(id_document=document_id)
    internal_doc = Correction_invoice_v3.objects.filter(dreamkas_id=document_id)
    if internal_doc.__len__() == 0 or external_doc == False:
        from mainapp.Dreamkas_documents.update_documents import update_document
        update_document(document_id)
        return False,False,False
    internal_doc = internal_doc.first()
    parent_document_dreamkas_id = None
    if 'parentId' in external_doc:
        parent_document_dreamkas_id = external_doc['parentId']
    internal_doc.parent_document_dreamkas_id = parent_document_dreamkas_id
    internal_doc.save()
    i = 0
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    if Position_correction_invoice_v3.objects.filter(correction_invoice_v3_fk=internal_doc).all().__len__() > 0:
        positions_to_delete = internal_doc.position_correction_invoice_v3_set.filter(position_num__gt=external_doc['positions'].__len__() - 1)
        i = 0
        for position_external in external_doc['positions']:
            position_internal = Position_correction_invoice_v3.objects.filter(correction_invoice_v3_fk=internal_doc,position_num=i).first()
            if position_internal is None:
                break
            product_fk = Product.objects.filter(id_out=position_external['productId'])
            if product_fk.__len__() == 0:
                flag_found = False 
            else:
                product_fk = product_fk.first()
                flag_found = True
            position_amount = parse_number(position_external.get('amount'))
            position_price = parse_number(position_external.get('costWithTax'))
            position_sum = parse_number(position_external.get('sumCost'))
            position_internal.flag_found = flag_found
            position_internal.position_amount = position_amount  / 1000 if position_amount is not None else None
            position_internal.position_price = position_price / 100 if position_price is not None else None
            position_internal.position_sum = position_sum / 100 if position_sum is not None else None
            position_internal.position_name = position_external['name']
            position_internal.position_id = position_external['productId']
            positions_to_update.append(position_internal)
            i = i + 1
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
        position_price = parse_number(position_external.get('costWithTax'))
        position_sum = parse_number(position_external.get('sumCost'))
        
        position_to_create = Position_correction_invoice_v3(
            correction_invoice_v3_fk = internal_doc,
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
    return positions_to_create,positions_to_update,positions_to_delete

def update_correction_invoices(limit=1000,offset=None,acceptedAtFrom=None,accetpedAtTo=None,query=None):
    documents_external = DREAM_KAS_API.get_documents(limit=limit,query=query, offset=offset,document_type="7",acceptedAtFrom=acceptedAtFrom,acceptedAtTo=accetpedAtTo)
    print('Correction invoices fetched')
    draft_cleanup(documents_external)
    print('Draft cleanup done')
    internal_dreamkas_documents_map = get_map(Correction_invoice_v3,"dreamkas_id")
    correction_invoices_to_create,correction_invoices_to_update = define_correction_invoices_to_update_or_create(internal_dreamkas_documents_map,documents_external)
    print('Correction invoices to create and update defined')
    to_create = prep_correction_invoices_for_bulk_creation(correction_invoices_to_create)
    to_update = prep_correction_invoices_for_bulk_update(correction_invoices_to_update)
    print('Correction invoices to create and update prepared')
    Correction_invoice_v3.objects.bulk_create(to_create)
    Correction_invoice_v3.objects.bulk_update(to_update,['supplier','supplier_fk','number','issue_date','destination','totalSum','flag_status','flag_payment_overdue','acceptedAt','flag_payment_type'])
    print('Correction invoices created and updated')
    all_docs = correction_invoices_to_create + correction_invoices_to_update
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    j = 0
    
    for document in all_docs:
        if all_docs.__len__() > 10:
            if j % int(all_docs.__len__()*0.1) == 0:
                print("Updating_correction_invoices. Progress", j, "/", limit)
        else:
            print("Updating_correction_invoices. Progress", j, "/", limit)
        j = j + 1
        to_create,to_update,to_delete = define_and_prep_document_positions_internal(document['id'])
        if to_create is False:
            continue
        positions_to_create.extend(to_create)
        positions_to_update.extend(to_update)
        positions_to_delete.extend(to_delete)
    print('Positions to create and update defined')
    Position_correction_invoice_v3.objects.bulk_create(positions_to_create)
    print("created", positions_to_create.__len__(), "positions")
    Position_correction_invoice_v3.objects.bulk_update(positions_to_update,['flag_found','position_amount','position_price','position_sum','position_name','position_id'])
    i = 0
    for position in positions_to_delete:
        position.delete()
        i = i + 1
    print("deleted", i, "positions")
    print('Positions created and updated')
    all_doc_ids = []
    for doc in all_docs:
        all_doc_ids.append(doc['id'])
    return True,all_doc_ids

def update_correction_invoice(dreamkas_id):
    if type(dreamkas_id) == int or type(dreamkas_id) == str:
        document = DREAM_KAS_API.get_document(id_document=dreamkas_id)
    else:
        document = dreamkas_id
    if document is False:
        document_internal = fetch_document_object(dreamkas_id)
        document_internal.status = 2
        document_internal.save()
        return False
    correction_object = Correction_invoice_v3.objects.filter(dreamkas_id=dreamkas_id)
    create = False
    if correction_object.__len__() == 0:
        create = True
        correction_object = Correction_invoice_v3.objects.create(dreamkas_id=dreamkas_id)
    else:
        correction_object = correction_object.first()
        
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
        
    # Handle totalSum - corrections may not have totalSum
    if 'totalSum' in document:
        totalSum = Decimal(int(document['totalSum']) / 100).quantize(Decimal('0.00'), rounding=ROUND_UP)
    else:
        totalSum = Decimal('0.00')
        
    if str(totalSum).split('.')[0].__len__() > 10:
        print("Sum is too long!")
        print("unable to update correction invoice", dreamkas_id, document['num'])
        return False
        
    correction_object.totalSum = totalSum
    correction_object.supplier = document['sourceLegalEntity']['name'] if 'sourceLegalEntity' in document else None
    correction_object.supplier_fk = supplier
    correction_object.flag_payment_overdue = flag_payment_overdue
    correction_object.flag_payment_type = True if "[НАЛ]" in document['num'] else False
    correction_object.number = document['num']
    correction_object.issue_date = document['issueDate']
    correction_object.destination = store
    correction_object.acceptedAt = acceptedAt
    correction_object.flag_status = status_to_flag(document['status'])
    
    # Handle parent document
    if 'parentId' in document:
        correction_object.parent_document_dreamkas_id = document['parentId']

    if create:
        correction_object.flag_paid = False

    correction_object.save()
    
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    to_create, to_update, to_delete = define_and_prep_document_positions_internal(document['id'])
    if to_create is False:
        return False
    positions_to_create.extend(to_create)
    positions_to_update.extend(to_update)
    positions_to_delete.extend(to_delete)
    
    Position_correction_invoice_v3.objects.bulk_create(positions_to_create)
    Position_correction_invoice_v3.objects.bulk_update(positions_to_update, ['flag_found','position_amount','position_price','position_sum','position_name','position_id'])
    
    for position in positions_to_delete:
        position.delete()
    find_latest_document_iteration(dreamkas_id)

    return True