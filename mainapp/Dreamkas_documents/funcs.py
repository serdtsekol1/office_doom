from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object
from mainapp.Dreamkas_products.Products import update_product
from mainapp.models import Product
def define_if_document_is_invalid(document_id):
    a()
    
    def a():
        return
def status_to_flag(status):
    """
    Convert status string to flag_status numeric value
    # 0 - Draft
    # 1 - Accepted
    # 2 - Deleted
    # 3 - Rejected
    """
    status_mapping = {
        'ACCEPTED': 1,
        'DRAFT': 0,
        'DELETED': 2,
        'REJECTED': 3
    }
    return status_mapping.get(status, 0)  # Default to 0 (Draft) if status not found

def calculate_profit(document_id=None, document_object=None, document=None,flag_ignore_non_priced_positions=False):
    from mainapp.Dreamkas_documents.fetch_document_object import fetch_documents_positions
    # 0 - Can't calculate profit
    # 1 - Profit calculated
    # 2 - Pricing order's positions do not match with invoice's positions
    # 3 - Positions are missing
    if document_object is not None:
        document_id = document_object.id_dreem
    if document is not None:
        document_id = document['id']
    if document_id is None:
        return False,False
    initial_invoice = fetch_document_object(document_id)
    latest_iteration = find_latest_document_iteration(document_id)
    if latest_iteration is None:
        print("Latest iteration not found for id: ",document_id)
        return False,False
    print(latest_iteration)
    if latest_iteration['latest_pricing'] is None:
        return False,False
    invoice = fetch_document_object(initial_invoice.latest_iteration_id)
    pricing = fetch_document_object(initial_invoice.latest_pricing_id)
    if pricing.flag_invalid is True or invoice.flag_invalid is True:
        return 0 , None
    invoice_positions = fetch_documents_positions(document_id=invoice.dreamkas_id)
    pricing_positions = fetch_documents_positions(document_id=pricing.dreamkas_id)
    if invoice_positions == None:
        return 3, latest_iteration['latest_invoice']
    if pricing_positions == None:
        return 3, latest_iteration['latest_pricing']
    non_priced_positions = []
    total_profit = 0
    total_income = 0
    
    for invoice_position in invoice_positions:
        found = False
        product_object = Product.objects.filter(id_out=invoice_position.position_id)
        if invoice_position is None:
            print("Invoice position is None",document_id)
            return 0
        if product_object.__len__() == 0:
            update_product(invoice_position.position_id)
            product_object = Product.objects.filter(id_out=invoice_position.position_id)
            if product_object.__len__() == 0:
                continue
        if Product.objects.filter(id_out=invoice_position.position_id).first().flag_ignore_on_pricing is True:
            continue
        for pricing_position in pricing_positions:
            if str(invoice_position.position_id) == str(pricing_position.position_id):
                found = True
                try:
                    income = pricing_position.position_price_new * invoice_position.position_amount
                    if income < 0:
                        invoice_position.flag_negative_income = True
                    else:
                        invoice_position.flag_negative_income = False
                    profit = income - invoice_position.position_sum
                    invoice_position.position_profit = profit
                    invoice_position.position_income = income
                    invoice_position.save()
                    total_profit += profit
                    total_income += income
                    break
                except Exception as e:
                    invoice.flag_invalid = True
                    pricing.flag_invalid = True
                    invoice.flag_invalid_reason = "Что-то не так с накладной или расценкой накладной или их позициями - невозможно рассчитать прибыль"
                    pricing.flag_invalid_reason = "Что-то не так с накладной или расценкой накладной или их позициями - невозможно рассчитать прибыль"
                    invoice.save()
                    pricing.save()
                    print("Что-то не так с накладной", invoice.dreamkas_id, "И \ или Расценкой", pricing.dreamkas_id, "При расценке позиции", invoice_position.position_name)
        if found:
            continue
        non_priced_positions.append(invoice_position)

    if len(non_priced_positions) > 0:
        if flag_ignore_non_priced_positions:
                invoice.profit = total_profit
                invoice.income = total_income
                invoice.save()
                return 1,None
        invoice.flag_invalid = True
        pricing.flag_invalid = True
        invoice.flag_invalid_reason = "Что-то не так с накладной или расценкой накладной или их позициями - невозможно рассчитать прибыль"
        pricing.flag_invalid_reason = "Что-то не так с накладной или расценкой накладной или их позициями - невозможно рассчитать прибыль"
        invoice.save()
        pricing.save()
        return 2,None
    initial_invoice.profit = total_profit
    initial_invoice.income = total_income
    initial_invoice.save()
    invoice.profit = total_profit
    invoice.income = total_income
    invoice.save()
    return 1,None

    
