import datetime
import json
import os
import pickle
import webbrowser
from dataclasses import dataclass
from decimal import Decimal
import py7zr
import pandas
import requests
import simplegmail
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.db.models import Sum, Value
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from simplegmail import gmail
from simplegmail.query import construct_query

from dremkas.settings import DREAM_KAS_API, DIADOC_API
from mainapp.models import Invoice, GoodGroups, DiadocInvoice, Supplier, Gmail_Messages, Position, DailyInvoiceReport
from .gmail_invoices import create_document_from_excel, get_gmail_messages
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
    # template = '%(function)s(%(distinct)s%(expressions)s)'
    allow_distinct = True

    def __init__(self, expression, distinct=False, **extra):
        super(Concat, self).__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
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


@csrf_exempt
def get_index_page(request, keyword='index'):




    # probelems = problematic_invoices()
    # probelems_suppliers = get_suppliers_with_no_payment_time()
    # problems_goods_department = DREAM_KAS_API.goods_analyzer(date_from=(datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
    #                                                          date_to=datetime.datetime.today().strftime("%Y-%m-%d"))
    #
    #


    # ,devices=[31391,34796,163617]
    # invoice_report()
    # problems_goods = DREAM_KAS_API.goods_analyzer(date_from=datetime.datetime.now() - datetime.timedelta(days=1), date_to=datetime.datetime.now(),devices=[31391,34796,163617])

    return render(request, "mainapp/pages/index.html",)
                  #{'problematic_invoices': probelems, 'problematic_suppliers': probelems_suppliers, 'problematic_goods_department': problems_goods_department})


@csrf_exempt
def get_all_gmail_messages(request):
    if request.method == 'GET':
        messages = get_gmail_messages(120)
        return render(request, 'mainapp/pages/gmail_all_messages.html', {'gmail_all_messages': messages})


@csrf_exempt
def good_groups(request, keyword='inaaadex'):
    if request.method == 'POST':
        GoodGroups.update_good_groups()
        return redirect(request.path)
    # list_of_groups_from_dreamkas = DREAM_KAS_API.get_groups()['categories']
    # file = 0
    # try:
    #     list_from_file = pickle.load(open("D:\groups", "rb"))
    #     file = 1
    # except:
    #     file = 0
    # compare_list_from_file = []
    # compare_list_from_dreamkas = []
    # if file == 1:
    #     for item in list_from_file:
    #         compare_list_from_file.append({'id': item['id']})
    #     for item in list_of_groups_from_dreamkas:
    #         compare_list_from_dreamkas.append({'id': item['id']})
    #     print(compare_list_from_file)
    #     print(compare_list_from_dreamkas)
    #     for item in compare_list_from_dreamkas:
    #         if item not in compare_list_from_file:
    #             compare_list_from_file.append({'name': item['name'], 'id': item['id'], 'pricingpercent': '0', 'roundnumber': '0', 'rule': '0'})
    # if file == 0:
    #     for item in list_of_groups_from_dreamkas:
    #         compare_list_from_file.append({'name': item['name'], 'id': item['id'], 'pricingpercent': '0', 'roundnumber': '0', 'rule': '0'})

    # pickle.dump(compare_list_from_file, open(f"D:\groups", "wb"))
    # list_from_file = pickle.load(open("D:\groups", "rb"))

    # return render(request, "mainapp/pages/good_groups.html", {'list_from_file': list_from_file, 'good_groups': GoodGroups.objects.all()})
    return render(request, "mainapp/pages/good_groups.html", {'good_groups': GoodGroups.objects.all()})


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
def generate_daily_report(request):
    DailyInvoiceReport.generate_invoice_report()
@csrf_exempt
def reports(request):
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
        return render(request, 'mainapp/pages/reports.html', {'selected_invoice_report': selected_invoice_report, 'selected_date' : date, 'date_formatted' : date_formatted})
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
        return {
            'selected_invoice_report' : selected_invoice_report, 'selected_date' : date, 'date_formatted' : date_formatted,
        }
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
    documents = DREAM_KAS_API.get_documents(limit=1000)
    count = 0
    for document in documents:
        count += 1
        print(count, document)
        Invoice.objects.update_or_create(id_dreem=document['id'], defaults={
            'number': document['num'],
            'supplier': document['sourceName'],
            'sum': Decimal(int(document['totalSum']) / 100),
            'issue_date': document['issueDate'],
            # 'issue_date': str(document['issueDate'].split("-")[2])+"."+str(document['issueDate'].split("-")[1])+"."+str(document['issueDate'].split("-")[0])
            # 'issue_date': document['issueDate'],
        })

    return JsonResponse({}, safe=False)


@csrf_exempt
def create_pricing_order(request):
    if request.method == 'POST':
        DREAM_KAS_API.create_pricing_order(parentId=request.POST.get("parentId"))
        return redirect(reverse('invoices'))


@csrf_exempt
def invoices_update(request):
    if request.method == 'POST':
        Invoice.update_invoices()
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


