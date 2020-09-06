from integration.zoho.core.api_helpers import create_bill
from books.model.LineItem import LineItem
from integration.zoho import *
import datetime


bills_api = zoho_books.get_bills_api()

"""

    Deprecated !
    
"""


def get_tax_id(item, spec):
    for preference in item['item_tax_preferences']:
        if preference['tax_specification'] == spec:
            return preference['tax_id']
    raise Exception("Tax ID not found")


def create_line_item(item_obj, rate, quantity, discount, tax_id=None):
    line_item = LineItem()
    line_item.set_item_id(item_obj['item_id'])
    line_item.set_rate(rate)
    line_item.set_quantity(quantity)
    line_item.set_discount(discount)
    if tax_id:
        line_item.set_tax_id(tax_id)
    return line_item


def find_vendor(company):
    all_contacts = find_all_contacts(cached=True)
    for contact in all_contacts:
        if contact['contact_name'] == company and contact['contact_type'] == 'vendor':
            return contact
    raise Exception('Contact: {} not found'.format(company))


def find_item(product_name):
    all_items = find_all_items(cached=True)
    for item in all_items:
        if item['name'] == product_name:
            return item
    raise Exception("Item: {} not found".format(product_name))


def import_invoice(s_invoice):
    vendor = find_vendor(s_invoice.Company_Name)
    line_items = []
    for item in s_invoice.line_items:
        item_obj = find_item(item.Product_Name)
        tax_id = get_tax_id(item_obj, 'intra') if vendor['gst_treatment'] != 'business_none' else None
        line_item = create_line_item(item_obj, item.Rate, item.Quantity, item.Discount, tax_id=tax_id)
        line_items.append(line_item)
    invoice_id = s_invoice.Purchase_Invoice_Id
    invoice_id = invoice_id.strftime('%Y-%m-%d') if type(invoice_id) is datetime.datetime else invoice_id
    bill = create_bill(invoice_id, vendor['contact_id'], s_invoice.Purchase_Invoice_Date, line_items)
    print(bill.to_json())
    bills_api.create(bill)

