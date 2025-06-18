from datetime import datetime, timedelta
from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object, fetch_documents_positions
from mainapp.Dreamkas_documents.draft_cleanup import draft_cleanup, pricing_order_draft_cleanup
from dremkas.settings import DREAM_KAS_API

from mainapp.Dreamkas_documents.suppliers import fetch_or_create_supplier
from mainapp.Dreamkas_documents.update_invoices import update_invoice
from mainapp.models import Pricing_order_v3, Position_pricing_order_v3, Product
from mainapp.Dreamkas_documents.funcs import get_map, parse_number, status_to_flag, find_latest_document_iteration
from mainapp.Dreamkas_documents.stores import fetch_or_create_store
from decimal import ROUND_UP, Decimal
from mainapp import global_var


def update_pricing_order(dreamkas_id):
    if type(dreamkas_id) == int or type(dreamkas_id) == str:
        document = DREAM_KAS_API.get_document(id_document=dreamkas_id)
    else:
        document = dreamkas_id
    if document is False or document['status'] == 404:
        document_internal = fetch_document_object(dreamkas_id)
        document_internal.status = 2
        document_internal.save()
        return False
    pricing_order_object = Pricing_order_v3.objects.filter(dreamkas_id=dreamkas_id)
    create = False
    if pricing_order_object.__len__() == 0:
        create = True
        pricing_order_object = Pricing_order_v3.objects.create(dreamkas_id=dreamkas_id)
    else:
        pricing_order_object = pricing_order_object.first()
        
    store = None
    if "targetStoreId" in document:
        store = fetch_or_create_store(document['targetStoreId'])
        
                
    if document["status"] == 'ACCEPTED':
        acceptedAt = document["acceptedAt"]
    else:
        acceptedAt = None
        
        

    pricing_order_object.number = document['num']
    pricing_order_object.issue_date = document['issueDate']
    pricing_order_object.destination = store
    pricing_order_object.acceptedAt = acceptedAt
    pricing_order_object.flag_status = status_to_flag(document['status'])
    
    # Handle parent document
    if 'parentId' in document:
        pricing_order_object.parent_document_dreamkas_id = document['parentId']

    if create:
        pricing_order_object.flag_paid = False

    pricing_order_object.save()
    
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    success, to_create, to_update, to_delete = define_and_prep_document_positions_internal_and_get_parent_document(document['id'])
    if success is False:
        return False
    positions_to_create.extend(to_create)
    positions_to_update.extend(to_update)
    positions_to_delete.extend(to_delete)
    
    Position_pricing_order_v3.objects.bulk_create(positions_to_create)
    Position_pricing_order_v3.objects.bulk_update(positions_to_update, ['flag_found','position_price_old','position_price_new','position_name','position_id','product_fk'])
    
    for position in positions_to_delete:
        position.delete()
    find_latest_document_iteration(dreamkas_id)
        
    return True

def create_pricing_order(dreamkas_id,leave_prices=False):
    document = fetch_document_object(dreamkas_id)
    positions = fetch_documents_positions(document)
    targetStoreId = document.destination.store_id
    positions_new = []

    data = {"products": [], "useMrp": True}
    for pos in positions:
        data["products"].append({"id": pos.position_id})
    original_positions = DREAM_KAS_API.session.post("https://kabinet.dreamkas.ru/api/v2/products/find", json=data).json()
    ## Get priceRef
    original_amounts = []
    original_prices = []
    for original_position in original_positions:
        old_price = None
        original_amount = None
        for price in original_position['prices']:
            if price['shopId'] == targetStoreId:
                old_price = price['price']
                break
        original_prices.append({'id':original_position['id'],"priceRef":old_price})
        for stock in original_position['stock']:
            if stock[0] == targetStoreId:
                original_amount = stock[1]
                break
        original_amounts.append({'id':original_position['id'],'amount':original_amount})
    
    ## Get position amounts
    
    if leave_prices == False:
        prices_new = price_document_positions(positions=positions)
    
    for position in positions:
        priceRef = None
        for original_price in original_prices:
            if position.position_id == original_price["id"]:
                priceRef = original_price["priceRef"]
                if leave_prices == True:
                    price = original_price["priceRef"]
                break

        if leave_prices == False:
            price = None
            for new_price in prices_new:
                if position.position_id == new_price["id"]:
                    price = new_price["price"]
                    break
                
        positions_new.append({
                                "productId":position.position_id, 
                                "name":position.position_name,
                                "price":price if price else 0,
                                "priceRef":priceRef if priceRef else 0,
                                "costWithTax":None,
                                'amount':original_amount if original_amount else 0,
                                'amountRef':original_amount if original_amount else 0,
                              })
    pricing_order_draft_cleanup(dreamkas_id)
    resp = DREAM_KAS_API.create_pricing_order_v2(
        targetStoreId=targetStoreId,positions=positions_new,parentId=dreamkas_id,partnerId=None)

    print(resp)
    

    
