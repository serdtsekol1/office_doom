def fetch_latest_iterations_for_documents(dreamkas_ids):
    """
    Fetch the latest iteration for each document in the list of dreamkas_ids
    If the document is not found in the latest iteration, return the initial document
    Args:
        dreamkas_ids (list): List of dreamkas_ids or QuerySet of objects.
    Returns:
        list: List of documents
    """
    if str(type(dreamkas_ids)) != "<class 'django.db.models.query.QuerySet'>": 
        initial_documents = fetch_document_object_bulk(dreamkas_ids)
    else:
        initial_documents = dreamkas_ids
    final_list = []
    for document in initial_documents:
        if document.latest_iteration_id != document.dreamkas_id:
            final_list.append(document.latest_iteration_id)
        else:
            final_list.append(document.dreamkas_id)
    final_list = fetch_document_object_bulk(final_list)
    return final_list
    

def fetch_document_object_bulk(dreamkas_ids):    
    from mainapp.models import Invoice_v3, Pricing_order_v3, Correction_invoice_v3, Outcome_order_v3
    models = [Invoice_v3, Pricing_order_v3, Correction_invoice_v3, Outcome_order_v3]
    result_dict = {}
    for model in models:
        for obj in model.objects.filter(dreamkas_id__in=dreamkas_ids):
            result_dict[obj.dreamkas_id] = obj
    final_result = []
    for dreamkas_id in dreamkas_ids:
        if dreamkas_id in result_dict:
            final_result.append(result_dict[dreamkas_id])
    return final_result
    

def fetch_document_object(dreamkas_id):
    from mainapp.models import Invoice_v3, Pricing_order_v3, Correction_invoice_v3, Outcome_order_v3
    
    invoice_found = Invoice_v3.objects.filter(dreamkas_id=dreamkas_id)
    pricing_found = Pricing_order_v3.objects.filter(dreamkas_id=dreamkas_id)
    correction_invoice_found = Correction_invoice_v3.objects.filter(dreamkas_id=dreamkas_id)
    outcome_order_found = Outcome_order_v3.objects.filter(dreamkas_id=dreamkas_id)
    
    # Count how many tables have this document
    found_count = sum([
        invoice_found.__len__() > 0,
        pricing_found.__len__() > 0,
        correction_invoice_found.__len__() > 0,
        outcome_order_found.__len__() > 0
    ])
    
    if found_count > 1:
        print(f"Error. Document {dreamkas_id} found in {found_count} tables")
        if invoice_found.__len__() > 0:
            print("Document found in Invoice table")
        if pricing_found.__len__() > 0:
            print("Document found in Pricing table")
        if correction_invoice_found.__len__() > 0:
            print("Document found in Correction invoice table")
        if outcome_order_found.__len__() > 0:
            print("Document found in Outcome order table")
        return None
        
    if invoice_found.__len__() > 0:
        return invoice_found.first()
    elif pricing_found.__len__() > 0:
        return pricing_found.first()
    elif correction_invoice_found.__len__() > 0:
        return correction_invoice_found.first()
    elif outcome_order_found.__len__() > 0:
        return outcome_order_found.first()
    return None

def fetch_documents_positions(document_object=None,document_id=None):
    from mainapp.models import Invoice_v3, Pricing_order_v3, Correction_invoice_v3, Outcome_order_v3
    if document_id is not None:
        document_object = fetch_document_object(document_id)
    if document_object is None:
        return None
    if document_object.__class__ == Invoice_v3:
        return document_object.position_invoice_v3_set.all()
    elif document_object.__class__ == Pricing_order_v3:
        return document_object.position_pricing_order_v3_set.all()
    elif document_object.__class__ == Correction_invoice_v3:
        return document_object.position_correction_invoice_v3_set.all()
    elif document_object.__class__ == Outcome_order_v3:
        return document_object.position_outcome_order_v3_set.all()
    return None

