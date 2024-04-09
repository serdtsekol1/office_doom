import json
import os

from requests.auth import HTTPBasicAuth
from requests_html import HTMLSession
from dremkas.settings import DREAM_KAS_API, SHOP_AMOUNT
from mainapp.models import Product, Prices, Barcodes, Prices_shop
import time
def turn_number_to_ean_13(code):
    if len(code) != 12:
        return False
    if type(code) is not str:
        code = str(code)
    result = 0
    for digit in range(0, 12, 2):
        result = result + int(code[digit]) + int(code[digit + 1]) * 3
    if result % 10 == 0:
        print(result)
        result = 0
    else:
        result = 10 - result % 10
    return code + str(result)

def calculate_prices_per_shop_for_all_products():
    #SHOP IDS begin with 1.
    Shops = json.loads(os.environ.get('SHOP_IDS'))
    Product_objects = Product.objects.all()
    for product in Product_objects:
        prices_device = Prices.objects.filter(product_fk=product)
        i = 0
        for Shop in Shops:
            i = i + 1
            shop_prices = []
            for device_id in Shop:
                shop_price = prices_device.filter(device_id=device_id).first()
                if shop_price is not None:
                    shop_prices.append(shop_price.value)
            unique_prices_of_shop = list(set(shop_prices))
            if unique_prices_of_shop.__len__() > 1:
                print(product.id_out)
                print('Имеет несколько цен для магазина', i)
                print("За основу будет взята цена случайного магазина. Пофиксите!")
            if unique_prices_of_shop.__len__() == 0:
                continue
            price_internal = product.prices_shop_set.filter(shop_id=i)
            price_shop = Prices_shop(
                product_fk=product,
                shop_id=i,
                value=unique_prices_of_shop[0],
            )
            print(price_shop.shop_id,'  ', price_shop.value)