# def problematic_invoices():
#     dublicate_invoices = Invoice.objects.filter(hide=False).values("number", "sum", "issue_date", "supplier").annotate(
#         number_c=Concat("number"),
#         id_2=Concat("id"),
#         supplier_c=Concat("supplier"),
#         sum_c=Concat("sum"),
#         issue_date_c=Concat("issue_date"),
#         count=Count("number")
#     ).filter(count__gte=2).values(
#         "id_2",
#         "number_c",
#         "supplier_c",
#         "sum_c",
#         "issue_date_c").aggregate(id3=Concat('id_2'))['id3'].split(',')  # після валуес можна спокійно робити ордер бай.
#     possible_problematic_invoices_sum = Invoice.objects.values("number", "issue_date", "supplier").annotate(
#         number_c=Concat("number"),
#         id_2=Concat("id"),
#         supplier_c=Concat("supplier"),
#         issue_date_c=Concat("issue_date"),
#         count=Count("number")
#     ).filter(count__gte=2).values(
#         "id_2",
#         "number_c",
#         "supplier_c",
#         "issue_date_c").aggregate(id3=Concat('id_2'))['id3'].split(',')
#     possible_problematic_invoices_supplier = Invoice.objects.values("number", "sum", "issue_date").annotate(
#         number_c=Concat("number"),
#         id_2=Concat("id"),
#         sum_c=Concat("sum"),
#         issue_date_c=Concat("issue_date"),
#         count=Count("number")
#     ).filter(count__gte=2).values(
#         "id_2",
#         "number_c",
#         "sum_c",
#         "issue_date_c").aggregate(id3=Concat('id_2'))['id3'].split(',')
#
#     possible_problematic_invoices_sum = list(set(possible_problematic_invoices_sum) - set(dublicate_invoices))
#     possible_problematic_invoices_supplier = list(set(possible_problematic_invoices_supplier) - set(possible_problematic_invoices_sum) - set(dublicate_invoices))
#
#     return {
#         'duplicate_invoices': Invoice.objects.filter(id__in=dublicate_invoices),
#         'possible_problematic_invoices_sum': Invoice.objects.filter(id__in=possible_problematic_invoices_sum),
#         'possible_problematic_invoices_supplier': Invoice.objects.filter(id__in=possible_problematic_invoices_supplier)
#     }


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
    try:
        Supplier.objects.update_or_create(name=invoice['sourceLegalEntity']['name'], defaults={
            'inn': invoice['sourceLegalEntity']['inn'],
        })
    except Exception as ex:
        print(ex)
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
    return render(request, 'mainapp/pages/dreamkas_invoice.html', {'invoice': invoice, 'good_groups': GoodGroups.objects.all(), 'priced': priced, 'total': total})


@csrf_exempt
def dreamkas_suppliers(request):
    suppliers = Supplier.objects.all()
    return render(request, 'mainapp/pages/suppliers.html', {'suppliers': suppliers})  #


def dreamkas_supplier(request, supplier_name):
    supplier = Supplier.objects.get(name=supplier_name)
    dreamkas_invoices = Invoice.objects.filter(hide=False).order_by("-issue_date")
    return render(request, 'mainapp/pages/dreamkas_supplier.html', {'supplier': supplier, 'dreamkas_invoices': dreamkas_invoices})


def invoices_diadoc(request):
    diadocinvoices = DiadocInvoice.objects.all().order_by("-issue_date")
    dreamkas_invoices = Invoice.objects.all()
    matching_invoices = []
    for diadoc_invoice in diadocinvoices:

        # dreamkas_invoices = Invoice.objects.filter(issue_date=diadoc_invoice.issue_date, supplier=diadoc_invoice.kontragent, number=diadoc_invoice.number).first()
        # if dreamkas_invoices != None:
        #     print(dreamkas_invoices.issue_date, dreamkas_invoices.supplier, dreamkas_invoices.number    )
        #     matching_invoices.append(dreamkas_invoice)
        for dreamkas_invoice in dreamkas_invoices:
            if dreamkas_invoice.number == diadoc_invoice.number and dreamkas_invoice.issue_date == diadoc_invoice.issue_date and dreamkas_invoice.supplier == diadoc_invoice.kontragent:
                matching_invoices.append(dreamkas_invoice)
    return render(request, 'mainapp/pages/invoices_diadoc.html', {'invoices': diadocinvoices, 'matching_invoices': matching_invoices})


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
def gmail_messages(request):
    gmail_messages = Gmail_Messages.objects.all().order_by("-message_date")

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
def update_gmail_messages(request):
    if request.method == 'POST':
        Gmail_Messages.update_gmail_messages()
    return redirect(reverse('gmail_messages'))


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
                        positions=document["resulting_goods_list"])
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
            pandas_document = pandas.read_excel(result, keep_default_na=False, header=None).transpose()
            return JsonResponse({"document_html": pandas_document.to_html()}, safe=False)
    # document = document.to_html()
    return render(request, 'mainapp/pages/supplier_ruleset_editor.html')


@csrf_exempt
def create_document_from_diadoc(request):
    if request.method == 'POST':
        file_name = f'media/diadoc_files/{request.POST.get("diadoc_id")}.xml'
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
