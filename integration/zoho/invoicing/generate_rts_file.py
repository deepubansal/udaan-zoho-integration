from integration.zoho import *
from openpyxl import Workbook
from datetime import datetime


excel_header = ["Date", "Order-Id", "Buyer Org Name", "Buyer Ph Num", "Buyer GSTIN", "Fulfill", "Order Line Id", "ListingId", "Product Id", "Product Title","Is A Set","Size of Set","Hsn","Cess %","Gst %","Total Units","Unit Of Measurement","Unit Price (Rs.) (Inclusive Taxes)","Invoice Id","No. of Boxes","Total weight of Boxes (Kg)","Order Notes"]

invoice_api = zoho_books.get_invoices_api()


def get_invoice_by_number(invoice_number):
    invoice = invoice_api.get_invoices({'invoice_number': invoice_number}).get_invoices()[0]
    invoice_details = invoice_api.get(invoice.invoice_id)
    return invoice_details


def get_custom_field_value(invoice, field_name, defaultValue=None):
    fields = invoice.get_custom_fields()
    for field in fields:
        if field.get_label() == field_name:
            return field.get_value()
    return defaultValue


def generate_file(invoice_number, output_path='shipping_label.xlsx'):
    book = Workbook()
    sheet = book.active
    sheet.append(excel_header)
    print("Looking for Invoice Number: {}".format(invoice_number))
    invoice = get_invoice_by_number(invoice_number)
    first = True
    for line_item in invoice.line_items:
        row = []
        row.append(datetime.strptime(invoice.get_date(), '%Y-%m-%d').strftime('%d-%b-%Y 10:00'))
        row.append(get_custom_field_value(invoice, 'Udaan Order ID', ''))
        row.append(invoice.get_customer_name())
        row.append('+91-{}'.format(invoice.get_contact_persons()[0]['mobile']))
        row.append(invoice.gst_no)
        row.append('Yes')
        item_id = 'TLHKP{0}{0}'.format(line_item.line_item_id)[:31]
        row.append(item_id)
        row.append(item_id)
        row.append(item_id)
        row.append(line_item.name)
        row.append('No')
        row.append('NA')
        row.append(line_item.get_hsn_or_sac())
        row.append(0)
        row.append(line_item.tax_percentage)
        row.append(line_item.quantity)
        row.append('Pieces')
        if str(line_item.discount).endswith('%'):
            discount_percent = float(line_item.discount[:-1])
        else:
            discount_percent = float(line_item.discount)
        discounted_rate = round((line_item.rate * (100 - discount_percent) / 100.0), 2)
        row.append(round(discounted_rate * (100 + line_item.tax_percentage) / 100.0, 2))
        row.append(invoice.invoice_number[3:])
        if first:
            first = False
            row.append(get_custom_field_value(invoice, 'No of Boxes', 1))
            row.append(get_custom_field_value(invoice, 'Total Weight', 5))
        sheet.append(row)
    book.save(home/output_path)
    return home/output_path


def generate_files(invoice_number):
    file_path_format = 'invoice_file_{}.xlsx'
    output_file = generate_file(invoice_number, file_path_format.format(invoice_number))
    return output_file
