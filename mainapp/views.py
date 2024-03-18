import datetime
import json
import os
import pickle
import re
import time
import webbrowser
from dataclasses import dataclass
from decimal import Decimal
import py7zr
import pandas
import requests
import simplegmail
import xlrd
from crispy_forms.helper import FormHelper
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.db.models import Sum, Value, Q, OuterRef, Prefetch
from django.db.models.functions import Lower
from django import forms
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
import openpyxl
from simplegmail import gmail
from simplegmail.query import construct_query

import mainapp
from dremkas.settings import DREAM_KAS_API, DIADOC_API, CURRENT_IDS
from mainapp.models import Invoice, GoodGroups, DiadocInvoice, Supplier, Gmail_Messages, Position, DailyInvoiceReport, Product, Barcodes, Prices, Store, Supplier_name, PresetGmail, DiadocPreset
from . import dreamkas_documents, dreamkas_to_massaK, diadoc_to_dreamkas, gmail_to_dreamkas
from .diadoc_to_dreamkas import create_invoice_from_diadoc_document_v2
from .dreamkas_documents import dreamkas_update_suppliers
from .dreamkas_Products import product_update, Find_and_delete_barcode, Create_barcode_for_product
from .dreamkas_to_massaK import create_or_change_massak_codes_for_product, create_excel_document_for_massaK
from .gmail_invoices import create_document_from_excel, get_gmail_messages
from .gmail_to_dreamkas import get_document_and_attachments_from_gmail, get_supplier_data_for_preset
from .helper import send_document, delete_file, save_to_json

from django.core.validators import MinValueValidator, MaxValueValidator, EMPTY_VALUES
from django.utils import timezone

from django.db.models import Count
from django.db import models
from django.db.models import Aggregate

# DREAM_KAS_API = None
GOOGLEMAIL = [
    "auto_mail@mpk-skvortsovo.ru",
]
# diadoc_suppliers = []
# for file in os.listdir("media/diadoc_suppliers/"):
#     company = []
#     company.append(file['supplier_inn'])

COMPANIES = [
    ('ip_martovoy', 'ИП Мартовой'),
    ('ooo_partner', 'OOO Partnfer'),
    ('ooo_VNNA', 'Vinniy Aliansv'),
    ('ip_baykov', 'IP Baykov'),
    ('ooo_invest_torg', 'OOO Invest Torg'),
    ('ip_td_mihalin', 'Ip Td Mihalin'),
    ('ip_glazichev_m_g', 'Ip Glazichev Maksim Gennadievich'),
    ('ooo_veles_vip', 'OOO Veles ViP'),
    ('ooo_faeton', 'OOO Faeton'),
    ('ooo_prod_alians_krim', 'OOO ProdAlians-Krim'),
    ('ooo_torgoviy_dom_vremia', 'OOO Torgoviy Dom Vremia'),
    ('ooo_krim_frost', 'OOO Krim frost'),
    ('ooo_sir_mol_prom_yug', 'OOO Sir Mol Prom Yug'),
    ('ooo_partner_yug_diadoc', 'OOO Partner Yug'),
    ('ooo_orient', 'OOO ORIENT'),
    ('ip_atamanov_aleksandr_evgenievich', "IP Atmanov Aleksandr Evgenievich"),
    ('ooo_krim_prod_snab', "OOO Krim Prod Snab"),
    ('ooo_df_ruslana', "OOO DF Ruslana"),
    ('ip_nikonenko_vasiliy_leonidovich', "IP Nikonenko Vasiliy Leonidovich"),
    ('ooo_ideal_krim', "OOO Ideal Krim"),
    ('ooo_td_ideal_krim', "OOO TD Ideal Krim"),
    ('ip_baykov_diadoc', 'IP Baykov'),
    ('ooo_ors', 'OOO ORS'),
    ('ip_vovchenko_yana_iosifovna', 'IP Vovchenko Yana Iosifovna'),
    ('ooo_megatreyd_yug', 'OOO Megatrade Yug'),
    ('ooo_prodlayn', 'OOO ProdLayn'),
    ('ooo_troyanda_krim', 'OOO Troyanda Krim'),
    ('ooo_rosttreyd', 'OOO RostTreyd'),
    ('ooo_td_stariy_amsterdam', 'OOO Staryiy Amsterdam'),
    ('ooo_Dakort_Krim', "OOO Dakort Krim"),
    ('ooo_krim_product', "OOO Krim Product"),
    ('ooo_real_krim', "OOO Real Krim"),
    ('ip_popov_aleksandr_aleksandrovich', "Saksoye Morojenoye, popov A A"),
    ('ip_melnikova_tatiana_bogdanovna', "IP Melnikova Tatiana Bogdanovna"),
    ('ip_yarosh_sergey_valerievich', 'IP Yarosh Sergey Valerievich'),
    ('ip_desna_vasility_anatolievich', ", IP Desna Vasiliy Anatolievich"),
    ('ip_trusov_A_Yu', ", IP Trusov Aleksandr Yurievich"),
    ('ip_goliakov_vitaliy_viktorovich', ", IP Goliakov Vitaliy Viktorovich"),
    ('ooo_yusan', "ooo Yusan")

]


@dataclass
class PresetModelValue:
    exists = bool
    value = str
    int = bool
    float = bool
    str = bool

    def __init__(self, _value=None, _int=False, _float=False, _str=False, _exists=True):
        self.value = _value
        self.int = _int
        self.float = _float
        self.str = _str
        self.exists = _exists


class Concat(Aggregate):
    function = 'GROUP_CONCAT'
    template = "%(function)s(%(distinct)s%(expressions)s SEPARATOR '%(separator)s')"
    allow_distinct = True

    def __init__(self, expression, distinct=False, separator=',', **extra):
        super(Concat, self).__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            separator=separator,
            output_field=models.CharField(),
            **extra
        )


@dataclass
class PresetModel:
    company = str
    inn = str
    doc_id = str
    product_name = PresetModelValue()
    product_code = PresetModelValue()
    product_qty = PresetModelValue()
    product_sum = PresetModelValue()

    def to_json(self):
        return self.__dict__
    # def __init__(self, company=None, inn=None, doc_id=None, product_name=None, product_code=None, product_qty=None, product_sum=None):
    #     self.company = company
    #     self.inn = inn
    #     self.doc_id = doc_id
    #     self.product_name = product_name
    #     self.product_code = product_code
    #     self.product_qty = product_qty
    #     self.product_sum = product_sum