def fetch_children_of_document(document_id=None, document_object=None, document=None):
    from mainapp.models import Correction_invoice_v3, Pricing_order_v3, Outcome_order_v3
    
    if document_object is not None:
        document_id = document_object.id_dreem
    if document is not None:
        document_id = document['id']
    if document_id is None:
        return False
    # Get all documents that have this ID as a parent document. All classes(correction,pricing,outcome)
    correction_children = Correction_invoice_v3.objects.filter(parent_document_dreamkas_id=document_id)
    pricing_children = Pricing_order_v3.objects.filter(parent_document_dreamkas_id=document_id)
    outcome_children = Outcome_order_v3.objects.filter(parent_document_dreamkas_id=document_id)
    return correction_children,pricing_children,outcome_children

def fetch_all_ids_of_tree(document_id=None, document_object=None, document=None):
    if document_object is not None:
        document_id = document_object.id_dreem
    if document is not None:
        document_id = document['id']
    if document_id is None:
        return []
    document_tree = build_tree_of_documents(document_id)
    if not document_tree:
        return []
    all_ids = []
    def collect_ids(doc_structure):
        if doc_structure is None:
            return
        all_ids.append(doc_structure['id'])
        for child in doc_structure['children']:
            collect_ids(child)
    
    # Always start from the root of the tree (first key in document_tree)
    root_doc_id = list(document_tree.keys())[0]
    root_doc = document_tree[root_doc_id]
    collect_ids(root_doc)
    return all_ids

def build_tree_of_documents(document_id=None, document_object=None, document=None):
    # Initialize dictionary to store the document tree
    document_tree = {}
    processed_ids = set()  # Track processed document IDs to prevent cycles
    
    # Get initial document ID
    if document_object is not None:
        document_id = document_object.id_dreem
    elif document is not None:
        document_id = document['id']
    
    if not document_id:
        return {}
    
    def create_document_structure(doc_id, parent_id=None):
        if doc_id in processed_ids:
            return None
            
        processed_ids.add(doc_id)
        
        try:
            # Get the document object to determine its type
            doc_object = fetch_document_object(doc_id)
            if doc_object is None:
                return None
                
            # Initialize document structure
            doc_structure = {
                'id': doc_id,
                'document_type': None,
                'children': [],
                'parent': parent_id
            }
            
            # Set document type based on the document object's class
            if doc_object.__class__.__name__ == 'Invoice_v3':
                doc_structure['document_type'] = 'Invoice'
            elif doc_object.__class__.__name__ == 'Correction_invoice_v3':
                doc_structure['document_type'] = 'Invoice Correction'
            elif doc_object.__class__.__name__ == 'Pricing_order_v3':
                doc_structure['document_type'] = 'Pricing Order'
            elif doc_object.__class__.__name__ == 'Outcome_order_v3':
                doc_structure['document_type'] = 'Outcome Order'
            
            # Get children
            correction_children, pricing_children, outcome_children = fetch_children_of_document(document_id=doc_id)
            
            # Process correction children
            for doc in correction_children:
                child_structure = create_document_structure(doc.dreamkas_id, doc_id)
                if child_structure:
                    doc_structure['children'].append(child_structure)
            
            # Process pricing children
            for doc in pricing_children:
                child_structure = create_document_structure(doc.dreamkas_id, doc_id)
                if child_structure:
                    doc_structure['children'].append(child_structure)
            
            # Process outcome children
            for doc in outcome_children:
                child_structure = create_document_structure(doc.dreamkas_id, doc_id)
                if child_structure:
                    doc_structure['children'].append(child_structure)
            
            return doc_structure
                    
        except Exception as e:
            print(f"Error processing document {doc_id}: {str(e)}")
            return None
    
    # Start building the tree from the root document
    root_structure = create_document_structure(document_id)
    if root_structure:
        document_tree[document_id] = root_structure
    
    return document_tree

