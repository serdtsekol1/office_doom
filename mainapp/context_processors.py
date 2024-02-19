from mainapp.models import Store


def get_settings(request):
    if store_id:=request.session.get('store_id'):
        store = Store.objects.filter(store_id=store_id).first()
    else:
        print("Default Store Selected auto")
        store = Store.objects.filter(store_id=185449).first()
        try:
            request.session['store_id'] = store.store_id
        except:
            pass
    return {'STORES':Store.objects.all(), 'CURRENT_STORE':store}