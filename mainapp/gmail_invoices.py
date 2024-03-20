import datetime

import pandas
import os
import json
import simplegmail

from barcodenumber import check_code
from simplegmail.query import construct_query

from dremkas.settings import DREAM_KAS_API
from mainapp.models import PresetGmail, Store, Gmail_Messages

nds = ["0%", "10%", "20%", "30%", "Без НДС"]
amount_type = ["шт", "шт.", "штук", "упак.", "упак", "кг", "гр", "г"]


def check_gmail_invoice_original(filepath):
    try:
        file = pandas.read_excel(filepath)
        return 1  # Can open file, file is good

    except Exception as ex:
        return 0  # Cannot open file, file is bad


def open_document_as_data_dict(document_path):
    pandas_document = pandas.read_excel(document_path, keep_default_na=False).transpose()
    return pandas_document


def get_gmail_messages(client_secret_json, days=14):
    gmail = simplegmail.Gmail(client_secret_file=client_secret_json)
    query_params = {
        "newer_than": (days, "day")
    }
    result = gmail.get_messages(query=construct_query(query_params))
    return result

    # Create_dreamkas_document_from_excel


def update_gmail_messages(client_secret_json):
    if not client_secret_json:
        print('error, client secret == none')
    companies_list = []
    for preset in PresetGmail.objects.all():
        if preset.supplier_mail:
            companies_list.append(preset)

    messages = get_gmail_messages(client_secret_json)
    for message in messages:
        message_id = message.headers.get('Message-Id') or message.headers.get('Message-ID')
        if message_id:
            message_id = message_id.replace('<', '').replace('>', '')
        else:
            return "Error, can't get message_id"
        message_sender = message.sender.split('<')[1].replace('>','')
        valid_presets = get_prerequisites_for_a_message(message)
        message_date = message.date
        message_store = Store.objects.get(gmail_client_secret=client_secret_json).store_id
        message_name = message.subject
        print(valid_presets)
        if valid_presets.__len__() == 0:
            print('len = 0')
            Gmail_Messages.objects.update_or_create(
                message_id=message_id,
                message_date_str=message_date,
                message_sender_display='Необработанное сообщение',
                message_store_id=message_store,
                message_sender=message_sender,
                message_name=message_name)
        else:
            print('len != 0')
            Gmail_Messages.objects.update_or_create(
                message_id=message_id,
                message_date=datetime.datetime.strptime(message_date, valid_presets[0].supplier_time_format),
                message_sender_display=valid_presets[0].supplier_fk.supplier_name_set.first().name,
                message_store_id=message_store,
                message_sender=message_sender,
                message_name=message_name
            )


def get_prerequisites_for_a_message(message):
    message_sender = message.sender.split('<')[1].replace('>','')
    print('msg sender' , message_sender)
    valid_presets = PresetGmail.objects.filter(supplier_mail=message_sender)
    valid_preset_list = []
    for preset in valid_presets:
        attributes = ['supplier_inn', 'document_store_destination', 'supplier_fk', 'product_name_col', 'product_sum_col','product_amount_col']
        exit_outer_loop = False
        for attr in attributes:
            if getattr(preset, attr) is None:
                exit_outer_loop = True
                break
        if exit_outer_loop:
            continue
        valid_preset_list.append(preset)
    return valid_preset_list


def replace_month_to_number(input):
    MONTHS = [("январь", "01"), ("января", "01"),
              ("февраль", "02"), ("февраля", "02"),
              ("март", "03"), ("марта", "03"),
              ("апрель", "04"), ("апреля", "04"),
              ("май", "05"), ("мая", "05"),
              ("июнь", "06"), ("июня", "06"),
              ("июль", "07"), ("июля", "07"),
              ("август", "08"), ("августа", "08"),
              ("сентябрь", "09"), ("сентября", "09"),
              ("октябрь", "10"), ("октября", "10"),
              ("ноябрь", "11"), ("ноября", "11"),
              ("декабрь", "12"), ("декабря", "12")]
    for item in MONTHS:
        if input == item[0]:
            return item[1]