def product_update(id_out, debug=0):
    product_external = DREAM_KAS_API.get_product(id_out)
    if 'status' in product_external:
        print('404 error')
        print(id_out)
        print('404 error')
        if debug==1:            print('Продукт с ид не найден');
        return 404
    product_internal = Product.objects.filter(id_out=id_out)
    if product_internal.__len__() > 1:
        print('Duplicate found')
        print(id_out)
        print('Duplicate found')
        if debug==1:            print('2+ продукта с ид найдено в базе внутренней');
        return 500
    elif product_internal.__len__() == 0:
        product_internal = Product.objects.create(
            id_out=product_external['id'],
            name=product_external['name'],
            type=product_external['unit'],
            marked_good=product_external['isMarked'],
            nds=product_external['tax'],
            group_id=product_external['departmentId'],
            updatedAt=product_external['updatedAt'],
                               )
        if debug==1:            print('Создан продукт');            print(product_internal, product_internal.id_out,product_internal.name);
        #barcodes
        for barcode in product_external['barcodes']:
            barcode_obj = Barcodes.objects.filter(barcode=barcode)
            if barcode_obj.__len__() == 0:
                new_barcode = Barcodes.objects.create(product_fk=product_internal,
                                                      barcode=barcode,
                                                      multiplier=1
                                                      )
                if debug == 1: print('Создан штрихкод', new_barcode.product_fk.id_out); print(new_barcode.barcode)
            if barcode_obj.__len__() > 1:
                print('Дубликат штрихкода в базе. Найдено 2 или более!')
                continue
            if barcode_obj.__len__() == 1:
                barcode_obj = Barcodes.objects.filter(barcode=barcode).first()
                if barcode_obj.product_fk.id_out == product_external['id']:
                    continue
                else:
                    if debug == 1:                    print('Удален штрихкод', barcode_obj.barcode)
                    barcode_obj.delete()
                new_barcode = Barcodes.objects.create(product_fk=product_internal,
                                                      barcode=barcode,
                                                      multiplier=1
                                                      )
                if debug == 1: print('Создан штрихкод', new_barcode.product_fk.id_out); print(new_barcode.barcode)

        #prices
        prices_internal = Prices.objects.filter(product_fk=product_internal)
        for price_external in product_external['prices']:
            device_id = price_external['deviceId']
            value = price_external['value']
            price_internal = prices_internal.filter(device_id=device_id)
            if price_internal.__len__() == 0:
                new_price = Prices.objects.create(
                    product_fk=product_internal,
                    device_id=device_id,
                    value=value
                )
                if debug == 1:                    print('Создан штрихкод', new_price.product_fk.id_out, new_price.device_id, new_price.value);
                continue
            else:
                price_internal = price_internal.first()
                price_internal.value = value
                if debug == 1:                    print('обновлен', new_price.product_fk.id_out, new_price.device_id, new_price.value);
                price_internal.save()
    elif product_internal.__len__() == 1:
        product_internal = product_internal.first()
        product_internal.id_out = product_external['id']
        product_internal.name = product_external['name']
        product_internal.type = product_external['unit']
        product_internal.marked_good = product_external['isMarked']
        product_internal.nds = product_external['tax']
        product_internal.group_id = product_external['departmentId']
        product_internal.updatedAt = product_external['updatedAt']
        product_internal.save()
        #barcodes
        for barcode in product_external['barcodes']:
            barcode_obj = Barcodes.objects.filter(barcode=barcode)
            if barcode_obj.__len__() == 0:
                new_barcode = Barcodes.objects.create(product_fk=product_internal,
                                                      barcode=barcode,
                                                      multiplier=1
                                                      )
                if debug == 1: print('Создан штрихкод', new_barcode.product_fk.id_out); print(new_barcode.barcode)
            if barcode_obj.__len__() > 1:
                print('Дубликат штрихкода в базе. Найдено 2 или более!')
                continue
            if barcode_obj.__len__() == 1:
                barcode_obj = Barcodes.objects.filter(barcode=barcode).first()
                if barcode_obj.product_fk.id_out == product_external['id']:
                    continue
                else:
                    if debug == 1:                    print('Удален штрихкод', barcode_obj.barcode)
                    barcode_obj.delete()
                new_barcode = Barcodes.objects.create(product_fk=product_internal,
                                                      barcode=barcode,
                                                      multiplier=1
                                                      )
                if debug == 1: print('Создан штрихкод', new_barcode.product_fk.id_out); print(new_barcode.barcode)
        #prices
        prices_internal = Prices.objects.filter(product_fk=product_internal)
        for price_external in product_external['prices']:
            device_id = price_external['deviceId']
            value = price_external['value']
            price_internal = prices_internal.filter(device_id=device_id)
            if price_internal.__len__() == 0:
                Prices.objects.create(
                    product_fk=product_internal,
                    device_id=device_id,
                    value=value
                )
                continue
            else:
                price_internal = price_internal.first()
                price_internal.value = value
                price_internal.save()
    product_internal = Product.objects.filter(id_out=id_out).first()
    barcodes_internal = Barcodes.objects.filter(product_fk=product_internal)
    for barcode_obj in barcodes_internal:
        if barcode_obj.product_fk.id_out != product_external['id']:
            barcode_obj.delete()
        if barcode_obj.barcode not in product_external['barcodes']:
            barcode_obj.delete()

# def check_barcode_existance_in_dreamkas(barcode):
#     search_result = DREAM_KAS_API.search_goods(barcode)
#     if search_result is None:
#         return search_result['name']
#     return True
def Create_barcode_for_product(id_out, barcode):
    #True - OK
    #Else - Not OK, name of product is returned.
    search_result = DREAM_KAS_API.search_goods(barcode)
    if search_result is not None:
        print('Данный штрихкод или код уже существует и пренадлежит какому-то товару. Удалите данный штрихкод с другого товара!')
        print(search_result['name'])
        return search_result['name']
    product_external = DREAM_KAS_API.get_product_v2(id_out)
    ean = DREAM_KAS_API.check_code(barcode)
    if ean is None:
        product_external['vendorCodes'].append(barcode)
    else:
        product_external['barcodes'].append(barcode)
    resp = DREAM_KAS_API.update_product(id_out, product_external)
    product_update(id_out)
    return True