def find_latest_document_iteration(document_id=None, document_object=None, document=None):
    if document_object is not None:
        document_id = document_object.id_dreem
    if document is not None:
        document_id = document['id']
    if document_id is None:
        return False
    initial_invoice = fetch_document_object(document_id)
    document_tree = build_tree_of_documents(document_id)
    if not document_tree:
        return None
        
    # Get the root document
    root_doc = document_tree[document_id]
    
    # First find the latest invoice/correction
    latest_invoice = None
    latest_invoice_id = None
    
    def find_latest_invoice(doc_structure):
        nonlocal latest_invoice, latest_invoice_id
        
        # Check if current document is an invoice or correction
        if doc_structure['document_type'] in ['Invoice', 'Invoice Correction']:
            doc_object = fetch_document_object(doc_structure['id'])
            if doc_object:
                # For invoice, check if it has any accepted corrections
                if doc_structure['document_type'] == 'Invoice':
                    has_accepted_corrections = False
                    for child in doc_structure['children']:
                        if child['document_type'] == 'Invoice Correction':
                            child_doc = fetch_document_object(child['id'])
                            if child_doc and child_doc.flag_status == '1':  # 1 = ACCEPTED
                                has_accepted_corrections = True
                                break
                    
                    # If no accepted corrections, this is the latest
                    if not has_accepted_corrections:
                        latest_invoice = doc_object
                        latest_invoice_id = doc_structure['id']
                
                # For correction, check if it's accepted and has higher ID
                elif doc_structure['document_type'] == 'Invoice Correction':
                    if doc_object.flag_status == '1':  # 1 = ACCEPTED
                        if latest_invoice_id is None or str(doc_structure['id']) > str(latest_invoice_id):
                            latest_invoice = doc_object
                            latest_invoice_id = doc_structure['id']
        
        # Recursively check children
        for child in doc_structure['children']:
            find_latest_invoice(child)
    
    # Find latest invoice/correction
    find_latest_invoice(root_doc)
    
    if not latest_invoice:
        return None
    
    # Now find the latest pricing order for the latest invoice
    latest_pricing = None
    latest_pricing_id = None
    
    def find_latest_pricing(doc_structure):
        nonlocal latest_pricing, latest_pricing_id
        
        # Check if current document is a pricing order
        if doc_structure['document_type'] == 'Pricing Order':
            doc_object = fetch_document_object(doc_structure['id'])
            if doc_object and doc_object.flag_status == '1':  # 1 = ACCEPTED
                # Check if this pricing order is linked to the latest invoice
                if str(doc_object.parent_document_dreamkas_id) == str(latest_invoice_id):
                    if latest_pricing_id is None or str(doc_structure['id']) > str(latest_pricing_id):
                        latest_pricing = doc_object
                        latest_pricing_id = doc_structure['id']
        
        # Recursively check children
        for child in doc_structure['children']:
            find_latest_pricing(child)
    
    # Find latest pricing order
    find_latest_pricing(root_doc)
    initial_invoice.latest_iteration_id = latest_invoice.dreamkas_id if latest_invoice is not None else None
    initial_invoice.latest_pricing_id = latest_pricing.dreamkas_id if latest_pricing is not None else None
    initial_invoice.save()
    return {
        'latest_invoice': latest_invoice,
        'latest_pricing': latest_pricing
    }

def parse_number(value):
    if value is None:
        return None
    try:
        # First try to convert to float directly
        return float(value)
    except (ValueError, TypeError):
        try:
            # If that fails, try replacing comma with dot
            return float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            return None

def get_map(model,whattomap):
    map = []
    for item in model.objects.all():
        exec("map.append(item." + whattomap + ")")
    return map
