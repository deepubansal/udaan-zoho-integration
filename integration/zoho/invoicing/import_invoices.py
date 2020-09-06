from books.model.Invoice import Invoice
from books.model.CustomField import CustomField
from books.model.LineItem import LineItem
from integration.zoho import *

invoice_api = zoho_books.get_invoices_api()

"""
    Deprecated !
"""


def create_invoice(invoice_id, customer_id, udaan_order_id, invoice_date, line_items):
    invoice = Invoice()
    invoice.set_invoice_number('RET{}'.format(invoice_id))
    invoice.set_customer_id(customer_id)
    invoice.set_date(invoice_date.strftime('%Y-%m-%d'))
    custom_field = CustomField()
    custom_field.set_label('cf_udaan_order_id')
    custom_field.set_value(udaan_order_id)
    invoice.set_custom_fields(custom_field)
    for line_item in line_items:
        invoice.set_line_items(line_item)
    return invoice


def create_line_item(item_id, rate, quantity, discount):
    line_item = LineItem()
    line_item.set_item_id(item_id)
    line_item.set_rate(rate)
    line_item.set_quantity(quantity)
    line_item.set_discount('{}%'.format(discount))
    return line_item


def find_customer_id(company, phone):
    all_customers = find_all_contacts(cached=True)
    for customer in all_customers:
        if customer['contact_name'] == '{} ({})'.format(company, phone):
            return customer['contact_id']
    raise Exception('Contact: {} ({}) not found'.format(company, phone))


def find_item_id(product_name):
    all_items = find_all_items(cached=True)
    for item in all_items:
        if item['name'] == product_name:
            return item['item_id']
    raise Exception("Item: {} not found".format(product_name))


def import_invoice(s_invoice):
    customer_id = find_customer_id(s_invoice.Company_Name, s_invoice.Phone_No)
    line_items = []
    for item in s_invoice.line_items:
        item_id = find_item_id(item.Product_Name)
        line_item = create_line_item(item_id, item.Rate, item.Quantity, item.Discount)
        line_items.append(line_item)
    invoice = create_invoice(s_invoice.Invoice_Id, customer_id, s_invoice.Udaan_Order_ID, s_invoice.Invoice_Date, line_items)
    print(invoice.to_json())
    invoice_api.create(invoice, ignore_auto_number_generation=True)
