from mainapp.models import Supplier,Supplier_name

def create_supplier(name,inn=None):
    supplier = Supplier.objects.create(name=name,inn=inn)
    supplier_name = Supplier_name.objects.update_or_create(name=name,supplier_fk=supplier)
    
def fetch_or_create_supplier(sourcename_or_inn):
    supplier = Supplier_name.objects.filter(name=sourcename_or_inn)
    found = False
    if supplier.__len__() > 0:
        found = True
        supplier = supplier.first().supplier_fk
    if found == False:
        if sourcename_or_inn.isdigit():
            supplier = Supplier.objects.filter(inn=sourcename_or_inn)
            if supplier.__len__() > 0:
                found = True
                supplier = supplier.first()
    if found == False:
        create_supplier(sourcename_or_inn)   
        supplier = Supplier_name.objects.filter(name=sourcename_or_inn).first().supplier_fk
    return supplier


