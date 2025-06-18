import pandas as pd
import datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side
from mainapp.models import Invoice_v3, Supplier_name
from mainapp.Dreamkas_documents.fetch_document_object import fetch_document_object

def invoice_report_range_of_dates(date_from, date_to):
    # Convert string dates to datetime objects if they are strings
    if isinstance(date_from, str):
        date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
    if isinstance(date_to, str):
        date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
        
    current_date = date_from
    invoice_groups = []
    while current_date <= date_to:
        invoice_groups.append({"date": current_date, "invoices": invoice_report(current_date)})
        current_date += datetime.timedelta(days=1)
    invoices_concat = []
    for invoice_group in invoice_groups:
        total_sum = 0
        total_profit = 0
        flag_unpriced_invoices = False
        for invoice in invoice_group["invoices"]:
            total_sum += invoice.totalSum
            if invoice.profit != None:
                total_profit += invoice.profit
            else:
                flag_unpriced_invoices = True
        invoice_group["total_sum"] = total_sum
        invoice_group["total_profit"] = total_profit
        invoice_group["flag_unpriced_invoices"] = flag_unpriced_invoices
        invoice_group["count"] = invoice_group["invoices"].__len__()
        invoices_concat.append(invoice_group)
    return invoices_concat
        
        


def invoice_report(date_for_report):
    if not date_for_report or date_for_report == "":
        date_for_report = datetime.date.today()
    invoices = Invoice_v3.objects.filter(flag_status=1, acceptedAt=date_for_report)
    for i, invoice in enumerate(invoices, start=1):
        if invoice.latest_iteration_id is None:
            invoice.flag_invalid = True
            invoice.flag_invalid_reason = "Нету последней итерации"
            invoice.save()
        if invoice.latest_iteration_id != invoice.dreamkas_id and invoice.latest_iteration_id is not None:
            invoice = fetch_document_object(invoice.latest_iteration_id)

        supplier_name = None
        if invoice.supplier_fk != None:
            supplier_name = invoice.supplier_fk.name
        if supplier_name == "" or supplier_name == None:
            supplier_name = Supplier_name.objects.filter(supplier_fk=invoice.supplier_fk).first().name
        if supplier_name == "" or supplier_name == None:
            supplier_name = "Неизвестный поставщик"
        invoice.supplier = supplier_name
    return invoices
def create_invoice_report(date=datetime.date.today()):
    invoices = Invoice_v3.objects.filter(flag_status=1, acceptedAt=date)

    # Prepare data for the DataFrame
    data = []
    for i, invoice in enumerate(invoices, start=1):
        if invoice.latest_iteration_id != invoice.dreamkas_id:
            invoice = fetch_document_object(invoice.latest_iteration_id)
        supplier_name = invoice.supplier_fk.name
        if supplier_name == "" or supplier_name == None:
            supplier_name = Supplier_name.objects.filter(supplier_fk=invoice.supplier_fk).first().name
        if supplier_name == "" or supplier_name == None:
            supplier_name = "Неизвестный поставщик"
        
        # Append the required information to the data list
        data.append([i, supplier_name, invoice.number, invoice.totalSum, invoice.profit])

    # Create a DataFrame
    df = pd.DataFrame(data, columns=["№", "Организация", "Номер накладной", "Сумма", "Прибыль"])

    # Calculate total sums and profits
    total_sum = df['Сумма'].sum()
    total_profit = df['Прибыль'].sum()

    # Append the totals to the DataFrame
    totals = pd.DataFrame([['Итого', '', '', total_sum, total_profit]], columns=["№", "Организация", "Номер накладной", "Сумма", "Прибыль"])
    df = pd.concat([df, totals], ignore_index=True)

    # Create an Excel writer object
    with pd.ExcelWriter('invoice_report.xlsx', engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')
        
        # Access the workbook and the sheet
        workbook = writer.book
        worksheet = writer.sheets['Invoices']
        
        # Set the title with the new date format
        formatted_date = date.strftime("%d %m %Y")  # Change date format to d m y
        title = f"Опись принятых накладных за {formatted_date}"
        worksheet.insert_rows(1)
        worksheet.merge_cells('A1:E1')
        worksheet['A1'] = title
        worksheet['A1'].alignment = Alignment(horizontal='center', vertical='center')
        
        # Set the row height for the title
        worksheet.row_dimensions[1].height = 30
        
        # Set the column widths
        worksheet.column_dimensions['A'].width = 5
        worksheet.column_dimensions['B'].width = 30
        worksheet.column_dimensions['C'].width = 20
        worksheet.column_dimensions['D'].width = 15
        worksheet.column_dimensions['E'].width = 15
        
        # Add borders to the table
        thin_border = Border(left=Side(style='thin'), 
                            right=Side(style='thin'), 
                            top=Side(style='thin'), 
                            bottom=Side(style='thin'))
        
        # Adjust the range to include the last row of the data and the totals row
        for row in worksheet.iter_rows(min_row=2, max_row=len(data) + 3, min_col=1, max_col=5):
            for cell in row:
                cell.border = thin_border
        
        # Set the title row to bold
        for cell in worksheet[2]:
            cell.font = cell.font.copy(bold=True)

        # Set the totals row to bold
        for cell in worksheet[len(data) + 2]:  # Adjusting for the totals row
            cell.font = cell.font.copy(bold=True)

        # Adjust the page setup for A4
        worksheet.page_setup.paperSize = worksheet.PAPERSIZE_A4
        worksheet.page_setup.orientation = worksheet.ORIENTATION_LANDSCAPE
        worksheet.page_setup.fitToPage = True
        worksheet.page_setup.fitToHeight = 1
        worksheet.page_setup.fitToWidth = 1