@method_decorator(csrf_exempt, name='dispatch')
class Preset(View):
    def get(self, request):
        list_presets = []
        for file_name in os.listdir('media/presets'):
            print(file_name)
            with open(f'media/presets/{file_name}', 'rb') as f:
                list_presets.append(pickle.load(f).to_json())

        return JsonResponse(list_presets, safe=False)

    def post(self, request):
        print(request.POST)

        preset = PresetModel()
        preset.company = request.POST.get('type_cell_company', None)
        preset.inn = request.POST.get('input_type_cell_inn', None)
        preset.doc_id = request.POST.get('input_type_cell_doc_id', None)
        # TODO Зроботи так щоб берігалось  в датаклас PresetModelValue 
        # preset.product_name = request.POST.get('type_cell_name', None)
        # preset.product_code = request.POST.get('type_cell_code', None)
        # preset.product_qty = request.POST.get('type_cell_qty', None)
        # preset.product_sum = request.POST.get('type_cell_sum_price', None)
        select_name = request.POST.get('select_name', None).split(',')
        select_code = request.POST.get('select_code', None).split(',')
        select_qty = request.POST.get('select_qty', None).split(',')
        select_sum = request.POST.get('select_sum_price', None).split(',')
        preset.product_name = PresetModelValue(_value=request.POST.get('type_cell_name', None), **{f'_{f}': True for f in select_name})
        preset.product_code = PresetModelValue(_value=request.POST.get('type_cell_code', None), **{f'_{f}': True for f in select_code})
        preset.product_qty = PresetModelValue(_value=request.POST.get('type_cell_qty', None), **{f'_{f}': True for f in select_qty})
        preset.product_syn = PresetModelValue(_value=request.POST.get('type_cell_sum_price', None), **{f'_{f}': True for f in select_sum})

        with open(f'media/presets/{preset.company}.obj', 'wb') as f:
            pickle.dump(preset, f)
        # ttt = pickle.load(open('preset.obj', 'rb'))
        return JsonResponse({'success': True}, safe=False)

    def patch(self, request):
        return JsonResponse({}, safe=False)


### Store / Device Related ###
@csrf_exempt
def delete_all_stores(request):
    for store in Store.objects.all():
        store.delete()
    return JsonResponse({'success':True})
@csrf_exempt
def set_store_id(request):
    request.session['store_id'] = request.POST.get('store_id')
    return redirect("/")


### Goods Related ###
@csrf_exempt
def change_printer_file_location(request):
    if request.method == 'POST':
        new_path = request.POST.get('file_location')
        if not os.path.exists('config.json'):
            # If file does not exist, create it
            with open('config.json', 'w') as f:
                json.dump({}, f)
        with open('config.json', 'r') as f:
            loaded_data = json.load(f)
        loaded_data['file_location'] = new_path
        with open('config.json', 'w') as f:
            json.dump(loaded_data, f)
        return JsonResponse({'success': True}, safe=False)


@csrf_exempt
def create_or_change_printer_code_for_product(request):
    if request.method == 'POST':
        status, code = create_or_change_massak_codes_for_product(request.POST.get("id_out", None), request.POST.get("printer_code", None))
        if status is None:
            return JsonResponse({'success': False, 'message': f'Код {code} или Товар является неверным'}, safe=False)
        elif status is True:
            return JsonResponse({'success': True, 'message': 'Успешно'}, safe=False)
        else:
            return JsonResponse({'success': False, 'message': f'Код {code} уже занят продуктом {status}'}, safe=False)


@csrf_exempt
def create_or_change_short_name_for_product(request):
    print('asd')
    if request.method == 'POST':
        dreamkas_to_massaK.create_or_change_short_name_for_product(request.POST.get("id_out", None), request.POST.get("short_name", None))
        return JsonResponse({'success': True})


@csrf_exempt
def update_one_product(request, id_out):
    if request.method == 'GET':
        product_update(id_out)
        return redirect(reverse('products'))


@csrf_exempt
def display_all_goods_for_printer(request):
    if request.method == 'GET':
        return render(request, "mainapp/pages/display_products.html", {'list_of_goods': Product.objects.filter(barcodes__barcode__startswith='999999999')})


@csrf_exempt
def products(request):
    try:
        with open('config.json', 'r') as f:
            loaded_data = json.load(f)
            current_printer_file_location = loaded_data['file_location']
    except:
        current_printer_file_location = None
    current_shop_ids = []
    for shop_id in CURRENT_IDS.split(','):
        current_shop_ids.append(shop_id)
    if request.method == 'GET':
        products = Product.objects.all().order_by('name')
        page = Paginator(products, 250).page(request.GET.get("page", 1))
        return render(request, "mainapp/pages/display_products.html", {'list_of_goods': page, 'current_shop_ids': current_shop_ids, 'current_printer_file_location': current_printer_file_location})
    if request.method == 'POST':
        query = request.GET.get("query", None)
        if query:
            products = Product.objects.filter(
                Q(barcodes__barcode__icontains=query.lower()) | Q(name__icontains=query.lower())
            ).annotate(
                barcode_list=Concat('barcodes__barcode')
            ).order_by('name')
        else:
            products = Product.objects.all().order_by('name')
        page = Paginator(products, 250).page(request.GET.get("page", 1))
        products_list_contents = render_to_string('mainapp/parts/product_list_display.html', {'list_of_goods': page, 'current_shop_ids': current_shop_ids}, request)
        return JsonResponse({"products_list_contents": products_list_contents}, safe=False)


@csrf_exempt
def good_groups(request, keyword='inaaadex'):
    if request.method == 'POST':
        GoodGroups.update_good_groups()
        return redirect(request.path)
    return render(request, "mainapp/pages/good_groups.html", {'good_groups': GoodGroups.objects.all()})


@csrf_exempt
def update_all_goods(request):
    if request.method == 'POST' or request.method == 'GET':
        from mainapp.dreamkas_Products import Products_update
        Products_update()
        return redirect(reverse('products'))


@csrf_exempt
def generate_xlsx_file_for_printer(request):
    if request.method == 'POST' or request.method == 'GET':
        with open('config.json', 'r') as f:
            loaded_data = json.load(f)
        try:
            file_path = loaded_data['file_location']
        except:
            return JsonResponse({'success': False})
        create_excel_document_for_massaK(file_path)
        return JsonResponse({'success': True})


@csrf_exempt
def update_stores_and_devices(request):
    print('test')
    Store.update_stores_and_devices()
    return redirect(reverse('invoices'))


@csrf_exempt
def delete_all_suppliers(request):
    dreamkas_documents.delete_all_suppliers()
    return redirect(reverse('dreamkas_suppliers'))


@csrf_exempt
def delete_broken_suppliers(request):
    dreamkas_documents.delete_broken_suppliers()
    return redirect(reverse('dreamkas_suppliers'))


@csrf_exempt
def update_all_suppliers(request):
    dreamkas_documents.dreamkas_update_suppliers()
    map = []
    for supplier_name in Supplier_name.objects.all():
        if supplier_name.name not in map:
            map.append(supplier_name.name)
        else:
            supplier_name.name = supplier_name.name + (' ИНН: ') + str(supplier_name.supplier_fk.inn)
            print(supplier_name.name)
    return redirect(reverse('dreamkas_suppliers'))


