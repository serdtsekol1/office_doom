



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