def price_document_positions(dreamkas_id=None,document_object=None,positions=None):
    from mainapp.models import GoodGroups
    if dreamkas_id == None and positions == None and document_object == None:
        return 2
    if dreamkas_id:
        positions = fetch_documents_positions(fetch_document_object(dreamkas_id))
    if document_object:
        positions = fetch_documents_positions(document_object)
    new_prices = []
    for position in positions:
        
        Product_obj = Product.objects.filter(id_out=positions[0].position_id)
        if not Product_obj:
            from mainapp.Dreamkas_products.Products import update_product
            update_product(position.position_id)
        Product_obj = Product.objects.filter(id_out=positions[0].position_id).first()
        
        good_group_obj = GoodGroups.objects.filter(group_id=Product_obj.group_id)
        if not good_group_obj:
            GoodGroups.update_good_groups()
        good_group_obj = GoodGroups.objects.filter(group_id=Product_obj.group_id).first()
        if good_group_obj.roundnumber == 0 or good_group_obj.pricingpercent == 0 or good_group_obj.rule == 0:
                    new_prices.append({'id':position.position_id,'price':0})
        new_price =float(position.position_price) * (1 + good_group_obj.pricingpercent/100)
        
        threshold = good_group_obj.roundnumber * (good_group_obj.rule / 100)
        lower_bound = (new_price // good_group_obj.roundnumber) * good_group_obj.roundnumber
        upper_bound = lower_bound + good_group_obj.roundnumber
        new_price = lower_bound if new_price < (lower_bound + threshold) else upper_bound

        new_prices.append({'id':position.position_id,'price':new_price*100})
    return new_prices


def define_and_prep_document_positions_internal_and_get_parent_document(document_id):
    external_doc = DREAM_KAS_API.get_document(id_document=document_id)
    if external_doc == False:
        return False, None, None, None
    internal_doc = Pricing_order_v3.objects.filter(dreamkas_id=document_id)
    parent_document_dreamkas_id = None
    if 'parentId' in external_doc:
        parent_document_dreamkas_id = external_doc['parentId']
    if internal_doc.__len__() == 0:
        return False, None,None,None
    internal_doc = internal_doc.first()
    internal_doc.parent_document_dreamkas_id = parent_document_dreamkas_id
    internal_doc.save()
    i = 0
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    if Position_pricing_order_v3.objects.filter(pricing_order_v3_fk=internal_doc).all().__len__() > 0:
        positions_to_delete = internal_doc.position_pricing_order_v3_set.filter(position_num__gt=external_doc['positions'].__len__() - 1)
        for position_external in external_doc['positions']:
            position_internal = Position_pricing_order_v3.objects.filter(pricing_order_v3_fk=internal_doc,position_num=i).first()
            if position_internal is None:
                break
            product_fk = Product.objects.filter(id_out=position_external['productId'])
            if product_fk.__len__() == 0:
                flag_found = False 
            else:
                product_fk = product_fk.first()
                flag_found = True
            position_price_old =  parse_number(position_external.get('priceRef'))
            position_price_new = parse_number(position_external.get('price'))
            position_internal.position_id = position_external['productId']
            position_internal.position_name = position_external['name']
            position_internal.position_price_old = position_price_old / 100 if position_price_old is not None else None
            position_internal.position_price_new = position_price_new / 100 if position_price_new is not None else None
            position_internal.flag_found = flag_found
            position_internal.product_fk = product_fk if flag_found is True else None
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

        position_price_old =  parse_number(position_external.get('priceRef'))
        position_price_new = parse_number(position_external.get('price'))
        position_to_create = Position_pricing_order_v3(
            pricing_order_v3_fk = internal_doc,
            flag_found = flag_found,
            product_fk = product_fk if flag_found is True else None,
            position_name = position_external['name'],
            position_num = j,
            position_id = position_external['productId'] if 'productId' in position_external else None,
            position_price_old = position_price_old / 100 if position_price_old is not None else None,
            position_price_new = position_price_new / 100 if position_price_new is not None else None
        )
        positions_to_create.append(position_to_create)
        j = j + 1
    return True,positions_to_create,positions_to_update,positions_to_delete
        
    
def define_pricing_orders_to_update_or_create(internal_dreamkas_documents_map,external_documents):
    pricing_orders_to_create =[]
    pricing_orders_to_update =[]
    for external_document in external_documents:
        if int(external_document['id']) not in internal_dreamkas_documents_map:
            pricing_orders_to_create.append(external_document)
            continue
        pricing_orders_to_update.append(external_document)
    return pricing_orders_to_create,pricing_orders_to_update

def prep_pricing_orders_for_bulk_creation(pricing_orders_to_create):
    to_create = []
    for pricing_order_to_create in pricing_orders_to_create:
        store = None
        if "targetStoreId" in pricing_order_to_create:
            store = fetch_or_create_store(pricing_order_to_create['targetStoreId'])
        if pricing_order_to_create["status"] == 'ACCEPTED':
            acceptedAt = pricing_order_to_create["acceptedAt"]
        else:
            acceptedAt = None
            
        # Map status to flag_status using the utility function
        flag_status = status_to_flag(pricing_order_to_create["status"])
        
        pricing_order_new = Pricing_order_v3(
            dreamkas_id=pricing_order_to_create['id'],
            number=pricing_order_to_create['num'],
            issue_date=pricing_order_to_create['issueDate'],
            destination=store,
            acceptedAt=acceptedAt,
            flag_status=flag_status,
        )
        if global_var.debug is True:
            print(pricing_order_new.number,'|' ,pricing_order_new.issue_date, pricing_order_new.destination, pricing_order_new.flag_status)
        to_create.append(pricing_order_new)
    return to_create


def prep_pricing_orders_for_bulk_update(pricing_orders_to_update):
    to_update = []
    for pricing_order_to_update in pricing_orders_to_update:
        store = None
        pricing_order_internal = Pricing_order_v3.objects.filter(dreamkas_id=pricing_order_to_update['id'])
        if pricing_order_internal.__len__() == 0:
            print("Error. Pricing order that needs to be updated is not found")
            print(pricing_order_internal)
            print("Error End.")
            continue
        pricing_order_internal = pricing_order_internal.first()      
        if pricing_order_to_update["status"] == 'ACCEPTED':
            acceptedAt = pricing_order_to_update["acceptedAt"]
        else:
            acceptedAt = None
            
        # Map status to flag_status using the utility function
        flag_status = status_to_flag(pricing_order_to_update["status"])
        
        if "targetStoreId" in pricing_order_to_update:
            store = fetch_or_create_store(pricing_order_to_update['targetStoreId'])
        pricing_order_internal.number=pricing_order_to_update['num']
        pricing_order_internal.issue_date=pricing_order_to_update['issueDate']
        pricing_order_internal.destination=store
        pricing_order_internal.flag_status=flag_status
        pricing_order_internal.acceptedAt=acceptedAt        
        to_update.append(pricing_order_internal)
    return to_update



def update_pricing_orders(limit=250,offset=None,acceptedAtFrom=None,accetpedAtTo=None,query=None):
    documents_external = DREAM_KAS_API.get_documents(limit=limit,query=query, offset=offset,document_type="11",acceptedAtFrom=acceptedAtFrom,acceptedAtTo=accetpedAtTo)
    draft_cleanup(documents_external)
    internal_dreamkas_pricing_orders_map = get_map(Pricing_order_v3,"dreamkas_id")
    pricing_orders_to_create,pricing_orders_to_update = define_pricing_orders_to_update_or_create(internal_dreamkas_pricing_orders_map,documents_external)
    to_create = prep_pricing_orders_for_bulk_creation(pricing_orders_to_create)
    print('Pricing orders to create prepared')
    to_update = prep_pricing_orders_for_bulk_update(pricing_orders_to_update)
    print('Pricing orders to update prepared')
    Pricing_order_v3.objects.bulk_create(to_create)
    print(pricing_orders_to_create.__len__(),'Pricing orders created')
    Pricing_order_v3.objects.bulk_update(to_update,['number','issue_date','destination','flag_status'])
    all_docs = pricing_orders_to_create + pricing_orders_to_update
    positions_to_create = []
    positions_to_update = []
    positions_to_delete = []
    j = 0
    for document in all_docs:
        if all_docs.__len__() > 10:
            if j % int(all_docs.__len__()*0.1) == 0:
                print("Updating pricing orders. Progress", j, "/", limit)
        else:
            print("Updating pricing orders. Progress", j, "/", limit)
        j = j + 1
        completion_flag,to_create,to_update,to_delete = define_and_prep_document_positions_internal_and_get_parent_document(document['id'])
        if completion_flag is False:
            continue
        positions_to_create.extend(to_create)
        positions_to_update.extend(to_update)
        positions_to_delete.extend(to_delete)
    print('Positions to create and update defined')
    Position_pricing_order_v3.objects.bulk_create(positions_to_create)
    print("created", positions_to_create.__len__(), "positions")
    Position_pricing_order_v3.objects.bulk_update(positions_to_update,['flag_found','position_price_old','position_price_new','position_name','position_id','product_fk'])
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
    
def create_blank_pricing_if_not_priced_for_long(dreamkas_id,accept=True,ignore_accept_date=False):
    from mainapp.Dreamkas_documents.update_documents import update_document
    initial_id = dreamkas_id
    invoice = fetch_document_object(dreamkas_id=dreamkas_id)
    if invoice.dreamkas_id != invoice.latest_iteration_id:
        invoice = fetch_document_object(dreamkas_id=invoice.latest_iteration_id)
    if ignore_accept_date == True:
        delta = 0
    else:
        delta = 1
    if (
        invoice.flag_status == '1' and  # 1 = ACCEPTED
        invoice.latest_pricing_id == None and
        invoice.acceptedAt != None and
        datetime.now().date() >= invoice.acceptedAt + timedelta(days=delta) and
        (invoice.flag_invalid == False or (invoice.flag_invalid == True and invoice.flag_invalid_fixed == True))
    ):
    
        failsafe_resp=DREAM_KAS_API.get_document(dreamkas_id)
        for child_doc in failsafe_resp['children']:
            child_obj = fetch_document_object(child_doc['id'])
            if child_obj.__class__.__name__ == 'Pricing_order_v3' and child_obj.flag_status == '1' and invoice.latest_pricing_id == None and invoice.latest_pricing_id == None:
                update_document(invoice.dreamkas_id)
                invoice = fetch_document_object(dreamkas_id=dreamkas_id)
                if invoice.dreamkas_id != invoice.latest_iteration_id:
                    invoice = fetch_document_object(dreamkas_id=invoice.latest_iteration_id)
                if invoice.latest_pricing_id != None:
                    return
            if child_obj == None:
                # Import locally to avoid circular dependency

                update_document(child_doc['id'])
                update_document(invoice.dreamkas_id)
                invoice = fetch_document_object(dreamkas_id=dreamkas_id)
                if invoice.dreamkas_id != invoice.latest_iteration_id:
                    invoice = fetch_document_object(dreamkas_id=invoice.latest_iteration_id)
                if invoice.latest_pricing_id != None:
                    return True, None
                child_obj = fetch_document_object(child_doc['id'])
                if child_obj == None:
                    invoice.flag_invalid = True
                    invoice.flag_invalid_reason = 'Программа не может распознать документы привязанные к накладной. Обратитесь к Администратору.'
                    invoice.save()
        resp = DREAM_KAS_API.create_pricing_order(parentId=invoice.dreamkas_id,leave_prices=True,parent_document=failsafe_resp)
        if resp == -1:
            invoice.flag_invalid = True
            invoice.flag_invalid_reason = 'В Накладной позиции на устройство на которой либо нет предыдущей цены, либо нет предыдущей цены на устройство. Возможно устройство было удалено либо в накладной новые товары.'
            invoice.save()
        if resp == -2:
            invoice.flag_invalid = True
            invoice.flag_invalid_reason = 'Накладная не была расценена автоматически. Расцените вручную.'
            invoice.save()
        if resp == -1 or resp == -2:
            for child_doc in failsafe_resp['children']:
                DREAM_KAS_API.delete_document(child_doc['id'])
            return 2,None
        print('https://kabinet.dreamkas.ru/app/#!/documents/card~2F' + resp['id'])
        print('https://kabinet.dreamkas.ru/app/#!/documents/card~2F' + resp['parentId'])
        if 'id' in resp:
            if accept == True:
                resp_2 = DREAM_KAS_API.accept_document(resp['id'])
                if resp_2.status_code == 200:
                    invoice.auto_priced_unchanged = True
                    invoice.save()
                    update_pricing_order(dreamkas_id=resp['id'])
                    document = fetch_document_object(dreamkas_id=resp['id'])
                    document.auto_priced_unchanged = True
                    document.save()
                    update_invoice(initial_id)
                    print(resp_2)
                    
    else:
        print(('ПОДТВЕРЖДЕНА' if invoice.flag_status == '1' else 'ЧЕРНОВИК'),'|',invoice.latest_pricing_id if invoice.latest_pricing_id else "Нету Расценки",'|',invoice.acceptedAt if invoice.acceptedAt else "None",'|',f'ПРОШЛО {datetime.now().date() - invoice.acceptedAt + timedelta(days=1)} дней' if invoice.acceptedAt else "None" + '- НЕ РАСЦЕНЕНА')
    return 1, None