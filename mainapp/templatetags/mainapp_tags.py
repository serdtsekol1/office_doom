from __future__ import unicode_literals
import re
from decimal import Decimal
from itertools import groupby

from django import template
import os.path

from django.db.models import Count
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _, get_language
import json

from dremkas.settings import MEDIA_ROOT
from mainapp.models import Device, Store, Supplier

register = template.Library()


@register.filter(name='split')
def split(value, key):
    """
        Returns the value turned into a list.
    """
    if len(key) == 1:
        return value.split(key)
    else:
        return value.split(key[0])[int(key[1])]


@register.simple_tag
def call_method(obj, method_name, **kwargs):
    """
    Визиває функцію моделі з параметрами
    Example {% call_method article 'get_last_articles' limit=10 as articles %}
    :param obj: Модель
    :param method_name: Функція
    :param kwargs: Параметри
    :return: Результат функції
    """
    method = getattr(obj, method_name)
    return method(**kwargs)


@register.simple_tag
def get_svg(url):
    try:
        f = open(os.path.join(MEDIA_ROOT, url))
        content = f.read()
        return content
    except Exception as e:
        return ''


@register.filter
def filter_image_x2(value, x=2):
    """Фільтер для збільшеня width/height картинки в 2 рази"""
    return int(value) * x


@register.filter
def multiply(num1, num2):
    """Фільтер для збільшеня width/height картинки в 2 рази"""
    return Decimal(str(num1).replace(",", ".")) * Decimal(str(num2).replace(",", "."))


@register.filter
def divide(num1, num2):
    """Фільтер для збільшеня width/height картинки в 2 рази"""
    try:
        return Decimal(num1) / Decimal(num2)
    except Exception as ex:
        return 0


@register.filter
def subtract(num1, num2):
    """Фільтер для збільшеня width/height картинки в 2 рази"""
    try:
        return Decimal(num1) - Decimal(num2)
    except Exception as ex:
        return 0


@register.simple_tag
def tag_get_full_path(request, path=None):
    if path:
        url = 'https://' + request.get_host() + path if request.is_secure() else 'http://' + request.get_host() + path
    else:
        url = 'https://' + request.get_host() + request.path if request.is_secure() else 'http://' + request.get_host() + request.path
    return url


@register.filter
def filter_phone_trim(phone):
    phone = re.sub("\D+", '', str(phone))
    return str(phone)


@register.filter
def media_url(value, request):
    return ''.join([request.scheme, "://", request.META['HTTP_HOST'], value])


@register.filter
def add_language_to_link(url, lng):
    url = url.split('/')
    url[2] = f"{url[2]}/{lng}"
    return '/'.join(url)


@register.filter
def get_price_for_device(prices, store):
    device_ids = Device.objects.filter(store_id=store.store_id).values_list('device_id', flat=True)
    price_obj = prices.filter(device_id__in=device_ids).first()
    return price_obj.value / 100 if price_obj else None


@register.filter
def get_first_name_for_supplier(supplier_id):
    supplier = Supplier.objects.filter(id=supplier_id).first()
    if supplier is None:
        supplier = Supplier.objects.filter(inn=supplier_id).first()
    return supplier.supplier_name_set.first().name if supplier.supplier_name_set.first() else supplier.inn


@register.simple_tag
def get_printer_code_from_barcode(barcodes):
    try:
        for barcode in barcodes:
            if str(barcode.barcode).startswith('999999999'):
                return {'barcode_id': barcode.id, 'printer_code': barcode.barcode[9:12]}
    except:
        pass
    try:
        if str(barcodes).startswith('999999999'):
            return {'printer_code': barcodes[9:12]}
    except:
        pass
    return {'barcode_id': None, 'printer_code': None}