def Delete_barcode_for_product(id_out, barcode):
    search_result = DREAM_KAS_API.get_product_v2(id_out)
    if barcode in search_result['vendorCodes']:
        search_result['vendorCodes'].remove(barcode)
    if barcode in search_result['barcodes']:
        search_result['barcodes'].remove(barcode)

    resp = DREAM_KAS_API.update_product(search_result['id'], search_result)
    product_update(search_result['id'])
    product_update(id_out)
def Find_and_delete_barcode(barcode):
    search_result = DREAM_KAS_API.search_goods(barcode)
    if search_result == None:
        return
    else:
        search_result = DREAM_KAS_API.get_product_v2(search_result['id'])
        if barcode in search_result['vendorCodes']:
            search_result['vendorCodes'].remove(barcode)
        if barcode in search_result['barcodes']:
            search_result['barcodes'].remove(barcode)
    resp = DREAM_KAS_API.update_product(search_result['id'], search_result)
    product_update(search_result['id'])

def delete_duplicate_barcode_objects():
    from django.db.models import Count, Max
    from django.db.models import F

    # First, we group the objects by barcode and count the number of occurrences
    barcodes_counts = Barcodes.objects.values('barcode').annotate(count=Count('barcode'))

    # Next, we filter to get only the barcodes that have multiple occurrences
    duplicate_barcodes = barcodes_counts.filter(count__gt=1)

    # Now, for each duplicate barcode, we find the object with the biggest id and delete it
    for barcode_count in duplicate_barcodes:
        max_id = Barcodes.objects.filter(barcode=barcode_count['barcode']).aggregate(max_id=Max('id'))['max_id']
        Barcodes.objects.filter(id=max_id).delete()


