from datetime import datetime,timedelta,date
from decimal import ROUND_UP, Decimal
import time
from django.utils import timezone
from dremkas.settings import DREAM_KAS_API
from mainapp import global_var
from mainapp.Dreamkas_documents.correction_invoice import update_correction_invoice, update_correction_invoices

from mainapp.Dreamkas_documents.draft_cleanup import flag_deleted_drafts
from mainapp.Dreamkas_documents.funcs import find_latest_document_iteration, fetch_document_object
from mainapp.Dreamkas_documents.pricing_orders import create_blank_pricing_if_not_priced_for_long, update_pricing_order, update_pricing_orders
from mainapp.Dreamkas_documents.update_invoices import define_if_document_is_invalid, define_if_invalid_document_was_fixed, update_invoice, update_invoices
from mainapp.logging_utils import log_item
from mainapp.models import Invoice_v3, Position_invoice_v3, Product, Pricing_order_v3
import pandas as pd
def invoice_update(invoice_limit,acceptedAtFrom,acceptedAtTo,query):
    if invoice_limit > 1000:
        id_list_inv_total = []
        offset = 0
        while offset < invoice_limit:
            status_inv, id_list_inv = update_invoices(limit=1000,acceptedAtFrom=acceptedAtFrom,accetpedAtTo=acceptedAtTo, offset=offset,query=query)
            offset = offset + 1000
            id_list_inv_total = id_list_inv_total + id_list_inv
        id_list_inv = id_list_inv_total
    else:
        status_inv, id_list_inv = update_invoices(limit=invoice_limit,acceptedAtFrom=acceptedAtFrom,accetpedAtTo=acceptedAtTo,query=query)
    return status_inv, id_list_inv
def pricing_update(pricing_order_limit,acceptedAtFrom,acceptedAtTo,query):
    if pricing_order_limit > 1000:
        id_list_pricing_total = []
        offset = 0
        while offset < pricing_order_limit:
            status_pricing, id_list_pricing = update_pricing_orders(limit=1000,acceptedAtFrom=acceptedAtFrom,accetpedAtTo=acceptedAtTo, offset=offset,query=query)
            offset = offset + 1000
            id_list_pricing_total = id_list_pricing_total + id_list_pricing
        id_list_pricing = id_list_pricing_total
    else:
        status_pricing, id_list_pricing = update_pricing_orders(limit=pricing_order_limit,acceptedAtFrom=acceptedAtFrom,accetpedAtTo=acceptedAtTo,query=query)
    return status_pricing, id_list_pricing
def correction_update(correction_invoice_limit,acceptedAtFrom,acceptedAtTo,query):
    if correction_invoice_limit > 1000:
        id_list_correction_total = []
        offset = 0
        while offset < correction_invoice_limit:
            status_correction, id_list_correction = update_correction_invoices(limit=1000,acceptedAtFrom=acceptedAtFrom,accetpedAtTo=acceptedAtTo, offset=offset,query=query)
            offset = offset + 1000
            id_list_correction_total = id_list_correction_total + id_list_correction
        id_list_correction = id_list_correction_total
    else:
        status_correction, id_list_correction = update_correction_invoices(limit=correction_invoice_limit,acceptedAtFrom=acceptedAtFrom,accetpedAtTo=acceptedAtTo,query=query)
    return status_correction, id_list_correction


def update_document(dreamkas_id):
    document = DREAM_KAS_API.get_document(dreamkas_id)
    if document is False:
        document = fetch_document_object(dreamkas_id)
        if document is None:
            return
        document.flag_status = 2
        document.save()
        return
    if document['type'] == 'INCOME_INVOICE':
        update_invoice(dreamkas_id,document_external=document)
    elif document['type'] == 'PRICING_ORDER':
        update_pricing_order(dreamkas_id)
    elif document['type'] == 'INCOME_INVOICE_CORRECTION':
        update_correction_invoice(dreamkas_id)
