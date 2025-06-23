from dremkas.settings import DREAM_KAS_API
from mainapp.models import Product
from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object
from mainapp.models import Pricing_order_v3,Invoice_v3,Correction_invoice_v3

def old_and_unused_products_cleanup():
    return 0
def update_products_from_pricing_order(dreamkas_id):
    pricing_order = fetch_document_object(dreamkas_id)
    if pricing_order is None:
        return None
    if pricing_order.__class__ == Invoice_v3:
        if pricing_order.latest_pricing_id is None:
            return None
        pricing_order = fetch_document_object(pricing_order.latest_pricing_id)
    if pricing_order.__class__ == Correction_invoice_v3:
        if pricing_order.latest_pricing_id is None:
            return None
        pricing_order = fetch_document_object(pricing_order.latest_pricing_id)
    if pricing_order.__class__ == Pricing_order_v3:
        pricing_order = fetch_document_object(pricing_order.parent_document_dreamkas_id)
        if pricing_order is None:
            return None
        if pricing_order.__class__ == Invoice_v3:
            if pricing_order.latest_pricing_id is None:
                return None
            pricing_order = fetch_document_object(pricing_order.latest_pricing_id)
        if pricing_order.__class__ == Correction_invoice_v3:
            if pricing_order.latest_pricing_id is None:
                return None
            pricing_order = fetch_document_object(pricing_order.latest_pricing_id)
    print(pricing_order)
        

def update_product(product_id):
    product_data = DREAM_KAS_API.get_product(product_id)
    if 'status' in product_data and product_data['status'] == 404:
        product = Product.objects.filter(id_out=product_id).first()
        if product.__len__() == 0:
            return
        if product.__len__() == 1:
            product.flag_deleted = True
            product.save()
            return
    product, created = Product.objects.get_or_create(id_out=product_data['id'])
    if not product_data or ('status' in product_data and product_data['status'] == 404):
        product.flag_deleted = True
        product.save()
        return
    product.name = product_data['name']
    product.type = 796 if product_data['unit'] == '796' else 166
    product.marked_good = product_data.get('isMarked', False)
    tax_mapping = {
        'NDS_NO_TAX': None,
        'NDS_0': 0,
        'NDS_10': 10,
        'NDS_20': 20,
        'NDS_10_110': 110,
        'NDS_20_120': 120
    }
    product.nds = tax_mapping.get(product_data.get('tax'), None)
    product.group_id = product_data.get('departmentId')
    product.updatedAt = product_data.get('updatedAt')
    product.save()
    
    return product
    
def update_products():
    products_list = DREAM_KAS_API.get_products()
    existing_products_list = Product.objects.all()
    existing_products_map = {product.id_out: product for product in existing_products_list}
    
        