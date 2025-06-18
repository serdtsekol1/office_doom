from datetime import datetime,timedelta
from dremkas.settings import DREAM_KAS_API

from mainapp.models import Invoice_v3, Pricing_order_v3, Correction_invoice_v3
def pricing_order_draft_cleanup(dreamkas_id):
    from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object
    from mainapp.Dreamkas_documents.funcs import build_tree_of_documents
    
    # Get a tree of documents
    document_tree = build_tree_of_documents(document_id=dreamkas_id)
    if not document_tree:
        return 0
    
    deletions = 0
    
    # Helper function to find all pricing orders in the tree
    def find_pricing_orders(doc_structure):
        nonlocal deletions
        
        # Check if current document is a pricing order
        if doc_structure['document_type'] == 'Pricing Order':
            doc_object = fetch_document_object(doc_structure['id'])
            # If document is a draft, delete it
            if doc_object and doc_object.flag_status == 'DRAFT':
                DREAM_KAS_API.delete_document(doc_structure['id'])
                
                # Update internal document status if it exists
                document_internal = Pricing_order_v3.objects.filter(dreamkas_id=doc_structure['id'])
                if document_internal.__len__() > 0:
                    doc_internal = document_internal.first()
                    doc_internal.flag_status = 2  # Mark as deleted
                    doc_internal.save()
                
                deletions += 1
        
        # Recursively check children
        for child in doc_structure['children']:
            find_pricing_orders(child)
    
    # Start processing from the root document
    root_doc = document_tree[dreamkas_id]
    find_pricing_orders(root_doc)
    
    if deletions > 0:
        print("Deleted", deletions, "draft pricing orders")
    
    return deletions
def flag_deleted_drafts():
    from mainapp.models import Invoice_v3
    invoices = Invoice_v3.objects.filter(flag_status=0)
    for invoice in invoices:
        document = DREAM_KAS_API.get_document(invoice.dreamkas_id)
        if document == False:
            invoice.flag_status = 2
            invoice.save()
    corrections = Correction_invoice_v3.objects.filter(flag_status=0)
    for correction in corrections:
        document = DREAM_KAS_API.get_document(correction.dreamkas_id)
        if document == False:
            correction.flag_status = 2
            correction.save()
    pricing_orders = Pricing_order_v3.objects.filter(flag_status=0)
    for pricing_order in pricing_orders:
        document = DREAM_KAS_API.get_document(pricing_order.dreamkas_id)
        if document == False:
            pricing_order.flag_status = 2
            pricing_order.save()
            
def draft_cleanup(documents_external=None):
    deletions = 0
    if documents_external == None:
        documents_external = DREAM_KAS_API.get_documents(limit=1000, offset=None)
    ids_to_delete = []
    for document_external in documents_external:
        if datetime.now() > datetime.strptime(document_external['createdAt'], '%Y-%m-%d') + timedelta(days=3) and document_external['status'] == 'DRAFT':
            DREAM_KAS_API.delete_document(document_external['id'])
            document_internal = Invoice_v3.objects.filter(dreamkas_id=document_external['id'])
            if document_internal.__len__() > 1:
                doc_internal = document_internal.first()
                doc_internal.flag_status = 2 # 2 - deleted
                doc_internal.save()
                
            deletions = deletions + 1
            ids_to_delete.append(document_external['id'])
    for id_to_delete in ids_to_delete:
        for document_external in documents_external:
            if document_external['id'] == id_to_delete:
                documents_external.remove(document_external)
                break
        
    if deletions > 0:
        print("Deleted ",deletions, " draft documents")
    