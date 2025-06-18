from mainapp import global_var
from mainapp.models import Outcome_order_v3,position_outcome_order_v3,Product
from dremkas.settings import DREAM_KAS_API
from mainapp.Dreamkas_documents.draft_cleanup import draft_cleanup
from mainapp.Dreamkas_documents.funcs import get_map, parse_number, status_to_flag
from mainapp.Dreamkas_documents.stores import fetch_or_create_store
from decimal import Decimal, ROUND_UP

def define_outcome_orders_to_update_or_create(internal_dreamkas_documents_map,external_documents):
    outcome_orders_to_create =[]
    outcome_orders_to_update =[]
    for external_document in external_documents:
        if int(external_document['id']) not in internal_dreamkas_documents_map:
            outcome_orders_to_create.append(external_document)
            continue
        outcome_orders_to_update.append(external_document)
    return outcome_orders_to_create,outcome_orders_to_update

def prep_outcome_orders_for_bulk_creation(outcome_orders_to_create):
    to_create = []
    for outcome_order_to_create in outcome_orders_to_create:
        store = None
        if "targetStoreId" in outcome_order_to_create:
            store = fetch_or_create_store(outcome_order_to_create['targetStoreId'])
        # Map status to flag_status using the utility function
        flag_status = status_to_flag(outcome_order_to_create["status"])
        
        invoice_new = Outcome_order_v3(
            dreamkas_id=outcome_order_to_create['id'],
            number=outcome_order_to_create['num'],
            issue_date=outcome_order_to_create['issueDate'],
            destination=store,
            flag_status=flag_status,
        )
        to_create.append(invoice_new)
    return to_create

def prep_outcome_orders_for_bulk_update(outcome_orders_to_update):
    to_update = []
    for outcome_order_to_update in outcome_orders_to_update:
        store = None
        outcome_order_internal = Outcome_order_v3.objects.filter(dreamkas_id=outcome_order_to_update['id'])
        if outcome_order_internal.__len__() == 0:
            print("Error. Outcome order that needs to be updated is not found")
            print(outcome_order_internal)
            print("Error End.")
            continue
        outcome_order_internal = outcome_order_internal.first()      
        if "targetStoreId" in outcome_order_to_update:
            store = fetch_or_create_store(outcome_order_to_update['targetStoreId'])
        # Map status to flag_status using the utility function
        flag_status = status_to_flag(outcome_order_to_update["status"])
        
        outcome_order_internal.destination=store
        outcome_order_internal.number=outcome_order_to_update['num']
        outcome_order_internal.issue_date=outcome_order_to_update['issueDate']
        outcome_order_internal.flag_status=flag_status
        to_update.append(outcome_order_internal)
    return to_update

def define_and_prep_document_positions_internal(document_id):
    to_create = []
    to_update = []
    to_delete = []
    external_doc = DREAM_KAS_API.get_document(id_document=document_id)
    internal_doc = Outcome_order_v3.objects.filter(dreamkas_id=document_id)
    if internal_doc.__len__() == 0:
        ##TODO: error handling.
        return False
    internal_doc = internal_doc.first()
    i = 0
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    if position_outcome_order_v3.objects.filter(outcome_order_v3_fk=internal_doc).all().__len__() > 0:
        positions_to_delete = internal_doc.position_outcome_order_v3_set.filter(position_num__gt=external_doc['positions'].__len__() - 1)
        i = 0
        for position_external in external_doc['positions']:
            position_internal = position_outcome_order_v3.objects.filter(outcome_order_v3_fk=internal_doc,position_num=i).first()
            if position_internal is None:
                break
            product_fk = Product.objects.filter(id_out=position_external['productId'])
            if product_fk.__len__() == 0:
                flag_found = False 
            else:
                product_fk = product_fk.first()
                flag_found = True
            position_amount = parse_number(position_external.get('amount'))
            position_internal.flag_found = flag_found
            position_internal.position_amount = position_amount  / 1000 if position_amount is not None else None
            position_internal.position_name = position_external['name']
            position_internal.position_id = position_external['productId']
            positions_to_update.append(position_internal)
            # if global_var.debug is True:
            #     print(position_internal.position_num, '|',position_internal.position_name)
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
        
        position_to_create = position_outcome_order_v3(
            outcome_order_v3_fk = internal_doc,
            flag_found = flag_found,
            position_name = position_external['name'],
            position_num = j,
            position_id = position_external['productId'] if 'productId' in position_external else None,
            position_amount = position_amount / 1000 if position_amount is not None else None,
        )
        positions_to_create.append(position_to_create)
        j = j + 1
    return positions_to_create,positions_to_update,positions_to_delete

def update_outcome_orders(limit=1000,offset=None):
    documents_external = DREAM_KAS_API.get_documents(limit=limit, offset=offset,document_type='4')
    draft_cleanup(documents_external)
    internal_dreamkas_documents_map = get_map(Outcome_order_v3,"dreamkas_id")
    outcome_orders_to_create = []
    outcome_orders_to_update = []
    outcome_orders_to_create,outcome_orders_to_update = define_outcome_orders_to_update_or_create(internal_dreamkas_documents_map,documents_external)
    to_create = prep_outcome_orders_for_bulk_creation(outcome_orders_to_create)
    to_update = prep_outcome_orders_for_bulk_update(outcome_orders_to_update)
    Outcome_order_v3.objects.bulk_create(to_create)
    Outcome_order_v3.objects.bulk_update(to_update,['number','issue_date','destination','flag_status'])
    all_docs = outcome_orders_to_create + outcome_orders_to_update
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    j = 0
    for outcome_order in all_docs:
        if all_docs.__len__() > 10:
            if j % int(all_docs.__len__()*0.1) == 0:
                print("Updating_outcome_orders. Progress", j, "/", limit)
        else:
            print("Updating_outcome_orders. Progress", j, "/", limit)
        j = j + 1
        to_create,to_update,to_delete = define_and_prep_document_positions_internal(outcome_order['id'])
        positions_to_create.extend(to_create)
        positions_to_update.extend(to_update)
        positions_to_delete.extend(to_delete)
    position_outcome_order_v3.objects.bulk_create(positions_to_create)
    position_outcome_order_v3.objects.bulk_update(positions_to_update,['flag_found','position_amount','position_name','position_id'])
    for position in positions_to_delete:
        position.delete()
        i = i + 1