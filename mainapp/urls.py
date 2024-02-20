from django.urls import path
from mainapp.views import get_index_page, test, invoices, manual_invoice, good_groups, test_union, paid_update, Preset, good_groups_user_form, invoices_update, create_pricing_order, invoices_diadoc, \
    update_diadoc_invoices, create_document_from_diadoc, dreamkas_invoice, update_item_group, dreamkas_suppliers, dreamkas_supplier, supplier_paymenttime_update, gmail_messages, update_gmail_messages, \
    inventory_checks, update_inventory_check, inventory_check, merge_inventory_check_items, create_documents_from_gmail_message, show_excel_document, hide_invoice, get_all_gmail_messages, test_page, \
    generate_goods_report, edit_existing_report, invoice_reports, generate_invoice_report, update_all_goods, generate_xlsx_file_for_printer, display_all_goods_for_printer, products, \
    update_one_product, create_or_change_printer_code_for_product, change_printer_file_location, delete_all_suppliers, update_all_suppliers, set_store_id, update_stores_and_devices, \
    find_invoice_duplicates, delete_broken_suppliers

urlpatterns = [
    path('', get_index_page, name="index"),
    # path('save_product/', save_product, name="save_product"),
    # path('update_product/', update_product, name="update_product"),
    path('test/', test, name="test"),
    ##STORE and DEVICES
    path('set_store_id/', set_store_id, name="set_store_id"),
    path('update_stores_and_devices/', update_stores_and_devices, name="update_stores_and_devices"),

    path('manual_invoice/', manual_invoice, name="manual_invoice"),
    path('test_page/', test_page, name="test_page"),
    path('good_groups/', good_groups, name="good_groups"),
    path('generate_goods_report/', generate_goods_report, name="generate_goods_report"),
    path('invoice_reports/', invoice_reports, name="overall_reports"),
    path('generate_invoice_report/',generate_invoice_report, name='generate_invoice_report'),
    path('update_all_goods/',update_all_goods, name='update_all_goods'),
    path('display_all_goods_for_printer/',display_all_goods_for_printer, name='display_all_goods_for_printer'),
    path('products/',products, name='products'),
    path('update_one_product/<str:id_out>/',update_one_product,name="update_one_product"),
    path('generate_xlsx_file_for_printer/',generate_xlsx_file_for_printer, name='generate_xlsx_file_for_printer'),
    path('create_or_change_printer_code_for_product/',create_or_change_printer_code_for_product, name='create_or_change_printer_code_for_product'),
    path('change_printer_file_location',change_printer_file_location,name='change_printer_file_location'),


    ##DREAMKAS INVOICES
    path('invoices/', invoices, name="invoices"),
    path('dreamkas_invoice/<int:invoiceid>/', dreamkas_invoice, name="dreamkas_invoice"),
    path('invoices_update/', invoices_update, name="invoices_update"),
    path('create_pricing_order/', create_pricing_order, name="create_pricing_order"),
    path('paid_update/', paid_update, name="paid_update"),
    path('find_invoice_duplicates/',find_invoice_duplicates,name="find_invoice_duplicates"),
    ##DREAMKAS RELATED
    path('suppliers/', dreamkas_suppliers, name="dreamkas_suppliers"),
    path('dreamkas_supplier/<str:supplier_data>', dreamkas_supplier, name="dreamkas_supplier"),
    path('supplier_paymenttime_update/', supplier_paymenttime_update, name="supplier_paymenttime_update"),
    path('good_groups_user_form/', good_groups_user_form, name="good_groups_user_form"),
    path('test_union/', test_union, name="test_union"),
    path('delete_all_suppliers/',delete_all_suppliers, name="delete_all_suppliers"),
    path('delete_broken_suppliers/',delete_broken_suppliers, name="delete_broken_suppliers"),
    path('update_all_suppliers/',update_all_suppliers, name="delete_all_suppliers"),

    path('preset/', Preset.as_view(), name="preset"),
    path('update_item_group/', update_item_group, name="update_item_group"),
    path('edit_existing_report/', edit_existing_report, name="edit_existing_report"),

    path('inventory_check/<int:inventory_check_id>/', inventory_check, name="inventory_check"),
    path('inventory_checks/', inventory_checks, name="inventory_checks"),
    path('merge_inventory_check_items/<int:inventory_check_id>/', merge_inventory_check_items, name="merge_inventory_check_items"),
    path('update_inventory_check/<int:inventory_check_id>/', update_inventory_check, name="update_inventory_check"),

    ## DIADOC
    path('invoices_diadoc/', invoices_diadoc, name="invoices_diadoc"),
    path('invoices_diadoc_update/', update_diadoc_invoices, name="invoices_diadoc_update"),
    path('create_document_from_diadoc/', create_document_from_diadoc, name="create_document_from_diadoc"),

    ## GMAIL
    path('gmail_messages/', gmail_messages, name="gmail_messages"),
    path('gmail_all_messages/', get_all_gmail_messages, name="gmail_all_messages"),
    path('update_gmail_invoices/', update_gmail_messages, name="update_gmail_messages"),
    path('create_documents_from_gmail_message/', create_documents_from_gmail_message, name="create_documents_from_gmail_message"),
    path('show_excel_document/', show_excel_document, name="show_excel_document"),

    ## INDEX PAGE
    path('hide_invoice/', hide_invoice,  name="hide_invoice"),

    # create_document_from_diadoc

    # re_path(r'^sitemap1-(?P<section>.+).xml$', {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap')
]