def update_documents(
                    invoices=True,
                     pricing_orders=True,
                     correction_invoices=True,
                     invoice_limit=100,
                     pricing_order_limit=100,
                     correction_invoice_limit=100,
                     acceptedAtFrom=None,
                     acceptedAtTo=None,
                     blanks=True,
                     find_latest_iterations=True,
                     query=None,
                     to_calculate_profit=True,
                     to_fetch_unpriced_invoices=True,
                     to_check_for_fixed_documents=True,
                     ):
    log_item(f'Updating_invoices, params: {invoices}, {pricing_orders}, {correction_invoices}, {invoice_limit}, {pricing_order_limit}, {correction_invoice_limit}, {acceptedAtFrom}, {acceptedAtTo}, {blanks}, {find_latest_iterations}, {query}, {to_calculate_profit}, {to_fetch_unpriced_invoices}')
    try:
        from mainapp.Dreamkas_documents.funcs import calculate_profit
        from mainapp.models import Correction_invoice_v3,Invoice_v3
        if to_check_for_fixed_documents == True:
            invalid_invoices = Invoice_v3.objects.filter(flag_invalid=True).values('dreamkas_id')
            invalid_correction_invoices = Correction_invoice_v3.objects.filter(flag_invalid=True).values('dreamkas_id')
            documents = invalid_invoices.union(invalid_correction_invoices)
            for document in documents:
                update_document(document['dreamkas_id'])
                define_if_invalid_document_was_fixed(document['dreamkas_id'])
        id_list_inv = []
        id_list_pricing = []
        id_list_correction = []
        if invoices == True:
            status_inv, id_list_inv = invoice_update(invoice_limit,acceptedAtFrom,acceptedAtTo,query)
        if pricing_orders == True:
            status_pricing, id_list_pricing = pricing_update(pricing_order_limit,acceptedAtFrom,acceptedAtTo,query)
        if correction_invoices == True:
            status_correction, id_list_correction = correction_update(correction_invoice_limit,acceptedAtFrom,acceptedAtTo,query)
        inv_and_corr_ids = id_list_inv + id_list_correction
        for id in inv_and_corr_ids:
            define_if_document_is_invalid(id)
            define_if_invalid_document_was_fixed(id)
        if find_latest_iterations == True:
            for id in inv_and_corr_ids:
                find_latest_document_iteration(id)
            for obj in Invoice_v3.objects.filter(latest_iteration_id=None):
                find_latest_document_iteration(obj.dreamkas_id)
        if blanks == True:
            for id in inv_and_corr_ids:
                res_status,res_info = create_blank_pricing_if_not_priced_for_long(id)
                if res_status == 2:
                    update_documents(
                            invoices=True,
                            pricing_orders=True,
                            correction_invoices=True,
                            invoice_limit=10,
                            pricing_order_limit=10,
                            correction_invoice_limit=10,
                            acceptedAtFrom=datetime.strptime(res_info['acceptedAt'], '%Y-%m-%d'),
                            acceptedAtTo=datetime.strptime(res_info['acceptedAt'], '%Y-%m-%d') + timedelta(days=1),
                            blanks=False,
                            query=res_info['num']
                            )
                    res_status,res_info = create_blank_pricing_if_not_priced_for_long(id)
            for document in Invoice_v3.objects.filter(
                flag_status=1,
                latest_pricing_id=None,
                acceptedAt__lte=datetime.now() - timedelta(days=1),
                flag_invalid=False):
                res_status,res_info = create_blank_pricing_if_not_priced_for_long(document.dreamkas_id)
        if to_calculate_profit == True:
            for id in id_list_inv:
                if str(id) == "87062856":
                    print("DEBUG")
                if Invoice_v3.objects.filter(dreamkas_id=id).first().flag_status == 0:
                    continue
                if Invoice_v3.objects.filter(dreamkas_id=id).first().flag_invalid is True:
                    if Invoice_v3.objects.filter(dreamkas_id=id).first().flag_invalid_fixed is False:
                        continue
                id = fetch_document_object(id).latest_iteration_id
                res_status,res_info = calculate_profit(id)
            for id in id_list_correction:
                res_status,res_info = calculate_profit(id)
        if to_fetch_unpriced_invoices == True:
            queryset1 =  Invoice_v3.objects.filter(latest_pricing_id=None,flag_status=1,flag_hide=False, flag_invalid=False)
            queryset2 =  Invoice_v3.objects.filter(profit=None,flag_status=1,flag_hide=False, flag_invalid=False)
            unpriced_invoices = queryset1.union(queryset2)
            for invoice in unpriced_invoices:
                if invoice.dreamkas_id == "87062856":
                    print("DEBUG")
                update_invoice(invoice.dreamkas_id)
                if invoice.latest_pricing_id is None:
                    res_status,res_info = create_blank_pricing_if_not_priced_for_long(invoice.dreamkas_id)
                calculate_profit(invoice.dreamkas_id)
            queryset1 =  Invoice_v3.objects.filter(latest_pricing_id=None,flag_status=1,flag_hide=False, flag_invalid=False)
            queryset2 =  Invoice_v3.objects.filter(profit=None,flag_status=1,flag_hide=False, flag_invalid=False)
            unpriced_invoices = queryset1.union(queryset2)
            for invoice in unpriced_invoices:
                log_item(f'Unable to price invoice: https://kabinet.dreamkas.ru/app/#!/documents/card~2F{invoice.dreamkas_id}')
        flag_deleted_drafts()
        return id_list_inv, id_list_pricing, id_list_correction
    except Exception as e:
        global_var.invoices_being_updated = False
        raise(e)        


    
    