def Products_update():
    products_list = DREAM_KAS_API.get_products()
    existing_products_list = Product.objects.all()
    existing_products_map = {product.id_out: product for product in existing_products_list}
    products_to_update = []
    products_to_create = []
    i = 0
    for product_external in products_list:
        if i % 1000 == 0:
            print('Подготовка листов для создания и обновления товаров. Прогресс - ', i)
        i = i + 1
        if product_external['id_out'] in existing_products_map:
            product_internal = existing_products_map[product_external['id_out']]
            price_difference = False
            if product_internal.updatedAt != product_external['updatedAt']:
                price_difference = True
            else:
                for price in product_external['prices']:
                    price_internal = product_internal.prices_set.filter(device_id=price['deviceId'])
                    if not price_internal or price_internal[0].value != price['value']:
                        price_difference = True
                        break
            if price_difference:
                product_internal.name = product_external['name']
                product_internal.type = product_external['type'] # Type here because unit is loaded into type when doing lists of products
                product_internal.marked_good = product_external['marked_good']
                product_internal.nds = product_external['nds']
                product_internal.group_id = product_external['group_id'] if 'group_id' in product_external else None
                product_internal.updatedAt = product_external['updatedAt'] if 'updatedAt' in product_external else None
                products_to_update.append(product_internal)
        else:
            product_data = Product(
                id_out=product_external['id_out'],
                name=product_external['name'],
                type=product_external['type'], # Type here because unit is loaded into type when doing lists of products
                marked_good=product_external['marked_good'],
                nds=product_external['nds'],
                group_id=product_external['group_id'] if 'group_id' in product_external else None,
                updatedAt=product_external['updatedAt'] if 'updatedAt' in product_external else None
            )
            products_to_create.append(product_data)
    print('Создание новых товаров. Кол-во' ,products_to_create.__len__())
    Product.objects.bulk_create(products_to_create)
    print('Обновление существующих товаров. Кол-во' ,products_to_update.__len__())
    Product.objects.bulk_update(products_to_update, ['name', 'type', 'marked_good', 'nds', 'group_id','updatedAt'])
    id_out_set = set(product['id_out'] for product in products_list)
    products_to_delete = Product.objects.exclude(id_out__in=id_out_set)
    i = 0
    for product in products_to_delete:
        resp = DREAM_KAS_API.get_product(product.id_out)
        if 'status' in resp:
            if resp['status'] == int(404):
                product.delete()
                i = i + 1
        else:
            print(product.id_out, "is in delete list but exists")
    print('Удаление несуществующих товаров из базы. Кол-во:', i)
    updated_ids = {product.id_out for product in products_to_update}
    created_ids = {product.id_out for product in products_to_create}
    all_ids = updated_ids.union(created_ids)
    all_ids_set = set(all_ids)
    products_dict = {product['id_out']: product for product in products_list}
    products_internal = Product.objects.filter(id_out__in=all_ids_set)
    products_internal_dict = {product.id_out: product for product in products_internal}
    barcodes_to_create = []
    prices_to_create = []
    prices_to_update = []
    del_counter = 0
    #з кожним товаром шо поминявся\добавлений.
    for id_out in all_ids:
        product_external = products_dict.get(id_out)
        product_internal = products_internal_dict.get(id_out)
        barcodes_internal = Barcodes.objects.filter(product_fk=product_internal)
        barcodes_external = product_external['barcodes']
        prices_internal = Prices.objects.filter(product_fk=product_internal)
        prices_external = product_external['prices']
        for barcode_external in barcodes_external:
            barcode_internal = Barcodes.objects.filter(barcode=barcode_external)
            if barcode_internal.__len__() > 1: # More than obj with this barcode exist!
                print(barcode_internal, barcode_internal.first().barcode, 'Multiple queries with said barcode found. Check and fix external database.')
                continue
            if barcode_internal.__len__() == 0: # Barcode does not exist. Create it.
                new_barcode = Barcodes(product_fk=product_internal, barcode=barcode_external, multiplier=1)
                barcodes_to_create.append(new_barcode)
                continue
            barcode_internal = barcode_internal.first()
            # Barcode exists and belongs to a product, id_out of which matches our current product's id_out
            if barcode_internal.product_fk.id_out == product_external['id_out']:
                continue
            # Barcode exists, and it belongs to a product, id_out of which doesn't match our current product's id_out. Delete ie and add create new one with proper product.
            if barcode_internal.product_fk.id_out != product_external['id_out']:
                new_barcode = Barcodes(product_fk=product_internal, barcode=barcode_external, multiplier=1)
                barcodes_to_create.append(new_barcode)
                barcode_internal.delete()
                del_counter = del_counter + 1
                continue
        for barcode_internal in barcodes_internal:
            if barcode_internal.barcode in product_external['barcodes']:
                continue
            else:
                barcode_internal.delete()
                del_counter = del_counter + 1
        for price_external in prices_external:
            device_id = price_external['deviceId']
            value = price_external['value']
            price_internal = prices_internal.filter(device_id=device_id).first()
            if price_internal is None:
                new_price = Prices(product_fk=product_internal, device_id=device_id, value=value)
                prices_to_create.append(new_price)
                continue
            if price_internal.value != value:
                price_internal.value = value
                prices_to_update.append(price_internal)
    print("Создание Цен. Кол-во - ", prices_to_create.__len__())
    Prices.objects.bulk_create(prices_to_create)
    print("Обновление Цен. Кол-во - ", prices_to_update.__len__())
    Prices.objects.bulk_update(prices_to_update, ['value'])
    print("Удалено", del_counter, "Штрихкодов")
    print("Создание Штрихкодов. Кол-во - ", prices_to_update.__len__())
    Barcodes.objects.bulk_create(barcodes_to_create)














