from mainapp.models import Store
from dremkas.settings import DREAM_KAS_API
def update_stores():
    for store in DREAM_KAS_API.get_stores():
        Store.objects.update_or_create(store_id=store['id'], defaults = {
            'store_name': store['name'],
        })
def fetch_or_create_store(store_id):
    store = Store.objects.filter(store_id=store_id)
    if store.__len__() == 0:
        store = Store.objects.create(store_id=store_id)
    else:
        store = store.first()
    return store