def create_document_from_excel(document_path):
    document_date = None
    try:
        pandas_document = pandas.read_excel(document_path, keep_default_na=False, header=None).transpose()
    except Exception as Ex:
        print(Ex)
        print("Failed to open" + r"media/gmail_suppliers/")
        return
    for file in os.listdir("media/gmail_suppliers"):
        try:
            with open(r"media/gmail_suppliers/" + file, encoding='ascii') as f:
                company = json.load(f)
        except Exception as Ex:
            print(Ex)
            print("Failed to open " + r"media/gmail_suppliers/" + file + "as JSON")
            continue

        try:
            if company["company_unique_information"] in str(pandas_document.iloc[company["company_unique_information_row"], company["company_unique_information_col"]]):
                partnerid = DREAM_KAS_API.search_partner_id_by_inn(company["company_inn"])

                try:
                    if company["document_non_regular_number"] == True:
                        document_number = eval(company["document_non_regular_number_instructions"])
                    else:
                        document_number = pandas_document.iloc[company["document_number_row"], company["document_number_col"]]
                except Exception as ex:
                    print(ex)
                    print("Что-то пошло не так при получении номера документа. Документ будет проименован как 000-000")
                    document_number = "000-000"
                try:
                    if company["document_date_col"] is not None and company["document_date_row"] is not None and company["document_non_regular_date"] is not True:
                        document_date = datetime.datetime.strptime(pandas_document.iloc[company["document_date_row"], company["document_date_col"]], company["document_date_format"]).date().strftime(
                            "%Y-%m-%d")
                    else:
                        document_date = eval(company["document_non_regular_date_instructions"])
                except Exception as ex:
                    print(ex)
                    print("SOMETHING GONE WRONG WHEN GETTING A DATE")

                if document_date == None:
                    print("Date None. Default will be set by Dreamkas which is date of creation of document in dreamkas.")
                conditions = 0
                prefix = company["company_prefix"]
                resulting_good = None
                goods_list = []
                resulting_goods_list = []
                product_name = None
                product_code = None
                product_amount_type = None
                product_nds = None
                product_amount = None
                product_sum = None
                product_code_priority = 0
                # 0 - default
                # 1 - name
                try:
                    product_code_priority = company['product_code_priority']
                except:
                    pass
                if company["product_name_row"] is not None:
                    conditions = conditions + 1
                if company["product_code_row"] is not None:
                    conditions = conditions + 1
                if company["product_amount_type_row"] is not None:
                    conditions = conditions + 1
                if company["product_amount_row"] is not None:
                    conditions = conditions + 1
                if company["product_nds_row"] is not None:
                    conditions = conditions + 1
                if company["product_sum_row"] is not None:
                    conditions = conditions + 1
                    print("a")
                for i in range(len(pandas_document.columns)):
                    try:
                        met_conditions = 0
                        if company["product_name_row"] is not None:
                            product_name = str(pandas_document.iloc[company["product_name_row"], i])
                            met_conditions = met_conditions + 1
                        if company["product_code_row"] is not None:
                            product_code = str(pandas_document.iloc[company["product_code_row"], i])
                            met_conditions = met_conditions + 1
                        if company["product_amount_type_row"] is not None:
                            product_amount_type = str(pandas_document.iloc[company["product_amount_type_row"], i])
                            if product_amount_type in amount_type:
                                met_conditions = met_conditions + 1
                        if company["product_amount_row"] is not None:
                            product_amount = float(pandas_document.iloc[company["product_amount_row"], i])
                            met_conditions = met_conditions + 1
                        if company["product_nds_row"] is not None:
                            product_nds = str(pandas_document.iloc[company["product_nds_row"], i])
                            if product_nds in nds:
                                met_conditions = met_conditions + 1
                        if company["product_sum_row"] is not None:
                            product_sum = float(pandas_document.iloc[company["product_sum_row"], i])
                            met_conditions = met_conditions + 1
                        if met_conditions == conditions:
                            if product_name is not None:
                                print("Товар: " + product_name)
                            if product_code is not None:
                                print("Код: " + product_code)
                            print("Кол-во: " + str(product_amount))
                            print("Сумма: " + str(product_sum))
                            good = {
                                "product_name": product_name,
                                "product_code": product_code if product_code is not None else None,
                                "product_amount": product_amount,
                                "product_sum": product_sum

                            }
                            goods_list.append(good)

                        # if product_name != '' and product_code != '' and product_amount is not None and product_sum is not None:
                        #     print("Товар: " + product_name)
                        #     print("Код: " + product_code)
                        #     print("Кол-во: " + str(product_amount))
                        #     print("Сумма: " + str(product_sum))

                    except Exception as ex:
                        continue
                if goods_list == []:
                    print("0 goods error")
                    continue
                for good in goods_list:
                    resulting_good = DREAM_KAS_API.search_goods_gmail(
                        prefix=company["company_prefix"],
                        product_name=good["product_name"],
                        product_code=good["product_code"],
                        product_amount=good["product_amount"],
                        product_sum=good["product_sum"],
                        priority=product_code_priority)
                    resulting_goods_list.append(resulting_good)
                    print(resulting_good)
                print(resulting_goods_list)
                result_data = {
                    "partnerid": partnerid,
                    "document_number": document_number,
                    "document_date": document_date,
                    "resulting_goods_list": resulting_goods_list
                }
                return result_data
            else:
                print("Cannot match document to format of this iteration of company's instructions")
                print("В документе зачастую есть уникальная информация о поставщике. Либо не так указано либо не нашло")
                continue
        except Exception as ex:
            print(ex)

# def find_excel_supplier(document):
#         for company in compan
#         ies_list:
#               if company[1] in document.iloc[company[2],company[3]].

#         return 0