@csrf_exempt
def get_index_page(request, keyword='index'):
    # aaaa = Product.update_products()
    return render(request, "mainapp/pages/index.html", )


@csrf_exempt
def get_all_gmail_messages(request):
    if request.method == 'GET':
        store_id = request.session['store_id']
        client_secret_json = Store.objects.filter(store_id=store_id).first().gmail_client_secret
        messages = get_gmail_messages(28, client_secret_json)
        return render(request, 'mainapp/pages/gmail_all_messages.html', {'gmail_all_messages': messages})


def get_suppliers_with_no_payment_time():
    no_payment_suppliers = Supplier.objects.filter(paymenttime__isnull=True)
    return no_payment_suppliers


@csrf_exempt
def test_page(request):
    good_groups = GoodGroups.objects.all()
    problems_goods_department = None
    # problems_goods_department = DREAM_KAS_API.goods_analyzer(date_from=(datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
    #                                                          date_to=datetime.datetime.today().strftime("%Y-%m-%d"))
    date = datetime.datetime.strftime(datetime.datetime.today(), "%d-%m-%Y")
    if os.path.exists(f"media/report_technical_files/report_goods_invalid_department_{date}.json"):
        with open(f"media/report_technical_files/report_goods_invalid_department_{date}.json", "rb") as file:
            problems_goods_department = json.load(file)
    return render(request, "mainapp/pages/testpage.html", {'good_groups': good_groups, 'problematic_goods_department': problems_goods_department})


@csrf_exempt
def edit_existing_report(request):
    report = datetime.datetime.strftime(datetime.datetime.today(), "%d-%m-%Y")
    if request.method - "POST":
        with open(f"media/report_technical_files/report_goods_invalid_department_{report}.json", "rb") as file:
            report_to_edit = json.load(file)
        good_name = None
        group_id = None
        good_id = request.POST.get('good_id')
        try:
            good_name = request.POST.get('good_name')
            print("good_name = " + good_name)

        except:
            pass
        try:
            group_id = request.POST.get('group_id')
            print("group_id = " + group_id)
        except:
            pass

        if group_id is not None:
            for item in report_to_edit:
                if item['id'] == good_id:
                    item['group'] = group_id
        if good_name is not None:
            for item in report_to_edit:
                if item['id'] == good_id:
                    item['good_name'] = good_name
        save_to_json(f"media/report_technical_files/report_goods_invalid_department_{report}.json", report_to_edit)
        return redirect(reverse('test_page'))


@csrf_exempt
def generate_invoice_report(request):
    if request.method == "POST":
        DailyInvoiceReport.generate_invoice_report()
        return JsonResponse({'success': True})


@csrf_exempt
def invoice_reports(request):
    if request.method == "GET":
        date = datetime.date.today()
        try:
            selected_invoice_report = DailyInvoiceReport.objects.filter(date=date)[0]
        except:
            selected_invoice_report = -1
        if str(date.month).__len__() == 1:
            date_month = "0" + str(date.month)
        else:
            date_month = str(date.month)
        if str(date.day).__len__() == 1:
            date_day = "0" + str(date.day)
        else:
            date_day = str(date.day)
        date_formatted = str(date.year) + "-" + date_month + "-" + date_day
        return render(request, 'mainapp/pages/invoice_reports.html', {'selected_invoice_report': selected_invoice_report, 'selected_date': date, 'date_formatted': date_formatted})
    if request.method == "POST":
        date = request.POST.get("date")
        try:
            selected_invoice_report = DailyInvoiceReport.objects.filter(date=date)[0]
        except:
            selected_invoice_report = -1
        if str(date.month).__len__() == 1:
            date_month = "0" + str(date.month)
        else:
            date_month = str(date.month)
        if str(date.day).__len__() == 1:
            date_day = "0" + str(date.day)
        else:
            date_day = str(date.day)
        date_formatted = str(date.year) + "-" + date_month + "-" + date_day
        return (JsonResponse
            ({
            'success': True,
            'selected_invoice_report': selected_invoice_report,
            'selected_date': date,
            'date_formatted': date_formatted,
        }))


