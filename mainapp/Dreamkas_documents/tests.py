
def check_missing_invoices():
    print('MISSING DOCUMENTS CHECK')
    """
    Checks for invoices, pricing orders, and correction invoices that exist in DreamKas API but are missing in their respective models.
    Prints details of missing documents.
    """
    from mainapp.models import Invoice_v3, Pricing_order_v3, Correction_invoice_v3
    from dremkas.settings import DREAM_KAS_API
    
    # Get documents from DreamKas API for invoices
    documents = DREAM_KAS_API.get_documents(
        limit=1000,
        offset=0,
        document_type="5,13"
    )
    
    if documents == -1:
        print("Failed to get documents from DreamKas API")
        return
        
    # Get all existing records
    existing_invoices = set(str(id) for id in Invoice_v3.objects.values_list('dreamkas_id', flat=True))
    
    # Check each document for regular invoices
    for document in documents:
        if str(document['id']) not in existing_invoices:
            print(f"Missing invoice - ID: {document['id']}, Date: {document['acceptedAt'] if 'acceptedAt' in document else 'N/A'}, Number: {document['num']}")
    
    # Get correction invoices
    correction_documents = DREAM_KAS_API.get_documents(
        limit=1000,
        offset=0,
        document_type="7"
    )
    
    if correction_documents == -1:
        print("Failed to get correction invoices from DreamKas API")
        return
        
    # Get existing correction invoices
    existing_corrections = set(str(id) for id in Correction_invoice_v3.objects.values_list('dreamkas_id', flat=True))
    
    # Check each correction document
    for document in correction_documents:
        if str(document['id']) not in existing_corrections:
            print(f"Missing correction invoice - ID: {document['id']}, Date: {document['acceptedAt'] if 'acceptedAt' in document else 'N/A'}, Number: {document['num']}")
    
    # Get pricing orders
    pricing_orders = DREAM_KAS_API.get_documents(
        limit=1000,
        offset=0,
        document_type="11"
    )
    
    if pricing_orders == -1:
        print("Failed to get pricing orders from DreamKas API")
        return
        
    # Get existing pricing orders
    existing_pricing_orders = set(str(id) for id in Pricing_order_v3.objects.values_list('dreamkas_id', flat=True))
    
    # Check each pricing order
    for document in pricing_orders:
        if str(document['id']) not in existing_pricing_orders:
            print(f"Missing pricing order - ID: {document['id']}, Date: {document['acceptedAt'] if 'acceptedAt' in document else 'N/A'}, Number: {document['num']}")