@csrf_exempt
def generate_goods_report(request):
    if "media" not in os.listdir():
        os.mkdir("media")
    if "report_technical_files" not in os.listdir("media"):
        os.mkdir("media/report_technical_files")
    if request.method == "POST":
        date = datetime.datetime.strftime(datetime.datetime.today(), "%d-%m-%Y")
        if not os.path.exists(f"media/report_technical_files/report_goods_invalid_department_{date}.json"):
            DREAM_KAS_API.goods_analyzer(date_from=(datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                                         date_to=datetime.datetime.today().strftime("%Y-%m-%d"))
    return redirect(reverse('test_page'))


@csrf_exempt
def manual_invoice(request, keyword='index'):
    if request.method == "POST":
        if request.FILES:
            if request.POST.get("company", None):
                for key, val in COMPANIES:
                    result = send_document(company=key, file=request.FILES['file'], DREAM_KAS_API=DREAM_KAS_API)
                    if not result:
                        continue
                    else:
                        break
                for file_name in os.listdir('media/files'):
                    delete_file(f'media/files/{file_name}')

            # DREAM_KAS_API.patch_document("33816274",ooopartnergoods,"Test")
            # print(DREAM_KAS_API.patch_document("33816274",ooopartnergoods,"Test"))
            # return render(request, "mainapp/pages/index.html", {})
            #  def createdocument(self, dataofdocument, comment, partner_id, target_store_id=185449, positions=None):
    # return render(request, "mainapp/pages/index.html", {"COMPANIES": COMPANIES, 'table': table})
    return render(request, "mainapp/pages/manual_invoice.html", {"COMPANIES": COMPANIES, })


def test(request):
    create_excel_document_for_massaK()


@csrf_exempt
def create_pricing_order(request):
    if request.method == 'POST':
        DREAM_KAS_API.create_pricing_order(parentId=request.POST.get("parentId"))
        return redirect(reverse('invoices'))


@csrf_exempt
def invoices_update(request):
    if request.method == 'POST':
        dreamkas_documents.update_invoices()
        return redirect(reverse('invoices'))


def problematic_invoices():
    dublicate_invoices = Invoice.objects.filter(hide=False).order_by("-issue_date").values("number", "sum", "issue_date", "supplier").annotate(
        number_c=Concat("number"),
        id_2=Concat("id"),
        supplier_c=Concat("supplier"),
        sum_c=Concat("sum"),
        issue_date_c=Concat("issue_date"),
        count=Count("number")
    ).filter(count__gte=2).values(
        "id_2",
        "number_c",
        "supplier_c",
        "sum_c",
        "issue_date_c")
    possible_problematic_invoices_sum = Invoice.objects.filter(hide=False).order_by("-issue_date").values("number", "issue_date", "supplier").annotate(
        number_c=Concat("number"),
        id_2=Concat("id"),
        supplier_c=Concat("supplier"),
        sum_c=Value(0),
        issue_date_c=Concat("issue_date"),
        count=Count("number"),

    ).filter(count__gte=2).values(
        "id_2",
        "number_c",
        "supplier_c",
        "sum_c",
        "issue_date_c"
    )
    possible_problematic_invoices_supplier = Invoice.objects.filter(hide=False).order_by("-issue_date").values("number", "sum", "issue_date").annotate(
        number_c=Concat("number"),
        id_2=Concat("id"),
        supplier_c=Value('supplier'),
        sum_c=Concat("sum"),
        issue_date_c=Concat("issue_date"),
        count=Count("number")
    ).filter(count__gte=2).values(
        "id_2",
        "number_c",
        "supplier_c",
        "sum_c",
        "issue_date_c"
    )

    possible_problematic_invoices_sum |= dublicate_invoices
    possible_problematic_invoices_supplier |= possible_problematic_invoices_sum | dublicate_invoices

    # Get objects with ids provided from previous 3 actions:

    dupes = []
    for item in dublicate_invoices:
        group = []
        for id in item['id_2'].split(','):
            group.append(Invoice.objects.filter(id=id).get())
        dupes.append(group)

    sum_dupes = []
    for item in possible_problematic_invoices_sum:
        group = []
        for id in item['id_2'].split(','):
            group.append(Invoice.objects.filter(id=id).get())
        sum_dupes.append(group)

    supplier_dupes_objects = []
    for item in possible_problematic_invoices_supplier:
        group = []
        for id in item['id_2'].split(','):
            group.append(Invoice.objects.filter(id=id).get())
        supplier_dupes_objects.append(group)

    # Remove duplicates that can be cross-found.
    sum_dupes_result = []
    for item in sum_dupes:
        if item not in dupes:
            sum_dupes_result.append(item)

    supplier_dupes_result = []
    for item in supplier_dupes_objects:
        if item not in dupes and item not in sum_dupes:
            supplier_dupes_result.append(item)
    return {
        'duplicate_invoices': dupes,
        'possible_problematic_invoices_sum': sum_dupes_result,
        'possible_problematic_invoices_supplier': supplier_dupes_result
    }


@csrf_exempt
def find_invoice_duplicates(request):
    dreamkas_documents.find_duplicate_invoices()
    return redirect(reverse('invoices'))


def invoices(request):
    invoices = Invoice.objects.all().filter(hide=False).order_by("-issue_date")
    page = Paginator(invoices, 500).page(request.GET.get("page", 1))
    return render(request, 'mainapp/pages/invoices.html', {'invoices': page})


@csrf_exempt
def hide_invoice(request):
    if request.method == 'POST':
        id = request.POST.get("id_dreem")
        invoice = Invoice.objects.get(id_dreem=id)
        invoice.hide = True
        comment = request.POST.get("comment", None)
        invoice.hide_comment = str(comment)
        invoice.save()
        return JsonResponse({"success": True})


def invoice_origin_check():
    for item in Invoice.objects.all().order_by("-issue_date"):
        if item['created_via_program'] == False and item['created_via_program'] not in Supplier.objects.filter(name=item['supplier'])['invoice_non_program']:
            Supplier.objects.update(name=item['supplier'], defaults={
                'invoice_non_program': 'invoice_non_program' + item['id_dreem'] + ','})
        if item['created_via_program'] == True and item['created_via_program'] not in Supplier.objects.filter(name=item['supplier'])['invoice_program']:
            Supplier.objects.update(name=item['supplier'], defaults={
                'invoice_program': 'invoice_program' + item['id_dreem'] + ','})


##def goods_analyzer():

## Todo: for positions in http responce - concat all positions for last 90 days
##      then for positions get  dreamkas_good(position)
##      if position invomce_invoice > 1 year old or  doesn't exist - flag it as problematic. Comment - Good is never received via invoice or received long time ago.
##      if position Good Group = Null - flag it as problematic. Comment - Good is not assigned a group.
##      if position last sale is not in in concat all positions  - flag as problematic. Comment - Goods is not being sold.
##      if poisition income_invoice > 1 year old or doesn't exist and is in concat all positions - Flag is as double problematic. COmment - Goods is not received via invomce invoice or received long time ago BUT is being sold.
##      if position count < 0 - flag it as problematic. Comment - Negative good amount.
##      if position count < 0 and is in concat all position  - flag it as double problematic. Comment - Negative good amount of sold goods.
##      for each day in concat all positons - get amount of sales of position.
##      if sales_total / 90 * profit_per_good > average_profit_per_good - flag it as popular good.
##      More scenarios need to be check and done.
def dreamkas_invoice(request, invoiceid):
    print(invoiceid)
    invoice = DREAM_KAS_API.get_document(invoiceid)
    Invoice.objects.update_or_create(id_dreem=invoiceid, defaults={
        "invoice_status": True if invoice['status'] == "ACCEPTED" else False,
    })
    # try:
    #     Supplier.objects.update_or_create(name=invoice['sourceLegalEntity']['name'], defaults={
    #         'inn': invoice['sourceLegalEntity']['inn'],
    #     })
    # except Exception as ex:
    #     print(ex)
    priced = 0
    if invoice.get('children'):
        for item in invoice['children']:
            pricing_invoice = DREAM_KAS_API.get_document(item['id'])
            if pricing_invoice['status'] == "ACCEPTED":
                priced = pricing_invoice['id']
                for key, item_invoice in enumerate(invoice['positions']):
                    for item_pricing_invoice in pricing_invoice['positions']:
                        if item_invoice['productId'] == item_pricing_invoice['productId']:
                            invoice['positions'][key]['price'] = item_pricing_invoice['price']
                            break
                        else:
                            invoice['positions'][key]['price'] = 0
                    # invoice['positions'][key]['price'] = item['price']
                break

    if priced == 0:
        invoice['positions'] = DREAM_KAS_API.price_invoice(invoice['positions'])
    total = 0
    # for item in invoice['positions']:
    #        total = total + int(item['costWithTax']) / 1000
    print(invoice)
    i = 1
    for position in invoice['positions']:
        position['position_position'] = i
        i = i + 1
    return render(request, 'mainapp/pages/dreamkas_invoice.html', {'invoice': invoice, 'good_groups': GoodGroups.objects.all(), 'priced': priced, 'total': total})


@csrf_exempt
def dreamkas_suppliers(request):
    suppliers = Supplier.objects.all()
    return render(request, 'mainapp/pages/suppliers.html', {'suppliers': suppliers})  #


def dreamkas_supplier(request, supplier_data):
    if supplier_data.isdigit():
        supplier = Supplier.objects.get(inn=supplier_data)
    else:
        supplier = Supplier_name.objects.get(name=supplier_data).supplier_fk
    supplier_names = []
    for supplier_name_obj in supplier.supplier_name_set.all():
        supplier_names.append(supplier_name_obj.name)
    dreamkas_invoices = Invoice.objects.filter(hide=False).order_by("-issue_date")
    return render(request, 'mainapp/pages/dreamkas_supplier.html', {'supplier': supplier, 'dreamkas_invoices': dreamkas_invoices, 'supplier_names': supplier_names})

@csrf_exempt
def update_supplier_prefix(request):
    supplier_obj = Supplier.objects.get(id=request.POST.get('supplier_id'))
    supplier_obj.supplier_prefix = request.POST.get('supplier_prefix')
    supplier_obj.save()
    return JsonResponse({'success': True})


def invoices_diadoc(request):
    diadocinvoices = DiadocInvoice.objects.all().order_by("-issue_date")
    dreamkas_invoices = Invoice.objects.all()
    matching_invoices = []
    for diadoc_invoice in diadocinvoices:
        for dreamkas_invoice in dreamkas_invoices:
            if dreamkas_invoice.number == diadoc_invoice.number and dreamkas_invoice.issue_date == diadoc_invoice.issue_date and dreamkas_invoice.supplier == diadoc_invoice.kontragent:
                matching_invoices.append(dreamkas_invoice)
    page = Paginator(diadocinvoices, 1000).page(request.GET.get("page", 1))
    return render(request, 'mainapp/pages/invoices_diadoc.html', {'invoices': page, 'matching_invoices': matching_invoices})
@csrf_exempt
def delete_diadoc_invoices(request):
    for diadoc_invoice_obj in DiadocInvoice.objects.all():
        diadoc_invoice_obj.delete()
    return JsonResponse({'success' : True})

@csrf_exempt
def invoices_diadoc_v2(request):
    start_time = time.time()
    diadocinvoices = DiadocInvoice.objects.filter(store_id=request.session['store_id']).order_by("-issue_date")[:request.GET.get("page", 1)*1000]
    dreamkas_invoices = Invoice.objects.all()
    dreamkas_dict = {}
    for dreamkas_invoice in dreamkas_invoices:
        key = (dreamkas_invoice.number, dreamkas_invoice.issue_date, dreamkas_invoice.supplier)
        if key not in dreamkas_dict:
            dreamkas_dict[key] = []
        dreamkas_dict[key].append(dreamkas_invoice)
    # Initialize the list for matching invoices
    matching_invoices = []

    # Iterate through diadoc invoices and check if there are corresponding dreamkas invoices
    for diadoc_invoice in diadocinvoices:
        key = (diadoc_invoice.number, diadoc_invoice.issue_date, diadoc_invoice.kontragent)
        if key in dreamkas_dict:
            matching_invoices.extend(dreamkas_dict[key])
    print('6:', time.time() - start_time)
    page = Paginator(diadocinvoices, 1000).page(request.GET.get("page", 1))
    print('7:', time.time() - start_time)
    return render(request, 'mainapp/pages/invoices_diadoc.html', {'invoices': page, 'matching_invoices': matching_invoices})


@csrf_exempt
def diadoc_presets(request):
    if request.method == 'GET':
        diadoc_preset = DiadocPreset.objects.first()
        if diadoc_preset is None:
            create_diadoc_preset(request)
        diadoc_presets = DiadocPreset.objects.all()
        suppliers = Supplier.objects.all().order_by('supplier_name__name')
        stores = Store.objects.all()
        return render(request, 'mainapp/pages/diadoc_presets.html',
                      {'diadoc_preset': diadoc_preset,
                       'diadoc_presets': diadoc_presets,
                       'suppliers': suppliers,
                       'stores': stores})
    if request.method == 'POST':
        diadoc_preset = DiadocPreset.objects.filter(id=request.POST.get("preset_id")).first()
        diadoc_presets = DiadocPreset.objects.all()
        suppliers = Supplier.objects.all().order_by('supplier_name__name')
        stores = Store.objects.all()
        diadoc_preset_contents = render_to_string('mainapp/parts/diadoc_preset_display.html', {'diadoc_preset': diadoc_preset,
                                                                                               'diadoc_presets': diadoc_presets, 'suppliers': suppliers, 'stores': stores})
        return JsonResponse({'diadoc_preset_contents': diadoc_preset_contents}, safe=False)


@csrf_exempt
def create_diadoc_preset(request):
    if request.method == 'POST':
        diadoc_preset = DiadocPreset.objects.create(preset_name='Новый шаблон')
        diadoc_presets = DiadocPreset.objects.all()
        suppliers = Supplier.objects.all()
        diadoc_preset_contents = render_to_string('mainapp/parts/diadoc_preset_display.html', {'diadoc_preset': diadoc_preset,
                                                                                               'diadoc_presets': diadoc_presets, 'suppliers': suppliers})
        return JsonResponse({'diadoc_preset_contents': diadoc_preset_contents}, safe=False)


@csrf_exempt
def update_diadoc_preset(request):
    diadoc_preset = DiadocPreset.objects.get(id=request.POST.get('preset_id'))
    what_to_change_to = request.POST.get('what_change_to')
    if what_to_change_to == '':
        what_to_change_to = None
    if request.POST.get('obj_to_change') != 'store_destination_fk':
        setattr(diadoc_preset, request.POST.get('obj_to_change'), what_to_change_to)
    if request.POST.get('obj_to_change') == 'supplier_fk_id':
        diadoc_preset.supplier_inn = Supplier.objects.get(id=what_to_change_to).inn
        diadoc_preset.supplier_prefix = Supplier.objects.get(id=what_to_change_to).supplier_prefix
        diadoc_preset.supplier_name = Supplier.objects.get(id=what_to_change_to).supplier_name_set.first().name
    if request.POST.get('obj_to_change') == 'store_destination_fk':
        diadoc_preset.store_destination_fk = Store.objects.filter(store_id=what_to_change_to).first()
        if diadoc_preset.store_destination_fk is None:
            diadoc_preset.store_destination_fk = Store.objects.filter(id=what_to_change_to)
    diadoc_preset.save()

    return JsonResponse({'success': True})


@csrf_exempt
def show_duplicate_diadoc_invoices(request):
    diadoc_id_map = []
    diadoc_dupe_map = []
    for diadoc_invoice_obj in DiadocInvoice.objects.all():
        if diadoc_invoice_obj.diadoc_id not in diadoc_id_map:
            diadoc_id_map.append(diadoc_invoice_obj.diadoc_id)
            continue
        diadoc_dupe_map.append(diadoc_invoice_obj.diadoc_id)

    print(diadoc_dupe_map)
    return redirect(reverse('invoices_diadoc'))


@csrf_exempt
def update_item_group(request):
    if request.method == 'POST':
        good_id = request.POST.get("good_id")
        group_id = request.POST.get("group_id")
        print(good_id)
        print(group_id)
        DREAM_KAS_API.update_good(good_id, group_id=group_id)
        return JsonResponse({})


@csrf_exempt
def update_diadoc_invoices(request):
    if request.method == 'POST':
        try:
            DiadocInvoice.update_diadoc_invoices()
            return JsonResponse({'success': True})
        except Exception as Ex:
            print(Ex)
            return JsonResponse({'success': False})


@csrf_exempt
def update_diadoc_invoices_v2(request):
    if request.method == 'POST':
        store_id = request.session['store_id']
        diadoc_id = Store.objects.get(store_id=request.session['store_id']).diadoc_id
        try:
            diadoc_to_dreamkas.update_diadoc_invoices_v2(diadoc_id, store_id)
            return JsonResponse({'success': True})
        except Exception as Ex:
            print(Ex)
            return JsonResponse({'success': False})


@csrf_exempt
def gmail_messages(request):
    gmail_messages = Gmail_Messages.objects.all().filter(message_store_id=request.session['store_id']).order_by("-message_date")
    return render(request, 'mainapp/pages/gmail_messages.html', {'gmail_messages': gmail_messages})


@csrf_exempt
def update_inventory_check(request, inventory_check_id):  # document_id
    if request.method == 'POST':
        json_data_list = json.loads(request.body)
        inventory_check = DREAM_KAS_API.update_inventory_check(inventory_check_id, json_data_list)
        for item in json_data_list:
            print(item['data-id'], item['value'])

    return JsonResponse({'success': True})


@csrf_exempt
def inventory_check(request, inventory_check_id):
    if request.method == 'GET':
        inventory_check_document = DREAM_KAS_API.inventory_check(inventory_check_id)
        return render(request, 'mainapp/pages/inventory_check.html', {'inventory_check_id': inventory_check_id, "inventory_check_document": inventory_check_document})


@csrf_exempt
def inventory_checks(request):
    if request.method == 'GET':
        inventory_checks = DREAM_KAS_API.get_inventory_checks()
        return render(request, 'mainapp/pages/inventory_checks.html', {'inventory_checks': inventory_checks})


@csrf_exempt
def merge_inventory_check_items(request, inventory_check_id):
    if request.method == 'GET':
        responce = DREAM_KAS_API.merge_inventory_check_items(inventory_check_id)
        return render(request, 'mainapp/pages/inventory_checks.html', {'inventory_checks': inventory_checks})

@csrf_exempt
def delete_gmail_messages(request):
    for msg in Gmail_Messages.objects.all():
        msg.delete()
    return JsonResponse({'success':True})
@csrf_exempt
def update_gmail_messages(request):
    if request.method == 'POST':
        client_secret_json = Store.objects.filter(store_id=request.session['store_id']).first().gmail_client_secret
        mainapp.gmail_invoices.update_gmail_messages(client_secret_json)
    return redirect(reverse('gmail_messages'))


class PresetGmailForm(forms.ModelForm):
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.helper = FormHelper(self)
    #     self.helper.include_media = False
    #     self.helper.form_method = 'post'
    document_date_between_second = forms.CharField()

    class Meta:
        model = PresetGmail
        fields = "__all__"


@csrf_exempt
def create_gmail_preset(request):
    if request.method == 'GET':
        gmail_preset = PresetGmail.objects.create(preset_name='Новый шаблон')
        gmail_presets = PresetGmail.objects.all()
        return render(request, 'mainapp/pages/gmail_presets.html',
                      {'gmail_preset': gmail_preset,
                       'gmail_presets': gmail_presets})
    if request.method == 'POST':
        gmail_preset = PresetGmail.objects.create(preset_name='Новый шаблон')
        gmail_presets = PresetGmail.objects.all()
        suppliers = Supplier.objects.all().order_by('supplier_name__name')
        gmail_preset_contents = render_to_string('mainapp/parts/gmail_preset_display.html', {'gmail_preset': gmail_preset,
                                                                                             'gmail_presets': gmail_presets, 'suppliers': suppliers})
        return JsonResponse({'gmail_preset_contents': gmail_preset_contents}, safe=False)


@csrf_exempt
def update_gmail_preset(request):
    gmail_preset = PresetGmail.objects.get(id=request.POST.get('preset_id'))
    what_to_change_to = request.POST.get('what_change_to')
    if what_to_change_to == '':
        what_to_change_to = None
    setattr(gmail_preset, request.POST.get('obj_to_change'), what_to_change_to)
    if request.POST.get('obj_to_change') == 'supplier_fk_id':
        gmail_preset.supplier_inn = Supplier.objects.get(id=what_to_change_to).inn
        gmail_preset.supplier_prefix = Supplier.objects.get(id=what_to_change_to).supplier_prefix
        gmail_preset.supplier_name = Supplier.objects.get(id=what_to_change_to).supplier_name_set.first().name
    gmail_preset.save()
    return JsonResponse({'success': True})


@csrf_exempt
def gmail_presets(request):
    if request.method == 'GET':
        gmail_preset = PresetGmail.objects.first()
        gmail_presets = PresetGmail.objects.all()
        suppliers = Supplier.objects.all().order_by('supplier_name__name')
        stores = Store.objects.all()
        return render(request, 'mainapp/pages/gmail_presets.html',
                      {'gmail_preset': gmail_preset,
                       'gmail_presets': gmail_presets, 'suppliers': suppliers, 'stores': stores})
    if request.method == 'POST':
        gmail_preset = PresetGmail.objects.filter(id=request.POST.get("preset_id")).first()
        gmail_presets = PresetGmail.objects.all()
        suppliers = Supplier.objects.all().order_by('supplier_name__name')
        stores = Store.objects.all()
        gmail_preset_contents = render_to_string('mainapp/parts/gmail_preset_display.html', {'gmail_preset': gmail_preset,
                                                                                             'gmail_presets': gmail_presets, 'suppliers': suppliers, 'stores': stores})
        return JsonResponse({'gmail_preset_contents': gmail_preset_contents}, safe=False)


@csrf_exempt
def update_store(request):
    store = Store.objects.get(id=request.POST.get('store_id'))
    what_to_change_to = request.POST.get('what_change_to')
    if what_to_change_to == '':
        what_to_change_to = None
    setattr(store, request.POST.get('obj_to_change'), what_to_change_to)
    store.save()
    return JsonResponse({'success': True})


@csrf_exempt
def stores(request):
    if request.method == 'GET':
        store = Store.objects.first()
        stores = Store.objects.all()
        return render(request, 'mainapp/pages/stores.html',
                      {'store': store,
                       'stores': stores})
    if request.method == 'POST':
        store = Store.objects.filter(id=request.POST.get("store_id")).first()
        stores = Store.objects.all()
        store_contents = render_to_string('mainapp/parts/store_display.html', {'store': store,
                                                                               'stores': stores})
        return JsonResponse({'store_contents': store_contents}, safe=False)
    # if request.method == 'GET':
    #     gmail_preset = PresetGmail.objects.first()
    #     gmail_presets = PresetGmail.objects.all()
    #
    #     preset_gmail_form = PresetGmailForm(instance=gmail_preset)
    #
    #     gmail_preset_next = PresetGmail.objects.filter(id__gt=gmail_preset.id).first()
    #     gmail_preset_prev = PresetGmail.objects.filter(id__lt=gmail_preset.id).first()
    #     return render(request,'mainapp/pages/gmail_presets.html',{"preset_gmail_form": preset_gmail_form, 'gmail_preset': gmail_preset, 'gmail_preset_next':gmail_preset_next, 'gmail_preset_prev':gmail_preset_prev, 'gmail_presets' : gmail_presets})
    # if request.method == 'POST':
    #
    #     gmail_preset = PresetGmail.objects.get(id=request.POST.get("preset_id"))
    #     preset_gmail_form = PresetGmailForm(request.POST, instance=gmail_preset)
    #     if preset_gmail_form.is_valid():
    #         preset_gmail_form.save()
    #
    #     gmail_presets = PresetGmail.objects.all()
    #     gmail_preset_next = PresetGmail.objects.filter(id__gt=gmail_preset.id).first()
    #     gmail_preset_prev = PresetGmail.objects.filter(id__lt=gmail_preset.id).first()
    #     return render(request,'mainapp/pages/gmail_presets.html',{'gmail_preset': gmail_preset, 'gmail_preset_next':gmail_preset_next, 'gmail_preset_prev':gmail_preset_prev, 'gmail_presets' : gmail_presets})

@csrf_exempt
def create_documents_from_gmail_message_v2(request):
    if request.method == 'POST':
        message_id = request.POST.get("gmail_message_id")
        query_params = {
            "id": request.POST.get("gmail_message_id")
        }
        store_id = request.session['store_id']
        msg_sender = get_document_and_attachments_from_gmail(message_id, store_id)
        links = []
        for attachment in os.listdir("media/gmail_invoices"):
            try:
                links.append(gmail_to_dreamkas.create_document_from_excel(attachment,msg_sender))
            except:
                continue
        for attachment in os.listdir("media/gmail_invoices"):
            os.remove("media/gmail_invoices/" + attachment)
        return JsonResponse({'success':True, 'links':links})



@csrf_exempt
def create_documents_from_gmail_message(request):
    if request.method == 'POST':
        result = None
        gmail = simplegmail.Gmail()
        query_params = {
            "id": request.POST.get("gmail_message_id")
        }
        message = gmail.get_messages(query=construct_query(query_params))
        if len(os.listdir("media/gmail_invoices/")) > 1:
            print("Папка не пуста. Все файлы в media/gmail_invoices/ будут удалены")
            for file in os.listdir("media/gmail_invoices/"):
                os.remove("media/gmail_invoices/" + file)
        if message[0].attachments:
            for attachment in message[0].attachments:
                attachment.save("media/gmail_invoices/" + attachment.filename, overwrite=True)
                if attachment.filename.endswith(".rar") or attachment.filename.endswith(".zip"):
                    try:
                        with py7zr.SevenZipFile('media/gmail_invoices/' + attachment.filename, mode='r') as z:
                            z.extractall('media/gmail_invoices/')
                            os.remove('media/gmail_invoices/' + attachment.filename)
                    except Exception as ex:
                        print(ex)
                        try:
                            os.remove('media/gmail_invoices/' + attachment.filename)
                        except:
                            pass

        for attachment in os.listdir("media/gmail_invoices"):
            try:
                document = create_document_from_excel("media/gmail_invoices/" + attachment)
                if document == None:
                    continue
                try:
                    result = DREAM_KAS_API.createdocument(
                        document["document_date"],
                        "Документ Создан Автоматически. Источник - Почта",
                        document["partnerid"],
                        str(document["document_number"]),
                        positions=document["resulting_goods_list"],
                        target_store_id=document['target_store_id'],
                    )
                    webbrowser.open_new_tab('https://kabinet.dreamkas.ru/app/#!/documents/card~2F' + result['id'])
                    supplier, supplier_create = Supplier.objects.update_or_create(name=result['sourceLegalEntity']['name'], defaults={})
                    Invoice.objects.update_or_create(id_dreem=result['id'], defaults={
                        'number': result['num'],
                        'supplier': result['sourceLegalEntity']['name'],
                        'supplier_fk': supplier,
                        'sum': Decimal(int(result['totalSum']) / 100),
                        'issue_date': result['issueDate'],
                        'invoicetype': True if "НАЛ" in result['num'] else False,
                        'overdue': False,
                        'invoice_status': False,
                        'printed': False,
                        'hide': False,
                        'created_via_program': True,
                    })
                    Invoice_obj = Invoice.objects.get(id_dreem=result['id'])
                    for position in result['positions']:
                        position = Position.objects.create(
                            position_id=position['productId'] if position['productId'] else position['name'],
                            position_amount=Decimal(Decimal(position['amount']) / 100),
                            position_sum=Decimal(int(result['totalSum']) / 100)
                        )
                        Invoice_obj.positions.add(position)
                except Exception as ex:
                    print("Failed to send document")
                    print(ex)
            except Exception as ex:
                print(ex)
            try:
                os.remove("media/gmail_invoices/" + attachment)
            except Exception as ex:
                print(ex)
        print("send_document_result_done")
        if result is not None:
            return redirect(reverse('gmail_messages'))
        else:
            print("Что-то пошло не так. НУЖНО ЧИНИТЬ. ЧЕРТ.")


@csrf_exempt
def show_excel_document(request):
    if request.method == "POST":
        if request.FILES:
            result = request.FILES['file']
            file_name = default_storage.save(result.name, result)
            file_path = default_storage.path(file_name)
            wb = xlrd.open_workbook(file_path, encoding_override='cp1251')
            pandas_document = pandas.read_excel(wb, keep_default_na=False, header=None)
            return JsonResponse({"document_html": pandas_document.to_json(orient='index')}, safe=False)
    # document = document.to_html()
    return render(request, 'mainapp/parts/show_document.html')


@csrf_exempt
def create_document_from_diadoc(request):
    if request.method == 'POST':
        file_name = f'media/diadoc_files/{request.POST.get("filename")}.xml'
        DIADOC_API.download(url=request.POST.get("link_document_attachment"), file_name=file_name)
        # with open(file_name,"r") as f:
        f = open(file_name, "r")
        file = UploadedFile(f, f.name)

        for key, val in COMPANIES:
            result = send_document(company=key, file=file, DREAM_KAS_API=DREAM_KAS_API)
            if not result:
                continue
            else:
                # Invoice.objects.update_or_create(id_dreem=result['id'], defaults={
                #     'number': result['num'],
                #     'sum': Decimal(int(result['totalSum']) / 100),
                #     'issue_date': result['issueDate']})
                break
        for file_name in os.listdir('media/files'):
            delete_file(f'media/files/{file_name}')
        import webbrowser
        # if result is None:
        #     return {"status": result}
        # if result["id"] is not None:

        # if result is not None:
        supplier, supplier_create = Supplier.objects.update_or_create(name=result['sourceLegalEntity']['name'], defaults={})
        Invoice.objects.update_or_create(id_dreem=result['id'], defaults={
            'number': result['num'],
            'supplier': result['sourceLegalEntity']['name'],
            'supplier_fk': supplier,
            'sum': Decimal(int(result['totalSum']) / 100),
            'issue_date': result['issueDate'],
            'invoicetype': True if "НАЛ" in result['num'] else False,
            'overdue': False,
            'invoice_status': False,
            'printed': False,
            'hide': False,
            'created_via_program': True,
        })
        positions = []
        Invoice_obj = Invoice.objects.get(id_dreem=result['id'])
        for position in result['positions']:
            position = Position.objects.create(
                position_id=position['productId'],
                position_amount=Decimal(Decimal(position['amount']) / 100),
                position_sum=Decimal(int(result['totalSum']) / 100)
            )
            Invoice_obj.positions.add(position)
        # return (webbrowser.open_new_tab("mainapp/pages/dreamkas_invoice/" + str(result['id'])))
        # return redirect(reverse('dreamkas_invoice', args=[result['id']]))
        return redirect(reverse('invoices_diadoc'), webbrowser.open_new_tab('https://kabinet.dreamkas.ru/app/#!/documents/card~2F' + result['id']))
        # else:
        #    return JsonResponse({"status": True if result else False}, safe=True)


@csrf_exempt
def create_document_from_diadoc_v2(request):
    if request.method == 'POST':
        diadoc_document_id = request.POST.get("diadoc_document_id")
        diadoc_user_id = Store.objects.get(store_id=request.session['store_id']).diadoc_id
        links = []
        try:
            links.append(create_invoice_from_diadoc_document_v2(diadoc_user_id, diadoc_document_id))
        except:
            return JsonResponse({'success':False})


def test_union(request):
    invoices = Invoice.objects.all()

    from collections import defaultdict
    groups = defaultdict(list)
    for obj in invoices:
        groups[obj.supplier].append(obj)
    invoices = list(groups.items())
    print(invoices)
    return render(request, 'mainapp/pages/invoice.html', {'invoices': invoices})


def save_file(json_string):
    with open('json_data.json', 'w') as outfile:
        json.dump(json_string, outfile)


def read_file():
    data = None
    with open('json_data.json') as json_file:
        data = json.load(json_file)
        print(data)
    return data


@csrf_exempt
def paid_update(request):
    invoice_id = request.POST.get('id', None)
    paid = int(request.POST.get('paid', 0))
    print(request.POST)
    if invoice_id:
        if paid == 1:
            paid = True
        else:
            paid = False

        invoice = Invoice.objects.get(id=invoice_id)
        invoice.paid = paid
        invoice.save()
    return JsonResponse({'success': True})


@csrf_exempt
def good_groups_user_form(request):
    id = request.POST.get('id', None)
    field_name = request.POST.get('field_name', None)
    field_value = request.POST.get('field_value', None)
    print(id, field_name, field_value)
    if id:
        good_group = GoodGroups.objects.get(id=id)
        if not field_value or field_value == "undefined":
            field_value = 0
        good_group.__setattr__(field_name, field_value)
        good_group.save()
        print(good_group.__dict__)
    return JsonResponse({'success': True})


@csrf_exempt
def supplier_paymenttime_update(request):
    id = request.POST.get('id', None)
    paymenttime = request.POST.get('paymenttime', None)
    try:
        paymenttime = int(paymenttime)
        Supplier.objects.update_or_create(id=id, defaults={
            'paymenttime': paymenttime,
        })
        return JsonResponse({'success': True})
    except:
        return JsonResponse({"success": False, "message": "Incorrect format"})

# @csrf_exempt
# def save_product(request):
#     price = request.POST.get("price", None)
#     code = request.POST.get("code", None)
#     print(price, code)
#     if price and code:
#         product = Product.objects.filter(barcodes__code=code).first()
#         if product:
#             session = HTMLSession()
#             product_api = session.get(f'https://kabinet.dreamkas.ru/api/products/{product.id_out}',
#                                       auth=HTTPBasicAuth(LOGIN, PASSWORD)).json()
#
#             prices = product_api.get("prices", [])
#             for price_api in prices:
#                 price_api['value'] = price
#             product_api['prices'] = prices
#             result = session.patch(f'https://kabinet.dreamkas.ru/api/products/{product.id_out}', json=product_api,
#                                    auth=HTTPBasicAuth(LOGIN, PASSWORD))
#             print(result.status_code)
#             return JsonResponse({'status': True}, safe=False)
#     return JsonResponse({'status': False}, safe=False)
#
#
# def update_product(request):
#     session = HTMLSession()
#
#     array_result = []
#     offset = 0
#     result = session.get(f'https://kabinet.dreamkas.ru/api/products?limit=1000&offset={offset}',
#                          auth=HTTPBasicAuth(LOGIN, PASSWORD)).json()
#
#     while True:
#         offset += 1000
#         if result:
#             result = session.get(f'https://kabinet.dreamkas.ru/api/products?limit=1000&offset={offset}',
#                                  auth=HTTPBasicAuth(LOGIN, PASSWORD)).json()
#             array_result += result
#         else:
#             break
#         # print(array_result)
#     counter = 0
#     for product_arr in array_result:
#         counter += 1
#         print(counter)
#         product, product_bool = Product.objects.update_or_create(id_out=product_arr.get('id'), defaults={
#             'name': product_arr.get('name', None),
#             'type': product_arr.get('type', None),
#             'price': Decimal(product_arr.get('price', 0) if product_arr.get('price', None) else 0),
#         })
#         for price in product_arr.get('prices', []):
#             Prices.objects.update_or_create(product_fk_id=product.id, deviceid=price.get('deviceId', None),
#                                             defaults={'value': price.get('value')})
#         for barcode in product_arr.get('barcodes', []):
#             Barcodes.objects.get_or_create(product_fk_id=product.id, code=barcode)
#     print(len(array_result))
#     # print(array_result)
